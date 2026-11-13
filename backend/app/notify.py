"""Send a notice in the app and by email. Emails carry only a generic "you have an update"."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mailer import send_email
from app.models.notification import Notification
from app.models.user import User


def notify(db: Session, user_id: int | None, kind: str, link: str, dedupe_key: str | None = None, **params) -> bool:
    """Returns False when nothing was sent: no such active user, or this dedupe key already fired."""
    if user_id is None or (dedupe_key and db.scalar(select(Notification.id).where(Notification.dedupe_key == dedupe_key))):
        return False
    user = db.get(User, user_id)
    if not user or not user.is_active:
        return False
    db.add(Notification(user_id=user.id, kind=kind, link=link, params=params, dedupe_key=dedupe_key))
    send_email(db, user.email, user.locale, "update")
    return True


def notify_contact(db: Session, email: str) -> None:
    """Grievance update for a complainant with no account (anonymous, or a walk-in who gave an email)."""
    send_email(db, email, "en", "grievance_update")
