"""Batch facts atomically update source ownership and run history without partial state."""

import json
import shutil
import sqlite3

from fastapi.testclient import TestClient
import pytest

from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.server import create_workbench_app
from tests.workbench.test_voltage_review_intake import inputs, build, NoChat


@pytest.fixture
def project(tmp_path):
    files = inputs.__wrapped__(tmp_path)
    context = build(files)
    journal = tmp_path / "review.sqlite"
    app = create_workbench_app(
        context, NoChat(), review_db=journal, auto_datasheet_candidates=False
    )
    with TestClient(app) as client:
        yield client, app, journal, files


def request_for(client, selections=None):
    view = client.get("/api/workbench/voltage-review").json()
    selected = selections or [("P12", "confirm", "p12")]
    return dict(
        expected_project_id=view["project_id"],
        expected_run_id=view["run_id"],
        expected_revision=view["revision"],
        reviewer="SYNTHETIC BATCH AUTHOR",
        reason="Public synthetic review, not actual engineering approval",
        selections=[
            dict(
                net=net,
                mode="dc",
                action=action,
                candidate_id=id,
                expected_scope_sha256=next(
                    s["scope_sha256"] for s in view["scopes"] if s["net"] == net
                ),
            )
            for net, action, id in selected
        ],
    )


def rows(journal):
    with sqlite3.connect(journal) as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: list(db.execute("SELECT * FROM " + t)) for t in tables}


def test_confirm_save_reopen_and_revoke_same_project_without_changing_sources(project):
    client, app, journal, files = project
    before = client.get("/api/workbench/state").json()
    original = files[1].read_bytes()
    request = request_for(client)
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 200, response.text
    after = response.json()
    assert (
        after["project_id"] == request["expected_project_id"]
        and after["run_id"] != request["expected_run_id"]
    )
    assert next(s for s in after["scopes"] if s["net"] == "P12")["status"] == "confirmed"
    assert client.get("/api/workbench/components/C1").json()["deterministic_status"] == "ERROR"
    assert files[1].read_bytes() == original
    assert len(after["review"]["confirmations"]) == 3
    catalog = ManagedProjects(journal).list()
    assert len(catalog) == 1
    new_context = app.state.workbench_context["value"]
    assert new_context.managed_project_id == catalog[0]["id"]
    shutil.rmtree(files[0])
    reopened, directory = ManagedProjects(journal).open(catalog[0]["id"])
    try:
        assert reopened.design.voltage_review.model_dump(mode="json") == after["review"]
    finally:
        from hardwise.workbench.context import close_workbench_context

        close_workbench_context(reopened)
        shutil.rmtree(directory)
    revoked = client.post(
        "/api/workbench/voltage-review/confirm",
        json=request_for(client, [("P12", "unknown", None)]),
    )
    assert revoked.status_code == 200, revoked.text
    assert client.get("/api/workbench/components/C1").json()["deterministic_status"] == "UNKNOWN"
    assert len(revoked.json()["review"]["confirmations"]) == 4
    store = ManagedProjects(journal)
    with store.journal.connect() as db:
        descriptor = json.loads(db.execute("SELECT descriptor FROM managed_projects").fetchone()[0])
    assert len(descriptor["retained_snapshots"]) >= 2
    assert (
        client.get("/api/workbench/state").json()["review_decisions"]["project_id"]
        == before["review_decisions"]["project_id"]
    )


@pytest.mark.parametrize("field", ["expected_project_id", "expected_run_id", "expected_revision"])
def test_stale_batch_does_not_write_any_journal_rows(project, field):
    client, app, journal, _ = project
    request = request_for(client)
    request[field] = "0" * 64
    before = rows(journal)
    context = app.state.workbench_context["value"]
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 409, response.text
    assert rows(journal) == before and app.state.workbench_context["value"] is context


def test_one_bad_selection_rolls_back_entire_batch(project):
    client, app, journal, _ = project
    request = request_for(client, [("P12", "confirm", "p12"), ("GND", "confirm", "missing")])
    before = rows(journal)
    view = client.get("/api/workbench/voltage-review").json()
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 422
    assert rows(journal) == before and client.get("/api/workbench/voltage-review").json() == view


@pytest.mark.parametrize("failure", ["catalog", "snapshot", "activation"])
def test_storage_or_prepublication_failure_keeps_catalog_run_and_active_facts(
    project, monkeypatch, failure
):
    client, app, journal, _ = project
    request = request_for(client)
    before = rows(journal)
    context = app.state.workbench_context["value"]
    view = client.get("/api/workbench/voltage-review").json()

    def fail(*args, **kwargs):
        raise OSError("synthetic failure before publication")

    if failure == "catalog":
        original_publish = ManagedProjects.publish

        def write_then_fail(self, *args, **kwargs):
            original_publish(self, *args, **kwargs)
            raise OSError("synthetic failure after catalog SQL write")

        monkeypatch.setattr(ManagedProjects, "publish", write_then_fail)
    elif failure == "snapshot":
        from hardwise.workbench.managed_inputs import ManagedInputs

        monkeypatch.setattr(ManagedInputs, "capture", fail)
    else:
        monkeypatch.setattr(app.state.workbench_context, "publish", fail)
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 422, response.text
    assert rows(journal) == before
    assert app.state.workbench_context["value"] is context
    assert client.get("/api/workbench/voltage-review").json() == view
    assert client.get("/api/workbench/export?format=csv").status_code == 200


