import enum
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(enum.StrEnum):
    student = "student"
    guardian = "guardian"
    support_staff = "support_staff"
    nodal_officer = "nodal_officer"
    grievance_officer = "grievance_officer"
    administrator = "administrator"


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)  # stored lower-case
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null until invited staff set one
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role]
    date_of_birth: Mapped[date | None]  # required for students (under-18 consent rule)
    locale: Mapped[str] = mapped_column(String(5), default="en")
    is_active: Mapped[bool] = mapped_column(default=True)
    email_verified_at: Mapped[datetime | None]
    token_version: Mapped[int] = mapped_column(default=0)  # bump = every issued JWT dies
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]


class EmailCode(Base):
    __tablename__ = "email_codes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # verify | reset
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(default=0)
    consumed_at: Mapped[datetime | None]


class DevEmail(Base):
    """Dev outbox. Only written when SMTP is not configured and env is not prod."""

    __tablename__ = "dev_emails"

    to: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
