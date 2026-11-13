from datetime import date, datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.crypto import EncryptedJSON, EncryptedText
from app.db import Base

GRIEVANCE_STATUSES = ("received", "under_review", "resolved", "escalated")
GRIEVANCE_CATEGORIES = (
    "accommodation_not_provided",
    "physical_accessibility",
    "accessible_material",
    "examination",
    "discrimination_or_conduct",
    "other",
)
# Received -> Under review -> Resolved / Escalated. An escalated case can still be resolved.
TRANSITIONS = {
    "received": ("under_review",),
    "under_review": ("resolved", "escalated"),
    "escalated": ("resolved",),
    "resolved": (),
}


class Grievance(Base):
    """All content and every identifying field is encrypted. There is deliberately no plain
    foreign key to the complainant: only the grievance officer's endpoints decrypt identity."""

    __tablename__ = "grievances"
    __audited__ = True

    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # the public tracking key
    is_anonymous: Mapped[bool]
    category: Mapped[str] = mapped_column(String(40))
    subject: Mapped[str] = mapped_column(EncryptedText)
    description: Mapped[str] = mapped_column(EncryptedText)
    status: Mapped[str] = mapped_column(String(20), default="received")
    complainant_user_id: Mapped[int | None] = mapped_column(EncryptedJSON)  # null when anonymous
    complainant_name: Mapped[str | None] = mapped_column(EncryptedText)  # null when anonymous
    contact_email: Mapped[str | None] = mapped_column(EncryptedText)  # optional, for status emails
    escalation_flagged_at: Mapped[datetime | None]  # set automatically after too long under review


class GrievanceEvent(Base):
    """One row per status change; its created_at is the timestamp of that status."""

    __tablename__ = "grievance_events"
    __audited__ = True

    grievance_id: Mapped[int] = mapped_column(ForeignKey("grievances.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    public_note: Mapped[str | None] = mapped_column(EncryptedText)  # shown on the tracking page
    internal_note: Mapped[str | None] = mapped_column(EncryptedText)  # grievance officer only
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # the officer; null on submission


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(40), unique=True)
    value: Mapped[dict | list | int | str] = mapped_column(JSON)


class Holiday(Base):
    __tablename__ = "holidays"

    day: Mapped[date] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(120))
