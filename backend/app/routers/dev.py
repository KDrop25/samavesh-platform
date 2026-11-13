"""Dev outbox. main.py mounts this router only when ENV is not prod."""

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB
from app.models.user import DevEmail

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/emails")
def dev_emails(db: DB):
    rows = db.scalars(select(DevEmail).order_by(DevEmail.id.desc()).limit(50)).all()
    return [{"to": r.to, "subject": r.subject, "body": r.body, "at": r.created_at} for r in rows]
