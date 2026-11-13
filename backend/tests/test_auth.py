from datetime import timedelta

import jwt
from fastapi.routing import APIRoute
from sqlalchemy import select

from app import security
from app.config import get_settings
from app.db import utcnow
from app.deps import current_user
from app.main import app
from app.models.user import EmailCode, Role, User

STUDENT = {
    "email": "Asha@Example.com",
    "password": "a long passphrase",
    "full_name": "Asha Verma",
    "role": "student",
    "date_of_birth": "2004-05-01",
}

# Routes that are reachable without signing in. Everything else must depend on current_user.
PUBLIC = {
    "GET /health",
    "POST /auth/register",
    "POST /auth/resend",
    "POST /auth/verify",
    "POST /auth/login",
    "POST /auth/password/forgot",
    "POST /auth/password/reset",
    "GET /dev/emails",
    # File transfer: authorised by a short-lived single-purpose signed token, issued only after
    # an access check on an authenticated endpoint (see app/routers/files.py).
    "POST /files",
    "GET /files/{file_id}",
    # Grievances can be raised and tracked without an account (GET /grievances is NOT public).
    "POST /grievances",
    "GET /grievances/track/{reference}",
    # Scheduler entry point: authorised by the shared JOBS_SECRET header, disabled when unset.
    "POST /internal/jobs/run",
}


def _uses(dependant, fn) -> bool:
    return dependant.call is fn or any(_uses(d, fn) for d in dependant.dependencies)


def test_every_route_requires_auth_unless_allowlisted():
    seen = set()
    # FastAPI nests included routers; flatten them to per-route contexts (full path + dependant).
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    for nested in app.routes:
        if hasattr(nested, "effective_route_contexts"):
            routes += list(nested.effective_route_contexts())
    for route in routes:
        for method in route.methods - {"HEAD"}:
            key = f"{method} {route.path}"
            seen.add(key)
            if key not in PUBLIC:
                assert _uses(route.dependant, current_user), f"{key} has no auth dependency"
    assert PUBLIC <= seen, f"stale allowlist entries: {PUBLIC - seen}"


def test_register_verify_login(client, db, last_code):
    assert client.post("/auth/register", json=STUDENT).status_code == 201
    user = db.scalar(select(User))
    assert user.email == "asha@example.com"
    assert user.password_hash.startswith("scrypt$") and "passphrase" not in user.password_hash

    creds = {"email": STUDENT["email"], "password": STUDENT["password"]}
    assert client.post("/auth/login", json=creds).json()["code"] == "email_not_verified"

    r = client.post("/auth/verify", json={"email": STUDENT["email"], "code": last_code(user.email)})
    assert r.status_code == 200 and r.json()["expires_in"] == 30 * 60

    token = client.post("/auth/login", json=creds).json()["token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "student"


def test_student_must_give_date_of_birth_and_staff_roles_cannot_self_register(client):
    assert client.post("/auth/register", json={**STUDENT, "date_of_birth": None}).status_code == 422
    assert client.post("/auth/register", json={**STUDENT, "role": "administrator"}).status_code == 422


def test_code_locks_after_five_wrong_attempts(client, db, last_code):
    client.post("/auth/register", json=STUDENT)
    good = last_code("asha@example.com")
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        r = client.post("/auth/verify", json={"email": STUDENT["email"], "code": bad})
        assert r.json()["code"] == "code_invalid"
    r = client.post("/auth/verify", json={"email": STUDENT["email"], "code": good})
    assert r.json()["code"] == "code_locked"


def test_code_expires_after_ten_minutes(client, db, last_code):
    client.post("/auth/register", json=STUDENT)
    row = db.scalar(select(EmailCode))
    assert timedelta(minutes=9) < row.expires_at - utcnow() <= timedelta(minutes=10)
    assert row.code_hash != last_code("asha@example.com")  # stored hashed
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    r = client.post("/auth/verify", json={"email": STUDENT["email"], "code": last_code("asha@example.com")})
    assert r.json()["code"] == "code_expired"


def test_resend_is_rate_limited(client):
    client.post("/auth/register", json=STUDENT)
    codes = [client.post("/auth/resend", json={"email": STUDENT["email"]}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 200, 429]


def test_login_locks_after_five_failures(client, make_user):
    user, _ = make_user(Role.student)
    wrong = {"email": user.email, "password": "not the password"}
    for _ in range(5):
        assert client.post("/auth/login", json=wrong).json()["code"] == "invalid_credentials"
    right = {"email": user.email, "password": "correct horse battery"}
    assert client.post("/auth/login", json=right).json()["code"] == "account_locked"


def test_expired_and_revoked_tokens_are_rejected(client, make_user):
    user, headers = make_user(Role.student)
    assert client.get("/auth/me", headers=headers).status_code == 200

    old = utcnow() - timedelta(minutes=31)
    claims = {"sub": str(user.id), "tv": 0, "iat": old, "exp": old + timedelta(minutes=30)}
    expired = jwt.encode(claims, get_settings().secret_key, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.post("/auth/refresh", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_rbac_and_staff_invite_flow(client, make_user, last_code):
    _, student = make_user(Role.student)
    _, admin = make_user(Role.administrator)
    assert client.get("/admin/users").status_code == 401
    assert client.get("/admin/users", headers=student).status_code == 403
    assert client.get("/admin/users", headers=admin).status_code == 200

    invite = {"email": "nodal@example.com", "full_name": "N. Officer", "role": "nodal_officer"}
    assert client.post("/admin/users", json=invite, headers=student).status_code == 403
    created = client.post("/admin/users", json=invite, headers=admin)
    assert created.status_code == 201
    assert client.post("/admin/users", json=invite, headers=admin).json()["code"] == "email_taken"

    # Public registration must not be able to take over the invited staff account.
    client.post("/auth/register", json={**STUDENT, "email": invite["email"]})
    client.post("/auth/password/forgot", json={"email": invite["email"]})
    reset = {"email": invite["email"], "code": last_code(invite["email"]), "new_password": "nodal passphrase"}
    assert client.post("/auth/password/reset", json=reset).status_code == 200
    session = client.post("/auth/login", json={"email": invite["email"], "password": "nodal passphrase"})
    assert session.json()["user"]["role"] == "nodal_officer"

    # Deactivation signs the user out and blocks sign-in.
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    uid = created.json()["id"]
    assert client.patch(f"/admin/users/{uid}", json={"is_active": False}, headers=admin).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401
