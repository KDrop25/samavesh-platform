from datetime import date, timedelta

from sqlalchemy import select, text

from app.audit import AuditLog
from app.models.student import Consent, StudentProfile
from app.models.user import Role
from app.rules.dates import age_on, is_minor, today
from app.security import create_purpose_token

ADULT = date(2000, 1, 1)
MINOR = today() - timedelta(days=15 * 365)
PDF = b"%PDF-1.4 disability certificate for the student"


def test_age_rule():
    assert age_on(date(2008, 3, 10), date(2026, 3, 9)) == 17
    assert age_on(date(2008, 3, 10), date(2026, 3, 10)) == 18
    assert is_minor(date(2008, 3, 10), date(2026, 3, 9))
    assert not is_minor(date(2008, 3, 10), date(2026, 3, 10))
    assert is_minor(None, date(2026, 1, 1))  # unknown age never skips consent


def test_profile_is_visible_only_to_the_right_people(client, db, make_user):
    student, s = make_user(Role.student, date_of_birth=ADULT)
    _, other_student = make_user(Role.student, "other@example.com", date_of_birth=ADULT)
    guardian, g = make_user(Role.guardian)
    _, other_guardian = make_user(Role.guardian, "guardian2@example.com")
    staff, st = make_user(Role.support_staff)
    _, other_staff = make_user(Role.support_staff, "staff2@example.com")
    _, nodal = make_user(Role.nodal_officer)
    _, admin = make_user(Role.administrator)
    _, grievance = make_user(Role.grievance_officer)
    url = f"/students/{student.id}"

    profile = {"support_needs": "Needs a scribe for exams", "disability_categories": ["low_vision"]}
    assert client.put(f"{url}/profile", json=profile, headers=s).status_code == 200
    link = client.post(f"{url}/guardians", json={"guardian_email": guardian.email, "relationship": "Mother"}, headers=s)
    assert link.json()["status"] == "active"
    assert client.post(f"{url}/assignments", json={"staff_id": staff.id}, headers=st).status_code == 403
    assert client.post(f"{url}/assignments", json={"staff_id": staff.id}, headers=nodal).status_code == 201

    expected = [
        (s, 200), (g, 200), (st, 200), (nodal, 200), (admin, 200),
        (other_student, 404), (other_guardian, 404), (other_staff, 404), (grievance, 403), ({}, 401),
    ]  # fmt: skip
    for headers, status in expected:
        assert client.get(url, headers=headers).status_code == status
    assert client.get(url, headers=g).json()["profile"]["support_needs"] == "Needs a scribe for exams"

    # Lists are filtered the same way; guardians and staff cannot edit what they should not.
    assert [x["id"] for x in client.get("/students", headers=st).json()] == [student.id]
    assert client.get("/students", headers=other_staff).json() == []
    assert len(client.get("/students", headers=nodal).json()) == 2
    assert client.put(f"{url}/profile", json=profile, headers=g).status_code == 403
    assert client.put(f"{url}/profile", json=profile, headers=other_staff).status_code == 404

    # Encrypted at rest, and the audit trail records the change without the sensitive values.
    raw = db.execute(text("SELECT support_needs, disability_categories FROM student_profiles")).one()
    assert b"scribe" not in bytes(raw[0]) and b"low_vision" not in bytes(raw[1])
    logged = db.scalars(select(AuditLog).where(AuditLog.entity_type == "student_profiles")).all()
    assert [(row.action, row.actor_user_id) for row in logged] == [("create", student.id)]
    assert "scribe" not in str([row.changed_fields for row in db.scalars(select(AuditLog))])


def test_under_18_profile_needs_recorded_consent_first(client, db, make_user):
    minor, m = make_user(Role.student, date_of_birth=MINOR)
    guardian, g = make_user(Role.guardian, full_name="Sunita Menon")
    staff, st = make_user(Role.support_staff)
    _, nodal = make_user(Role.nodal_officer)
    url = f"/students/{minor.id}"
    client.post(f"{url}/guardians", json={"guardian_email": guardian.email, "relationship": "Mother"}, headers=m)
    client.post(f"{url}/assignments", json={"staff_id": staff.id}, headers=nodal)
    profile = {"support_needs": "Wheelchair access"}

    assert client.put(f"{url}/profile", json=profile, headers=st).json()["code"] == "consent_required"
    assert client.put(f"{url}/profile", json=profile, headers=nodal).json()["code"] == "consent_required"
    assert client.put(f"{url}/profile", json=profile, headers=m).status_code == 403  # minors cannot self-create
    assert db.scalar(select(StudentProfile)) is None

    assert client.get(url, headers=g).json()["can"]["give_consent"] is True
    assert client.post(f"{url}/consent", json={}, headers=g).status_code == 201
    consent = db.scalar(select(Consent))
    assert (consent.consenting_person_name, consent.relationship) == ("Sunita Menon", "Mother")
    assert (consent.consent_date, consent.method, consent.consenting_user_id) == (today(), "in_app", guardian.id)
    assert client.post(f"{url}/consent", json={}, headers=g).json()["code"] == "consent_exists"

    assert client.put(f"{url}/profile", json=profile, headers=st).status_code == 200
    assert db.scalar(select(StudentProfile)).consent_id == consent.id


