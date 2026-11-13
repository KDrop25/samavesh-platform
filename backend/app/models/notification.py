from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.crypto import EncryptedJSON
from app.db import Base


class Notification(Base):
    """In-app notice. `kind` is a translation key (notice.<kind> in the UI); `params` holds only
    identifiers and short codes, never disability or grievance content."""

    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    link: Mapped[str] = mapped_column(String(200))
    params: Mapped[dict] = mapped_column(EncryptedJSON)
    read_at: Mapped[datetime | None]
    dedupe_key: Mapped[str | None] = mapped_column(String(120), unique=True)  # makes reminders idempotent
