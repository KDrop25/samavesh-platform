"""Object-level access rules. Role gates live on the routers; these decide "which records".

A support profile is visible only to the student, their linked guardian, their assigned
support staff, nodal officers and administrators. Grievance officers see none.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.student import GuardianLink, StaffAssignment
from app.models.user import Role, User
from app.rules.dates import is_minor, today

OVERSIGHT = (Role.nodal_officer, Role.administrator)


def is_guardian_of(db: Session, user: User, student_id: int) -> bool:
    return user.role == Role.guardian and bool(
        db.scalar(
            select(GuardianLink.id).where(
                GuardianLink.student_id == student_id,
                GuardianLink.guardian_user_id == user.id,
                GuardianLink.status == "active",
            )
        )
    )


def is_assigned_staff(db: Session, user: User, student_id: int) -> bool:
    return user.role == Role.support_staff and bool(
        db.scalar(
            select(StaffAssignment.id).where(
                StaffAssignment.student_id == student_id,
                StaffAssignment.staff_id == user.id,
                StaffAssignment.ended_at.is_(None),
            )
        )
    )


def can_view_student(db: Session, user: User, student_id: int) -> bool:
    return (
        user.role in OVERSIGHT
        or (user.role == Role.student and user.id == student_id)
        or is_guardian_of(db, user, student_id)
        or is_assigned_staff(db, user, student_id)
    )


def can_edit_profile(db: Session, user: User, student: User) -> bool:
    """Oversight roles, assigned staff, or the student themselves once they are an adult."""
    own = user.id == student.id and not is_minor(student.date_of_birth, today())
    return user.role in OVERSIGHT or own or is_assigned_staff(db, user, student.id)


def can_manage_guardians(user: User, student_id: int) -> bool:
    return user.role in OVERSIGHT or user.id == student_id


def visible_student_ids(db: Session, user: User) -> list[int] | None:
    """Ids of students this user may see. None means "all" (oversight roles)."""
    if user.role in OVERSIGHT:
        return None
    if user.role == Role.student:
        return [user.id]
    if user.role == Role.guardian:
        query = select(GuardianLink.student_id).where(
            GuardianLink.guardian_user_id == user.id, GuardianLink.status == "active"
        )
        return list(db.scalars(query))
    if user.role == Role.support_staff:
        query = select(StaffAssignment.student_id).where(
            StaffAssignment.staff_id == user.id, StaffAssignment.ended_at.is_(None)
        )
        return list(db.scalars(query))
    return []


def require_student_access(db: Session, user: User, student_id: int) -> User:
    """Load a student the user may see, or fail. 404 for both "missing" and "not yours"
    so that record existence is not revealed."""
    student = db.get(User, student_id)
    if not student or student.role != Role.student or not can_view_student(db, user, student_id):
        raise AppError(404, "not_found")
    return student


def activate_guardian_links(db: Session, user: User) -> None:
    """Called once a guardian has proved their email address: pending invitations become active."""
    if user.role != Role.guardian:
        return
    for link in db.scalars(
        select(GuardianLink).where(GuardianLink.guardian_email == user.email, GuardianLink.status == "invited")
    ):
        link.guardian_user_id, link.status = user.id, "active"
