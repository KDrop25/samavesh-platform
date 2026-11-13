from datetime import date
from typing import Literal, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.deps import DB, CurrentUser, require_roles
from app.errors import AppError
from app.models.plan import ACCOMMODATION_TYPES, AccommodationPlan, PlanItem, PlanStatus, ProvisionLog, Term
from app.models.student import StudentProfile
from app.models.user import Role, User
from app.permissions import OVERSIGHT, is_assigned_staff, require_student_access, visible_student_ids
from app.routers.students import PROFILE_ROLES
from app.rules.dates import today
from app.rules.provision import is_overdue, next_due, planned_in_term

router = APIRouter(tags=["plans"], dependencies=[Depends(require_roles(*PROFILE_ROLES))])

AccommodationType = Literal[ACCOMMODATION_TYPES]  # type: ignore[valid-type]
EDITABLE = (PlanStatus.draft, PlanStatus.rejected)
# Statuses during which a plan was (or is) in force, and so count towards "planned".
IN_FORCE = (PlanStatus.approved, PlanStatus.superseded, PlanStatus.ended)


class TermIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def ends_after_start(self) -> Self:
        if self.end_date <= self.start_date:
            raise ValueError("end_date_required")
        return self


class ItemIn(BaseModel):
    type: AccommodationType
    details: str | None = Field(None, max_length=2000)
    interval_days: int | None = Field(None, ge=1, le=365)


class PlanIn(BaseModel):
    start_date: date
    review_date: date
    notes: str | None = Field(None, max_length=4000)
    items: list[ItemIn] = Field(min_length=1, max_length=len(ACCOMMODATION_TYPES))

    @model_validator(mode="after")
    def check(self) -> Self:
        if self.review_date <= self.start_date:
            raise ValueError("review_date_required")
        if len({item.type for item in self.items}) != len(self.items):
            raise ValueError("items_required")  # one entry per accommodation type
        return self


class ProvisionIn(BaseModel):
    provided_on: date
    notes: str | None = Field(None, max_length=2000)


def is_active(plan: AccommodationPlan, on: date) -> bool:
    """A plan is inactive until a nodal officer approves it, and before its start date."""
    return plan.status == PlanStatus.approved and plan.start_date <= on


def _profile(db: Session, student_id: int) -> StudentProfile:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))
    if not profile:
        raise AppError(409, "profile_required")
    return profile


def _plan_for_user(db: Session, user: User, plan_id: int) -> tuple[AccommodationPlan, int]:
    """Load a plan the user may see, with its student id. 404 if missing or not theirs."""
    row = db.execute(
        select(AccommodationPlan, StudentProfile.student_id)
        .join(StudentProfile, StudentProfile.id == AccommodationPlan.profile_id)
        .where(AccommodationPlan.id == plan_id)
    ).first()
    if not row:
        raise AppError(404, "not_found")
    require_student_access(db, user, row[1])
    return row[0], row[1]


def _require_assigned_staff(db: Session, user: User, student_id: int) -> None:
    """Plans are drafted and provisions logged by the student's assigned support staff."""
    if not is_assigned_staff(db, user, student_id):
        raise AppError(403, "forbidden")


def _set_items(db: Session, plan: AccommodationPlan, items: list[ItemIn]) -> None:
    for old in db.scalars(select(PlanItem).where(PlanItem.plan_id == plan.id)):
        db.delete(old)
    for item in items:
        db.add(PlanItem(plan_id=plan.id, type=item.type, details=item.details or None, interval_days=item.interval_days))


def _item_view(db: Session, plan: AccommodationPlan, item: PlanItem, on: date) -> dict:
    logs = db.execute(
        select(ProvisionLog, User.full_name)
        .join(User, User.id == ProvisionLog.staff_id)
        .where(ProvisionLog.plan_item_id == item.id)
        .order_by(ProvisionLog.provided_on.desc(), ProvisionLog.id.desc())
    ).all()
    last = logs[0][0].provided_on if logs else None
    active = is_active(plan, on)
    return {
        "id": item.id,
        "type": item.type,
        "details": item.details,
        "interval_days": item.interval_days,
        "last_provided_on": last,
        "next_due_on": next_due(item.interval_days, plan.start_date, last) if active else None,
        "overdue": active and is_overdue(item.interval_days, plan.start_date, last, on),
        "logs": [{"provided_on": log.provided_on, "staff_name": name, "notes": log.notes} for log, name in logs],
    }


