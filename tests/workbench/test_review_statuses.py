"""Canonical human judgments coexist with uninterpreted legacy decisions."""

import json
import re
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
from hardwise.workbench.decision_journal import DecisionJournal
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.project_backup import backup_projects, restore_projects
from hardwise.workbench.review_decisions import ReviewDecisionRequest, ReviewDecisionStore
from hardwise.workbench.server import create_workbench_app
from hardwise.workbench.task_projection import build_review_tasks


class Chat:
    datasheet_search_enabled = False


@pytest.mark.parametrize("status", ["accepted_risk", "false_positive", "accepted", "waived"])
def test_restart_preserves_exact_meaning_and_changed_inputs_keep_previous_status(tmp_path, status):
    path = tmp_path / "review.sqlite"
    store = ReviewDecisionStore(path)
    store.begin_run("public", {"a": "original"})
    if status in {"accepted", "waived"}:
        record = dict(
            stable_key="a",
            status=status,
            reason="公开合成人工判断 <原始理由>",
            updated_at="2026-10-24T00:00:00+00:00",
            previous_status=None,
            fingerprint="original",
            current_fingerprint="original",
        )
        persisted = DecisionJournal(path)
        _, revision = persisted.load("public")
        persisted.save(
            "public",
            store.summary([]).run_id,
            {"a": record},
            [
                dict(
                    event="human_decision",
                    stable_key="a",
                    created_at=record["updated_at"],
                    decision=record,
                )
            ],
            expected_revision=revision,
        )
    else:
        store.update(
            known_keys=["a"],
            fingerprints={"a": "original"},
            request=ReviewDecisionRequest(
                stable_keys=["a"],
                status=status,
                reason="公开合成人工判断 <原始理由>",
                expected_run_id=store.summary([]).run_id,
            ),
        )
    with sqlite3.connect(path) as db:
        original = db.execute("SELECT * FROM review_events").fetchall()
        state = db.execute("SELECT * FROM review_state").fetchall()
    restarted = ReviewDecisionStore(path)
    restarted.begin_run("public", {"a": "original"})
    assert getattr(restarted.summary(["a"]), status) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM review_events").fetchall() == original
        assert db.execute("SELECT * FROM review_state").fetchall() == state
    restarted.begin_run("public", {"a": "changed"})
    event = restarted.history()[0]["decision"]
    assert event["status"] == "needs_review"
    assert event["previous_status"] == status
    assert event["reason"] == "公开合成人工判断 <原始理由>"
    count = len(restarted.history())
    restarted.begin_run("public", {"a": "changed"})
    assert len(restarted.history()) == count
    assert restarted.summary(["a"]).needs_review == 1


@pytest.mark.parametrize(
    "status,label", [("accepted_risk", "接受风险"), ("false_positive", "误报")]
)
def test_new_and_legacy_decisions_roundtrip_every_report_and_saved_backup(
    managed_review, tmp_path, status, label
):
    _, context, journal, _, legacy_key, _ = managed_review
    with TestClient(create_workbench_app(context, Chat(), review_db=journal)) as client:
        initial = client.get("/api/workbench/state").json()
        ids = initial["review_decisions"]
        task = next(t for t in initial["review_tasks"] if t["stable_key"] != legacy_key)
        key = task["stable_key"]
        payload = dict(stable_keys=[key], status=status, expected_run_id=ids["run_id"])
        assert client.put("/api/workbench/review-decisions", json=payload).status_code == 400
        reason = "公开合成判断理由：不是机器通过 </script>"
        response = client.put("/api/workbench/review-decisions", json={**payload, "reason": reason})
        assert response.status_code == 200
        current = response.json()
        assert current["summary"] == initial["summary"]
        assert [(t["stable_key"], t["assessment"]) for t in current["review_tasks"]] == [
            (t["stable_key"], t["assessment"]) for t in initial["review_tasks"]
        ]
        summary = current["review_decisions"]
        assert summary[status] == 1 and summary["waived"] == 1
        assert (
            sum(
                summary[s]
                for s in [
                    "open",
                    "accepted_risk",
                    "false_positive",
                    "accepted",
                    "waived",
                    "resolved",
                    "needs_review",
                ]
            )
            == summary["total_tasks"]
        )
        for fmt in ["json", "csv", "annotations"]:
            exported = client.get("/api/workbench/export", params={"format": fmt})
            assert exported.status_code == 200
            assert status in exported.text and reason in exported.text
        for endpoint in [
            "/api/workbench/prep-packet",
            f"/api/workbench/components/{task['refdes']}/prep-packet",
        ]:
            markdown = client.get(endpoint, params={"format": "markdown"}).text
            assert f"{status}（{label}）" in markdown and reason in markdown
        html = client.get(
            "/api/workbench/offline-report",
            params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
        ).text
        snapshot = json.loads(
            re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", html)[1]
        )
        assert {e["decision"]["status"] for e in snapshot["review_history"]["events"]} == {
            status,
            "waived",
        }
        frozen = {t["stable_key"]: t["review_decision"] for t in snapshot["state"]["review_tasks"]}
        assert frozen[key]["status"] == status
        assert frozen[legacy_key]["status"] == "waived"
        saved = client.post(
            "/api/workbench/projects/save", params={"expected_run_id": ids["run_id"]}
        )
        assert saved.status_code == 200
    archive = tmp_path / "saved.zip"
    backup_projects(journal, archive)
    restored = Path(restore_projects(archive, tmp_path / "restored")["journal"])
    reopened, directory = ManagedProjects(restored).open(saved.json()["id"])
    try:
        tasks = build_review_tasks(reopened)
        fps = review_fingerprints(reopened, tasks)
        decisions = ReviewDecisionStore(restored)
        decisions.begin_run(review_project_key(reopened), fps)
        items = {t.stable_key: t.review_decision for t in decisions.apply(tasks, fingerprints=fps)}
        assert items[key].status == status
        assert items[key].reason == reason
        assert items[legacy_key].status == "waived"
        assert len(decisions.history()) == 2
    finally:
        close_workbench_context(reopened)
        shutil.rmtree(directory)


@pytest.mark.parametrize("status", ["accepted", "waived", "needs_review"])
def test_api_rejects_ambiguous_or_derived_new_decisions_without_writing(managed_review, status):
    _, context, journal, _, key, _ = managed_review
    with TestClient(create_workbench_app(context, Chat(), review_db=journal)) as client:
        state = client.get("/api/workbench/state").json()

        def recorded():
            with sqlite3.connect(journal) as db:
                return {
                    table: db.execute("SELECT * FROM " + table + " ORDER BY rowid").fetchall()
                    for table in ["review_state", "review_events", "review_runs", "review_heads"]
                }

        before = recorded()
        response = client.put(
            "/api/workbench/review-decisions",
            json={
                "stable_keys": [key],
                "status": status,
                "reason": "拒绝此新写入",
                "expected_run_id": state["review_decisions"]["run_id"],
            },
        )
        assert response.status_code == 422
        assert recorded() == before
        assert client.get("/api/workbench/state").json() == state
