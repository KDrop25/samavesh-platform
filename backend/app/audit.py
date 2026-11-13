"""Append-only audit log.

Any model with `__audited__ = True` gets a row here for every create/update/delete, written in
the same transaction. UPDATE/DELETE on the table are blocked by database triggers, and there is
no API that modifies it.
"""

import enum

from sqlalchemy import DDL, JSON, String, event, insert, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.crypto import EncryptedBytes
from app.db import Base, utcnow


class AuditLog(Base):
    __tablename__ = "audit_log"

    actor_user_id: Mapped[int | None]  # null for system jobs and for grievance complainants
    actor_role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(8))  # create | update | delete
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int]
    changed_fields: Mapped[dict | None] = mapped_column(JSON)


def append_only_ddl(table: str) -> dict[str, list[str]]:
    """Trigger DDL per dialect. Used by create_all (below) and by the Alembic migrations."""
    msg = f"{table} is append-only"
    return {
        "sqlite": [
            f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{msg}'); END",
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{msg}'); END",
        ],
        "postgresql": [
            f"CREATE OR REPLACE FUNCTION {table}_append_only() RETURNS trigger "
            f"LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION '{msg}'; END $$",
            f"CREATE TRIGGER {table}_no_change BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {table}_append_only()",
            f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
            f"FOR EACH STATEMENT EXECUTE FUNCTION {table}_append_only()",
        ],
    }


def make_append_only(table) -> None:
    for dialect, statements in append_only_ddl(table.name).items():
        for sql in statements:
            event.listen(table, "after_create", DDL(sql).execute_if(dialect=dialect))


make_append_only(AuditLog.__table__)


def _json(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return value.value if isinstance(value, enum.Enum) else str(value)


def _changes(obj) -> dict:
    state = inspect(obj)
    changed = {}
    for attr in state.mapper.column_attrs:
        hist = state.attrs[attr.key].history
        if not hist.has_changes():
            continue
        if isinstance(attr.columns[0].type, EncryptedBytes):
            changed[attr.key] = "[encrypted]"  # never copy sensitive values into the log
        else:
            old = _json(hist.deleted[0]) if hist.deleted else None
            new = _json(hist.added[0]) if hist.added else None
            changed[attr.key] = [old, new]
    return changed


@event.listens_for(Session, "after_flush")
def _write_audit(session, flush_context):
    # after_flush: primary keys exist, attribute history is still the pre-flush history.
    actor_id, actor_role = session.info.get("actor", (None, "system"))
    rows = []
    for objects, action in ((session.new, "create"), (session.dirty, "update"), (session.deleted, "delete")):
        for obj in objects:
            if not getattr(obj, "__audited__", False):
                continue
            changed = _changes(obj) if action == "update" else None
            if action == "update" and not changed:
                continue
            rows.append(
                {
                    "actor_user_id": actor_id,
                    "actor_role": actor_role,
                    "action": action,
                    "entity_type": obj.__tablename__,
                    "entity_id": obj.id,
                    "changed_fields": changed,
                    "created_at": utcnow(),
                }
            )
    if rows:
        session.connection().execute(insert(AuditLog.__table__), rows)
