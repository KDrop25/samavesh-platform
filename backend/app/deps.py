from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models.user import Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def current_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    claims = decode_token(creds.credentials) if creds else None
    user = db.get(User, int(claims["sub"])) if claims else None
    if not user or not user.is_active or user.token_version != claims.get("tv"):
        raise AppError(401, "not_authenticated")
    db.info["actor"] = (user.id, user.role.value)  # read by the audit listener
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*roles: Role):
    """Server-side RBAC gate. Use on every router or route that is not public."""

    def dep(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden")
        return user

    return dep
