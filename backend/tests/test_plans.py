from datetime import date, timedelta

from sqlalchemy import select, text

from app.audit import AuditLog
from app.models.plan import AccommodationPlan, PlanStatus
from app.models.user import Role
from app.rules.dates import today
from app.rules.provision import is_overdue, next_due, planned_in_term

ADULT = date(2000, 1, 1)
D = date


def test_overdue_rule():
    start = D(2026, 1, 1)
    assert next_due(7, start, None) == D(2026, 1, 8)
    assert not is_overdue(7, start, None, D(2026, 1, 8))  # due today is not yet overdue
    assert is_overdue(7, start, None, D(2026, 1, 9))  # never provided, interval passed
    assert not is_overdue(7, start, D(2026, 1, 5), D(2026, 1, 12))
    assert is_overdue(7, start, D(2026, 1, 5), D(2026, 1, 13))
    assert not is_overdue(None, start, None, D(2030, 1, 1))  # standing arrangement never goes overdue


def test_planned_in_term_rule():
    term = (D(2026, 1, 1), D(2026, 4, 30))  # 120 days
    assert planned_in_term(30, D(2025, 6, 1), None, *term) == 4  # active all term
    assert planned_in_term(30, D(2026, 3, 2), None, *term) == 2  # started mid-term: 60 days
    assert planned_in_term(30, D(2025, 6, 1), D(2026, 1, 31), *term) == 1  # ended in January
    assert planned_in_term(7, D(2026, 6, 1), None, *term) == 0  # not active in this term
    assert planned_in_term(None, D(2025, 6, 1), None, *term) is None  # standing arrangement


def _setup(client, db, make_user):
    student, s = make_user(Role.student, date_of_birth=ADULT)
    staff, st = make_user(Role.support_staff)
    _, other_staff = make_user(Role.support_staff, "staff2@example.com")
    guardian, g = make_user(Role.guardian)
    _, nodal = make_user(Role.nodal_officer)
    url = f"/students/{student.id}"
    client.put(f"{url}/profile", json={}, headers=s)
    client.post(f"{url}/assignments", json={"staff_id": staff.id}, headers=nodal)
    client.post(f"{url}/guardians", json={"guardian_email": guardian.email, "relationship": "Father"}, headers=s)
    return {"url": url, "student": s, "staff": st, "other_staff": other_staff, "guardian": g, "nodal": nodal}


def _plan(start: date, **extra):
    return {
        "start_date": str(start),
        "review_date": str(start + timedelta(days=180)),
        "notes": "Agreed with the student in the planning meeting",
        "items": [
            {"type": "scribe", "details": "Scribe for written exams", "interval_days": 30},
            {"type": "physical_access", "details": "Ground-floor classroom"},
        ],
        **extra,
    }


def _approve(db, plan_id: int):
    """Approval itself is module 5; here the status is set directly."""
    db.get(AccommodationPlan, plan_id).status = PlanStatus.approved
    db.commit()


def test_only_assigned_staff_draft_plans_and_everyone_else_reads_or_is_refused(client, db, make_user):
    ctx = _setup(client, db, make_user)
    plans = f"{ctx['url']}/plans"
    body = _plan(today())

    for who in ("student", "guardian", "nodal"):
        assert client.post(plans, json=body, headers=ctx[who]).status_code == 403
    assert client.post(plans, json=body, headers=ctx["other_staff"]).status_code == 404
    bad_dates = {**body, "review_date": body["start_date"]}
    assert client.post(plans, json=bad_dates, headers=ctx["staff"]).status_code == 422
    assert client.post(plans, json={**body, "items": []}, headers=ctx["staff"]).status_code == 422
    plan_id = client.post(plans, json=body, headers=ctx["staff"]).json()["id"]

    for who in ("student", "guardian", "staff", "nodal"):
        listed = client.get(plans, headers=ctx[who]).json()["plans"]
        assert [p["status"] for p in listed] == ["draft"] and listed[0]["is_active"] is False
    assert client.get(plans, headers=ctx["other_staff"]).status_code == 404
    assert client.get(f"/plans/{plan_id}", headers=ctx["other_staff"]).status_code == 404

    # Plan content is encrypted at rest and audited without values.
    raw = db.execute(text("SELECT notes FROM accommodation_plans")).scalar()
    assert b"planning meeting" not in bytes(raw)
    assert db.scalar(select(AuditLog.action).where(AuditLog.entity_type == "accommodation_plans")) == "create"

    assert client.post(f"/plans/{plan_id}/submit", headers=ctx["student"]).status_code == 403
    assert client.post(f"/plans/{plan_id}/submit", headers=ctx["staff"]).json()["status"] == "submitted"
    assert client.put(f"/plans/{plan_id}", json=body, headers=ctx["staff"]).json()["code"] == "plan_not_editable"


