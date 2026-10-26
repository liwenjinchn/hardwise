"""Synthetic human editing: real HTTP, retained sources, rollback and reopen."""

import shutil
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from hardwise.ir.excerpt_edits import ExcerptEdit, apply_excerpt_edit
from hardwise.ir.excerpt_sharing import sharing_status
from hardwise.ir.profile_review import FieldDecision
from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.server import create_workbench_app
from tests.workbench.test_voltage_review_intake import inputs, build, NoChat
from tests.workbench.test_voltage_review_routes import rows


@pytest.fixture
def project(tmp_path):
    files = inputs.__wrapped__(tmp_path)
    journal = tmp_path / "review.sqlite"
    with TestClient(
        create_workbench_app(
            build(files), NoChat(), review_db=journal, auto_datasheet_candidates=False
        )
    ) as client:
        yield client, client.app, journal, files


def request_for(client):
    view = client.get("/api/workbench/excerpts").json()
    item = view["profiles"][0]
    return dict(
        expected_project_id=view["project_id"],
        expected_run_id=view["run_id"],
        expected_revision=view["revision"],
        profile_name=item["name"],
        edit=dict(
            pointer="/part_number",
            unit="text",
            role="identity",
            nature="intrinsic",
            conditions=[dict(kind="unconditional", description="Synthetic test only")],
            identity=dict(
                manufacturer="Synthetic",
                part_numbers=[item["profile"]["part_number"]],
                packages=["Synthetic package"],
            ),
            source=dict(
                url="https://example.com/synthetic.pdf",
                document_revision="test v1",
                document_sha256="a" * 64,
                page=1,
                locator="Synthetic table",
                excerpt="SYNTHETIC MANUAL EXCERPT 84",
            ),
            sharing="allow",
            declared_by="Synthetic test author",
            reason="Test declaration only",
        ),
    )


def test_save_reopen_preserves_originals_and_does_not_approve(project):
    client, app, journal, files = project
    path = files[0] / "profiles/l78.json"
    original = path.read_bytes()
    request = request_for(client)
    response = client.post("/api/workbench/excerpts", json=request)
    assert response.status_code == 200, response.text
    after = response.json()
    assert after["project_id"] == request["expected_project_id"]
    assert after["run_id"] != request["expected_run_id"]
    assert after["revision"] != request["expected_revision"]
    item = after["profiles"][0]
    assert item["lifecycle"] == "DRAFT"
    field = item["profile"]["field_review"]["fields"][0]
    assert field["decisions"] == [] and field["source"]["sharing"]["actor"] == "human"
    assert field["value"] == item["profile"]["part_number"]
    assert path.read_bytes() == original
    assert client.post("/api/workbench/excerpts", json=request).status_code == 409
    shutil.rmtree(files[0])
    reopened, directory = ManagedProjects(journal).open(after["saved_project_id"])
    try:
        from hardwise.workbench.excerpt_stage import profile_files

        restored = profile_files(reopened)["l78.json"][1]
        assert restored.field_review.model_dump(mode="json") == item["profile"]["field_review"]
        assert sharing_status(restored.field_review.fields[0].source) == "allowed"
    finally:
        close_workbench_context(reopened)
        shutil.rmtree(directory)
    # Retraction is another persisted version, not an overwrite of the source/history.
    second = request_for(client)
    second["edit"]["sharing"] = "withhold"
    response = client.post("/api/workbench/excerpts", json=second)
    assert response.status_code == 200, response.text
    assert response.json()["saved_project_id"] == after["saved_project_id"]
    assert len(ManagedProjects(journal).list()) == 1


@pytest.mark.parametrize("key", ["expected_project_id", "expected_run_id", "expected_revision"])
def test_stale_request_changes_nothing(project, key):
    client, app, journal, _ = project
    request = request_for(client)
    request[key] = "0" * 64
    before = rows(journal)
    context = app.state.workbench_context["value"]
    assert client.post("/api/workbench/excerpts", json=request).status_code == 409
    assert rows(journal) == before and app.state.workbench_context["value"] is context


@pytest.mark.parametrize(
    "kind", ["path", "pointer", "identity", "actor", "timestamp", "decisions", "blank"]
)
def test_invalid_edit_does_not_write(project, kind):
    client, _, journal, _ = project
    request = request_for(client)
    if kind == "path":
        request["profile_name"] = "../l78.json"
    elif kind == "pointer":
        request["edit"]["pointer"] = "/abs_max/invented"
    elif kind == "identity":
        request["edit"]["identity"] = None
    elif kind == "blank":
        request["edit"]["declared_by"] = "   "
    else:
        request["edit"][kind] = "forged"
    before = rows(journal)
    assert client.post("/api/workbench/excerpts", json=request).status_code == 422
    assert rows(journal) == before