def _plan_view(db: Session, plan: AccommodationPlan, on: date) -> dict:
    items = db.scalars(select(PlanItem).where(PlanItem.plan_id == plan.id).order_by(PlanItem.id)).all()
    return {
        "id": plan.id,
        "version": plan.version,
        "supersedes_plan_id": plan.supersedes_plan_id,
        "status": plan.status,
        "is_active": is_active(plan, on),
        "start_date": plan.start_date,
        "review_date": plan.review_date,
        "ended_on": plan.ended_on,
        "notes": plan.notes,
        "drafted_by": db.scalar(select(User.full_name).where(User.id == plan.drafted_by)),
        "submitted_at": plan.submitted_at,
        "items": [_item_view(db, plan, item, on) for item in items],
    }


# ---- Terms ----


@router.get("/terms")
def list_terms(db: DB):
    return [
        {"id": t.id, "name": t.name, "start_date": t.start_date, "end_date": t.end_date}
        for t in db.scalars(select(Term).order_by(Term.start_date.desc()))
    ]


@router.post("/terms", status_code=201, dependencies=[Depends(require_roles(Role.nodal_officer))])
def create_term(body: TermIn, db: DB):
    term = Term(**body.model_dump())
    db.add(term)
    db.commit()
    return {"id": term.id}


# ---- Plans ----


@router.get("/students/{student_id}/plans")
def list_plans(student_id: int, db: DB, user: CurrentUser):
    require_student_access(db, user, student_id)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))
    plans = (
        db.scalars(
            select(AccommodationPlan)
            .where(AccommodationPlan.profile_id == profile.id)
            .order_by(AccommodationPlan.id.desc())
        ).all()
        if profile
        else []
    )
    on = today()
    return {
        "has_profile": profile is not None,
        "can_draft": profile is not None and is_assigned_staff(db, user, student_id),
        "plans": [_plan_view(db, plan, on) for plan in plans],
    }


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: DB, user: CurrentUser):
    plan, student_id = _plan_for_user(db, user, plan_id)
    return {**_plan_view(db, plan, today()), "student_id": student_id}


@router.post("/students/{student_id}/plans", status_code=201)
def create_plan(student_id: int, body: PlanIn, db: DB, user: CurrentUser):
    require_student_access(db, user, student_id)
    _require_assigned_staff(db, user, student_id)
    plan = AccommodationPlan(
        profile_id=_profile(db, student_id).id,
        start_date=body.start_date,
        review_date=body.review_date,
        notes=body.notes or None,
        drafted_by=user.id,
    )
    db.add(plan)
    db.flush()
    _set_items(db, plan, body.items)
    db.commit()
    return {"id": plan.id}


@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, body: PlanIn, db: DB, user: CurrentUser):
    plan, student_id = _plan_for_user(db, user, plan_id)
    _require_assigned_staff(db, user, student_id)
    if plan.status not in EDITABLE:
        raise AppError(409, "plan_not_editable")  # approved plans change through a new version
    plan.start_date, plan.review_date, plan.notes = body.start_date, body.review_date, body.notes or None
    plan.status = PlanStatus.draft  # a rejected plan that is edited goes back to draft
    _set_items(db, plan, body.items)
    db.commit()
    return {"id": plan.id}


@router.post("/plans/{plan_id}/submit")
def submit_plan(plan_id: int, db: DB, user: CurrentUser):
    plan, student_id = _plan_for_user(db, user, plan_id)
    _require_assigned_staff(db, user, student_id)
    if plan.status != PlanStatus.draft:
        raise AppError(409, "plan_not_draft")
    plan.status, plan.submitted_at = PlanStatus.submitted, utcnow()
    db.commit()
    return {"status": plan.status}


