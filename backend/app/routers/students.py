from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.db import utcnow
from app.deps import DB, CurrentUser, require_roles
from app.errors import AppError
from app.mailer import send_email
from app.models.plan import AccommodationPlan
from app.models.student import (
    RPWD_CATEGORIES,
    Consent,
    GuardianLink,
    StaffAssignment,
    StoredFile,
    StudentProfile,
)
from app.models.user import Role, User
from app.permissions import (
    OVERSIGHT,
    can_edit_profile,
    can_manage_guardians,
    is_assigned_staff,
    is_guardian_of,
    require_student_access,
    visible_student_ids,
)
from app.routers.auth import find_user
from app.rules.dates import is_minor, today

# Grievance officers have no business with support profiles, so they are not let in at all.
PROFILE_ROLES = (Role.student, Role.guardian, Role.support_staff, Role.nodal_officer, Role.administrator)
router = APIRouter(tags=["students"], dependencies=[Depends(require_roles(*PROFILE_ROLES))])

RpwdCategory = Literal[RPWD_CATEGORIES]  # type: ignore[valid-type]


class GuardianIn(BaseModel):
    guardian_email: EmailStr
    relationship: str = Field(min_length=1, max_length=60)


class ConsentIn(BaseModel):
    """Guardians consenting in-app send nothing; staff recording a paper consent fill all three."""

    consenting_person_name: str | None = Field(None, min_length=1, max_length=120)
    relationship: str | None = Field(None, min_length=1, max_length=60)
    consent_date: date | None = None


class AssignmentIn(BaseModel):
    staff_id: int


class ProfileIn(BaseModel):
    """Every field is optional - a student decides what, if anything, to disclose."""

    enrollment_no: str | None = Field(None, max_length=40)
    programme: str | None = Field(None, max_length=120)
    department: str | None = Field(None, max_length=120)
    year_of_study: int | None = Field(None, ge=1, le=8)
    disability_categories: list[RpwdCategory] = []
    udid_number: str | None = Field(None, max_length=40)
    benchmark_percentage: int | None = Field(None, ge=0, le=100)
    support_needs: str | None = Field(None, max_length=4000)
    communication_preference: str | None = Field(None, max_length=500)


def active_consent(db, student_id: int) -> Consent | None:
    return db.scalar(
        select(Consent)
        .where(Consent.student_id == student_id, Consent.withdrawn_at.is_(None))
        .order_by(Consent.id.desc())
    )


def get_profile(db, student_id: int) -> StudentProfile | None:
    return db.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))


@router.get("/students")
def list_students(db: DB, user: CurrentUser):
    ids = visible_student_ids(db, user)
    query = select(User).where(User.role == Role.student).order_by(User.full_name)
    if ids is not None:
        query = query.where(User.id.in_(ids))
    students = db.scalars(query).all()
    with_profile = set(db.scalars(select(StudentProfile.student_id)))
    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "email": s.email,
            "is_minor": is_minor(s.date_of_birth, today()),
            "has_profile": s.id in with_profile,
        }
        for s in students
    ]


@router.get("/staff", dependencies=[Depends(require_roles(*OVERSIGHT))])
def list_support_staff(db: DB):
    query = select(User).where(User.role == Role.support_staff, User.is_active).order_by(User.full_name)
    return [{"id": u.id, "full_name": u.full_name} for u in db.scalars(query)]


