from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.crypto import EncryptedBytes, EncryptedJSON, EncryptedText
from app.db import Base

# The 21 specified disabilities in the Schedule to the Rights of Persons with Disabilities Act, 2016.
RPWD_CATEGORIES = (
    "blindness",
    "low_vision",
    "leprosy_cured",
    "hearing_impairment",
    "locomotor_disability",
    "dwarfism",
    "intellectual_disability",
    "mental_illness",
    "autism_spectrum_disorder",
    "cerebral_palsy",
    "muscular_dystrophy",
    "chronic_neurological_conditions",
    "specific_learning_disabilities",
    "multiple_sclerosis",
    "speech_and_language_disability",
    "thalassemia",
    "hemophilia",
    "sickle_cell_disease",
    "multiple_disabilities",
    "acid_attack_victim",
    "parkinsons_disease",
)


class GuardianLink(Base):
    __tablename__ = "guardian_links"

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    guardian_email: Mapped[str] = mapped_column(String(254), index=True)
    guardian_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # null until they register
    relationship: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(10), default="invited")  # invited | active | revoked
    invited_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ended_at: Mapped[datetime | None]


class Consent(Base):
    """Who consented to a support profile for a student under 18, and when."""

    __tablename__ = "consents"
    __audited__ = True

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    consenting_person_name: Mapped[str] = mapped_column(String(120))
    relationship: Mapped[str] = mapped_column(String(60))
    consenting_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # set when given in-app
    consent_date: Mapped[date]
    method: Mapped[str] = mapped_column(String(20))  # in_app | recorded_by_staff
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    withdrawn_at: Mapped[datetime | None]


class StoredFile(Base):
    """Uploaded document, encrypted at rest inside the database (10 MB cap enforced on upload)."""

    __tablename__ = "files"

    purpose: Mapped[str] = mapped_column(String(20))  # certificate | evidence
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    data: Mapped[bytes] = mapped_column(EncryptedBytes, deferred=True)  # loaded only on download
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class StudentProfile(Base):
    """Support profile. Every disability-related field is optional and encrypted."""

    __tablename__ = "student_profiles"
    __audited__ = True

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    consent_id: Mapped[int | None] = mapped_column(ForeignKey("consents.id"))  # required if under 18
    enrollment_no: Mapped[str | None] = mapped_column(String(40))
    programme: Mapped[str | None] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    year_of_study: Mapped[int | None]
    disability_categories: Mapped[list | None] = mapped_column(EncryptedJSON)
    udid_number: Mapped[str | None] = mapped_column(EncryptedText)
    benchmark_percentage: Mapped[int | None] = mapped_column(EncryptedJSON)
    support_needs: Mapped[str | None] = mapped_column(EncryptedText)
    communication_preference: Mapped[str | None] = mapped_column(EncryptedText)
    certificate_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
