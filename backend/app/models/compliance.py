from datetime import date

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

COMPLIANCE_STATUSES = ("compliant", "partially", "not_compliant", "not_applicable")


class ComplianceItem(Base):
    """One statutory or policy obligation the institution tracks. Configured by the nodal officer."""

    __tablename__ = "compliance_items"
    __audited__ = True

    description: Mapped[str] = mapped_column(Text)
    source_obligation: Mapped[str] = mapped_column(String(300))  # e.g. "RPwD Act 2016, s.16"
    due_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)  # required unless status is compliant
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class ComplianceEvidence(Base):
    __tablename__ = "compliance_evidence"

    item_id: Mapped[int] = mapped_column(ForeignKey("compliance_items.id"), index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
