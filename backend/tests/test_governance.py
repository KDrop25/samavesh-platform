from datetime import timedelta

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.models.plan import PlanDecision
from app.models.user import Role
from app.rules.dates import today
from tests.test_plans import _plan, _setup


def _submitted(client, ctx, start=None) -> int:
    plan_id = client.post(f"{ctx['url']}/plans", json=_plan(start or today()), headers=ctx["staff"]).json()["id"]
    client.post(f"/plans/{plan_id}/submit", headers=ctx["staff"])
    return plan_id


def _plans(client, ctx) -> dict[int, dict]:
    return {p["id"]: p for p in client.get(f"{ctx['url']}/plans", headers=ctx["student"]).json()["plans"]}


def test_a_plan_is_inactive_until_a_nodal_officer_approves_it(client, db, make_user):
    ctx = _setup(client, db, make_user)
    _, admin = make_user(Role.administrator)
    nodal_user = client.get("/auth/me", headers=ctx["nodal"]).json()
    plan_id = _submitted(client, ctx)
    decide = f"/plans/{plan_id}/decision"
    approve = {"decision": "approved", "reason": "Meets the student's documented needs"}

    assert _plans(client, ctx)[plan_id]["is_active"] is False
    assert [p["id"] for p in client.get("/approvals", headers=ctx["nodal"]).json()] == [plan_id]
    assert client.get("/approvals", headers=ctx["staff"]).status_code == 403

    # Only a nodal officer decides - not the drafter, the student, the guardian or an administrator.
    for who in (ctx["staff"], ctx["student"], ctx["guardian"], admin):
        assert client.post(decide, json=approve, headers=who).status_code == 403
    assert _plans(client, ctx)[plan_id]["is_active"] is False

    assert client.post(decide, json=approve, headers=ctx["nodal"]).json()["status"] == "approved"
    plan = _plans(client, ctx)[plan_id]
    assert plan["is_active"] is True
    assert [(d["decision"], d["approver"], d["reason"]) for d in plan["decisions"]] == [
        ("approved", nodal_user["full_name"], "Meets the student's documented needs")
    ]
    assert plan["decisions"][0]["decided_at"]  # timestamp
    assert client.post(decide, json=approve, headers=ctx["nodal"]).json()["code"] == "plan_not_submitted"
    assert client.get("/approvals", headers=ctx["nodal"]).json() == []


def test_approval_before_the_start_date_does_not_make_the_plan_active_yet(client, db, make_user):
    ctx = _setup(client, db, make_user)
    plan_id = _submitted(client, ctx, start=today() + timedelta(days=10))
    client.post(f"/plans/{plan_id}/decision", json={"decision": "approved"}, headers=ctx["nodal"])
    plan = _plans(client, ctx)[plan_id]
    assert (plan["status"], plan["is_active"]) == ("approved", False)


def test_rejection_needs_a_reason_and_the_plan_can_be_edited_and_resubmitted(client, db, make_user):
    ctx = _setup(client, db, make_user)
    plan_id = _submitted(client, ctx)
    decide = f"/plans/{plan_id}/decision"

    assert client.post(decide, json={"decision": "rejected"}, headers=ctx["nodal"]).status_code == 422
    assert client.post(decide, json={"decision": "rejected", "reason": "  "}, headers=ctx["nodal"]).status_code == 422
    reject = {"decision": "rejected", "reason": "Interval for the scribe is missing"}
    assert client.post(decide, json=reject, headers=ctx["nodal"]).json()["status"] == "rejected"
    assert _plans(client, ctx)[plan_id]["is_active"] is False

    assert client.put(f"/plans/{plan_id}", json=_plan(today()), headers=ctx["staff"]).status_code == 200
    assert client.post(f"/plans/{plan_id}/submit", headers=ctx["staff"]).json()["status"] == "submitted"
    client.post(decide, json={"decision": "approved"}, headers=ctx["nodal"])
    assert [d["decision"] for d in _plans(client, ctx)[plan_id]["decisions"]] == ["rejected", "approved"]


