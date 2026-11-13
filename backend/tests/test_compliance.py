from datetime import date, timedelta

from sqlalchemy import select

from app.audit import AuditLog
from app.models.user import Role
from app.rules.compliance import is_overdue, reminder_due, summarise
from app.rules.dates import today

D = date
PDF = b"%PDF-1.4 accessibility audit report"


def test_summary_overdue_and_reminder_rules():
    now = D(2026, 11, 13)
    items = [
        ("compliant", D(2026, 1, 1)),
        ("compliant", D(2027, 1, 1)),
        ("partially", D(2026, 11, 1)),  # open and past due -> overdue
        ("not_compliant", D(2026, 11, 20)),  # due in 7 days -> due soon
        ("not_applicable", D(2026, 1, 1)),
    ]
    summary = summarise(items, now)
    assert (summary["total"], summary["compliant"], summary["partially"]) == (5, 2, 1)
    assert (summary["not_compliant"], summary["not_applicable"]) == (1, 1)
    assert (summary["overdue"], summary["due_soon"]) == (1, 1)
    assert summary["percent_compliant"] == 50  # 2 of the 4 applicable items
    assert summarise([("not_applicable", now)], now)["percent_compliant"] is None

    assert not is_overdue("compliant", D(2020, 1, 1), now)  # done is never overdue
    assert reminder_due("partially", now + timedelta(days=7), now)  # exactly 7 days before
    assert not reminder_due("partially", now + timedelta(days=8), now)
    assert not reminder_due("partially", now - timedelta(days=1), now)  # past due: overdue, not "soon"
    assert not reminder_due("compliant", now + timedelta(days=3), now)


def test_nodal_officer_configures_the_checklist_and_others_only_read(client, db, make_user):
    _, nodal = make_user(Role.nodal_officer)
    _, staff = make_user(Role.support_staff)
    _, admin = make_user(Role.administrator)
    _, student = make_user(Role.student, date_of_birth=D(2000, 1, 1))
    _, grievance = make_user(Role.grievance_officer)
    item = {
        "description": "Ramps and accessible toilets in every academic block",
        "source_obligation": "RPwD Act 2016, s.16",
        "due_date": str(today() + timedelta(days=5)),
        "status": "partially",
        "reason": "Block C ramp is under construction",
    }

    for headers in (staff, admin):
        assert client.post("/compliance", json=item, headers=headers).status_code == 403
    for headers in (student, grievance):
        assert client.get("/compliance", headers=headers).status_code == 403

    # A reason is required for every status except Compliant.
    for status in ("partially", "not_compliant", "not_applicable"):
        assert client.post("/compliance", json={**item, "status": status, "reason": " "}, headers=nodal).status_code == 422
    assert client.post("/compliance", json={**item, "status": "compliant", "reason": None}, headers=nodal).status_code == 201
    item_id = client.post("/compliance", json=item, headers=nodal).json()["id"]

    for headers in (nodal, staff, admin):
        data = client.get("/compliance", headers=headers).json()
        assert data["summary"]["total"] == 2 and data["summary"]["due_soon"] == 1
        assert data["summary"]["percent_compliant"] == 50
    assert client.get("/compliance", headers=staff).json()["can_edit"] is False

    done = {**item, "status": "compliant", "reason": ""}
    assert client.put(f"/compliance/{item_id}", json=done, headers=staff).status_code == 403
    assert client.put(f"/compliance/{item_id}", json=done, headers=nodal).status_code == 200
    assert client.get("/compliance", headers=admin).json()["summary"]["percent_compliant"] == 100
    change = db.scalar(select(AuditLog).where(AuditLog.entity_type == "compliance_items", AuditLog.action == "update"))
    assert change.changed_fields["status"] == ["partially", "compliant"]


def test_evidence_upload_is_nodal_only_and_readable_by_checklist_readers(client, make_user):
    _, nodal = make_user(Role.nodal_officer)
    _, staff = make_user(Role.support_staff)
    _, student = make_user(Role.student, date_of_birth=D(2000, 1, 1))
    item = {"description": "Annual access audit", "source_obligation": "UGC guidelines", "due_date": str(today()), "status": "compliant"}
    item_id = client.post("/compliance", json=item, headers=nodal).json()["id"]
    request = {"purpose": "evidence", "ref_id": item_id, "return_to": f"/compliance/{item_id}"}

    assert client.post("/files/tokens/upload", json=request, headers=staff).status_code == 403
    assert client.post("/files/tokens/upload", json={**request, "ref_id": 999}, headers=nodal).status_code == 404
    token = client.post("/files/tokens/upload", json=request, headers=nodal).json()["token"]
    too_big = client.post(f"/files?token={token}", files={"file": ("big.pdf", b"%PDF" + bytes(10 * 1024 * 1024))}, follow_redirects=False)
    assert "upload_error=file_too_large" in too_big.headers["location"]
    ok = client.post(f"/files?token={token}", files={"file": ("audit.pdf", PDF)}, follow_redirects=False)
    assert ok.headers["location"].endswith(f"/compliance/{item_id}?uploaded=1")

    evidence = client.get(f"/compliance/{item_id}", headers=staff).json()["evidence"][0]
    assert evidence["filename"] == "audit.pdf"
    assert client.post(f"/files/{evidence['file_id']}/token", headers=student).status_code == 404
    download = client.post(f"/files/{evidence['file_id']}/token", headers=staff).json()["token"]
    assert client.get(f"/files/{evidence['file_id']}?token={download}").content == PDF

    assert client.delete(f"/compliance/{item_id}/evidence/{evidence['id']}", headers=staff).status_code == 403
    assert client.delete(f"/compliance/{item_id}", headers=nodal).status_code == 204
    assert client.get(f"/files/{evidence['file_id']}?token={download}").status_code == 404  # file went with the item