# ---- Provision delivered ----


@router.post("/plan-items/{item_id}/provisions", status_code=201)
def log_provision(item_id: int, body: ProvisionIn, db: DB, user: CurrentUser):
    item = db.get(PlanItem, item_id)
    if not item:
        raise AppError(404, "not_found")
    plan, student_id = _plan_for_user(db, user, item.plan_id)
    _require_assigned_staff(db, user, student_id)
    if not is_active(plan, today()):
        raise AppError(409, "plan_not_active")  # nothing is delivered against an unapproved plan
    if not plan.start_date <= body.provided_on <= today():
        raise AppError(422, "provision_date_invalid")
    db.add(ProvisionLog(plan_item_id=item.id, provided_on=body.provided_on, staff_id=user.id, notes=body.notes or None))
    db.commit()
    return {"status": "logged"}


@router.get("/students/{student_id}/provision-summary")
def provision_summary(student_id: int, term_id: int, db: DB, user: CurrentUser):
    """Planned vs delivered for one student in one term, per accommodation."""
    require_student_access(db, user, student_id)
    term = db.get(Term, term_id)
    if not term:
        raise AppError(404, "not_found")
    profile = db.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))
    rows = []
    if profile:
        query = (
            select(AccommodationPlan, PlanItem)
            .join(PlanItem, PlanItem.plan_id == AccommodationPlan.id)
            .where(AccommodationPlan.profile_id == profile.id, AccommodationPlan.status.in_(IN_FORCE))
            .order_by(AccommodationPlan.id, PlanItem.id)
        )
        for plan, item in db.execute(query):
            if plan.start_date > term.end_date or (plan.ended_on and plan.ended_on < term.start_date):
                continue  # not in force during this term
            delivered = db.scalar(
                select(func.count())
                .select_from(ProvisionLog)
                .where(
                    ProvisionLog.plan_item_id == item.id,
                    ProvisionLog.provided_on.between(term.start_date, term.end_date),
                )
            )
            # "Planned so far" stops at today for a term still in progress.
            planned = planned_in_term(
                item.interval_days, plan.start_date, plan.ended_on, term.start_date, min(term.end_date, today())
            )
            rows.append(
                {
                    "plan_id": plan.id,
                    "plan_version": plan.version,
                    "type": item.type,
                    "interval_days": item.interval_days,
                    "planned": planned,
                    "delivered": delivered,
                    "shortfall": max(planned - delivered, 0) if planned is not None else None,
                }
            )
    return {"term": {"id": term.id, "name": term.name, "start_date": term.start_date, "end_date": term.end_date}, "rows": rows}


@router.get("/provisions/overdue", dependencies=[Depends(require_roles(Role.support_staff, *OVERSIGHT))])
def overdue_provisions(db: DB, user: CurrentUser):
    """Every active accommodation whose interval has passed without a logged provision."""
    on = today()
    ids = visible_student_ids(db, user)
    query = (
        select(AccommodationPlan, PlanItem, User)
        .join(PlanItem, PlanItem.plan_id == AccommodationPlan.id)
        .join(StudentProfile, StudentProfile.id == AccommodationPlan.profile_id)
        .join(User, User.id == StudentProfile.student_id)
        .where(
            AccommodationPlan.status == PlanStatus.approved,
            AccommodationPlan.start_date <= on,
            PlanItem.interval_days.is_not(None),
        )
        .order_by(User.full_name, PlanItem.id)
    )
    if ids is not None:
        query = query.where(User.id.in_(ids))
    rows = []
    for plan, item, student in db.execute(query):
        last = db.scalar(select(func.max(ProvisionLog.provided_on)).where(ProvisionLog.plan_item_id == item.id))
        if is_overdue(item.interval_days, plan.start_date, last, on):
            due = next_due(item.interval_days, plan.start_date, last)
            rows.append(
                {
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "plan_id": plan.id,
                    "type": item.type,
                    "interval_days": item.interval_days,
                    "last_provided_on": last,
                    "due_on": due,
                    "days_overdue": (on - due).days,
                }
            )
    return rows
