"""Actual app restart keeps decisions and invalidates changed semantic inputs."""

import json
from pathlib import Path
import shutil
from fastapi.testclient import TestClient
import pytest
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path(__file__).parents[2].resolve()


class LocalOnlyChat:
    datasheet_search_enabled = False


def _inputs(tmp_path):
    root = ROOT / "tests/fixtures/allegro"
    for name in ("l78_regulator.net", "l78_regulator_bom.csv"):
        shutil.copyfile(root / name, tmp_path / name)
    (tmp_path / "profiles").mkdir()
    shutil.copyfile(ROOT / "data/datasheet_profiles/l78.json", tmp_path / "profiles/l78.json")
    facts = {
        "schema_version": "hardwise.voltage_facts.v1",
        "active_mode": "dc",
        "facts": [
            {
                "net": n,
                "reference_net": "GND",
                "minimum": v,
                "maximum": v,
                "source": "synthetic reviewer restart premise",
                "confirmed": True,
                "confirmed_by": "test author",
            }
            for n, v in [("+12V", 12), ("GND", 0)]
        ],
    }
    (tmp_path / "facts.json").write_text(json.dumps(facts))


def _app(root, durable=True):
    context = build_workbench_context(
        netlist_path=root / "l78_regulator.net",
        bom_path=root / "l78_regulator_bom.csv",
        profiles=root / "profiles",
        voltage_facts=root / "facts.json",
    )
    return create_workbench_app(
        context,
        LocalOnlyChat(),
        auto_datasheet_candidates=False,
        review_db=root / "review.sqlite" if durable else None,
    )


def _waive(client, refdes="C1"):
    current_state = client.get("/api/workbench/state").json()
    tasks = current_state["review_tasks"]
    task = next(
        t
        for t in tasks
        if t["refdes"] == refdes
        and (t["check"] == "capacitor_voltage_margin" if refdes == "C1" else t["pin_number"] == "3")
    )
    response = client.put(
        "/api/workbench/review-decisions",
        json={
            "stable_keys": [task["stable_key"]],
            "status": "accepted_risk",
            "reason": "Public engineer reason retained across restart",
            "expected_run_id": current_state["review_decisions"]["run_id"],
        },
    )
    assert response.status_code == 200, response.text
    return task


@pytest.mark.parametrize(
    "change", ["none", "whitespace", "unrelated_component", "voltage", "profile"]
)
def test_restart_and_semantic_change_classification(tmp_path, change):
    _inputs(tmp_path)
    with TestClient(_app(tmp_path)) as client:
        task = _waive(client, "U1" if change == "profile" else "C1")
        before = client.get("/api/workbench/components/" + task["refdes"]).json()["assessment"]
        assert (
            client.get("/api/workbench/state").json()["review_decisions"]["storage"] == "local_file"
        )
    if change == "whitespace":
        with (tmp_path / "l78_regulator.net").open("a") as stream:
            stream.write("\n\n")
    elif change == "unrelated_component":
        path = tmp_path / "l78_regulator_bom.csv"
        lines = path.read_text().splitlines()
        path.write_text(
            "\n".join(
                line.replace("100nF", "220nF") if line.startswith("C2,") else line for line in lines
            )
            + "\n"
        )
    elif change == "voltage":
        path = tmp_path / "facts.json"
        facts = json.loads(path.read_text())
        facts["facts"][0].update(minimum=20, maximum=20)
        path.write_text(json.dumps(facts))
    elif change == "profile":
        path = tmp_path / "profiles/l78.json"
        profile = json.loads(path.read_text())
        profile["schema_version"] = "reviewed-revision-test"
        path.write_text(json.dumps(profile))
    with TestClient(_app(tmp_path)) as client:
        state = client.get("/api/workbench/state").json()
        current = next(t for t in state["review_tasks"] if t["stable_key"] == task["stable_key"])
        decision = current["review_decision"]
        assert decision["status"] == (
            "needs_review" if change in {"voltage", "profile"} else "accepted_risk"
        )
        assert decision["reason"] == "Public engineer reason retained across restart"
        assert (
            client.get("/api/workbench/components/" + task["refdes"]).json()["assessment"] == before
        )
        history = client.get("/api/workbench/review-decisions/history").json()["events"]
        assert history[-1]["event"] == "human_decision"
        if change in {"voltage", "profile"}:
            assert history[0]["event"] == "inputs_changed"
            assert decision["previous_status"] == "accepted_risk"
        exported = client.get("/api/workbench/export?format=json").json()
        assert (
            next(t for t in exported["review_tasks"] if t["stable_key"] == task["stable_key"])[
                "review_decision"
            ]
            == decision
        )


