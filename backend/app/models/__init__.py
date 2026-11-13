"""Import every model module here so Base.metadata is complete for Alembic and create_all."""

from app.audit import AuditLog
from app.models.compliance import ComplianceEvidence, ComplianceItem
from app.models.plan import AccommodationPlan, PlanItem, ProvisionLog, Term
from app.models.student import Consent, GuardianLink, StaffAssignment, StoredFile, StudentProfile
from app.models.user import DevEmail, EmailCode, Role, User

__all__ = [
    "AccommodationPlan",
    "AuditLog",
    "ComplianceEvidence",
    "ComplianceItem",
    "PlanItem",
    "ProvisionLog",
    "Term",
    "Consent",
    "DevEmail",
    "EmailCode",
    "GuardianLink",
    "Role",
    "StaffAssignment",
    "StoredFile",
    "StudentProfile",
    "User",
]
