"""Managed reopen retains the journal namespace without old source paths."""

import shutil
import sqlite3

import pytest

from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key, review_fingerprints
from hardwise.workbench.decision_journal import DecisionJournal, ReviewConflictError
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.review_decisions import ReviewDecisionStore
from hardwise.workbench.task_projection import build_review_tasks


@pytest.fixture
def project(managed_review):
    return managed_review


def test_reopen_after_source_deletion_and_journal_move(project, tmp_path):
    source, context, journal, run, task_key, fps = project
    saved = ManagedProjects(journal).save(context, run)
    original_key = review_project_key(context)
    shutil.rmtree(source)
    moved = tmp_path / "搬迁后/review.sqlite"
    moved.parent.mkdir()
    shutil.move(journal, moved)
    shutil.move(
        journal.with_name(journal.name + ".inputs"), moved.with_name(moved.name + ".inputs")
    )
    reopened, directory = ManagedProjects(moved).open(saved["id"])
    try:
        assert review_project_key(reopened) == original_key
        tasks = build_review_tasks(reopened)
        fresh = review_fingerprints(reopened, tasks)
        # At least local pin premises must be identical after source relocation.
        assert fresh[task_key] == fps[task_key]
        decisions = ReviewDecisionStore(moved)
        decisions.begin_run(original_key, fresh)
        state = {
            t.stable_key: t
            for t in decisions.apply(tasks, fingerprints=fresh, project=original_key)
        }
        assert state[task_key].review_decision.status == "waived"
        assert state[task_key].review_decision.reason == "公开合成理由"
        assert decisions.history()[0]["decision"]["reason"] == "公开合成理由"
    finally:
        close_workbench_context(reopened)
        shutil.rmtree(directory)


def test_stale_save_does_not_replace_catalog_entry(project):
    source, context, journal, run, _, _ = project
    store = ManagedProjects(journal)
    good = store.save(context, run)
    with pytest.raises(ReviewConflictError):
        store.save(context, "obsolete")
    assert store.list() == [good]


def test_corrupt_sources_refuse_open_and_preserve_journal(project):
    _, context, journal, run, _, _ = project
    store = ManagedProjects(journal)
    saved = store.save(context, run)
    (store.inputs.root / saved["snapshot"] / "files/000000.bin").write_bytes(b"corrupt")
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="hash mismatch"):
        store.open(saved["id"])
    assert journal.read_bytes() == before


def test_legacy_schema_is_additive_and_keeps_history(tmp_path):
    journal = tmp_path / "legacy.sqlite"
    old = DecisionJournal(journal)
    old.save("legacy", "run", {}, [{"event": "old"}])
    with sqlite3.connect(journal) as db:
        db.execute("DROP TABLE managed_projects")
        db.execute("PRAGMA user_version=1")
    reopened = ManagedProjects(journal)
    assert reopened.list() == []
    assert reopened.journal.history("legacy")[0]["event"] == "old"


class NoChat:
    datasheet_search_enabled = False


def test_api_save_open_and_rerun_keep_namespace(project):
    from fastapi.testclient import TestClient
    from hardwise.workbench.server import create_workbench_app

    source, context, journal, _, _, _ = project
    app = create_workbench_app(
        context, NoChat(), review_db=journal, auto_datasheet_candidates=False
    )
    with TestClient(app) as client:
        initial = client.get("/api/workbench/state").json()
        run = initial["review_decisions"]["run_id"]
        saved = client.post("/api/workbench/projects/save", params={"expected_run_id": run})
        assert saved.status_code == 200, saved.text
        identifier = saved.json()["id"]
        assert client.get("/api/workbench/projects").json()["projects"][0]["id"] == identifier
        shutil.rmtree(source)
        response = client.post(
            f"/api/workbench/projects/{identifier}/open", params={"expected_run_id": run}
        )
        assert response.status_code == 200, response.text
        reopened = response.json()
        assert (
            reopened["review_decisions"]["project_id"] == initial["review_decisions"]["project_id"]
        )
        assert reopened["review_decisions"]["waived"] == initial["review_decisions"]["waived"]
        assert (
            client.post("/api/workbench/projects/save", params={"expected_run_id": run}).status_code
            == 409
        )
        rerun = client.post("/api/workbench/rerun")
        assert rerun.status_code == 200, rerun.text
        assert (
            rerun.json()["review_decisions"]["project_id"]
            == initial["review_decisions"]["project_id"]
        )


def test_failed_api_open_keeps_active_context(project):
    from fastapi.testclient import TestClient
    from hardwise.workbench.server import create_workbench_app

    _, context, journal, _, _, _ = project
    app = create_workbench_app(
        context, NoChat(), review_db=journal, auto_datasheet_candidates=False
    )
    with TestClient(app) as client:
        initial = client.get("/api/workbench/state").json()
        run = initial["review_decisions"]["run_id"]
        saved = client.post("/api/workbench/projects/save", params={"expected_run_id": run}).json()
        store = ManagedProjects(journal)
        (store.inputs.root / saved["snapshot"] / "files/000000.bin").unlink()
        result = client.post(
            f"/api/workbench/projects/{saved['id']}/open", params={"expected_run_id": run}
        )
        assert result.status_code == 422, result.text
        assert app.state.workbench_context["value"] is context
        assert (
            client.get("/api/workbench/state").json()["review_decisions"]
            == initial["review_decisions"]
        )


def test_interrupted_schema_upgrade_rolls_back(project, monkeypatch):
    from contextlib import contextmanager

    _, _, journal, _, _, _ = project
    with sqlite3.connect(journal) as db:
        db.execute("DROP TABLE managed_projects")
        db.execute("PRAGMA user_version=1")
    original = DecisionJournal.connect

    class InterruptBeforeVersion:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, sql, *args):
            if sql == "PRAGMA user_version=2":
                raise OSError("simulated upgrade interruption")
            return self.connection.execute(sql, *args)

    @contextmanager
    def interrupted(self):
        with original(self) as db:
            yield InterruptBeforeVersion(db)

    with monkeypatch.context() as scoped:
        scoped.setattr(DecisionJournal, "connect", interrupted)
        with pytest.raises(OSError, match="upgrade interruption"):
            DecisionJournal(journal)
    with sqlite3.connect(journal) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert (
            db.execute(
                "SELECT count(*) FROM sqlite_master WHERE name='managed_projects'"
            ).fetchone()[0]
            == 0
        )
    assert DecisionJournal(journal).history_count(review_project_key(project[1])) == 1


@pytest.mark.parametrize("descriptor", ["{}", '{"schema_version":"future"}', "[]"])
def test_invalid_saved_descriptor_is_not_activated(project, descriptor):
    _, context, journal, run, _, _ = project
    store = ManagedProjects(journal)
    saved = store.save(context, run)
    with store.journal.connect() as db:
        db.execute("UPDATE managed_projects SET descriptor=? WHERE id=?", (descriptor, saved["id"]))
    with pytest.raises(ValueError):
        store.open(saved["id"])