def test_changing_an_approved_plan_creates_a_new_version_and_keeps_the_old_one_active_until_approval(client, db, make_user):
    ctx = _setup(client, db, make_user)
    v1 = _submitted(client, ctx, start=today() - timedelta(days=30))
    client.post(f"/plans/{v1}/decision", json={"decision": "approved"}, headers=ctx["nodal"])

    assert client.put(f"/plans/{v1}", json=_plan(today()), headers=ctx["staff"]).json()["code"] == "plan_not_editable"
    assert client.post(f"/plans/{v1}/revise", headers=ctx["nodal"]).status_code == 403
    v2 = client.post(f"/plans/{v1}/revise", headers=ctx["staff"]).json()["id"]
    assert client.post(f"/plans/{v1}/revise", headers=ctx["staff"]).json()["code"] == "revision_exists"

    plans = _plans(client, ctx)
    assert (plans[v2]["version"], plans[v2]["supersedes_plan_id"], plans[v2]["status"]) == (2, v1, "draft")
    assert [item["type"] for item in plans[v2]["items"]] == ["scribe", "physical_access"]  # copied
    client.post(f"/plans/{v2}/submit", headers=ctx["staff"])
    plans = _plans(client, ctx)
    assert plans[v1]["is_active"] is True and plans[v2]["is_active"] is False  # old stays in force

    client.post(f"/plans/{v2}/decision", json={"decision": "approved"}, headers=ctx["nodal"])
    plans = _plans(client, ctx)
    assert (plans[v1]["status"], plans[v1]["is_active"], plans[v1]["ended_on"]) == ("superseded", False, str(today()))
    assert (plans[v2]["status"], plans[v2]["is_active"]) == ("approved", True)

    assert client.post(f"/plans/{v2}/end", headers=ctx["staff"]).status_code == 403
    assert client.post(f"/plans/{v2}/end", headers=ctx["nodal"]).json()["status"] == "ended"
    assert _plans(client, ctx)[v2]["is_active"] is False


def test_decisions_cannot_be_edited_or_deleted(client, db, make_user):
    ctx = _setup(client, db, make_user)
    plan_id = _submitted(client, ctx)
    client.post(f"/plans/{plan_id}/decision", json={"decision": "approved"}, headers=ctx["nodal"])
    for statement in (update(PlanDecision).values(decision="rejected"), delete(PlanDecision)):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(statement)
        db.rollback()
    assert db.scalar(select(PlanDecision.decision)) == "approved"


def test_audit_log_is_readable_by_oversight_roles_only_and_has_no_write_endpoint(client, db, make_user):
    ctx = _setup(client, db, make_user)
    _, admin = make_user(Role.administrator)
    plan_id = _submitted(client, ctx)
    client.post(f"/plans/{plan_id}/decision", json={"decision": "rejected", "reason": "Needs detail"}, headers=ctx["nodal"])

    for who in (ctx["student"], ctx["guardian"], ctx["staff"]):
        assert client.get("/audit", headers=who).status_code == 403
    log = client.get("/audit", headers=admin).json()
    recorded = {(e["entity_type"], e["action"]) for e in log["entries"]}
    assert {
        ("student_profiles", "create"),
        ("accommodation_plans", "create"),
        ("accommodation_plans", "update"),
        ("plan_items", "create"),
        ("plan_decisions", "create"),
    } <= recorded
    assert "Needs detail" not in str(log) and "planning meeting" not in str(log)  # no sensitive values
    decision = next(e for e in log["entries"] if e["entity_type"] == "plan_decisions")
    assert decision["actor_role"] == "nodal_officer" and decision["actor"] and decision["at"]

    only_plans = client.get("/audit?entity_type=accommodation_plans", headers=ctx["nodal"]).json()
    assert {e["entity_type"] for e in only_plans["entries"]} == {"accommodation_plans"}

    # Nobody - including an administrator - can change or remove entries through the API.
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/audit", headers=admin).status_code == 405
        assert getattr(client, method)(f"/audit/{decision['id']}", headers=admin).status_code in (404, 405)
