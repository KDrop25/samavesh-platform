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
    password_hash = hash_password(DEMO_PASSWORD)
    for email, name, role, dob in USERS:
        db.add(
            User(
                email=email,
                full_name=name,
                role=role,
                date_of_birth=dob,
                password_hash=password_hash,
                email_verified_at=utcnow(),
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
