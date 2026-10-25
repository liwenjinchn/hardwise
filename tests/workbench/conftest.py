"""Shared public managed-review fixture for persistence integration tests."""

from pathlib import Path
import shutil
import pytest
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_project_key, review_fingerprints
from hardwise.workbench.review_decisions import ReviewDecisionStore
from hardwise.workbench.decision_journal import DecisionJournal
from hardwise.workbench.task_projection import build_review_tasks


@pytest.fixture
def managed_review(tmp_path):
    source = tmp_path / "sources"
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
    journal = tmp_path / "original/review.sqlite"
    decisions = ReviewDecisionStore(journal)
    tasks = build_review_tasks(context)
    fps = review_fingerprints(context, tasks)
    key = review_project_key(context)
    decisions.begin_run(key, fps)
    summary = decisions.summary([t.stable_key for t in tasks], project=key)
    task = next(t for t in tasks if t.kind == "pin_check")
    # A pre-upgrade persisted value, not a newly submitted legacy mutation.
    record = dict(
        stable_key=task.stable_key,
        status="waived",
        reason="公开合成理由",
        updated_at="2026-10-24T00:00:00+00:00",
        previous_status=None,
        fingerprint=fps[task.stable_key],
        current_fingerprint=fps[task.stable_key],
    )
    persisted = DecisionJournal(journal)
    _, revision = persisted.load(key)
    persisted.save(
        key,
        summary.run_id,
        {task.stable_key: record},
        [
            dict(
                event="human_decision",
                stable_key=task.stable_key,
                created_at=record["updated_at"],
                decision=record,
            )
        ],
        expected_revision=revision,
    )
    yield source, context, journal, summary.run_id, task.stable_key, fps
    close_workbench_context(context)
