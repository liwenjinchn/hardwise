"""Archive HTTP operations keep current review isolated from recovered copies."""

from pathlib import Path
import shutil
import pytest
from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key
from hardwise.workbench.managed_projects import ManagedProjects


class NoChat:
    datasheet_search_enabled = False


@pytest.fixture
def project(managed_review):
    return managed_review


def test_browser_archive_roundtrip_keeps_active_review_and_restores_history(project, tmp_path):
    from fastapi.testclient import TestClient
    from hardwise.workbench.server import create_workbench_app

    _, context, journal, _, key, _ = project
    app = create_workbench_app(
        context, NoChat(), review_db=journal, auto_datasheet_candidates=False
    )
    with TestClient(app) as client:
        state = client.get("/api/workbench/state").json()
        run = state["review_decisions"]["run_id"]
        assert (
            client.post("/api/workbench/projects/save", params={"expected_run_id": run}).status_code
            == 200
        )
        backup = client.post("/api/workbench/projects/backup", params={"expected_run_id": run})
        assert backup.status_code == 200, backup.text
        assert backup.headers["content-type"] == "application/zip"
        assert backup.headers["X-Hardwise-Backup-Saved-Projects"] == "1"
        restored = client.post(
            "/api/workbench/projects/restore",
            params={"expected_run_id": run},
            files={"archive": ("../../active.sqlite", backup.content, "application/zip")},
        )
        assert restored.status_code == 200, restored.text
        receipt = restored.json()
        restored_journal = Path(receipt["journal"])
        assert restored_journal != journal
        assert restored_journal.parent.parent == journal.resolve().with_name(
            journal.name + ".restored"
        )
        assert (restored_journal.parent / "restore-info.json").is_file()
        restored_store = ManagedProjects(restored_journal)
        opened, directory = restored_store.open(receipt["saved_project_ids"][0])
        try:
            data, _ = restored_store.journal.load(review_project_key(opened))
            assert data[key]["reason"] == "公开合成理由"
            assert data[key]["status"] == "waived"
        finally:
            close_workbench_context(opened)
            shutil.rmtree(directory)
        assert app.state.workbench_context["value"] is context
        assert (
            client.get("/api/workbench/state").json()["review_decisions"]
            == state["review_decisions"]
        )


@pytest.mark.parametrize("operation", ["backup", "restore"])
def test_archive_endpoints_reject_stale_run_before_work(project, operation):
    from fastapi.testclient import TestClient
    from hardwise.workbench.server import create_workbench_app

    _, context, journal, _, _, _ = project
    app = create_workbench_app(context, NoChat(), review_db=journal)
    with TestClient(app) as client:
        kwargs = (
            {"files": {"archive": ("bad.zip", b"invalid", "application/zip")}}
            if operation == "restore"
            else {}
        )
        response = client.post(
            f"/api/workbench/projects/{operation}", params={"expected_run_id": "old"}, **kwargs
        )
        assert response.status_code == 409, response.text
        assert not journal.with_name(journal.name + ".restored").exists()


def test_invalid_archive_upload_keeps_active_review(project, monkeypatch):
    from fastapi.testclient import TestClient
    from hardwise.workbench.server import create_workbench_app
    import hardwise.workbench.project_archive_routes as routes

    _, context, journal, _, _, _ = project
    app = create_workbench_app(context, NoChat(), review_db=journal)
    with TestClient(app) as client:
        before = client.get("/api/workbench/state").json()
        query = {"expected_run_id": before["review_decisions"]["run_id"]}
        response = client.post(
            "/api/workbench/projects/restore",
            params=query,
            files={"archive": ("bad.zip", b"invalid", "application/zip")},
        )
        assert response.status_code == 422, response.text
        monkeypatch.setattr(routes, "MAX_UPLOAD", 0)
        response = client.post(
            "/api/workbench/projects/restore",
            params=query,
            files={"archive": ("large.zip", b"too large", "application/zip")},
        )
        assert response.status_code == 413, response.text
        assert (
            client.get("/api/workbench/state").json()["review_decisions"]
            == before["review_decisions"]
        )
        assert app.state.workbench_context["value"] is context


def test_receipt_write_failure_removes_only_new_restored_copy(project, monkeypatch):
    from fastapi.testclient import TestClient
    from hardwise.workbench.server import create_workbench_app

    _, context, journal, _, _, _ = project
    app = create_workbench_app(context, NoChat(), review_db=journal)
    original = Path.write_text

    def failing_receipt(path, *args, **kwargs):
        if path.name == "restore-info.json":
            raise OSError("simulated receipt write failure")
        return original(path, *args, **kwargs)

    with TestClient(app) as client:
        before = client.get("/api/workbench/state").json()
        query = {"expected_run_id": before["review_decisions"]["run_id"]}
        assert client.post("/api/workbench/projects/save", params=query).status_code == 200
        backup = client.post("/api/workbench/projects/backup", params=query)
        assert backup.status_code == 200
        monkeypatch.setattr(Path, "write_text", failing_receipt)
        restored = client.post(
            "/api/workbench/projects/restore",
            params=query,
            files={"archive": ("backup.zip", backup.content, "application/zip")},
        )
        assert restored.status_code == 422, restored.text
        assert "receipt write failure" in restored.json()["detail"]
        root = journal.resolve().with_name(journal.name + ".restored")
        assert list(root.iterdir()) == []
        assert (
            client.get("/api/workbench/state").json()["review_decisions"]
            == before["review_decisions"]
        )


def test_restore_launch_instructions_quote_spaces_and_apostrophes():
    import shlex
    from hardwise.workbench.project_archive_routes import _receipt

    journal = "/tmp/公开 Bob's copy/journal.sqlite"
    receipt = _receipt(
        {"journal": journal, "saved_project_ids": ["saved-id"], "source_unowned_project_ids": []},
        "restore-id",
    )
    argv = shlex.split(receipt.launches[0].command_posix)
    assert argv[argv.index("--review-db") + 1] == journal
    assert argv[argv.index("--open-project") + 1] == "saved-id"
    assert "Bob''s copy" in receipt.launches[0].command_powershell
