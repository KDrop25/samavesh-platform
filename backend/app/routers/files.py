"""Encrypted file storage (disability certificates, compliance evidence).

Files travel browser <-> API directly, because the frontend host caps request bodies well below
10 MB. So these two transfer endpoints are authorised by a short-lived, single-purpose signed
token instead of the session: the token is issued only after the normal access check.
"""

import hashlib
import re
from typing import Literal

from fastapi import APIRouter, UploadFile
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import get_settings
from app.deps import DB, CurrentUser
from app.errors import AppError
from app.models.student import StoredFile, StudentProfile
from app.models.user import User
from app.permissions import can_edit_profile, can_view_student, require_student_access
from app.security import create_purpose_token, decode_purpose_token

router = APIRouter(prefix="/files", tags=["files"])

MAX_BYTES = 10 * 1024 * 1024
# Allowed types, each checked against the file's leading bytes rather than trusting the browser.
SIGNATURES = {"application/pdf": b"%PDF", "image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG"}
UPLOAD_MINUTES, DOWNLOAD_MINUTES = 15, 1


class UploadTokenIn(BaseModel):
    purpose: Literal["certificate"]
    ref_id: int  # certificate: the student's user id
    # Same-site path only: "/" then a non-slash, so "//host" and absolute URLs are rejected.
    return_to: str = Field(pattern=r"^/([\w\-.%][\w\-/?=&.%]*)?$", max_length=200)


def _check_upload_access(db, user: User, purpose: str, ref_id: int) -> None:
    if purpose == "certificate":
        student = require_student_access(db, user, ref_id)
        profile = db.scalar(select(StudentProfile.id).where(StudentProfile.student_id == ref_id))
        if not can_edit_profile(db, user, student):
            raise AppError(403, "forbidden")
        if not profile:
            raise AppError(409, "profile_required")


def _can_download(db, user: User, file: StoredFile) -> bool:
    if file.purpose == "certificate":
        student_id = db.scalar(
            select(StudentProfile.student_id).where(StudentProfile.certificate_file_id == file.id)
        )
        return student_id is not None and can_view_student(db, user, student_id)
    return False


@router.post("/tokens/upload")
def upload_token(body: UploadTokenIn, db: DB, user: CurrentUser):
    _check_upload_access(db, user, body.purpose, body.ref_id)
    token = create_purpose_token(
        "upload", UPLOAD_MINUTES, purpose=body.purpose, ref=body.ref_id, uid=user.id, back=body.return_to
    )
    return {"token": token}


@router.post("/{file_id}/token")
def download_token(file_id: int, db: DB, user: CurrentUser):
    file = db.get(StoredFile, file_id)
    if not file or not _can_download(db, user, file):
        raise AppError(404, "not_found")
    return {"token": create_purpose_token("download", DOWNLOAD_MINUTES, fid=file.id)}


def _back(path: str, **params) -> RedirectResponse:
    """Send the browser back to the page it came from (a signed, same-site path) with a result."""
    query = "&".join(f"{key}={value}" for key, value in params.items())
    separator = "&" if "?" in path else "?"
    return RedirectResponse(f"{get_settings().frontend_origin}{path}{separator}{query}", status_code=303)


@router.post("")
def upload(token: str, file: UploadFile, db: DB):
    """Plain HTML form post (works without JavaScript); answers with a redirect back to the page."""
    claims = decode_purpose_token(token, "upload")
    if not claims:
        raise AppError(401, "upload_link_expired")
    back = claims["back"]
    user = db.get(User, claims["uid"])
    if not user or not user.is_active:
        raise AppError(401, "not_authenticated")
    db.info["actor"] = (user.id, user.role.value)

    # ponytail: the framework spools the whole upload to a temp file before we get here, so a
    # larger body costs disk (not memory) until rejected. Put a body-size limit on the reverse
    # proxy if this is ever exposed to hostile traffic.
    data = file.file.read(MAX_BYTES + 1)
    if not data:
        return _back(back, upload_error="file_missing")
    if len(data) > MAX_BYTES:
        return _back(back, upload_error="file_too_large")
    content_type = next((ct for ct, magic in SIGNATURES.items() if data.startswith(magic)), None)
    if not content_type:
        return _back(back, upload_error="file_type")

    _check_upload_access(db, user, claims["purpose"], claims["ref"])  # access may have changed since issue
    stored = StoredFile(
        purpose=claims["purpose"],
        filename=re.sub(r"[^\w.\- ]", "_", file.filename or "document")[:255],
        content_type=content_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
        uploaded_by=user.id,
    )
    db.add(stored)
    db.flush()
    if claims["purpose"] == "certificate":
        profile = db.scalar(select(StudentProfile).where(StudentProfile.student_id == claims["ref"]))
        old = profile.certificate_file_id and db.get(StoredFile, profile.certificate_file_id)
        profile.certificate_file_id = stored.id
        if old:
            db.flush()
            db.delete(old)  # replaced: do not keep sensitive documents nobody can reach
    db.commit()
    return _back(back, uploaded="1")


@router.get("/{file_id}")
def download(file_id: int, token: str, db: DB):
    claims = decode_purpose_token(token, "download")
    file = db.get(StoredFile, file_id) if claims and claims.get("fid") == file_id else None
    if not file:
        raise AppError(404, "not_found")
    return Response(
        content=file.data,
        media_type=file.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
