"""Reset the database and load demo data: `uv run python -m app.seed`.

Destroys everything in the target database, so production needs an explicit --wipe-prod.
Grows with each module; demo logins are listed in the README.
"""

import sys
from datetime import date

from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers every table)
from app.config import get_settings
from app.db import Base, engine, utcnow
from app.models.student import GuardianLink, StaffAssignment, StudentProfile
from app.models.user import Role, User
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
    db.commit()


if __name__ == "__main__":
    if get_settings().is_prod and "--wipe-prod" not in sys.argv:
        sys.exit("Refusing to wipe a production database. Pass --wipe-prod if you really mean it.")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    print(f"Seeded {len(USERS)} demo users. Password for all: {DEMO_PASSWORD}")
