from datetime import date, timedelta

from sqlalchemy import select, text, update

from app.audit import AuditLog
from app.db import utcnow
from app.models.grievance import Grievance, GrievanceEvent
from app.models.user import Role
from app.routers.grievances import flag_overdue_grievances
from app.rules.working_days import escalation_due, working_days_between

D = date
MON_SAT = {0, 1, 2, 3, 4, 5}
COMPLAINT = {
    "category": "physical_accessibility",
    "subject": "Library ramp is blocked",
    "description": "The ramp at the library entrance has been blocked by furniture for two weeks.",
}


def test_working_day_rule():
    monday = D(2026, 11, 2)
    assert working_days_between(monday, monday, MON_SAT, set()) == 0
    assert working_days_between(monday, D(2026, 11, 3), MON_SAT, set()) == 1
    assert working_days_between(monday, D(2026, 11, 9), MON_SAT, set()) == 6  # Sunday skipped
    assert working_days_between(monday, D(2026, 11, 9), {0, 1, 2, 3, 4}, set()) == 5  # Mon-Fri week
    assert working_days_between(monday, D(2026, 11, 9), MON_SAT, {D(2026, 11, 4)}) == 5  # holiday skipped

    # 15 working days (Mon-Sat) after Mon 2 Nov is Thu 19 Nov; escalation is due the day after.
    assert working_days_between(monday, D(2026, 11, 19), MON_SAT, set()) == 15
    assert not escalation_due(monday, D(2026, 11, 19), 15, MON_SAT, set())
    assert escalation_due(monday, D(2026, 11, 20), 15, MON_SAT, set())
    assert not escalation_due(monday, D(2026, 11, 20), 15, MON_SAT, {D(2026, 11, 10)})  # a holiday buys a day


def test_anonymous_grievance_stores_nothing_identifying_even_when_signed_in(client, db, make_user):
    student, s = make_user(Role.student, date_of_birth=D(2000, 1, 1))
    body = {**COMPLAINT, "anonymous": True, "complainant_name": "Should be ignored"}
    reference = client.post("/grievances", json=body, headers=s).json()["reference"]
    assert reference.startswith("GRV-") and len(reference) == 18

    grievance = db.scalar(select(Grievance))
    assert (grievance.is_anonymous, grievance.complainant_user_id, grievance.complainant_name) == (True, None, None)
    assert grievance.contact_email is None
    # No row anywhere links this grievance to the student's account.
    logged = db.scalars(select(AuditLog).where(AuditLog.entity_type.in_(("grievances", "grievance_events")))).all()
    assert logged and all((row.actor_user_id, row.actor_role) == (None, "complainant") for row in logged)

    # Content is encrypted at rest.
    raw = db.execute(text("SELECT subject, description FROM grievances")).one()
    assert b"ramp" not in bytes(raw[0]) and b"furniture" not in bytes(raw[1])

    # Status can be checked with the reference alone - no sign-in.
    tracked = client.get(f"/grievances/track/{reference.lower()}").json()
    assert tracked["status"] == "received" and [e["status"] for e in tracked["events"]] == ["received"]
    assert "description" not in tracked and "subject" not in tracked
    assert client.get("/grievances/track/GRV-AAAA-BBBB-CCCC").json()["code"] == "reference_not_found"


def test_named_grievance_identity_is_visible_to_the_grievance_officer_only(client, db, make_user):
    student, s = make_user(Role.student, full_name="Asha Verma", date_of_birth=D(2000, 1, 1))
    _, officer = make_user(Role.grievance_officer)
    _, admin = make_user(Role.administrator)
    _, nodal = make_user(Role.nodal_officer)
    _, staff = make_user(Role.support_staff)

    client.post("/grievances", json=COMPLAINT, headers=s)  # named, signed in
    walk_in = {**COMPLAINT, "complainant_name": "R. Iyer", "contact_email": "R.Iyer@Example.com"}
    assert client.post("/grievances", json=COMPLAINT).json()["code"] == "name_required"  # named needs a name
    assert client.post("/grievances", json=walk_in).status_code == 201  # named, no account

    raw = db.execute(text("SELECT complainant_name, complainant_user_id, contact_email FROM grievances")).all()
    assert all(b"Asha" not in bytes(r[0]) and b"Iyer" not in bytes(r[0]) for r in raw)
    assert all(str(student.id).encode() != bytes(r[1] or b"") for r in raw)  # not a plain user id

    for who in (s, admin, nodal, staff, {}):
        assert client.get("/grievances", headers=who).status_code in (401, 403)
        assert client.get("/grievances/1", headers=who).status_code in (401, 403)

    first = client.get("/grievances/1", headers=officer).json()
    assert (first["complainant_name"], first["has_account"], first["contact_email"]) == ("Asha Verma", True, student.email)
    second = client.get("/grievances/2", headers=officer).json()
    assert (second["complainant_name"], second["has_account"], second["contact_email"]) == ("R. Iyer", False, "r.iyer@example.com")

    # Escalated cases reach the administrator with content and timeline, but never identity.
    client.post("/grievances/1/status", json={"status": "under_review", "internal_note": "Spoke to Asha Verma"}, headers=officer)
    client.post("/grievances/1/status", json={"status": "escalated", "public_note": "Referred to the Registrar"}, headers=officer)
    assert client.get("/grievances/escalated", headers=officer).status_code == 403
    escalated = client.get("/grievances/escalated", headers=admin).json()
    assert [case["reference"] for case in escalated] == [first["reference"]]
    assert escalated[0]["description"] == COMPLAINT["description"]
    assert [e["status"] for e in escalated[0]["events"]] == ["received", "under_review", "escalated"]
    assert "Asha" not in str(escalated) and student.email not in str(escalated)
    assert "complainant_name" not in escalated[0] and "internal_note" not in str(escalated)


