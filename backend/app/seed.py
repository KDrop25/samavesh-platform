"""Reset the database and load demo data: `uv run python -m app.seed`.

Destroys everything in the target database, so production needs an explicit --wipe-prod.
Grows with each module; demo logins are listed in the README.
"""

import sys
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers every table)
from app.config import get_settings
from app.db import Base, engine, utcnow
from app.models.compliance import ComplianceItem
from app.models.plan import AccommodationPlan, PlanDecision, PlanItem, PlanStatus, ProvisionLog, Term
from app.models.student import GuardianLink, StaffAssignment, StudentProfile
from app.models.user import Role, User
from app.rules.dates import today
from app.security import hash_password

DEMO_PASSWORD = "Samavesh-Demo-2026"

USERS = [
    # (email, name, role, date of birth)
    ("admin@samavesh.example.com", "Anita Rao", Role.administrator, None),
    ("nodal@samavesh.example.com", "Dr. Farhan Qureshi", Role.nodal_officer, None),
    ("grievance@samavesh.example.com", "Meera Iyer", Role.grievance_officer, None),
    ("staff@samavesh.example.com", "Rohit Kulkarni", Role.support_staff, None),
    ("staff2@samavesh.example.com", "Lakshmi Nair", Role.support_staff, None),
    ("student@samavesh.example.com", "Asha Verma", Role.student, date(2004, 5, 1)),
    ("student2@samavesh.example.com", "Imran Sheikh", Role.student, date(2003, 11, 19)),
    ("minor@samavesh.example.com", "Kavya Menon", Role.student, date(2010, 2, 14)),  # under 18
    ("guardian@samavesh.example.com", "Sunita Menon", Role.guardian, None),
]


def seed(db: Session) -> None:
    db.info["actor"] = (None, "system")
    password_hash = hash_password(DEMO_PASSWORD)
    users = {}
    for email, name, role, dob in USERS:
        users[email.split("@")[0]] = user = User(
            email=email,
            full_name=name,
            role=role,
            date_of_birth=dob,
            password_hash=password_hash,
            email_verified_at=utcnow(),
        )
        db.add(user)
    db.flush()
    nodal, staff, staff2 = users["nodal"], users["staff"], users["staff2"]
    asha, imran, kavya, sunita = users["student"], users["student2"], users["minor"], users["guardian"]

    # Module 2: guardian link, staff assignments, support profiles.
    # Kavya is under 18 and has NO consent yet, so the consent gate can be shown in a demo.
    db.add(
        GuardianLink(
            student_id=kavya.id,
            guardian_email=sunita.email,
            guardian_user_id=sunita.id,
            relationship="Mother",
            status="active",
            invited_by=kavya.id,
        )
    )
    for student, member in ((asha, staff), (kavya, staff), (imran, staff2)):
        db.add(StaffAssignment(student_id=student.id, staff_id=member.id, assigned_by=nodal.id))
    db.add(
        StudentProfile(
            student_id=asha.id,
            created_by=asha.id,
            enrollment_no="CS22B041",
            programme="B.Tech Computer Science and Engineering",
            department="Computer Science",
            year_of_study=3,
            disability_categories=["low_vision"],
            udid_number="MH1234567890123456",
            benchmark_percentage=40,
            support_needs="Large-print or digital course material, extra time in written exams, "
            "and a seat near the front of the classroom.",
            communication_preference="Email, with documents as accessible PDF or Word files.",
        )
    )
    db.add(
        StudentProfile(
            student_id=imran.id,
            created_by=staff2.id,
            enrollment_no="ME21B017",
            programme="B.Tech Mechanical Engineering",
            department="Mechanical Engineering",
            year_of_study=4,
            disability_categories=["locomotor_disability"],
            benchmark_percentage=60,
            support_needs="Step-free access to laboratories and a scribe for long written exams.",
            communication_preference="Phone call or WhatsApp message.",
        )
    )
    db.flush()
    seed_plans(db, asha, imran, staff, staff2, nodal)
    seed_compliance(db, nodal)
    db.commit()


