from datetime import date, timedelta

from sqlalchemy import select, update

from app.config import get_settings
from app.db import utcnow
from app.models.grievance import GrievanceEvent
from app.models.plan import AccommodationPlan
from app.models.user import DevEmail, Role
from app.rules.dates import today
from tests.test_governance import _submitted
from tests.test_grievances import COMPLAINT
from tests.test_plans import _approve, _setup

ADULT = date(2000, 1, 1)


def _kinds(client, headers) -> list[str]:
    return [n["kind"] for n in client.get("/notifications", headers=headers).json()["items"]]


def test_plan_decision_reaches_the_drafter_and_the_student_by_app_and_email(client, db, make_user):
    ctx = _setup(client, db, make_user)
    _, other = make_user(Role.student, "other@example.com", date_of_birth=ADULT)
    plan_id = _submitted(client, ctx)
    client.post(f"/plans/{plan_id}/decision", json={"decision": "approved"}, headers=ctx["nodal"])

    assert _kinds(client, ctx["student"]) == ["plan_approved"]
    assert _kinds(client, ctx["staff"]) == ["plan_approved"]
    assert _kinds(client, other) == [] and _kinds(client, ctx["guardian"]) == []
    inbox = client.get("/notifications", headers=ctx["student"]).json()
    assert inbox["unread"] == 1 and inbox["items"][0]["params"]["plan_id"] == plan_id

    # The email tells them to sign in and nothing about the plan itself.
    body = db.scalar(select(DevEmail.body).where(DevEmail.to == "student@example.com"))
    assert "/login" in body and "Scribe" not in body


def test_grievance_updates_reach_a_named_complainant_and_an_anonymous_contact_by_email(client, db, make_user):
    _, student = make_user(Role.student, date_of_birth=ADULT)
    _, officer = make_user(Role.grievance_officer)
    client.post("/grievances", json=COMPLAINT, headers=student)
    client.post("/grievances", json={**COMPLAINT, "anonymous": True, "contact_email": "walkin@example.com"})
    client.post("/grievances/1/status", json={"status": "under_review"}, headers=officer)
    client.post("/grievances/2/status", json={"status": "under_review"}, headers=officer)

    inbox = client.get("/notifications", headers=student).json()["items"]
    assert [(n["kind"], n["params"]["status"]) for n in inbox] == [("grievance_status", "under_review")]
    body = db.scalar(select(DevEmail.body).where(DevEmail.to == "walkin@example.com"))
    assert "/track" in body and "ramp" not in body.lower()  # no complaint content in email


def test_reminders_are_sent_once_per_day(client, db, make_user, monkeypatch):
    ctx = _setup(client, db, make_user)
    client.post(
        "/compliance",
        json={"description": "Access audit", "source_obligation": "s", "due_date": str(today() + timedelta(days=3)),
              "status": "partially", "reason": "In progress"},
        headers=ctx["nodal"],
    )
    plan_id = _submitted(client, ctx)
    _approve(db, plan_id)
    db.get(AccommodationPlan, plan_id).review_date = today() + timedelta(days=5)
    db.commit()
    monkeypatch.setattr(get_settings(), "jobs_secret", "s3cret")

    first = client.post("/internal/jobs/run", headers={"X-Jobs-Secret": "s3cret"}).json()
    assert first == {"escalations": 0, "compliance_reminders": 1, "plan_reviews": 1}
    assert client.post("/internal/jobs/run", headers={"X-Jobs-Secret": "s3cret"}).json() == {
        "escalations": 0, "compliance_reminders": 0, "plan_reviews": 0,
    }
    assert _kinds(client, ctx["nodal"]) == ["compliance_due"]
    assert _kinds(client, ctx["staff"]) == ["plan_review"]


def test_escalation_flag_notifies_administrators(client, db, make_user, monkeypatch):
    _, admin = make_user(Role.administrator)
    _, officer = make_user(Role.grievance_officer)
    client.post("/grievances", json={**COMPLAINT, "anonymous": True})
    client.post("/grievances/1/status", json={"status": "under_review"}, headers=officer)
    db.execute(update(GrievanceEvent).values(created_at=utcnow() - timedelta(days=60)))
    db.commit()
    monkeypatch.setattr(get_settings(), "jobs_secret", "s3cret")

    assert client.post("/internal/jobs/run", headers={"X-Jobs-Secret": "s3cret"}).json()["escalations"] == 1
    assert _kinds(client, admin) == ["escalation"]


def test_job_endpoint_is_off_without_a_secret_and_refuses_a_wrong_one(client, monkeypatch):
    assert client.post("/internal/jobs/run").status_code == 403  # no JOBS_SECRET configured
    monkeypatch.setattr(get_settings(), "jobs_secret", "s3cret")
    assert client.post("/internal/jobs/run", headers={"X-Jobs-Secret": "nope"}).status_code == 403
    assert client.post("/internal/jobs/run", headers={"X-Jobs-Secret": "s3cret"}).status_code == 200


def test_notifications_are_private_and_can_be_marked_read(client, db, make_user):
    ctx = _setup(client, db, make_user)
    plan_id = _submitted(client, ctx)
    client.post(f"/plans/{plan_id}/decision", json={"decision": "approved"}, headers=ctx["nodal"])
    assert client.get("/notifications").status_code == 401

    notice_id = client.get("/notifications", headers=ctx["student"]).json()["items"][0]["id"]
    assert client.post(f"/notifications/{notice_id}/read", headers=ctx["staff"]).status_code == 404
    assert client.post(f"/notifications/{notice_id}/read", headers=ctx["student"]).status_code == 200
    assert client.get("/notifications", headers=ctx["student"]).json()["unread"] == 0
    assert client.get("/notifications", headers=ctx["staff"]).json()["unread"] == 1
    client.post("/notifications/read-all", headers=ctx["staff"])
    assert client.get("/notifications", headers=ctx["staff"]).json()["unread"] == 0
