"""Public-fixture software workflow probe; never substitutes for human acceptance."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

RESTART = """
import json, shutil, sys
from pathlib import Path
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
from hardwise.workbench.review_decisions import ReviewDecisionStore
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.task_projection import build_review_tasks
c, directory = ManagedProjects(Path(sys.argv[1])).open(sys.argv[2])
try:
    tasks = build_review_tasks(c)
    fps = review_fingerprints(c, tasks)
    store = ReviewDecisionStore(Path(sys.argv[1]))
    store.begin_run(review_project_key(c), fps, provenance=build_run_provenance(c).model_dump(mode='json'))
    print(json.dumps(dict(
        project_id=review_project_key(c),
        decisions={t.stable_key: t.review_decision.model_dump(mode='json')
            for t in store.apply(tasks, fingerprints=fps) if t.review_decision},
        history=store.history(),
    ), ensure_ascii=False))
finally:
    close_workbench_context(c)
    shutil.rmtree(directory)
"""


class NoChat:
    datasheet_search_enabled = False


def require(value, message):
    if not value:
        raise ValueError(message)


def probe(root: Path, prefix: Path) -> dict:
    from fastapi.testclient import TestClient
    from hardwise.workbench.context import build_workbench_context, close_workbench_context
    from hardwise.workbench.project_backup import restore_projects
    from hardwise.workbench.server import create_workbench_app

    work = prefix.with_name(prefix.name + "-review")
    source = work / "source"
    source.mkdir(parents=True, exist_ok=False)
    (source / "profiles").mkdir()
    for name in ["l78_regulator.net", "l78_regulator_bom.csv"]:
        shutil.copy2(root / "tests/fixtures/allegro" / name, source / name)
    shutil.copy2(root / "data/datasheet_profiles/l78.json", source / "profiles/l78.json")
    context = build_workbench_context(
        netlist_path=source / "l78_regulator.net",
        bom_path=source / "l78_regulator_bom.csv",
        profiles=source / "profiles",
    )
    journal = work / "active/review.sqlite"
    reason = "公开合成自动复验：状态流程，不是人工批准"
    try:
        app = create_workbench_app(
            context, NoChat(), review_db=journal, auto_datasheet_candidates=False
        )
        with TestClient(app) as client:
            initial = client.get("/api/workbench/state").json()
            ids = initial["review_decisions"]
            expected = {}
            for refdes, status in [("C1", "accepted_risk"), ("C2", "false_positive")]:
                task = next(t for t in initial["review_tasks"] if t["refdes"] == refdes)
                key = task["stable_key"]
                response = client.put(
                    "/api/workbench/review-decisions",
                    json=dict(
                        stable_keys=[key],
                        status=status,
                        reason=reason,
                        expected_run_id=ids["run_id"],
                    ),
                )
                require(response.status_code == 200, "Canonical review mutation failed")
                expected[key] = status
            state = client.get("/api/workbench/state").json()
            require(state["summary"] == initial["summary"], "Human actions changed machine summary")
            require(
                [(t["stable_key"], t["assessment"]) for t in state["review_tasks"]]
                == [(t["stable_key"], t["assessment"]) for t in initial["review_tasks"]],
                "Human actions changed electrical assessments",
            )
            for legacy in ["accepted", "waived"]:
                response = client.put(
                    "/api/workbench/review-decisions",
                    json=dict(
                        stable_keys=list(expected),
                        status=legacy,
                        reason=reason,
                        expected_run_id=ids["run_id"],
                    ),
                )
                require(response.status_code == 422, "Ambiguous new decision was not rejected")
            require(
                client.get("/api/workbench/state").json() == state,
                "Rejected mutations changed state",
            )
            query = dict(expected_project_id=ids["project_id"], expected_run_id=ids["run_id"])
            response = client.get("/api/workbench/offline-report", params=query)
            require(response.status_code == 200, "Offline capture failed")
            html = response.text
            match = re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", html)
            require(match is not None, "Offline payload is missing")
            snapshot = json.loads(match[1])
            history = snapshot["review_history"]
            require(history["total"] == 2, "Offline history did not preserve both actions")
            require(
                all(e["decision"]["reason"] == reason for e in history["events"]),
                "Offline reasons changed",
            )
            offline = work / "public-offline-review.html"
            offline.write_text(html, encoding="utf-8")
            saved = client.post(
                "/api/workbench/projects/save", params={"expected_run_id": ids["run_id"]}
            )
            require(saved.status_code == 200, "Managed save failed")
            response = client.post(
                "/api/workbench/projects/backup", params={"expected_run_id": ids["run_id"]}
            )
            require(response.status_code == 200, "Saved-project backup failed")
            archive = work / "public-review-backup.zip"
            archive.write_bytes(response.content)
    finally:
        close_workbench_context(context)
    # Preserve original bytes, but make all original logical paths unavailable.
    source.rename(work / "original-source-retained")
    restored = restore_projects(archive, work / "restored")
    env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONUTF8="1")
    process = subprocess.run(
        [sys.executable, "-c", RESTART, restored["journal"], saved.json()["id"]],
        cwd=root,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    require(process.returncode == 0, "Restored-project process failed: " + process.stderr)
    reopened = json.loads(process.stdout)
    require(reopened["project_id"] == ids["project_id"], "Restored project identity changed")
    require(
        {k: v["status"] for k, v in reopened["decisions"].items()} == expected,
        "Decisions did not survive source loss and fresh-process restore",
    )
    require(
        all(v["reason"] == reason for v in reopened["decisions"].values()),
        "Restored reasons changed",
    )
    require(len(reopened["history"]) == 2, "Unchanged restore manufactured review events")
    return dict(
        passed=True,
        fixture="public synthetic L78",
        automated_actions_are_human_approval=False,
        canonical_statuses=list(expected.values()),
        legacy_new_writes_rejected=True,
        machine_assessments_unchanged=True,
        offline_history_count=history["total"],
        fresh_process_restored_history_count=len(reopened["history"]),
        original_source_paths_available=source.exists(),
        offline_report=str(offline),
        backup=str(archive),
        restored_journal=restored["journal"],
    )