def seed_plans(db: Session, asha: User, imran: User, staff: User, staff2: User, nodal: User) -> None:
    """Module 3. Dates are relative to today so the demo always shows one overdue item."""
    now = today()
    ago = lambda days: now - timedelta(days=days)  # noqa: E731
    db.add(Term(name="Monsoon semester 2026", start_date=ago(110), end_date=now + timedelta(days=40)))
    db.add(Term(name="Summer term 2026", start_date=ago(200), end_date=ago(125)))

    profile_of = lambda user: db.scalar(select(StudentProfile.id).where(StudentProfile.student_id == user.id))  # noqa: E731

    # Asha: an approved, active plan. Extra time is overdue; accessible material is on track.
    plan = AccommodationPlan(
        profile_id=profile_of(asha),
        status=PlanStatus.approved,
        start_date=ago(100),
        review_date=now + timedelta(days=80),
        notes="Agreed with Asha and her course coordinator at the start of the semester.",
        drafted_by=staff.id,
        submitted_at=utcnow() - timedelta(days=102),
    )
    db.add(plan)
    db.flush()
    extra_time = PlanItem(plan_id=plan.id, type="extra_time", details="20 minutes extra per hour in written tests.", interval_days=30)
    material = PlanItem(plan_id=plan.id, type="accessible_material", details="Lecture notes as tagged PDF, 18pt.", interval_days=14)
    seating = PlanItem(plan_id=plan.id, type="physical_access", details="Reserved front-row seat in all lecture halls.")
    db.add_all([extra_time, material, seating])
    db.add(
        PlanDecision(
            plan_id=plan.id,
            decision="approved",
            approver_id=nodal.id,
            reason="Consistent with the student's documented needs and the examination guidelines.",
        )
    )
    db.flush()
    for item, days, note in (
        (extra_time, 62, "Class test 1"),
        (extra_time, 32, "Mid-semester examination"),
        (material, 75, "Unit 1 notes"),
        (material, 47, "Unit 2 notes"),
        (material, 19, "Unit 3 notes"),
        (material, 5, "Unit 4 notes"),
    ):
        db.add(ProvisionLog(plan_item_id=item.id, provided_on=ago(days), staff_id=staff.id, notes=note))

    # Imran: a plan submitted and waiting for the nodal officer's decision.
    pending = AccommodationPlan(
        profile_id=profile_of(imran),
        status=PlanStatus.submitted,
        start_date=now + timedelta(days=3),
        review_date=now + timedelta(days=150),
        notes="Requested ahead of the end-semester examinations.",
        drafted_by=staff2.id,
        submitted_at=utcnow() - timedelta(days=1),
    )
    db.add(pending)
    db.flush()
    db.add(PlanItem(plan_id=pending.id, type="scribe", details="Scribe for all three-hour written papers.", interval_days=45))
    db.add(PlanItem(plan_id=pending.id, type="transport", details="Campus shuttle pick-up from Hostel 4."))


def seed_compliance(db: Session, nodal: User) -> None:
    """Module 4. Illustrative checklist drawn from the RPwD Act 2016 and UGC guidance.
    Section references are for demonstration and must be verified against the official text."""
    now = today()
    verify = " (verify against official text)"
    items = [
        # (description, source, due in days, status, reason)
        ("Admit students with disabilities without discrimination and provide equal opportunities for sports and recreation.",
         "RPwD Act 2016, s.16", 120, "compliant", None),
        ("Make the campus, buildings and facilities accessible, including ramps, lifts and accessible toilets in every block.",
         "RPwD Act 2016, s.16 and s.45", -12, "partially", "Lift in Block C is not yet commissioned; ramps and toilets are complete."),
        ("Provide reasonable accommodation and individualised support, including scribes and extra time in examinations.",
         "RPwD Act 2016, s.17; examination guidelines for persons with benchmark disabilities, 2018", 5, "partially",
         "Scribe panel is in place; the extra-time policy is awaiting Academic Council approval."),
        ("Reserve not less than five per cent of seats for persons with benchmark disabilities and allow five years' relaxation in the upper age limit.",
         "RPwD Act 2016, s.32", 200, "compliant", None),
        ("Publish an equal opportunity policy and register it with the competent authority.",
         "RPwD Act 2016, s.21", 30, "not_compliant", "Draft policy is with the Registrar for review."),
        ("Appoint a grievance redressal officer and publish how grievances can be lodged.",
         "RPwD Act 2016, s.23", 90, "compliant", None),
        ("Make the institution's website and learning portal conform to accessibility standards (WCAG 2.1 Level AA / GIGW).",
         "RPwD Act 2016, s.42 and s.46; GIGW", 60, "partially", "Main website audited; the learning portal audit is scheduled."),
        ("Provide hostel transport adapted for wheelchair users.",
         "UGC accessibility guidelines for higher education institutions", 365, "not_applicable",
         "The campus is fully residential and hostels are within 300 metres of all academic blocks."),
    ]
    for description, source, due_in, status, reason in items:
        db.add(
            ComplianceItem(
                description=description,
                source_obligation=source + verify,
                due_date=now + timedelta(days=due_in),
                status=status,
                reason=reason,
                updated_by=nodal.id,
            )
        )


if __name__ == "__main__":
    if get_settings().is_prod and "--wipe-prod" not in sys.argv:
        sys.exit("Refusing to wipe a production database. Pass --wipe-prod if you really mean it.")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    print(f"Seeded {len(USERS)} demo users. Password for all: {DEMO_PASSWORD}")
