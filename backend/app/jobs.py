"""Daily work: grievance escalation flags, compliance and plan-review reminders.

Run by GitHub Actions through POST /internal/jobs/run, or locally with `python -m app.jobs`.
Idempotent: every reminder has a dedupe key, so a second run the same day sends nothing new.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.compliance import ComplianceItem
from app.models.plan import AccommodationPlan, PlanStatus
from app.models.student import StudentProfile
from app.models.user import Role, User
from app.notify import notify
from app.rules.compliance import REMINDER_DAYS, reminder_due
from app.rules.dates import today
from app.routers.grievances import flag_overdue_grievances


def _active(db: Session, role: Role) -> list[User]:
    return list(db.scalars(select(User).where(User.role == role, User.is_active.is_(True))))


def run_jobs(db: Session) -> dict[str, int]:
    on = today()
    counts = {"escalations": 0, "compliance_reminders": 0, "plan_reviews": 0}

    for grievance in flag_overdue_grievances(db):
        for admin in _active(db, Role.administrator):
            counts["escalations"] += notify(
                db, admin.id, "escalation", "/grievances/escalated",
                dedupe_key=f"escalation:{grievance.id}:{admin.id}", reference=grievance.reference,
            )

    for item in db.scalars(select(ComplianceItem)):
        if reminder_due(item.status, item.due_date, on):
            for officer in _active(db, Role.nodal_officer):
                counts["compliance_reminders"] += notify(
                    db, officer.id, "compliance_due", f"/compliance/{item.id}",
                    dedupe_key=f"compliance:{item.id}:{item.due_date}:{officer.id}", days=REMINDER_DAYS,
                )

    for plan in db.scalars(select(AccommodationPlan).where(AccommodationPlan.status == PlanStatus.approved)):
        if on <= plan.review_date <= on + timedelta(days=REMINDER_DAYS):
            student_id = db.get(StudentProfile, plan.profile_id).student_id
            counts["plan_reviews"] += notify(
                db, plan.drafted_by, "plan_review", f"/students/{student_id}/plans",
                dedupe_key=f"plan_review:{plan.id}:{plan.review_date}", plan_id=plan.id,
            )

    db.commit()
    return counts


if __name__ == "__main__":
    with SessionLocal() as session:
        print(run_jobs(session))