def test_staff_can_record_a_paper_consent_with_person_and_date(client, db, make_user):
    minor, _ = make_user(Role.student, date_of_birth=MINOR)
    _, nodal = make_user(Role.nodal_officer)
    _, unassigned_staff = make_user(Role.support_staff)
    adult, _ = make_user(Role.student, "adult@example.com", date_of_birth=ADULT)
    url = f"/students/{minor.id}/consent"
    paper = {"consenting_person_name": "R. Menon", "relationship": "Father", "consent_date": str(today())}

    assert client.post(url, json=paper, headers=unassigned_staff).status_code == 404
    assert client.post(url, json={}, headers=nodal).json()["code"] == "consent_details_required"
    future = {**paper, "consent_date": str(today() + timedelta(days=1))}
    assert client.post(url, json=future, headers=nodal).json()["code"] == "date_in_future"
    assert client.post(url, json=paper, headers=nodal).status_code == 201
    consent = db.scalar(select(Consent))
    assert (consent.consenting_person_name, consent.method) == ("R. Menon", "recorded_by_staff")
    assert client.post(f"/students/{adult.id}/consent", json=paper, headers=nodal).json()["code"] == "consent_not_needed"


def test_guardian_invitation_activates_when_the_guardian_verifies_their_email(client, make_user, last_code):
    student, s = make_user(Role.student, date_of_birth=ADULT)
    url = f"/students/{student.id}"
    invite = {"guardian_email": "Parent@Example.com", "relationship": "Father"}
    assert client.post(f"{url}/guardians", json=invite, headers=s).json()["status"] == "invited"
    assert client.post(f"{url}/guardians", json=invite, headers=s).json()["code"] == "already_linked"

    account = {"email": "parent@example.com", "password": "guardian passphrase", "full_name": "P. Verma", "role": "guardian"}
    client.post("/auth/register", json=account)
    session = client.post("/auth/verify", json={"email": account["email"], "code": last_code(account["email"])})
    guardian = {"Authorization": f"Bearer {session.json()['token']}"}
    assert client.get(url, headers=guardian).status_code == 200

    link_id = client.get(url, headers=s).json()["guardians"][0]["id"]
    assert client.delete(f"{url}/guardians/{link_id}", headers=s).status_code == 204
    assert client.get(url, headers=guardian).status_code == 404  # revoked: access ends immediately


def test_certificate_upload_is_capped_typed_encrypted_and_access_controlled(client, db, make_user):
    student, s = make_user(Role.student, date_of_birth=ADULT)
    _, other = make_user(Role.student, "other@example.com", date_of_birth=ADULT)
    request = {"purpose": "certificate", "ref_id": student.id, "return_to": f"/students/{student.id}"}

    assert client.post("/files/tokens/upload", json=request, headers=s).json()["code"] == "profile_required"
    client.put(f"/students/{student.id}/profile", json={}, headers=s)
    assert client.post("/files/tokens/upload", json=request, headers=other).status_code == 404
    assert client.post("/files/tokens/upload", json={**request, "return_to": "//evil.example"}, headers=s).status_code == 422
    token = client.post("/files/tokens/upload", json=request, headers=s).json()["token"]

    def upload(data: bytes, name="certificate.pdf", tok=token):
        return client.post(f"/files?token={tok}", files={"file": (name, data)}, follow_redirects=False)

    assert "upload_error=file_too_large" in upload(b"%PDF" + bytes(10 * 1024 * 1024)).headers["location"]
    assert "upload_error=file_type" in upload(b"MZ this is an executable", "certificate.pdf").headers["location"]
    ok = upload(PDF)
    assert ok.status_code == 303 and ok.headers["location"].endswith(f"/students/{student.id}?uploaded=1")
    assert b"disability certificate" not in bytes(db.execute(text("SELECT data FROM files")).scalar())

    file_id = client.get(f"/students/{student.id}", headers=s).json()["profile"]["certificate"]["id"]
    assert client.post(f"/files/{file_id}/token", headers=other).status_code == 404
    download = client.post(f"/files/{file_id}/token", headers=s).json()["token"]
    got = client.get(f"/files/{file_id}?token={download}")
    assert got.content == PDF and got.headers["content-type"] == "application/pdf"

    # Tokens are single-purpose: none of them works as anything else.
    assert client.get(f"/files/{file_id}?token={token}").status_code == 404
    assert client.get(f"/files/{file_id + 1}?token={download}").status_code == 404
    assert upload(PDF, tok=download).status_code == 401
    assert upload(PDF, tok=s["Authorization"].split()[1]).status_code == 401
    forged_session = create_purpose_token("upload", 5, sub=str(student.id), tv=0)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged_session}"}).status_code == 401