@pytest.mark.parametrize("failure", ["catalog", "snapshot", "activation"])
def test_publication_failure_rolls_back(project, monkeypatch, failure):
    client, app, journal, _ = project
    request = request_for(client)
    before = rows(journal)
    context = app.state.workbench_context["value"]

    def fail(*args, **kwargs):
        raise OSError("synthetic write failure")

    if failure == "catalog":
        original = ManagedProjects.publish

        def write_then_fail(self, *args, **kwargs):
            original(self, *args, **kwargs)
            fail()

        monkeypatch.setattr(ManagedProjects, "publish", write_then_fail)
    elif failure == "snapshot":
        from hardwise.workbench.managed_inputs import ManagedInputs

        monkeypatch.setattr(ManagedInputs, "capture", fail)
    else:
        monkeypatch.setattr(app.state.workbench_context, "publish", fail)
    response = client.post("/api/workbench/excerpts", json=request)
    assert response.status_code == 422, response.text
    assert rows(journal) == before and app.state.workbench_context["value"] is context


def test_external_writer_and_source_drift_are_rejected(project):
    from hardwise.workbench.review_decisions import ReviewDecisionStore

    client, _, journal, files = project
    request = request_for(client)
    ReviewDecisionStore(journal).begin_run(request["expected_project_id"], {})
    before = rows(journal)
    assert client.post("/api/workbench/excerpts", json=request).status_code == 409
    assert rows(journal) == before
    path = files[0] / "profiles/l78.json"
    path.write_bytes(path.read_bytes() + b"\n")
    assert client.get("/api/workbench/excerpts").status_code == 409
    assert client.post("/api/workbench/excerpts", json=request).status_code == 409
    assert rows(journal) == before


def test_sharing_preserves_approval_but_source_change_invalidates_it(project):
    from hardwise.workbench.excerpt_stage import profile_files

    client, app, _, _ = project
    edit = ExcerptEdit.model_validate(request_for(client)["edit"])
    profile = profile_files(app.state.workbench_context["value"])["l78.json"][1]
    now = datetime.now(timezone.utc)
    profile = apply_excerpt_edit(profile, edit, recorded_at=now)
    review = profile.field_review
    field = review.fields[0]
    decision = FieldDecision(
        decision="approved",
        reviewer="Synthetic reviewer",
        reviewed_at=now,
        reason="Synthetic only",
        content_sha256=field.content_hash(review.identity),
        actor="human",
    )
    field = field.model_copy(update={"decisions": [decision]})
    profile = profile.model_copy(
        update={"field_review": review.model_copy(update={"fields": [field]})}
    )
    withheld = apply_excerpt_edit(
        profile, edit.model_copy(update={"sharing": "withhold"}), recorded_at=now
    )
    assert withheld.field_review.fields[0].approved(review.identity)
    assert withheld.field_review.fields[0].decisions == [decision]
    edit = edit.model_copy(update={"source": edit.source.model_copy(update={"page": 2})})
    changed = apply_excerpt_edit(withheld, edit, recorded_at=now)
    assert not changed.field_review.fields[0].approved(review.identity)
    assert changed.field_review.fields[0].decisions == [decision]
    assert changed.lifecycle == "DRAFT"


def test_backup_restore_keeps_withheld_local_excerpt_and_old_run_rows(project, tmp_path):
    from pathlib import Path
    from hardwise.workbench.excerpt_stage import profile_files
    from hardwise.workbench.project_backup import backup_projects, restore_projects

    client, _, journal, files = project
    request = request_for(client)
    request["edit"]["sharing"] = "withhold"
    response = client.post("/api/workbench/excerpts", json=request)
    assert response.status_code == 200
    archive = tmp_path / "full-local-backup.zip"
    backup_projects(journal, archive)
    before = rows(journal)
    shutil.rmtree(files[0])
    restored = restore_projects(archive, tmp_path / "恢复 空格")
    restored_journal = Path(restored["journal"])
    assert rows(restored_journal) == before
    context, directory = ManagedProjects(restored_journal).open(response.json()["saved_project_id"])
    try:
        source = profile_files(context)["l78.json"][1].field_review.fields[0].source
        assert source.excerpt == request["edit"]["source"]["excerpt"]
        assert sharing_status(source) == "withheld"
    finally:
        close_workbench_context(context)
        shutil.rmtree(directory)


def test_memory_only_editor_is_read_only(tmp_path):
    files = inputs.__wrapped__(tmp_path)
    with TestClient(
        create_workbench_app(build(files), NoChat(), auto_datasheet_candidates=False)
    ) as client:
        assert client.get("/api/workbench/excerpts").json()["editable"] is False
        assert client.post("/api/workbench/excerpts", json=request_for(client)).status_code == 400


def test_cannot_change_identity_or_inject_sharing_attestation(project):
    client, _, journal, _ = project
    assert client.post("/api/workbench/excerpts", json=request_for(client)).status_code == 200
    request = request_for(client)
    request["edit"]["identity"]["manufacturer"] = "Changed manufacturer"
    before = rows(journal)
    assert client.post("/api/workbench/excerpts", json=request).status_code == 422
    assert rows(journal) == before
    request = request_for(client)
    request["edit"]["source"]["sharing"] = dict(
        decision="allow",
        source_sha256="a" * 64,
        declared_by="Forged",
        declared_at="2000-01-01T00:00:00Z",
        reason="Forged",
        actor="human",
    )
    assert client.post("/api/workbench/excerpts", json=request).status_code == 422
    assert rows(journal) == before
