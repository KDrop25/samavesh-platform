from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select

from app.deps import DB, CurrentUser, require_roles
from app.errors import AppError
from app.mailer import send_email
from app.models.user import Role, User
from app.routers.auth import find_user

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles(Role.administrator))]
)


class InviteIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["support_staff", "nodal_officer", "grievance_officer", "administrator"]


class ActiveIn(BaseModel):
    is_active: bool


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    email_verified_at: datetime | None
    created_at: datetime


@router.get("/users")
def list_users(db: DB) -> list[AdminUserOut]:
    return db.scalars(select(User).order_by(User.full_name)).all()


@router.post("/users", status_code=201)
def invite_user(body: InviteIn, db: DB) -> AdminUserOut:
    if find_user(db, body.email):
        raise AppError(409, "email_taken")
    user = User(email=body.email.strip().lower(), full_name=body.full_name, role=Role(body.role))
    db.add(user)
    send_email(db, user.email, user.locale, "invite")
    db.commit()
    return user


@router.patch("/users/{user_id}")
def set_active(user_id: int, body: ActiveIn, db: DB, admin: CurrentUser) -> AdminUserOut:
    user = db.get(User, user_id)
    if not user:
        raise AppError(404, "not_found")
    if user.id == admin.id:
        raise AppError(400, "cannot_modify_self")
    user.is_active = body.is_active
    user.token_version += 1  # signs them out everywhere
    db.commit()
    return user
