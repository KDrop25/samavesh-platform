import secrets
import time
from collections import defaultdict, deque
from datetime import date
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.deps import DB, CurrentUser, bearer, require_roles
from app.errors import AppError
from app.models.grievance import (
    GRIEVANCE_CATEGORIES,
    GRIEVANCE_STATUSES,
    TRANSITIONS,
    Grievance,
    GrievanceEvent,
    Holiday,
    Setting,
)
from app.models.user import Role, User
from app.rules.dates import LOCAL_TZ, today
from app.rules.working_days import (
    DEFAULT_ESCALATION_DAYS,
    DEFAULT_WEEKDAYS,
    escalation_due,
    working_days_between,
)
from app.security import decode_token

router = APIRouter(tags=["grievances"])
officer_only = [Depends(require_roles(Role.grievance_officer))]
admin_only = [Depends(require_roles(Role.administrator))]
settings_roles = [Depends(require_roles(Role.administrator, Role.grievance_officer))]

REFERENCE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"  # no 0/O, 1/I/L, U: easy to read aloud and type

# ponytail: in-memory sliding-window limiter, per process. Enough to slow reference guessing
# on one instance; move to the reverse proxy or Redis if the API ever runs on several.
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(key: str, limit: int, window_seconds: int) -> None:
    now, hits = time.monotonic(), _hits[key]
    while hits and hits[0] < now - window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        raise AppError(429, "too_many_requests")
    hits.append(now)


class GrievanceIn(BaseModel):
    category: Literal[GRIEVANCE_CATEGORIES]  # type: ignore[valid-type]
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    anonymous: bool = False
    complainant_name: str | None = Field(None, max_length=120)
    contact_email: EmailStr | None = None


class StatusIn(BaseModel):
    status: Literal[GRIEVANCE_STATUSES]  # type: ignore[valid-type]
    public_note: str | None = Field(None, max_length=2000)
    internal_note: str | None = Field(None, max_length=2000)


class SettingsIn(BaseModel):
    working_weekdays: list[int] = Field(min_length=1, max_length=7)
    escalation_working_days: int = Field(ge=1, le=120)

    @model_validator(mode="after")
    def valid_weekdays(self) -> Self:
        if any(day not in range(7) for day in self.working_weekdays):
            raise ValueError("working_weekdays_required")
        return self


class HolidayIn(BaseModel):
    day: date
    name: str = Field(min_length=1, max_length=120)


# ---- Settings used by the escalation rule ----


def get_setting(db: Session, key: str, default):
    value = db.scalar(select(Setting.value).where(Setting.key == key))
    return default if value is None else value


def _calendar(db: Session) -> tuple[int, set[int], set[date]]:
    limit = get_setting(db, "escalation_working_days", DEFAULT_ESCALATION_DAYS)
    weekdays = set(get_setting(db, "working_weekdays", DEFAULT_WEEKDAYS))
    return limit, weekdays, set(db.scalars(select(Holiday.day)))


def _under_review_since(db: Session, grievance_id: int) -> date | None:
    at = db.scalar(
        select(GrievanceEvent.created_at)
        .where(GrievanceEvent.grievance_id == grievance_id, GrievanceEvent.status == "under_review")
        .order_by(GrievanceEvent.id.desc())
    )
    return at.astimezone(LOCAL_TZ).date() if at else None


def flag_overdue_grievances(db: Session) -> list[Grievance]:
    """Auto-flag for escalation: under review for more than the configured number of working
    days. Run by the daily job; returns the grievances newly flagged so they can be notified."""
    limit, weekdays, holidays = _calendar(db)
    flagged = []
    query = select(Grievance).where(Grievance.status == "under_review", Grievance.escalation_flagged_at.is_(None))
    for grievance in db.scalars(query):
        since = _under_review_since(db, grievance.id)
        if since and escalation_due(since, today(), limit, weekdays, holidays):
            grievance.escalation_flagged_at = utcnow()
            flagged.append(grievance)
    return flagged


# ---- Public: submit and track without signing in ----


def _new_reference(db: Session) -> str:
    while True:
        raw = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(12))  # ~59 bits
        reference = f"GRV-{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        if not db.scalar(select(Grievance.id).where(Grievance.reference == reference)):
            return reference