def test_live_rerun_marks_changed_facts_without_waiting_for_restart(tmp_path):
    _inputs(tmp_path)
    with TestClient(_app(tmp_path)) as client:
        task = _waive(client)
        path = tmp_path / "facts.json"
        facts = json.loads(path.read_text())
        facts["facts"][0].update(minimum=21, maximum=21)
        path.write_text(json.dumps(facts))
        response = client.post("/api/workbench/rerun")
        assert response.status_code == 200, response.text
        current = next(
            t for t in response.json()["review_tasks"] if t["stable_key"] == task["stable_key"]
        )
        assert current["review_decision"]["status"] == "needs_review"
        detail = client.get("/api/workbench/components/C1").json()
        assert (
            next(t for t in detail["tasks"] if t["stable_key"] == task["stable_key"])[
                "review_decision"
            ]["status"]
            == "needs_review"
        )


def test_old_service_reports_conflict_and_preserves_current_writer(tmp_path):
    _inputs(tmp_path)
    with TestClient(_app(tmp_path)) as old:
        original = old.get("/api/workbench/state").json()
        with TestClient(_app(tmp_path)) as current:
            task = _waive(current)
            committed = current.get("/api/workbench/state").json()
            history = current.get("/api/workbench/review-decisions/history").json()
            response = old.put(
                "/api/workbench/review-decisions",
                json={
                    "stable_keys": [task["stable_key"]],
                    "status": "resolved",
                    "reason": "Stale service must not replace the waiver",
                    "expected_run_id": original["review_decisions"]["run_id"],
                },
            )
            assert response.status_code == 409, response.text
            assert "another process" in response.json()["detail"]
            response = old.post("/api/workbench/rerun")
            assert response.status_code == 409, response.text
            old_state = old.get("/api/workbench/state").json()
            assert old_state["review_tasks"] == original["review_tasks"]
            assert old_state["review_decisions"]["run_id"] == original["review_decisions"]["run_id"]
            assert current.get("/api/workbench/state").json() == committed
            assert current.get("/api/workbench/review-decisions/history").json() == history


def test_explicit_rule_version_changes_the_review_fingerprint(tmp_path):
    from hardwise.workbench.decision_fingerprints import review_fingerprints
    from hardwise.workbench.task_projection import build_review_tasks

    _inputs(tmp_path)
    app = _app(tmp_path)
    with TestClient(app):
        context = app.state.workbench_context.current
        task = next(
            t
            for t in build_review_tasks(context)
            if t.refdes == "C1" and t.check == "capacitor_voltage_margin"
        )
        changed = task.model_copy(
            update={
                "assessment": task.assessment.model_copy(
                    update={"rule_version": "next-reviewed-rule"}
                )
            }
        )
        assert (
            review_fingerprints(context, [task])[task.stable_key]
            != review_fingerprints(context, [changed])[task.stable_key]
        )


def test_durable_updates_reject_unversioned_and_stale_browser_requests(tmp_path):
    _inputs(tmp_path)
    with TestClient(_app(tmp_path)) as client:
        task = _waive(client)
        old_run = client.get("/api/workbench/state").json()["review_decisions"]["run_id"]
        next_state = client.post("/api/workbench/rerun").json()
        payload = {
            "stable_keys": [task["stable_key"]],
            "status": "resolved",
            "reason": "Stale browser reason",
        }
        assert client.put("/api/workbench/review-decisions", json=payload).status_code == 400
        payload["expected_run_id"] = old_run
        assert client.put("/api/workbench/review-decisions", json=payload).status_code == 409
        assert len(client.get("/api/workbench/review-decisions/history").json()["events"]) == 1
        payload["expected_run_id"] = next_state["review_decisions"]["run_id"]
        response = client.put("/api/workbench/review-decisions", json=payload)
        assert response.status_code == 200
        assert response.json()["review_decisions"]["resolved"] == 1
        assert (
            next(
                t for t in response.json()["review_tasks"] if t["stable_key"] == task["stable_key"]
            )["assessment"]["result"]
            == "UNKNOWN"
        )


