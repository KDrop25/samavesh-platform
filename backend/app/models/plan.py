import enum
from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.crypto import EncryptedText
from app.db import Base

ACCOMMODATION_TYPES = (
    "scribe",
    "extra_time",
    "accessible_material",
    "assistive_tech",
    "physical_access",
    "transport",
)


class PlanStatus(enum.StrEnum):
    draft = "draft"
    submitted = "submitted"  # waiting for the nodal officer
    approved = "approved"  # the only status that can be active
    rejected = "rejected"
    superseded = "superseded"  # replaced by an approved newer version
    ended = "ended"


class Term(Base):
    __tablename__ = "terms"

    name: Mapped[str] = mapped_column(String(80))
    start_date: Mapped[date]
    end_date: Mapped[date]


class AccommodationPlan(Base):
    __tablename__ = "accommodation_plans"
    __audited__ = True

    profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"), index=True)
    version: Mapped[int] = mapped_column(default=1)
    supersedes_plan_id: Mapped[int | None] = mapped_column(ForeignKey("accommodation_plans.id"))
    status: Mapped[PlanStatus] = mapped_column(default=PlanStatus.draft)
    start_date: Mapped[date]
    review_date: Mapped[date]
    ended_on: Mapped[date | None]  # set when superseded or ended; bounds "planned" counts
    notes: Mapped[str | None] = mapped_column(EncryptedText)
    drafted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None]


class PlanItem(Base):
    __tablename__ = "plan_items"
    __audited__ = True

    plan_id: Mapped[int] = mapped_column(ForeignKey("accommodation_plans.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # one of ACCOMMODATION_TYPES
    details: Mapped[str | None] = mapped_column(EncryptedText)
    interval_days: Mapped[int | None]  # expected every N days; null = standing arrangement


class ProvisionLog(Base):
    """A provision actually delivered: what (plan item), when, and by which staff member."""

    __tablename__ = "provision_logs"
    __audited__ = True

    plan_item_id: Mapped[int] = mapped_column(ForeignKey("plan_items.id"), index=True)
    provided_on: Mapped[date]
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(EncryptedText)
