"""Durable decisions keep reasons, reject stale writers and commit atomically."""

import json
import os
import sqlite3
import subprocess
import sys
import pytest
from hardwise.workbench.review_decisions import ReviewDecisionStore, ReviewDecisionRequest


def _store(path, fingerprint="f1", project="project"):
    store = ReviewDecisionStore(path)
    store.begin_run(project, {"a": fingerprint, "b": "fb"})
    return store


def _decide(store, keys=("a",), status="waived", fps=None):
    return store.update(
        known_keys=["a", "b"],
        request=ReviewDecisionRequest(
            stable_keys=list(keys),
            status=status,
            reason="Public synthetic reason",
            expected_run_id=store.summary([]).run_id,
        ),
        fingerprints=fps or {"a": "f1", "b": "fb"},
    )


def test_restart_restores_same_snapshot_and_keeps_history(tmp_path):
    path = tmp_path / "review.sqlite"
    first = _store(path)
    _decide(first)
    second = _store(path)
    assert second.summary(["a"]).waived == 1
    assert second.history()[0]["decision"]["reason"] == "Public synthetic reason"
    _decide(second, status="open")
    assert second.summary(["a"]).open == 1
    assert [e["decision"]["status"] for e in second.history()] == ["open", "waived"]


def test_changed_fingerprint_requires_review_without_losing_original_reason(tmp_path):
    path = tmp_path / "review.sqlite"
    _decide(_store(path))
    second = _store(path, "changed")
    assert second.summary(["a"]).needs_review == 1
    item = second.history()[0]["decision"]
    assert item["previous_status"] == "waived"
    assert item["reason"] == "Public synthetic reason"
    assert _store(path, "changed").summary(["a"]).needs_review == 1
    assert len(_store(path, "changed").history()) == 2


def test_bulk_failure_rolls_back_database_and_memory(tmp_path):
    path = tmp_path / "review.sqlite"
    store = _store(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TRIGGER block_events BEFORE INSERT ON review_events BEGIN SELECT RAISE(ABORT,'test write failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        _decide(store, ("a", "b"))
    assert store.summary(["a", "b"]).open == 2
    fresh = _store(path)
    assert fresh.summary(["a", "b"]).open == 2
    assert fresh.history() == []


def test_stale_process_cannot_overwrite_a_newer_writer(tmp_path):
    path = tmp_path / "review.sqlite"
    first = _store(path)
    second = _store(path)
    _decide(second, ("b",))
    with pytest.raises(ValueError, match="another process"):
        _decide(first)
    assert _store(path).summary(["a", "b"]).waived == 1


def test_disappeared_task_is_history_not_human_resolution(tmp_path):
    path = tmp_path / "review.sqlite"
    store = _store(path)
    _decide(store)
    assert store.begin_run("project", {"b": "fb"}) == 1
    assert store.summary(["b"]).resolved == 0
    assert store.history()[0]["event"] == "disappeared"
    assert store.history()[0]["decision"]["status"] == "waived"


def test_projects_are_isolated_and_restorable(tmp_path):
    path = tmp_path / "review.sqlite"
    _decide(_store(path))
    other = _store(path, project="other")
    assert other.summary(["a"]).open == 1
    old_read = other.summary(["a"], project="project")
    assert old_read.waived == 0
    assert old_read.run_id is None
    assert old_read.project_id == "project"
    assert _store(path).summary(["a"]).waived == 1


def test_future_or_foreign_database_is_preserved(tmp_path):
    path = tmp_path / "foreign.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE sentinel(value TEXT)")
        db.execute("INSERT INTO sentinel VALUES('keep')")
        db.execute("PRAGMA user_version=9")
    with pytest.raises(ValueError, match="unsupported"):
        ReviewDecisionStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM sentinel").fetchone()[0] == "keep"


def test_unfingerprinted_legacy_decision_requires_review(tmp_path):
    path = tmp_path / "review.sqlite"
    _store(path)
    legacy = {
        "stable_key": "a",
        "status": "waived",
        "reason": "Old reason",
        "updated_at": "2026-01-01",
    }
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO review_state VALUES(?,?,?)", ("project", "a", json.dumps(legacy)))
    restored = _store(path)
    assert restored.summary(["a"]).needs_review == 1
    assert restored.history()[0]["decision"]["reason"] == "Old reason"


def test_process_exit_before_commit_preserves_last_committed_decision(tmp_path):
    path = tmp_path / "review.sqlite"
    _decide(_store(path))
    program = "import sqlite3,os,sys; db=sqlite3.connect(sys.argv[1]); db.execute('BEGIN IMMEDIATE'); db.execute('DELETE FROM review_state'); os._exit(17)"
    result = subprocess.run([sys.executable, "-c", program, str(path)], env=os.environ.copy())
    assert result.returncode == 17
    assert _store(path).summary(["a"]).waived == 1


def test_reverting_inputs_does_not_silently_reactivate_old_waiver(tmp_path):
    path = tmp_path / "review.sqlite"
    _decide(_store(path))
    _store(path, "changed")
    restored = _store(path, "f1")
    assert restored.summary(["a"]).needs_review == 1
    assert restored.history()[0]["decision"]["current_fingerprint"] == "f1"
    assert restored.history()[0]["decision"]["previous_status"] == "waived"
