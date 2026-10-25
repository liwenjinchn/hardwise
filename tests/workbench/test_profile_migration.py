"""Real default DRAFT import/export, honest coverage and preserved engineering state."""

from pathlib import Path
import hashlib

from fastapi.testclient import TestClient

from hardwise.workbench.chat import WorkbenchChatService
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path("tests/fixtures/allegro")


def test_default_project_never_turns_legacy_matching_into_approval(tmp_path):
    paths = list(Path("data/datasheet_profiles").glob("*.json"))
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    context = build_workbench_context(
        netlist_path=ROOT / "mixed_controller_power_stage.net",
        bom_path=ROOT / "mixed_controller_power_stage_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    assert all(p.lifecycle == "DRAFT" for p in context.validation_targets.values())
    app = create_workbench_app(
        context, WorkbenchChatService(context, mode="fake"), review_db=tmp_path / "draft.sqlite"
    )
    with TestClient(app) as client:
        state = client.get("/api/workbench/state").json()
        assert state["summary"] == dict(
            components=25,
            bom_matched=25,
            validated=22,
            manual=3,
            pass_count=0,
            warn_count=0,
            error_count=0,
            unknown_count=22,
            not_applicable_count=0,
        )
        lane = next(
            lane for lane in state["evidence_package"]["lanes"] if lane["id"] == "validation"
        )
        counts = {m["key"]: m["value"] for m in lane["metrics"]}
        assert counts == {"ready_profiles": 0, "draft_profiles": 9, "validated_components": 22}
        assert "不表示通过" in lane["summary"]
        for ref in ["U8", "U12", "Q12"]:
            detail = client.get("/api/workbench/components/" + ref).json()
            assert detail["profile"]["lifecycle"] == "DRAFT"
            assert detail["deterministic_status"] == "UNKNOWN"
            assert all(c["assessment"]["result"] == "UNKNOWN" for c in detail["checks"])
            assert all(
                p["assessment"]["result"] == "UNKNOWN" for p in detail["pins"] if p["assessment"]
            )
            assert all(
                e["source_class"] != "reviewed_profile"
                for c in detail["checks"]
                for e in c["evidence"]
            )
        # Independent generic/BOM checks retain their source-based result.
        cap = client.get("/api/workbench/components/C1").json()
        assert any(c["assessment"]["result"] == "PASS" for c in cap["checks"])
        tasks = state["review_tasks"]
        roots = {t["refdes"]: t["id"] for t in tasks if t["check"] == "profile_review_status"}
        dependent = [
            t
            for t in tasks
            if t["refdes"] in roots
            and t["check"] != "profile_review_status"
            and t["assessment"]
            and t["assessment"]["rule_version"].endswith(".profile-review1")
        ]
        assert dependent and all(t["derived_from_task_id"] == roots[t["refdes"]] for t in dependent)
        # Handling an UNKNOWN task cannot create a field approval or overwrite machine results.
        chosen = next(t for t in tasks if t["check"] == "profile_review_status")
        changed = client.put(
            "/api/workbench/review-decisions",
            json={
                "stable_keys": [chosen["stable_key"]],
                "expected_run_id": state["review_decisions"]["run_id"],
                "status": "accepted_risk",
                "reason": "Synthetic decision tests workflow only, not field approval.",
            },
        )
        assert changed.status_code == 200, changed.text
        again = client.get("/api/workbench/state").json()
        assert again["summary"] == state["summary"]
        assert (
            client.get("/api/workbench/components/" + chosen["refdes"]).json()["profile"][
                "lifecycle"
            ]
            == "DRAFT"
        )
        assert client.post("/api/workbench/rerun").status_code == 200
        ids = client.get("/api/workbench/state").json()["review_decisions"]
        exported = client.get(
            "/api/workbench/offline-report",
            params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
        )
        assert (
            exported.status_code == 200
            and "profile_candidate" in exported.text
            and "DRAFT" in exported.text
        )
        assert "Synthetic decision tests workflow only" in exported.text
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