@pytest.mark.parametrize("durable", [False, True])
def test_failed_import_publication_retains_previous_review_namespace(
    tmp_path, monkeypatch, durable
):
    _inputs(tmp_path)
    app = _app(tmp_path, durable)
    with TestClient(app) as client:
        task = _waive(client)
        manager = app.state.workbench_context

        def reject_publication(*args, **kwargs):
            raise RuntimeError("synthetic publication failure")

        monkeypatch.setattr(manager, "swap", reject_publication)
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("new.net", (tmp_path / "l78_regulator.net").read_bytes(), "text/plain"),
                "bom": ("new.csv", (tmp_path / "l78_regulator_bom.csv").read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 503
        state = client.get("/api/workbench/state").json()
        current = next(t for t in state["review_tasks"] if t["stable_key"] == task["stable_key"])
        assert current["review_decision"]["status"] == "accepted_risk"
        assert (
            current["review_decision"]["reason"] == "Public engineer reason retained across restart"
        )
        assert (
            client.get("/api/workbench/review-decisions/history").json()["events"][0]["event"]
            == "human_decision"
        )


@pytest.mark.parametrize("future", ["new_check", "new_version"])
def test_unknown_dependency_contract_uses_broad_snapshot(tmp_path, future):
    from hardwise.workbench.decision_fingerprints import review_fingerprints
    from hardwise.workbench.task_projection import build_review_tasks

    _inputs(tmp_path)
    app = _app(tmp_path)
    with TestClient(app):
        context = app.state.workbench_context.current
        task = next(
            t
            for t in build_review_tasks(context)
            if t.refdes == "C1" and t.check == "capacitor_voltage_margin"
        )
        unregistered = (
            task.model_copy(update={"check": "capacitor_graph_condition"})
            if future == "new_check"
            else task.model_copy(
                update={"assessment": task.assessment.model_copy(update={"rule_version": "next"})}
            )
        )
        local_before = review_fingerprints(context, [task])[task.stable_key]
        broad_before = review_fingerprints(context, [unregistered])[task.stable_key]
        context.design.components["C2"].value = "unrelated synthetic component change"
        assert review_fingerprints(context, [task])[task.stable_key] == local_before
        assert review_fingerprints(context, [unregistered])[task.stable_key] != broad_before


@pytest.mark.parametrize("durable", [False, True])
def test_history_pages_keep_scope_counts_and_original_reason(tmp_path, durable):
    _inputs(tmp_path)
    with TestClient(_app(tmp_path, durable)) as client:
        task = _waive(client)
        facts = json.loads((tmp_path / "facts.json").read_text())
        facts["facts"][0].update(minimum=21, maximum=21)
        (tmp_path / "facts.json").write_text(json.dumps(facts))
        state = client.post("/api/workbench/rerun").json()
        project = state["review_decisions"]["project_id"]
        params = {"limit": 1, "expected_project_id": project}
        newest = client.get("/api/workbench/review-decisions/history", params=params).json()
        assert newest["total"] == 2
        assert newest["project_id"] == project
        assert newest["run_id"] == state["review_decisions"]["run_id"]
        assert newest["events"][0]["event"] == "inputs_changed"
        assert newest["events"][0]["decision"]["previous_status"] == "accepted_risk"
        assert newest["events"][0]["stable_key"] == task["stable_key"]
        older = client.get(
            "/api/workbench/review-decisions/history", params={**params, "offset": 1}
        ).json()
        assert older["events"][0]["event"] == "human_decision"
        assert older["events"][0]["decision"]["status"] == "accepted_risk"
        assert older["events"][0]["decision"]["reason"] == newest["events"][0]["decision"]["reason"]
        empty = client.get(
            "/api/workbench/review-decisions/history", params={**params, "offset": 2}
        ).json()
        assert empty["events"] == [] and empty["total"] == 2
        stale = client.get(
            "/api/workbench/review-decisions/history", params={"expected_project_id": "old-project"}
        )
        assert stale.status_code == 409
        assert "events" not in stale.json()
        for invalid in ({"limit": 0}, {"limit": 1001}, {"offset": -1}):
            assert (
                client.get("/api/workbench/review-decisions/history", params=invalid).status_code
                == 422
            )
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (
                    "other.net",
                    (tmp_path / "l78_regulator.net").read_bytes(),
                    "text/plain",
                ),
                "bom": ("other.csv", (tmp_path / "l78_regulator_bom.csv").read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 200, response.text
        active = client.get("/api/workbench/review-decisions/history").json()
        assert active["project_id"] != project
        assert active["total"] == 0 and active["events"] == []
        assert (
            client.get("/api/workbench/review-decisions/history", params=params).status_code == 409
        )


def test_history_read_failure_is_retryable_without_modifying_decisions(tmp_path, monkeypatch):
    import sqlite3
    from hardwise.workbench.decision_journal import DecisionJournal

    _inputs(tmp_path)
    with TestClient(_app(tmp_path)) as client:
        _waive(client)
        state = client.get("/api/workbench/state").json()

        def fail_read(*args):
            raise sqlite3.OperationalError("synthetic read failure")

        monkeypatch.setattr(DecisionJournal, "history_page", fail_read)
        assert client.get("/api/workbench/review-decisions/history").status_code == 503
        assert client.get("/api/workbench/state").json() == state
