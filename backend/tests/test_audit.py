import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from app.audit import AuditLog
from tests.conftest import Widget


def test_create_update_delete_are_logged_without_sensitive_values(db):
    db.info["actor"] = (7, "support_staff")
    w = Widget(name="scribe", secret="low vision")
    db.add(w)
    db.commit()
    w.name, w.secret = "reader", "blind"
    db.commit()
    db.delete(w)
    db.commit()

    rows = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    assert [(r.action, r.entity_type, r.entity_id) for r in rows] == [
        ("create", "test_widgets", w.id),
        ("update", "test_widgets", w.id),
        ("delete", "test_widgets", w.id),
    ]
    assert all((r.actor_user_id, r.actor_role) == (7, "support_staff") for r in rows)
    assert rows[1].changed_fields == {"name": ["scribe", "reader"], "secret": "[encrypted]"}


def test_audit_log_cannot_be_updated_or_deleted(db):
    db.add(Widget(name="x"))
    db.commit()
    for statement in (update(AuditLog).values(action="edited"), delete(AuditLog), text("DELETE FROM audit_log")):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(statement)
        db.rollback()
    assert db.scalar(select(AuditLog.action)) == "create"