@router.get("/students/{student_id}")
def student_detail(student_id: int, db: DB, user: CurrentUser):
    student = require_student_access(db, user, student_id)
    minor = is_minor(student.date_of_birth, today())
    consent = active_consent(db, student_id)
    profile = get_profile(db, student_id)
    links = db.scalars(
        select(GuardianLink).where(GuardianLink.student_id == student_id, GuardianLink.status != "revoked")
    ).all()
    staff = db.execute(
        select(StaffAssignment.id, User.id, User.full_name)
        .join(User, User.id == StaffAssignment.staff_id)
        .where(StaffAssignment.student_id == student_id, StaffAssignment.ended_at.is_(None))
    ).all()
    certificate = db.get(StoredFile, profile.certificate_file_id) if profile and profile.certificate_file_id else None
    oversight = user.role in OVERSIGHT
    assigned = is_assigned_staff(db, user, student_id)

    return {
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "date_of_birth": student.date_of_birth,
            "is_minor": minor,
        },
        "guardians": [
            {"id": link.id, "guardian_email": link.guardian_email, "relationship": link.relationship, "status": link.status}
            for link in links
        ],
        "consent": consent
        and {
            "consenting_person_name": consent.consenting_person_name,
            "relationship": consent.relationship,
            "consent_date": consent.consent_date,
            "method": consent.method,
        },
        "staff": [{"assignment_id": a, "staff_id": sid, "full_name": name} for a, sid, name in staff],
        "profile": profile
        and {
            "enrollment_no": profile.enrollment_no,
            "programme": profile.programme,
            "department": profile.department,
            "year_of_study": profile.year_of_study,
            "disability_categories": profile.disability_categories or [],
            "udid_number": profile.udid_number,
            "benchmark_percentage": profile.benchmark_percentage,
            "support_needs": profile.support_needs,
            "communication_preference": profile.communication_preference,
            "certificate": certificate and {"id": certificate.id, "filename": certificate.filename},
        },
        # What this user may do here. The same checks are enforced by each endpoint below.
        "can": {
            "edit_profile": can_edit_profile(db, user, student),
            "manage_guardians": can_manage_guardians(user, student_id),
            "assign_staff": oversight,
            "give_consent": minor and not consent and is_guardian_of(db, user, student_id),
            "record_consent": minor and not consent and (oversight or assigned),
        },
    }


@router.post("/students/{student_id}/guardians", status_code=201)
def invite_guardian(student_id: int, body: GuardianIn, db: DB, user: CurrentUser):
    student = require_student_access(db, user, student_id)
    if not can_manage_guardians(user, student_id):
        raise AppError(403, "forbidden")
    email = body.guardian_email.strip().lower()
    duplicate = db.scalar(
        select(GuardianLink.id).where(
            GuardianLink.student_id == student_id,
            GuardianLink.guardian_email == email,
            GuardianLink.status != "revoked",
        )
    )
    if duplicate:
        raise AppError(409, "already_linked")

    link = GuardianLink(
        student_id=student_id, guardian_email=email, relationship=body.relationship, invited_by=user.id
    )
    existing = find_user(db, email)
    if existing and existing.role != Role.guardian:
        raise AppError(409, "not_a_guardian_account")
    if existing and existing.email_verified_at:
        link.guardian_user_id, link.status = existing.id, "active"
    db.add(link)
    send_email(db, email, existing.locale if existing else "en", "guardian_invite", student=student.full_name)
    db.commit()
    return {"id": link.id, "status": link.status}


@router.delete("/students/{student_id}/guardians/{link_id}", status_code=204)
def revoke_guardian(student_id: int, link_id: int, db: DB, user: CurrentUser):
    require_student_access(db, user, student_id)
    link = db.get(GuardianLink, link_id)
    if not can_manage_guardians(user, student_id):
        raise AppError(403, "forbidden")
    if not link or link.student_id != student_id:
        raise AppError(404, "not_found")
    link.status = "revoked"
    db.commit()


