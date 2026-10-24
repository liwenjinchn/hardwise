"""Frozen reviewer decisions/history must survive independently of the service."""

import json
import re
import sqlite3

from fastapi.testclient import TestClient
from hardwise.workbench.server import create_workbench_app


class Chat:
    datasheet_search_enabled = False


def _snapshot(html):
    return json.loads(re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", html)[1])


def test_report_retains_all_history_decisions_and_manifests_without_writes(managed_review):
    _, context, journal, _, _, _ = managed_review
    with TestClient(create_workbench_app(context, Chat(), review_db=journal)) as client:
        state = client.get("/api/workbench/state").json()
        ids = state["review_decisions"]
        key = state["review_tasks"][0]["stable_key"]
        for i in range(25):
            response = client.put(
                "/api/workbench/review-decisions",
                json={
                    "stable_keys": [key],
                    "status": "waived",
                    "reason": f"独立原始理由{i} </script> 中文",
                    "expected_run_id": ids["run_id"],
                },
            )
            assert response.status_code == 200
        with sqlite3.connect(journal) as db:
            db.execute(
                "INSERT INTO review_events(project,run_id,data) VALUES('foreign','foreign',?)",
                (json.dumps({"secret": "OTHER_PROJECT_MUST_NOT_LEAK"}),),
            )
            before = db.execute("SELECT * FROM review_events ORDER BY id").fetchall()
            run_count = db.execute("SELECT count(*) FROM review_runs").fetchone()[0]
        response = client.get(
            "/api/workbench/offline-report",
            params={
                "expected_project_id": ids["project_id"],
                "expected_run_id": ids["run_id"],
            },
        )
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "OTHER_PROJECT_MUST_NOT_LEAK" not in response.text
        report = _snapshot(response.text)
        assert report["review_history"]["total"] == 26
        reasons = [e["decision"]["reason"] for e in report["review_history"]["events"]]
        assert reasons[0] == "独立原始理由24 </script> 中文"
        assert reasons[-1] == "公开合成理由"
        task = next(t for t in report["state"]["review_tasks"] if t["stable_key"] == key)
        assert task["review_decision"]["reason"] == reasons[0]
        detail = report["components"][task["refdes"]]
        assert (
            next(t for t in detail["tasks"] if t["stable_key"] == key)["review_decision"]
            == task["review_decision"]
        )
        assert reasons[0] in report["component_prep_markdown"][task["refdes"]]
        assert reasons[0] in report["exports"]["csv"]
        assert report["state"]["review_decisions"]["history_count"] == 26
        assert report["review_history"]["run_provenance"][ids["run_id"]]["status"] == "recorded"
        assert any(
            r["status"] == "not_recorded"
            for r in report["review_history"]["run_provenance"].values()
        )
        assert report["state"]["summary"] == state["summary"]
        assert report["state"]["evidence_package"]["original_delivery"]["status"] == "not_attached"
        with sqlite3.connect(journal) as db:
            assert db.execute("SELECT * FROM review_events ORDER BY id").fetchall() == before
            assert db.execute("SELECT count(*) FROM review_runs").fetchone()[0] == run_count


def test_report_rejects_stale_namespace_and_cross_process_changes(managed_review):
    _, context, journal, _, _, _ = managed_review
    with TestClient(create_workbench_app(context, Chat(), review_db=journal)) as client:
        ids = client.get("/api/workbench/state").json()["review_decisions"]
        query = {"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]}
        for field in query:
            assert (
                client.get(
                    "/api/workbench/offline-report", params={**query, field: "old"}
                ).status_code
                == 409
            )
        with sqlite3.connect(journal) as db:
            db.execute(
                "UPDATE review_heads SET revision=revision+1 WHERE project=?", (ids["project_id"],)
            )
        assert client.get("/api/workbench/offline-report", params=query).status_code == 409


def test_memory_only_service_can_deliver_its_decisions_before_shutdown(managed_review):
    _, context, _, _, _, _ = managed_review
    with TestClient(create_workbench_app(context, Chat())) as client:
        state = client.get("/api/workbench/state").json()
        ids = state["review_decisions"]
        client.put(
            "/api/workbench/review-decisions",
            json={
                "stable_keys": [state["review_tasks"][0]["stable_key"]],
                "status": "accepted",
                "reason": "仅内存服务的原始理由",
                "expected_run_id": ids["run_id"],
            },
        ).raise_for_status()
        response = client.get(
            "/api/workbench/offline-report",
            params={
                "expected_project_id": ids["project_id"],
                "expected_run_id": ids["run_id"],
            },
        )
        assert response.status_code == 200
        report = _snapshot(response.text)
        assert report["review_history"]["total"] == 1
        assert report["review_history"]["events"][0]["decision"]["reason"] == "仅内存服务的原始理由"
        assert report["review_history"]["run_provenance"][ids["run_id"]]["status"] == "recorded"


def test_failed_history_capture_delivers_error_instead_of_partial_html(managed_review, monkeypatch):
    from hardwise.workbench.decision_journal import DecisionJournal

    _, context, journal, _, _, _ = managed_review
    with TestClient(create_workbench_app(context, Chat(), review_db=journal)) as client:
        ids = client.get("/api/workbench/state").json()["review_decisions"]

        def unavailable(*args, **kwargs):
            raise OSError("synthetic local read failure")

        monkeypatch.setattr(DecisionJournal, "offline_records", unavailable)
        response = client.get(
            "/api/workbench/offline-report",
            params={
                "expected_project_id": ids["project_id"],
                "expected_run_id": ids["run_id"],
            },
        )
        assert response.status_code == 503
        assert "no partial report" in response.json()["detail"]
        assert "<html" not in response.text
