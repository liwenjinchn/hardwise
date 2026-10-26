"""Candidate editing shares confirmation transaction and retains prior source versions."""

import json

import pytest

from tests.workbench.test_voltage_review_routes import project, request_for, rows
from tests.ir.test_voltage_review import candidate
from hardwise.workbench.managed_projects import ManagedProjects

# Imported fixture is deliberately reused across the two endpoint suites.
__all__ = ["project"]


def body(client, **updates):
    request = request_for(client)
    request.pop("selections")
    return {**request, "upserts": [], "remove_ids": [], "active_mode": None, **updates}


def test_edit_revert_and_reconfirm_retains_prior_candidate_and_confirmation(project):
    client, _, journal, _ = project
    assert (
        client.post("/api/workbench/voltage-review/confirm", json=request_for(client)).status_code
        == 200
    )
    original = client.get("/api/workbench/voltage-review").json()
    selected = next(c for c in original["review"]["candidates"] if c["id"] == "p12")
    changed = candidate("p12", 36, net="P12").model_dump(mode="json")
    response = client.post(
        "/api/workbench/voltage-review/candidates", json=body(client, upserts=[changed])
    )
    assert response.status_code == 200, response.text
    assert (
        next(s for s in response.json()["scopes"] if s["net"] == "P12")["status"] == "needs_review"
    )
    reverted = client.post(
        "/api/workbench/voltage-review/candidates", json=body(client, upserts=[selected])
    )
    assert reverted.status_code == 200, reverted.text
    assert (
        next(s for s in reverted.json()["scopes"] if s["net"] == "P12")["status"] == "needs_review"
    )
    assert reverted.json()["review"]["confirmations"] == original["review"]["confirmations"]
    assert reverted.json()["review"]["edits"][0]["changes"][0]["before"] == selected
    assert (
        client.post("/api/workbench/voltage-review/confirm", json=request_for(client)).status_code
        == 200
    )
    assert client.get("/api/workbench/components/C1").json()["deterministic_status"] == "ERROR"
    catalog = ManagedProjects(journal).list()
    assert len(catalog) == 1
    restored, directory = ManagedProjects(journal).open(catalog[0]["id"])
    try:
        assert len(restored.design.voltage_review.edits) == 2
    finally:
        import shutil
        from hardwise.workbench.context import close_workbench_context

        close_workbench_context(restored)
        shutil.rmtree(directory)


@pytest.mark.parametrize(
    "kind", ["foreign", "metadata", "missing_remove", "no_change", "wrong_origin"]
)
def test_bad_candidate_request_leaves_all_rows_and_view_unchanged(project, kind):
    client, _, journal, _ = project
    before = rows(journal)
    view = client.get("/api/workbench/voltage-review").json()
    request = body(client)
    if kind == "foreign":
        request["upserts"] = [candidate("new", net="FOREIGN").model_dump(mode="json")]
    elif kind == "metadata":
        request["confirmations"] = []
    elif kind == "missing_remove":
        request["remove_ids"] = ["missing"]
    elif kind == "wrong_origin":
        request["upserts"] = [candidate("new", origin="legacy_v1").model_dump(mode="json")]
    response = client.post("/api/workbench/voltage-review/candidates", json=request)
    assert response.status_code == 422, response.text
    assert rows(journal) == before and client.get("/api/workbench/voltage-review").json() == view


def test_active_mode_switch_preserves_other_mode_records_and_stale_request_rejected(project):
    client, _, journal, _ = project
    old = client.get("/api/workbench/voltage-review").json()
    request = body(client, active_mode="sleep")
    response = client.post("/api/workbench/voltage-review/candidates", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["review"]["active_mode"] == "sleep"
    assert response.json()["review"]["confirmations"] == old["review"]["confirmations"]
    assert client.get("/api/workbench/state").json()["voltage_facts"]["active_mode"] == "sleep"
    assert client.get("/api/workbench/components/R1").json()["deterministic_status"] == "UNKNOWN"
    before = rows(journal)
    assert client.post("/api/workbench/voltage-review/candidates", json=request).status_code == 409
    assert rows(journal) == before


def test_offline_snapshot_contains_readonly_full_candidate_view_and_edit_audit(project):
    client, _, _, _ = project
    r = client.post(
        "/api/workbench/voltage-review/candidates", json=body(client, remove_ids=["p24"])
    )
    assert r.status_code == 200, r.text
    state = client.get("/api/workbench/state").json()
    ids = state["review_decisions"]
    html = client.get(
        "/api/workbench/offline-report",
        params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
    )
    assert html.status_code == 200
    import re

    payload = json.loads(
        re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", html.text)[1]
    )
    assert payload["voltage_review"]["editable"] is False
    assert payload["voltage_review"]["review"] == r.json()["review"]
    assert payload["voltage_review"]["review"]["edits"][0]["changes"][0]["before"]["id"] == "p24"