@router.post("/students/{student_id}/consent", status_code=201)
def record_consent(student_id: int, body: ConsentIn, db: DB, user: CurrentUser):
    """Consent for a student under 18: given in-app by a linked guardian, or recorded by staff
    from a paper form. Either way we keep who consented and on what date."""
    student = require_student_access(db, user, student_id)
    if not is_minor(student.date_of_birth, today()):
        raise AppError(409, "consent_not_needed")
    if active_consent(db, student_id):
        raise AppError(409, "consent_exists")

    if is_guardian_of(db, user, student_id):
        link = db.scalar(
            select(GuardianLink).where(
                GuardianLink.student_id == student_id, GuardianLink.guardian_user_id == user.id
            )
        )
        consent = Consent(
            consenting_person_name=user.full_name,
            relationship=link.relationship,
            consenting_user_id=user.id,
            consent_date=today(),
            method="in_app",
        )
    elif user.role in OVERSIGHT or is_assigned_staff(db, user, student_id):
        if not (body.consenting_person_name and body.relationship and body.consent_date):
            raise AppError(422, "consent_details_required")
        if body.consent_date > today():
            raise AppError(422, "date_in_future")
        consent = Consent(
            consenting_person_name=body.consenting_person_name,
            relationship=body.relationship,
            consent_date=body.consent_date,
            method="recorded_by_staff",
        )
    else:
        raise AppError(403, "forbidden")

    consent.student_id, consent.recorded_by = student_id, user.id
    db.add(consent)
    db.commit()
    return {"id": consent.id}


@router.post("/students/{student_id}/assignments", status_code=201, dependencies=[Depends(require_roles(*OVERSIGHT))])
def assign_staff(student_id: int, body: AssignmentIn, db: DB, user: CurrentUser):
    require_student_access(db, user, student_id)
    staff = db.get(User, body.staff_id)
    if not staff or staff.role != Role.support_staff or not staff.is_active:
        raise AppError(422, "not_support_staff")
    duplicate = db.scalar(
        select(StaffAssignment.id).where(
            StaffAssignment.student_id == student_id,
            StaffAssignment.staff_id == staff.id,
            StaffAssignment.ended_at.is_(None),
        )
    )
    if duplicate:
        raise AppError(409, "already_assigned")
    db.add(StaffAssignment(student_id=student_id, staff_id=staff.id, assigned_by=user.id))
    db.commit()
    return {"status": "assigned"}


@router.delete(
    "/students/{student_id}/assignments/{assignment_id}",
    status_code=204,
    dependencies=[Depends(require_roles(*OVERSIGHT))],
)
def end_assignment(student_id: int, assignment_id: int, db: DB, user: CurrentUser):
    assignment = db.get(StaffAssignment, assignment_id)
    if not assignment or assignment.student_id != student_id:
        raise AppError(404, "not_found")
    assignment.ended_at = utcnow()
    db.commit()


@router.put("/students/{student_id}/profile")
def save_profile(student_id: int, body: ProfileIn, db: DB, user: CurrentUser):
    student = require_student_access(db, user, student_id)
    if not can_edit_profile(db, user, student):
        raise AppError(403, "forbidden")

    profile = get_profile(db, student_id)
    if not profile:
        consent = active_consent(db, student_id)
        if is_minor(student.date_of_birth, today()) and not consent:
            raise AppError(409, "consent_required")  # no profile for an under-18 without recorded consent
        profile = StudentProfile(student_id=student_id, created_by=user.id, consent_id=consent and consent.id)
        db.add(profile)
    for field, value in body.model_dump().items():
        # Blank strings and empty lists are stored as NULL; 0% is a real value and is kept.
        setattr(profile, field, value if field == "benchmark_percentage" else (value or None))
    db.commit()
    return {"status": "saved"}


@router.delete("/students/{student_id}/profile", status_code=204, dependencies=[Depends(require_roles(*OVERSIGHT))])
def delete_profile(student_id: int, db: DB, user: CurrentUser):
    require_student_access(db, user, student_id)
    profile = get_profile(db, student_id)
    if not profile:
        raise AppError(404, "not_found")
    if db.scalar(select(AccommodationPlan.id).where(AccommodationPlan.profile_id == profile.id)):
        raise AppError(409, "profile_has_plans")  # plans and their provision history must stay intact
    if profile.certificate_file_id:
        certificate = db.get(StoredFile, profile.certificate_file_id)
        profile.certificate_file_id = None
        db.flush()
        db.delete(certificate)
    db.delete(profile)
    db.commit()
