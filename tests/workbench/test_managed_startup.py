"""Saved-project startup needs no old sources and owns temporary reconstruction."""

from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key, review_fingerprints
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.review_decisions import ReviewDecisionStore
from hardwise.workbench.task_projection import build_review_tasks


@pytest.fixture
def saved_project(tmp_path):
    source = tmp_path / "sources"
    source.mkdir()
    (source / "profiles").mkdir()
    for name in ["l78_regulator.net", "l78_regulator_bom.csv"]:
        shutil.copyfile(Path("tests/fixtures/allegro") / name, source / name)
    shutil.copyfile("data/datasheet_profiles/l78.json", source / "profiles/l78.json")
    journal = tmp_path / "review.sqlite"
    context = build_workbench_context(
        netlist_path=source / "l78_regulator.net",
        bom_path=source / "l78_regulator_bom.csv",
        profiles=source / "profiles",
    )
    try:
        tasks = build_review_tasks(context)
        decisions = ReviewDecisionStore(journal)
        key = review_project_key(context)
        decisions.begin_run(key, review_fingerprints(context, tasks))
        run = decisions.summary([], project=key).run_id
        saved = ManagedProjects(journal).save(context, run)
    finally:
        close_workbench_context(context)
    shutil.rmtree(source)
    return journal, saved


def command(saved_project):
    journal, saved = saved_project
    return [
        "serve-workbench",
        "--review-db",
        str(journal),
        "--open-project",
        saved["id"],
        "--no-auto-datasheet-candidates",
    ]


def test_saved_startup_dry_run_without_original_sources(saved_project, monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = CliRunner().invoke(app, [*command(saved_project), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "mode=real" in result.output
    assert "3 components" in result.output


@pytest.mark.parametrize("failure", [False, True])
def test_saved_server_owns_materialization_until_server_exit(saved_project, monkeypatch, failure):
    import uvicorn
    import hardwise.workbench.startup as startup

    original = startup.ManagedProjects.open
    directories = []

    def tracked(self, identifier):
        context, directory = original(self, identifier)
        directories.append(directory)
        return context, directory

    def serve(app_obj, **_kwargs):
        assert directories[0].exists()
        with TestClient(app_obj) as client:
            state = client.get("/api/workbench/state").json()
            assert state["review_decisions"]["project_id"] == saved_project[1]["project_id"]
            assert client.post("/api/workbench/rerun").status_code == 200
        if failure:
            raise RuntimeError("simulated server exit")

    monkeypatch.setattr(startup.ManagedProjects, "open", tracked)
    monkeypatch.setattr(uvicorn, "run", serve)
    result = CliRunner().invoke(app, command(saved_project))
    assert result.exit_code == (1 if failure else 0), result.output
    assert len(directories) == 1
    assert not directories[0].exists()


@pytest.mark.parametrize(
    "extra", [["old.net"], ["--profiles", "other"], ["--voltage-facts", "facts.json"]]
)
def test_saved_startup_rejects_mixed_source_arguments(saved_project, extra):
    result = CliRunner().invoke(app, [*command(saved_project), *extra, "--dry-run"])
    assert result.exit_code == 1
    assert "cannot be combined" in result.output


def test_unknown_saved_project_does_not_start_server(saved_project):
    args = command(saved_project)
    args[args.index("--open-project") + 1] = "missing"
    result = CliRunner().invoke(app, [*args, "--dry-run"])
    assert result.exit_code == 1


def test_saved_startup_requires_existing_journal(tmp_path):
    missing = tmp_path / "missing.sqlite"
    result = CliRunner().invoke(
        app,
        ["serve-workbench", "--open-project", "missing", "--review-db", str(missing), "--dry-run"],
    )
    assert result.exit_code == 1
    assert "existing --review-db" in result.output
    assert not missing.exists()