def test_saved_project_identity_stays_stable_across_multiple_batches(project):
    client, _, journal, _ = project
    request = request_for(client)
    assert (
        client.post(
            "/api/workbench/projects/save", params={"expected_run_id": request["expected_run_id"]}
        ).status_code
        == 200
    )
    before = ManagedProjects(journal).list()[0]
    assert client.post("/api/workbench/voltage-review/confirm", json=request).status_code == 200
    assert ManagedProjects(journal).list()[0]["id"] == before["id"]
    assert client.post("/api/workbench/voltage-review/confirm", json=request).status_code == 409


def test_memory_only_service_exposes_read_only_review(tmp_path):
    files = inputs.__wrapped__(tmp_path)
    with TestClient(
        create_workbench_app(build(files), NoChat(), auto_datasheet_candidates=False)
    ) as client:
        assert client.get("/api/workbench/voltage-review").json()["editable"] is False
        assert (
            client.post(
                "/api/workbench/voltage-review/confirm", json=request_for(client)
            ).status_code
            == 400
        )


def test_client_cannot_supply_confirmation_timestamp_or_origin(project):
    client, _, journal, _ = project
    request = request_for(client)
    before = rows(journal)
    request["recorded_at"] = "2000-01-01T00:00:00Z"
    request["origin"] = "legacy_v1"
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 422 and rows(journal) == before


def test_multiple_scopes_confirm_together_and_unselected_conflicts_remain(project):
    client, _, _, _ = project
    request = request_for(client, [("P12", "confirm", "p24"), ("N12", "unknown", None)])
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 200, response.text
    scopes = {s["net"]: s for s in response.json()["scopes"]}
    assert scopes["P12"]["status"] == "confirmed" and scopes["N12"]["status"] == "unknown"
    assert len(response.json()["review"]["candidates"]) == 4
    assert len(response.json()["review"]["confirmations"]) == 4
    assert client.get("/api/workbench/components/C1").json()["deterministic_status"] == "UNKNOWN"


def test_external_journal_writer_rejects_stale_publication_without_extra_catalog(project):
    from hardwise.workbench.review_decisions import ReviewDecisionStore

    client, app, journal, _ = project
    request = request_for(client)
    external = ReviewDecisionStore(journal)
    external.begin_run(request["expected_project_id"], {})
    before = rows(journal)
    context = app.state.workbench_context["value"]
    response = client.post("/api/workbench/voltage-review/confirm", json=request)
    assert response.status_code == 409, response.text
    assert rows(journal) == before and app.state.workbench_context["value"] is context


def test_legacy_v1_confirmation_keeps_its_original_declarations_and_source_bytes(tmp_path):
    from hardwise.ir.voltage import VoltageFactsDocument

    files = inputs.__wrapped__(tmp_path)
    facts = [c.fact for c in files[2].candidates if c.id != "p24"]
    facts = [
        f.model_copy(
            update={
                "confirmed": f.net != "P12",
                "confirmed_by": "Original v1 author" if f.net != "P12" else "",
            }
        )
        for f in facts
    ]
    files[1].write_text(VoltageFactsDocument(facts=facts).model_dump_json())
    original = files[1].read_bytes()
    with TestClient(
        create_workbench_app(
            build(files),
            NoChat(),
            review_db=tmp_path / "legacy.sqlite",
            auto_datasheet_candidates=False,
        )
    ) as client:
        view = client.get("/api/workbench/voltage-review").json()
        assert all(
            d["origin"] == "legacy_v1" and d["recorded_at"] is None
            for d in view["review"]["confirmations"]
        )
        selected = next(c["id"] for c in view["review"]["candidates"] if c["fact"]["net"] == "P12")
        response = client.post(
            "/api/workbench/voltage-review/confirm",
            json=request_for(client, [("P12", "confirm", selected)]),
        )
        assert response.status_code == 200, response.text
        declarations = response.json()["review"]["confirmations"]
        assert declarations[:-1] == view["review"]["confirmations"]
        assert declarations[-1]["origin"] == "human" and declarations[-1]["recorded_at"]
        assert files[1].read_bytes() == original


def test_changed_voltage_decision_requires_review_once_and_keeps_original_reason(project):
    client, _, journal, _ = project
    before = client.get("/api/workbench/state").json()
    task = next(
        t
        for t in before["review_tasks"]
        if t["refdes"] == "C1" and t["check"] == "capacitor_voltage_margin"
    )
    response = client.put(
        "/api/workbench/review-decisions",
        json={
            "stable_keys": [task["stable_key"]],
            "status": "accepted_risk",
            "reason": "Original synthetic reason retained across voltage batch",
            "expected_run_id": before["review_decisions"]["run_id"],
        },
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/workbench/state").json()["review_decisions"]["history_count"] == 1
    old_run = before["review_decisions"]["run_id"]
    old_receipt = client.get(f"/api/workbench/review-runs/{old_run}/provenance").json()
    response = client.post("/api/workbench/voltage-review/confirm", json=request_for(client))
    assert response.status_code == 200, response.text
    after = client.get("/api/workbench/state").json()
    updated = next(t for t in after["review_tasks"] if t["stable_key"] == task["stable_key"])
    assert updated["review_decision"]["status"] == "needs_review"
    assert (
        updated["review_decision"]["reason"]
        == "Original synthetic reason retained across voltage batch"
    )
    assert after["review_decisions"]["history_count"] == 2
    rerun = client.post("/api/workbench/rerun")
    assert rerun.status_code == 200, rerun.text
    assert rerun.json()["review_decisions"]["history_count"] == 2
    assert client.get(f"/api/workbench/review-runs/{old_run}/provenance").json() == old_receipt
    assert len(ManagedProjects(journal).list()) == 1
