"""Read-only view of the audit log. There is deliberately no endpoint that writes to it:
rows are added by the session listener in app/audit.py and the database blocks UPDATE/DELETE."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.audit import AuditLog
from app.deps import DB, require_roles
from app.models.user import User
from app.permissions import OVERSIGHT

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_roles(*OVERSIGHT))])

PAGE = 50


@router.get("")
def audit_log(
    db: DB,
    entity_type: str | None = Query(None, max_length=64),
    before: int | None = Query(None, ge=1),
):
    """Newest first. `before` is the id of the last row of the previous page."""
    query = (
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.id.desc())
        .limit(PAGE + 1)
    )
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if before:
        query = query.where(AuditLog.id < before)
    rows = db.execute(query).all()
    page = rows[:PAGE]
    return {
        "entity_types": sorted(db.scalars(select(AuditLog.entity_type).distinct())),
        "next_before": page[-1][0].id if len(rows) > PAGE else None,
        "entries": [
            {
                "id": entry.id,
                "at": entry.created_at,
                "actor": name,
                "actor_role": entry.actor_role,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "changed_fields": entry.changed_fields,
            }
            for entry, name in page
        ],
    }
