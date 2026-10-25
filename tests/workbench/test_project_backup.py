"""A complete saved-project backup survives source loss and rejects unsafe archives."""

import json
from pathlib import Path
import shutil
import sqlite3
import stat
from unittest.mock import patch
import zipfile

import pytest
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
from hardwise.workbench.decision_journal import DecisionJournal
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.project_backup import backup_projects, restore_projects, MARKER
from hardwise.workbench.review_decisions import ReviewDecisionStore, ReviewDecisionRequest
from hardwise.workbench.task_projection import build_review_tasks


@pytest.fixture
def saved(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "profiles").mkdir()
    for name in ["l78_regulator.net", "l78_regulator_bom.csv"]:
        shutil.copyfile(Path("tests/fixtures/allegro") / name, source / name)
    shutil.copyfile("data/datasheet_profiles/l78.json", source / "profiles/l78.json")
    context = build_workbench_context(
        netlist_path=source / "l78_regulator.net",
        bom_path=source / "l78_regulator_bom.csv",
        profiles=source / "profiles",
    )
    journal = tmp_path / "review.sqlite"
    decisions = ReviewDecisionStore(journal)
    key = review_project_key(context)
    fps = review_fingerprints(context, build_review_tasks(context))
    decisions.begin_run(key, fps)
    run = decisions.summary([], project=key).run_id
    task = next(t for t in build_review_tasks(context) if t.kind == "pin_check")
    decisions.update(
        known_keys=list(fps),
        request=ReviewDecisionRequest(
            stable_keys=[task.stable_key],
            status="accepted_risk",
            reason="公开合成备份理由",
            expected_run_id=run,
        ),
        fingerprints=fps,
    )
    first = ManagedProjects(journal).save(context, run)
    second = ManagedProjects(journal).save(context, run)
    close_workbench_context(context)
    archive = tmp_path / "complete.zip"
    yield source, journal, first, second, archive, task.stable_key


def test_complete_restore_after_originals_and_journal_deleted(saved, tmp_path):
    source, journal, first, second, archive, task = saved
    backup_projects(journal, archive)
    shutil.rmtree(source)
    journal.unlink()
    shutil.rmtree(journal.with_name(journal.name + ".inputs"))
    result = restore_projects(archive, tmp_path / "恢复 空格")
    restored = Path(result["journal"])
    store = ManagedProjects(restored)
    assert store.list()[0]["id"] == second["id"] == first["id"]
    assert (store.inputs.root / first["snapshot"]).is_dir()
    assert (store.inputs.root / second["snapshot"]).is_dir()
    context, directory = store.open(second["id"])
    try:
        decisions = ReviewDecisionStore(restored)
        fps = review_fingerprints(context, build_review_tasks(context))
        decisions.begin_run(review_project_key(context), fps)
        state, _ = decisions._journal.load(second["project_id"])
        assert state[task]["reason"] == "公开合成备份理由"
        assert state[task]["status"] == "accepted_risk"
        assert decisions.history()[0]["decision"]["reason"] == "公开合成备份理由"
    finally:
        close_workbench_context(context)
        shutil.rmtree(directory)


def test_existing_output_and_restore_directory_are_preserved(saved, tmp_path):
    _, journal, _, _, archive, _ = saved
    archive.write_bytes(b"original archive")
    with pytest.raises(FileExistsError):
        backup_projects(journal, archive)
    assert archive.read_bytes() == b"original archive"
    archive.unlink()
    backup_projects(journal, archive)
    target = tmp_path / "exists"
    target.mkdir()
    (target / "keep").write_bytes(b"untouched")
    with pytest.raises(FileExistsError):
        restore_projects(archive, target)
    assert (target / "keep").read_bytes() == b"untouched"


