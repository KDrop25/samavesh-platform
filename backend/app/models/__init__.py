"""Import every model module here so Base.metadata is complete for Alembic and create_all."""

from app.audit import AuditLog
from app.models.compliance import ComplianceEvidence, ComplianceItem
from app.models.grievance import Grievance, GrievanceEvent, Holiday, Setting
from app.models.plan import AccommodationPlan, PlanDecision, PlanItem, ProvisionLog, Term
from app.models.student import Consent, GuardianLink, StaffAssignment, StoredFile, StudentProfile
from app.models.user import DevEmail, EmailCode, Role, User

__all__ = [
    "AccommodationPlan",
    "AuditLog",
    "ComplianceEvidence",
    "ComplianceItem",
    "Grievance",
    "GrievanceEvent",
    "Holiday",
    "PlanDecision",
    "Setting",
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
