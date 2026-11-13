import hmac
from datetime import date, timedelta
from typing import Literal, Self

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import security
from app.db import utcnow
from app.deps import DB, CurrentUser
from app.errors import AppError
from app.mailer import send_email
from app.models.user import EmailCode, Role, User

router = APIRouter(prefix="/auth", tags=["auth"])

Password = Field(min_length=10, max_length=128)
Code = Field(pattern=r"^\d{6}$")


class RegisterIn(BaseModel):
    # Field order = form order, so validation errors are listed in the order the user sees them.
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Password
    role: Literal["student", "guardian"]  # staff roles are invited by an administrator
    date_of_birth: date | None = None
    locale: Literal["en", "hi"] = "en"

    @model_validator(mode="after")
    def student_needs_date_of_birth(self) -> Self:
        if self.role == "student" and (self.date_of_birth is None or self.date_of_birth >= date.today()):
            raise ValueError("date_of_birth_required")
        return self


class EmailIn(BaseModel):
    email: EmailStr


class CodeIn(EmailIn):
    code: str = Code


class LoginIn(EmailIn):
    password: str = Field(max_length=128)


class ResetIn(CodeIn):
    new_password: str = Password


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    locale: str
    date_of_birth: date | None


class SessionOut(BaseModel):
    token: str
    expires_in: int  # seconds
    user: UserOut


def find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def _session(user: User) -> SessionOut:
    return SessionOut(
        token=security.create_token(user),
        expires_in=security.SESSION_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


def issue_code(db: Session, user: User, purpose: str) -> None:
    recent = db.scalar(
        select(func.count())
        .select_from(EmailCode)
        .where(EmailCode.user_id == user.id, EmailCode.created_at > utcnow() - timedelta(hours=1))
    )
    if recent >= security.CODES_PER_HOUR:
        raise AppError(429, "too_many_codes")
    code = security.make_code()
    db.add(
        EmailCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=security.hash_code(code, user.id, purpose),
            expires_at=utcnow() + timedelta(minutes=security.CODE_MINUTES),
        )
    )
    send_email(db, user.email, user.locale, purpose, code=code)


def consume_code(db: Session, user: User | None, purpose: str, code: str) -> None:
    row = user and db.scalar(
        select(EmailCode)
        .where(EmailCode.user_id == user.id, EmailCode.purpose == purpose, EmailCode.consumed_at.is_(None))
        .order_by(EmailCode.id.desc())
    )
    if not row:
        raise AppError(400, "code_invalid")
    if row.expires_at < utcnow():
        raise AppError(400, "code_expired")
    if row.attempts >= security.CODE_MAX_ATTEMPTS:
        raise AppError(400, "code_locked")
    if not hmac.compare_digest(row.code_hash, security.hash_code(code, user.id, purpose)):
        row.attempts += 1
        db.commit()  # the failed attempt must survive the error response
        raise AppError(400, "code_invalid")
    row.consumed_at = utcnow()


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: DB):
    """Same response whether or not the email is known, so accounts cannot be enumerated."""
    user = find_user(db, body.email)
    self_registered = user and user.role in (Role.student, Role.guardian)
    if user and (user.email_verified_at or not self_registered):
        send_email(db, user.email, user.locale, "account_exists")
    else:
        if not user:
            user = User(email=body.email.strip().lower())
            db.add(user)
        user.full_name, user.role, user.locale = body.full_name, Role(body.role), body.locale
        user.date_of_birth = body.date_of_birth if body.role == "student" else None
        user.password_hash = security.hash_password(body.password)
        db.flush()
        issue_code(db, user, "verify")
    db.commit()
    return {"status": "code_sent"}


@router.post("/resend")
def resend(body: EmailIn, db: DB):
    user = find_user(db, body.email)
    if user and not user.email_verified_at and user.password_hash:
        issue_code(db, user, "verify")
        db.commit()
    return {"status": "code_sent"}


@router.post("/verify")
def verify(body: CodeIn, db: DB) -> SessionOut:
    user = find_user(db, body.email)
    consume_code(db, user, "verify", body.code)
    user.email_verified_at = utcnow()
    db.commit()
    return _session(user)


@router.post("/login")
def login(body: LoginIn, db: DB) -> SessionOut:
    user = find_user(db, body.email)
    if user and user.locked_until and user.locked_until > utcnow():
        raise AppError(429, "account_locked")
    if not security.verify_password(body.password, user.password_hash if user else None):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= security.LOGIN_MAX_FAILURES:
                user.failed_logins = 0
                user.locked_until = utcnow() + timedelta(minutes=security.LOCKOUT_MINUTES)
            db.commit()
        raise AppError(401, "invalid_credentials")
    if not user.is_active:
        raise AppError(403, "account_disabled")
    if not user.email_verified_at:
        raise AppError(403, "email_not_verified")
    user.failed_logins = 0
    db.commit()
    return _session(user)


@router.post("/refresh")
def refresh(user: CurrentUser) -> SessionOut:
    """Sliding session: called by the frontend on activity; an expired token cannot refresh."""
    return _session(user)


@router.post("/logout", status_code=204)
def logout(user: CurrentUser, db: DB):
    user.token_version += 1  # invalidates every token issued so far
    db.commit()


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/password/forgot")
def forgot_password(body: EmailIn, db: DB):
    user = find_user(db, body.email)
    if user and user.is_active:
        issue_code(db, user, "reset")
        db.commit()
    return {"status": "code_sent"}


@router.post("/password/reset")
def reset_password(body: ResetIn, db: DB):
    """Also how invited staff set their first password; a valid emailed code proves the address."""
    user = find_user(db, body.email)
    consume_code(db, user, "reset", body.code)
    user.password_hash = security.hash_password(body.new_password)
    user.email_verified_at = user.email_verified_at or utcnow()
    user.token_version += 1
    user.failed_logins, user.locked_until = 0, None
    db.commit()
    return {"status": "password_set"}