@pytest.mark.parametrize(
    "damage",
    ["hash", "missing", "extra", "traversal", "symlink", "duplicate", "version", "metadata"],
)
def test_invalid_backup_never_creates_restore_destination(saved, tmp_path, damage):
    _, journal, _, _, archive, _ = saved
    backup_projects(journal, archive)
    with zipfile.ZipFile(archive) as z:
        members = {i.filename: z.read(i) for i in z.infolist()}
    if damage == "hash":
        members["journal.sqlite"] += b"tamper"
    elif damage == "missing":
        members.pop(next(n for n in members if n.endswith(".bin")))
    elif damage == "extra":
        members["unlisted"] = b"extra"
    elif damage in {"version", "metadata"}:
        manifest = json.loads(members["backup-manifest.json"])
        if damage == "version":
            manifest["schema_version"] = "future"
        else:
            manifest["saved_project_ids"] = ["invented"]
        members["backup-manifest.json"] = json.dumps(manifest).encode()
    elif damage == "traversal":
        manifest = json.loads(members["backup-manifest.json"])
        manifest["files"]["../escape"] = manifest["files"].pop("journal.sqlite")
        members["../escape"] = members.pop("journal.sqlite")
        members["backup-manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(archive, "w") as z:
        for name, content in members.items():
            if damage == "symlink" and name == "journal.sqlite":
                entry = zipfile.ZipInfo(name)
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(entry, content)
            else:
                z.writestr(name, content)
        if damage == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                z.writestr("journal.sqlite", members["journal.sqlite"])
    target = tmp_path / "rejected"
    with pytest.raises((ValueError, KeyError, zipfile.BadZipFile)):
        restore_projects(archive, target)
    assert not target.exists()
    assert not (tmp_path / "escape").exists()


def test_ordinary_publication_failure_cleans_only_new_destination(saved, tmp_path):
    _, journal, _, _, archive, _ = saved
    backup_projects(journal, archive)
    original_move = shutil.move
    target = tmp_path / "failed"

    def fail_journal(source, dest, *args, **kwargs):
        if Path(source).name == "journal.sqlite":
            raise OSError("simulated publication failure")
        return original_move(source, dest, *args, **kwargs)

    with patch("hardwise.workbench.project_backup.shutil.move", side_effect=fail_journal):
        with pytest.raises(OSError, match="publication failure"):
            restore_projects(archive, target)
    assert not target.exists()
    assert journal.is_file()


def test_incomplete_restore_marker_blocks_all_journal_opens(tmp_path):
    (tmp_path / MARKER).write_text("incomplete")
    with pytest.raises(ValueError, match="restore is incomplete"):
        DecisionJournal(tmp_path / "journal.sqlite")
    assert not (tmp_path / "journal.sqlite").exists()


def test_cli_backup_and_restore(saved, tmp_path):
    _, journal, _, second, archive, _ = saved
    runner = CliRunner()
    backup = runner.invoke(
        app, ["backup-projects", "--review-db", str(journal), "--output", str(archive)]
    )
    assert backup.exit_code == 0, backup.output
    restored = runner.invoke(
        app, ["restore-projects", str(archive), "--destination", str(tmp_path / "cli-restore")]
    )
    assert restored.exit_code == 0, restored.output
    data = json.loads(restored.output)
    result = runner.invoke(
        app,
        [
            "serve-workbench",
            "--review-db",
            data["journal"],
            "--open-project",
            second["id"],
            "--dry-run",
            "--no-auto-datasheet-candidates",
        ],
    )
    assert result.exit_code == 0, result.output


def test_backup_uses_frozen_catalog_when_another_save_commits(saved, tmp_path, monkeypatch):
    from hardwise.workbench.managed_inputs import ManagedInputs

    _, journal, first, second, archive, _ = saved
    store = ManagedProjects(journal)
    context, directory = store.open(second["id"])
    with sqlite3.connect(journal) as db:
        run = db.execute("SELECT run_id FROM review_runs ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    original = ManagedInputs.load
    committed = []

    def save_during_copy(self, snapshot):
        if not committed and self.root == store.inputs.root:
            committed.append(store.save(context, run))
        return original(self, snapshot)

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(ManagedInputs, "load", save_during_copy)
            backup_projects(journal, archive)
        assert committed[0]["snapshot"] != second["snapshot"]
        restored = restore_projects(archive, tmp_path / "frozen")
        restored_store = ManagedProjects(Path(restored["journal"]))
        assert restored_store.list()[0]["snapshot"] == second["snapshot"]
        assert {p.name for p in restored_store.inputs.root.iterdir()} == {
            first["snapshot"],
            second["snapshot"],
        }
    finally:
        close_workbench_context(context)
        shutil.rmtree(directory)


def test_process_exit_during_restore_leaves_blocked_incomplete_target(saved, tmp_path):
    import subprocess
    import sys

    _, journal, _, _, archive, _ = saved
    backup_projects(journal, archive)
    destination = tmp_path / "interrupted"
    code = """import os,sys
from pathlib import Path
import hardwise.workbench.project_backup as backup
original = backup.shutil.move
def interrupted(source, target):
    result = original(source, target)
    if str(source).endswith('.inputs'):
        os._exit(23)
    return result
backup.shutil.move = interrupted
backup.restore_projects(Path(sys.argv[1]), Path(sys.argv[2]))
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(archive), str(destination)], capture_output=True, text=True
    )
    assert child.returncode == 23, child.stderr
    assert (destination / MARKER).is_file()
    with pytest.raises(ValueError, match="restore is incomplete"):
        DecisionJournal(destination / "journal.sqlite")
    assert journal.is_file()
    restored = restore_projects(archive, tmp_path / "second-attempt")
    assert Path(restored["journal"]).is_file()


def test_backup_cannot_write_extra_files_into_owned_sources(saved):
    _, journal, _, second, _, _ = saved
    store = ManagedProjects(journal)
    target = store.inputs.root / second["snapshot"] / "backup.zip"
    with pytest.raises(ValueError, match="outside the managed input"):
        backup_projects(journal, target)
    assert not target.exists()
    store.inputs.load(second["snapshot"])


def test_restore_cannot_mutate_a_managed_input_directory(saved):
    _, journal, _, second, archive, _ = saved
    backup_projects(journal, archive)
    store = ManagedProjects(journal)
    target = store.inputs.root / second["snapshot"] / "restored"
    with pytest.raises(ValueError, match="outside managed input"):
        restore_projects(archive, target)
    assert not target.exists()
    store.inputs.load(second["snapshot"])
