from fastapi import APIRouter, Header
from typing import Annotated
import hmac

from sqlalchemy import func, select, update

from app.config import get_settings
from app.db import utcnow
from app.deps import DB, CurrentUser
from app.errors import AppError
from app.models.notification import Notification
from app.jobs import run_jobs

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def list_notifications(db: DB, user: CurrentUser):
    rows = db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(50)
    ).all()
    unread = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return {
        "unread": unread,
        "items": [
            {"id": n.id, "kind": n.kind, "link": n.link, "params": n.params, "read": n.read_at is not None, "at": n.created_at}
            for n in rows
        ],
    }


@router.post("/notifications/read-all")
def mark_all_read(db: DB, user: CurrentUser):
    db.execute(
        update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)).values(read_at=utcnow())
    )
    db.commit()
    return {"status": "read"}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: DB, user: CurrentUser):
    notice = db.get(Notification, notification_id)
    if not notice or notice.user_id != user.id:  # someone else's notice is "not found", not "forbidden"
        raise AppError(404, "not_found")
    notice.read_at = notice.read_at or utcnow()
    db.commit()
    return {"status": "read"}


@router.post("/internal/jobs/run")
def run_scheduled_jobs(db: DB, x_jobs_secret: Annotated[str | None, Header()] = None):
    """Called once a day by the scheduler. Disabled unless JOBS_SECRET is configured."""
    secret = get_settings().jobs_secret
    if not secret or not hmac.compare_digest(x_jobs_secret or "", secret):
        raise AppError(403, "forbidden")
    return run_jobs(db)
