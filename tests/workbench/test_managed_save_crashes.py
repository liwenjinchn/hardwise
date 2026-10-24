"""Real process exits at source/SQLite publication boundaries preserve saved data."""

import json
import shutil
import sqlite3
import subprocess
import sys
import zipfile

import pytest

from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.project_backup import backup_projects
from hardwise.workbench.review_decisions import ReviewDecisionStore
from hardwise.workbench.task_projection import build_review_tasks

CHILD = r"""
from contextlib import contextmanager
from pathlib import Path
import os, sys
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.decision_journal import DecisionJournal
from hardwise.workbench.managed_projects import ManagedProjects
source, journal, run, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
context = build_workbench_context(netlist_path=source/'l78_regulator.net', bom_path=source/'l78_regulator_bom.csv', profiles=source/'profiles')
store = ManagedProjects(journal)
original_rename = Path.rename

def interrupted_rename(path, target):
    if path.name.startswith('.staging-') and mode == 'before_publish':
        os._exit(41)
    result = original_rename(path, target)
    if path.name.startswith('.staging-') and mode == 'after_publish':
        os._exit(42)
    return result
Path.rename = interrupted_rename
original_connect = DecisionJournal.connect

class Transaction:
    def __init__(self, connection): self.connection = connection
    def execute(self, sql, *args):
        result = self.connection.execute(sql, *args)
        if sql.startswith('INSERT INTO managed_projects') and mode == 'before_commit':
            os._exit(43)
        return result

@contextmanager
def interrupted_connect(self):
    with original_connect(self) as connection:
        yield Transaction(connection)
    if mode == 'after_commit':
        os._exit(44)
DecisionJournal.connect = interrupted_connect
store.save(context, run)
raise AssertionError('failpoint was not reached')
"""


def _database_rows(journal):
    with sqlite3.connect(journal) as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in ("review_state", "review_events", "review_runs", "review_heads")
        }


@pytest.mark.parametrize(
    ("mode", "exit_code", "committed"),
    [
        ("before_publish", 41, False),
        ("after_publish", 42, False),
        ("before_commit", 43, False),
        ("after_commit", 44, True),
    ],
)
def test_process_exit_during_source_save_preserves_a_recoverable_version(
    managed_review, tmp_path, mode, exit_code, committed
):
    source, context, journal, run, task_key, _ = managed_review
    store = ManagedProjects(journal)
    previous = store.save(context, run)
    rows = _database_rows(journal)
    # A byte change without an electrical premise change exercises an actual new
    # saved source revision, rather than merely repeating the previous source hash.
    bom = source / "l78_regulator_bom.csv"
    original_bom = bom.read_bytes()
    changed_bom = original_bom + b"\n"
    bom.write_bytes(changed_bom)
    child = subprocess.run(
        [sys.executable, "-c", CHILD, str(source), str(journal), run, mode],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == exit_code, child.stderr
    reopened_store = ManagedProjects(journal)
    saved = reopened_store.list()[0]
    assert saved["id"] == previous["id"]
    assert (saved["snapshot"] != previous["snapshot"]) is committed
    assert _database_rows(journal) == rows
    # Both crash outcomes must survive the source files being removed.
    shutil.rmtree(source)
    reopened, directory = reopened_store.open(saved["id"])
    try:
        assert reopened.bom.source_file.read_bytes() == (changed_bom if committed else original_bom)
        tasks = build_review_tasks(reopened)
        fps = review_fingerprints(reopened, tasks)
        decisions = ReviewDecisionStore(journal)
        decisions.begin_run(review_project_key(reopened), fps)
        applied = {
            t.stable_key: t
            for t in decisions.apply(tasks, fingerprints=fps, project=review_project_key(reopened))
        }
        assert applied[task_key].review_decision.status == "waived"
        assert applied[task_key].review_decision.reason == "公开合成理由"
    finally:
        close_workbench_context(reopened)
        shutil.rmtree(directory)
    backup = tmp_path / "post-crash.zip"
    backup_projects(journal, backup)
    with zipfile.ZipFile(backup) as archive:
        manifest = json.loads(archive.read("backup-manifest.json"))
        members = manifest["files"]
        included = {
            name.split("/")[1] for name in members if name.startswith("journal.sqlite.inputs/")
        }
    expected = {previous["snapshot"], saved["snapshot"]}
    assert included == expected
    # A dead writer's staging/orphan directories are not promoted or backed up.
    if mode == "before_publish":
        assert any(p.name.startswith(".staging-") for p in reopened_store.inputs.root.iterdir())
    elif not committed:
        assert (
            len([p for p in reopened_store.inputs.root.iterdir() if not p.name.startswith(".")])
            == 2
        )