def test_provision_can_only_be_logged_against_an_active_plan(client, db, make_user):
    ctx = _setup(client, db, make_user)
    start = today() - timedelta(days=40)
    plan_id = client.post(f"{ctx['url']}/plans", json=_plan(start), headers=ctx["staff"]).json()["id"]
    item = client.get(f"/plans/{plan_id}", headers=ctx["staff"]).json()["items"][0]
    log = f"/plan-items/{item['id']}/provisions"
    entry = {"provided_on": str(today() - timedelta(days=35)), "notes": "Mid-term exam"}

    assert client.post(log, json=entry, headers=ctx["staff"]).json()["code"] == "plan_not_active"  # still a draft
    _approve(db, plan_id)
    assert client.post(log, json=entry, headers=ctx["student"]).status_code == 403
    assert client.post(log, json=entry, headers=ctx["nodal"]).status_code == 403
    future = {"provided_on": str(today() + timedelta(days=1))}
    assert client.post(log, json=future, headers=ctx["staff"]).json()["code"] == "provision_date_invalid"
    assert client.post(log, json=entry, headers=ctx["staff"]).status_code == 201

    scribe, access = client.get(f"/plans/{plan_id}", headers=ctx["guardian"]).json()["items"]
    assert scribe["logs"][0]["staff_name"] == "Support Staff" and scribe["logs"][0]["notes"] == "Mid-term exam"
    assert scribe["overdue"] is True and scribe["next_due_on"] == str(today() - timedelta(days=5))
    assert access["overdue"] is False and access["next_due_on"] is None  # standing arrangement

    overdue = client.get("/provisions/overdue", headers=ctx["staff"]).json()
    assert [(row["type"], row["days_overdue"]) for row in overdue] == [("scribe", 5)]
    assert client.get("/provisions/overdue", headers=ctx["other_staff"]).json() == []
    assert len(client.get("/provisions/overdue", headers=ctx["nodal"]).json()) == 1
    assert client.get("/provisions/overdue", headers=ctx["student"]).status_code == 403

    client.post(log, json={"provided_on": str(today())}, headers=ctx["staff"])
    assert client.get("/provisions/overdue", headers=ctx["staff"]).json() == []


def test_planned_versus_delivered_per_student_per_term(client, db, make_user):
    ctx = _setup(client, db, make_user)
    term = {"name": "Monsoon 2026", "start_date": str(today() - timedelta(days=89)), "end_date": str(today() + timedelta(days=30))}
    assert client.post("/terms", json=term, headers=ctx["staff"]).status_code == 403
    term_id = client.post("/terms", json=term, headers=ctx["nodal"]).json()["id"]

    plan_id = client.post(f"{ctx['url']}/plans", json=_plan(today() - timedelta(days=200)), headers=ctx["staff"]).json()["id"]
    _approve(db, plan_id)
    item = client.get(f"/plans/{plan_id}", headers=ctx["staff"]).json()["items"][0]
    for days_ago in (300, 60, 10):  # the first is before the term (and before the plan) and is refused
        client.post(
            f"/plan-items/{item['id']}/provisions",
            json={"provided_on": str(today() - timedelta(days=days_ago))},
            headers=ctx["staff"],
        )

    summary = client.get(f"{ctx['url']}/provision-summary?term_id={term_id}", headers=ctx["student"]).json()
    scribe, access = summary["rows"]
    # 90 days of the term have passed -> 3 planned at one every 30 days; 2 delivered inside the term.
    assert (scribe["planned"], scribe["delivered"], scribe["shortfall"]) == (3, 2, 1)
    assert (access["planned"], access["delivered"], access["shortfall"]) == (None, 0, None)
