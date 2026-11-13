"""Import every model module here so Base.metadata is complete for Alembic and create_all."""

from app.audit import AuditLog
from app.models.student import Consent, GuardianLink, StaffAssignment, StoredFile, StudentProfile
from app.models.user import DevEmail, EmailCode, Role, User

__all__ = [
    "AuditLog",
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
