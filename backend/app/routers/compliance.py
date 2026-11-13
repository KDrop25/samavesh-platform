from datetime import date
from typing import Literal, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import DB, CurrentUser, require_roles
from app.errors import AppError
from app.models.compliance import COMPLIANCE_STATUSES, ComplianceEvidence, ComplianceItem
from app.models.student import StoredFile
from app.models.user import Role
from app.rules.compliance import is_overdue, reminder_due, summarise
from app.rules.dates import today

# The nodal officer configures the checklist; support staff and administrators can read it.
COMPLIANCE_READERS = (Role.support_staff, Role.nodal_officer, Role.administrator)
router = APIRouter(prefix="/compliance", tags=["compliance"], dependencies=[Depends(require_roles(*COMPLIANCE_READERS))])
nodal_only = [Depends(require_roles(Role.nodal_officer))]


class ItemIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    source_obligation: str = Field(min_length=1, max_length=300)
    due_date: date
    status: Literal[COMPLIANCE_STATUSES]  # type: ignore[valid-type]
    reason: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def reason_unless_compliant(self) -> Self:
        if self.status != "compliant" and not (self.reason or "").strip():
            raise ValueError("reason_required")
        return self


def _item(db: Session, item_id: int) -> ComplianceItem:
    item = db.get(ComplianceItem, item_id)
    if not item:
        raise AppError(404, "not_found")
    return item


def _view(db: Session, item: ComplianceItem, on: date) -> dict:
    evidence = db.execute(
        select(ComplianceEvidence.id, StoredFile.id, StoredFile.filename)
        .join(StoredFile, StoredFile.id == ComplianceEvidence.file_id)
        .where(ComplianceEvidence.item_id == item.id)
        .order_by(ComplianceEvidence.id)
    ).all()
    return {
        "id": item.id,
        "description": item.description,
        "source_obligation": item.source_obligation,
        "due_date": item.due_date,
        "status": item.status,
        "reason": item.reason,
        "overdue": is_overdue(item.status, item.due_date, on),
        "due_soon": reminder_due(item.status, item.due_date, on),
        "evidence": [{"id": eid, "file_id": fid, "filename": name} for eid, fid, name in evidence],
    }


@router.get("")
def checklist(db: DB, user: CurrentUser):
    on = today()
    items = db.scalars(select(ComplianceItem).order_by(ComplianceItem.due_date, ComplianceItem.id)).all()
    return {
        "can_edit": user.role == Role.nodal_officer,
        "summary": summarise([(item.status, item.due_date) for item in items], on),
        "items": [_view(db, item, on) for item in items],
    }


@router.get("/{item_id}")
def get_item(item_id: int, db: DB):
    return _view(db, _item(db, item_id), today())


@router.post("", status_code=201, dependencies=nodal_only)
def create_item(body: ItemIn, db: DB, user: CurrentUser):
    item = ComplianceItem(**body.model_dump(), updated_by=user.id)
    item.reason = (body.reason or "").strip() or None
    db.add(item)
    db.commit()
    return {"id": item.id}


@router.put("/{item_id}", dependencies=nodal_only)
def update_item(item_id: int, body: ItemIn, db: DB, user: CurrentUser):
    item = _item(db, item_id)
    for field, value in body.model_dump().items():
        setattr(item, field, value)
    item.reason = (body.reason or "").strip() or None
    item.updated_by = user.id
    db.commit()
    return {"id": item.id}


def _remove_evidence(db: Session, evidence: ComplianceEvidence) -> None:
    file = db.get(StoredFile, evidence.file_id)
    db.delete(evidence)
    db.flush()
    db.delete(file)


@router.delete("/{item_id}", status_code=204, dependencies=nodal_only)
def delete_item(item_id: int, db: DB):
    item = _item(db, item_id)
    for evidence in db.scalars(select(ComplianceEvidence).where(ComplianceEvidence.item_id == item.id)):
        _remove_evidence(db, evidence)
    db.flush()
    db.delete(item)
    db.commit()


@router.delete("/{item_id}/evidence/{evidence_id}", status_code=204, dependencies=nodal_only)
def delete_evidence(item_id: int, evidence_id: int, db: DB):
    evidence = db.get(ComplianceEvidence, evidence_id)
    if not evidence or evidence.item_id != item_id:
        raise AppError(404, "not_found")
    _remove_evidence(db, evidence)
    db.commit()