@router.post("/grievances", status_code=201)
def submit_grievance(
    body: GrievanceIn, db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    """Open to everyone. Anonymous means anonymous: no account link, no name, no IP address.
    The tracking reference returned here is then the only way back to the case."""
    _rate_limit("submit", limit=30, window_seconds=60)
    claims = decode_token(creds.credentials) if creds else None
    user = db.get(User, int(claims["sub"])) if claims else None

    grievance = Grievance(
        reference=_new_reference(db),
        is_anonymous=body.anonymous,
        category=body.category,
        subject=body.subject,
        description=body.description,
        contact_email=body.contact_email and body.contact_email.strip().lower(),
    )
    if not body.anonymous:
        name = (body.complainant_name or "").strip() or (user.full_name if user else "")
        if not name:
            raise AppError(422, "name_required")
        grievance.complainant_name = name
        if user:
            grievance.complainant_user_id = user.id
            grievance.contact_email = grievance.contact_email or user.email

    # The audit trail must not reveal who complained, so the actor is never a user id here.
    db.info["actor"] = (None, "complainant")
    db.add(grievance)
    db.flush()
    db.add(GrievanceEvent(grievance_id=grievance.id, status="received"))
    db.commit()
    return {"reference": grievance.reference}


@router.get("/grievances/track/{reference}")
def track_grievance(reference: str, request: Request, db: DB):
    """Status check with only the tracking reference. Shows status, the time of every status
    change and the officer's public notes - never the complaint text or any identity."""
    _rate_limit(f"track:{request.client.host if request.client else ''}", limit=20, window_seconds=60)
    grievance = db.scalar(select(Grievance).where(Grievance.reference == reference.strip().upper()))
    if not grievance:
        raise AppError(404, "reference_not_found")
    events = db.scalars(
        select(GrievanceEvent).where(GrievanceEvent.grievance_id == grievance.id).order_by(GrievanceEvent.id)
    )
    return {
        "reference": grievance.reference,
        "category": grievance.category,
        "status": grievance.status,
        "events": [{"status": e.status, "at": e.created_at, "public_note": e.public_note} for e in events],
    }


# ---- Grievance officer: the only role that sees who complained ----


def _events(db: Session, grievance_id: int, internal: bool) -> list[dict]:
    rows = db.execute(
        select(GrievanceEvent, User.full_name)
        .outerjoin(User, User.id == GrievanceEvent.actor_id)
        .where(GrievanceEvent.grievance_id == grievance_id)
        .order_by(GrievanceEvent.id)
    ).all()
    return [
        {
            "status": event.status,
            "at": event.created_at,
            "public_note": event.public_note,
            **({"internal_note": event.internal_note, "officer": name} if internal else {}),
        }
        for event, name in rows
    ]


def _case(db: Session, grievance: Grievance, limit: int, weekdays: set[int], holidays: set[date]) -> dict:
    """Case fields that carry no identity - safe for the administrator's escalated view."""
    since = _under_review_since(db, grievance.id) if grievance.status == "under_review" else None
    return {
        "id": grievance.id,
        "reference": grievance.reference,
        "category": grievance.category,
        "subject": grievance.subject,
        "description": grievance.description,
        "status": grievance.status,
        "received_at": grievance.created_at,
        "working_days_under_review": working_days_between(since, today(), weekdays, holidays) if since else None,
        "escalation_limit": limit,
        "escalation_flagged": grievance.escalation_flagged_at is not None,
    }


@router.get("/grievances", dependencies=officer_only)
def list_grievances(db: DB):
    calendar = _calendar(db)
    rows = db.scalars(select(Grievance).order_by(Grievance.id.desc())).all()
    return [{**_case(db, g, *calendar), "is_anonymous": g.is_anonymous} for g in rows]


@router.get("/grievances/escalated", dependencies=admin_only)
def escalated_grievances(db: DB):
    """Administrator's view of escalated or auto-flagged cases: content and timeline only."""
    calendar = _calendar(db)
    query = (
        select(Grievance)
        .where((Grievance.status == "escalated") | Grievance.escalation_flagged_at.is_not(None))
        .order_by(Grievance.id.desc())
    )
    return [{**_case(db, g, *calendar), "events": _events(db, g.id, internal=False)} for g in db.scalars(query)]


@router.get("/grievances/{grievance_id}", dependencies=officer_only)
def get_grievance(grievance_id: int, db: DB):
    grievance = db.get(Grievance, grievance_id)
    if not grievance:
        raise AppError(404, "not_found")
    return {
        **_case(db, grievance, *_calendar(db)),
        "is_anonymous": grievance.is_anonymous,
        "complainant_name": grievance.complainant_name,
        "contact_email": grievance.contact_email,
        "has_account": grievance.complainant_user_id is not None,
        "next_statuses": TRANSITIONS[grievance.status],
        "events": _events(db, grievance.id, internal=True),
    }


@router.post("/grievances/{grievance_id}/status", dependencies=officer_only)
def change_status(grievance_id: int, body: StatusIn, db: DB, user: CurrentUser):
    grievance = db.get(Grievance, grievance_id)
    if not grievance:
        raise AppError(404, "not_found")
    if body.status not in TRANSITIONS[grievance.status]:
        raise AppError(409, "invalid_transition")
    grievance.status = body.status
    db.add(
        GrievanceEvent(
            grievance_id=grievance.id,
            status=body.status,
            public_note=(body.public_note or "").strip() or None,
            internal_note=(body.internal_note or "").strip() or None,
            actor_id=user.id,
        )
    )
    db.commit()
    return {"status": grievance.status}


# ---- Escalation settings and holidays ----


@router.get("/settings", dependencies=settings_roles)
def read_settings(db: DB):
    limit, weekdays, _ = _calendar(db)
    holidays = db.scalars(select(Holiday).order_by(Holiday.day)).all()
    return {
        "working_weekdays": sorted(weekdays),
        "escalation_working_days": limit,
        "holidays": [{"id": h.id, "day": h.day, "name": h.name} for h in holidays],
    }


@router.put("/settings", dependencies=settings_roles)
def save_settings(body: SettingsIn, db: DB):
    for key, value in (
        ("working_weekdays", sorted(set(body.working_weekdays))),
        ("escalation_working_days", body.escalation_working_days),
    ):
        row = db.scalar(select(Setting).where(Setting.key == key))
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    return {"status": "saved"}


@router.post("/holidays", status_code=201, dependencies=settings_roles)
def add_holiday(body: HolidayIn, db: DB):
    if db.scalar(select(Holiday.id).where(Holiday.day == body.day)):
        raise AppError(409, "holiday_exists")
    db.add(Holiday(day=body.day, name=body.name))
    db.commit()
    return {"status": "added"}


@router.delete("/holidays/{holiday_id}", status_code=204, dependencies=settings_roles)
def remove_holiday(holiday_id: int, db: DB):
    holiday = db.get(Holiday, holiday_id)
    if not holiday:
        raise AppError(404, "not_found")
    db.delete(holiday)
    db.commit()
