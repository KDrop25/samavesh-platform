import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt

from app.config import get_settings
from app.db import utcnow

SESSION_MINUTES = 30  # idle timeout: the token is re-issued on activity, never extended past this
CODE_MINUTES = 10
CODE_MAX_ATTEMPTS = 5
CODES_PER_HOUR = 5  # otherwise "resend" would reset the attempt cap indefinitely
LOGIN_MAX_FAILURES = 5
LOCKOUT_MINUTES = 15
SCRYPT = {"n": 2**15, "r": 8, "p": 3}  # an OWASP-listed parameter set; stored per hash


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=2**27, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = SCRYPT["n"], SCRYPT["r"], SCRYPT["p"]
    digest = _scrypt(password, salt, n, r, p)
    return f"scrypt${n}${r}${p}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        # Burn the same time as a real check so a missing account is not detectable by timing.
        _scrypt(password, b"0" * 16, SCRYPT["n"], SCRYPT["r"], SCRYPT["p"])
        return False
    _, n, r, p, salt, digest = stored.split("$")
    calc = _scrypt(password, base64.b64decode(salt), int(n), int(r), int(p))
    return hmac.compare_digest(calc, base64.b64decode(digest))


def make_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(code: str, user_id: int, purpose: str) -> str:
    msg = f"{purpose}:{user_id}:{code}".encode()
    return hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()


def create_token(user) -> str:
    now = utcnow()
    claims = {
        "sub": str(user.id),
        "role": user.role.value,
        "tv": user.token_version,
        "iat": now,
        "exp": now + timedelta(minutes=SESSION_MINUTES),
    }
    return jwt.encode(claims, get_settings().secret_key, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.InvalidTokenError:  # includes expired
        return None