def test_status_moves_received_to_review_to_resolved_or_escalated_with_timestamps(client, db, make_user):
    _, officer = make_user(Role.grievance_officer)
    reference = client.post("/grievances", json={**COMPLAINT, "anonymous": True}).json()["reference"]
    change = "/grievances/1/status"

    assert client.post(change, json={"status": "resolved"}, headers=officer).json()["code"] == "invalid_transition"
    assert client.get("/grievances/1", headers=officer).json()["next_statuses"] == ["under_review"]
    review = {"status": "under_review", "public_note": "Assigned to the estate office", "internal_note": "Call back Friday"}
    assert client.post(change, json=review, headers=officer).json()["status"] == "under_review"
    assert client.get("/grievances/1", headers=officer).json()["next_statuses"] == ["resolved", "escalated"]
    client.post(change, json={"status": "resolved", "public_note": "Ramp cleared and signage added"}, headers=officer)
    assert client.post(change, json={"status": "under_review"}, headers=officer).json()["code"] == "invalid_transition"

    tracked = client.get(f"/grievances/track/{reference}").json()
    assert [(e["status"], e["public_note"]) for e in tracked["events"]] == [
        ("received", None),
        ("under_review", "Assigned to the estate office"),
        ("resolved", "Ramp cleared and signage added"),
    ]
    assert all(e["at"] for e in tracked["events"])  # every status has its timestamp
    assert "Call back Friday" not in str(tracked)  # internal notes stay internal
    officer_view = client.get("/grievances/1", headers=officer).json()
    assert officer_view["events"][1]["internal_note"] == "Call back Friday"


def test_grievances_under_review_too_long_are_flagged_for_escalation(client, db, make_user):
    _, officer = make_user(Role.grievance_officer)
    _, admin = make_user(Role.administrator)
    _, staff = make_user(Role.support_staff)
    for _ in range(2):
        client.post("/grievances", json={**COMPLAINT, "anonymous": True})
    client.post("/grievances/1/status", json={"status": "under_review"}, headers=officer)
    client.post("/grievances/2/status", json={"status": "under_review"}, headers=officer)
    long_ago = utcnow() - timedelta(days=30)  # 30 calendar days is well over 15 working days
    db.execute(
        update(GrievanceEvent)
        .where(GrievanceEvent.grievance_id == 1, GrievanceEvent.status == "under_review")
        .values(created_at=long_ago)
    )
    db.commit()

    # The threshold is configurable: at 60 working days nothing is flagged yet.
    settings = {"working_weekdays": [0, 1, 2, 3, 4, 5], "escalation_working_days": 60}
    assert client.put("/settings", json=settings, headers=staff).status_code == 403
    assert client.put("/settings", json={**settings, "working_weekdays": [9]}, headers=admin).status_code == 422
    assert client.put("/settings", json=settings, headers=admin).status_code == 200
    assert flag_overdue_grievances(db) == []

    client.put("/settings", json={**settings, "escalation_working_days": 15}, headers=officer)
    flagged = flag_overdue_grievances(db)
    db.commit()
    assert [g.id for g in flagged] == [1]
    assert flag_overdue_grievances(db) == []  # flagged once, not on every run

    cases = {case["id"]: case for case in client.get("/grievances", headers=officer).json()}
    assert cases[1]["escalation_flagged"] is True and cases[1]["working_days_under_review"] > 15
    assert cases[2]["escalation_flagged"] is False and cases[2]["working_days_under_review"] == 0
    assert [case["id"] for case in client.get("/grievances/escalated", headers=admin).json()] == [1]

    holiday = {"day": "2026-12-25", "name": "Christmas"}
    assert client.post("/holidays", json=holiday, headers=admin).status_code == 201
    assert client.post("/holidays", json=holiday, headers=admin).json()["code"] == "holiday_exists"
    saved = client.get("/settings", headers=officer).json()
    assert saved["escalation_working_days"] == 15 and saved["holidays"][0]["name"] == "Christmas"
    assert client.delete(f"/holidays/{saved['holidays'][0]['id']}", headers=admin).status_code == 204
