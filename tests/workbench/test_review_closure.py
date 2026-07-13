from pathlib import Path

from fastapi.testclient import TestClient

from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app


class DummyChatService:
    datasheet_search_enabled = False


def _context():
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=Path("data/document_indexes/mixed_controller_power_stage_docs.csv"),
        generated_at="2026-07-12T00:00:00+00:00",
    )


def test_state_exposes_signoff_gate_dual_axis_and_grouped_noise() -> None:
    with TestClient(create_workbench_app(_context(), DummyChatService())) as client:  # type: ignore[arg-type]
        state = client.get("/api/workbench/state").json()

    assert state["summary"]["error_count"] == 4
    readiness = state["evidence_package"]["signoff_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["signoff_ready"] is False
    assert readiness["affected_tasks"] > 0
    assert "datasheet:xl1509.pdf#p8" in readiness["missing_tokens"]

    u1 = next(item for item in state["queue"] if item["refdes"] == "U1")
    assert u1["deterministic_status_group"] == "pass"
    assert u1["status_group"] == "manual"

    assert len(state["review_groups"]) < len(state["review_tasks"])
    capacitor = next(
        group
        for group in state["review_groups"]
        if group["check"] == "capacitor_rated_voltage_parse"
    )
    assert capacitor["raw_task_count"] == 18
    assert capacitor["derived_task_count"] == 9
    assert len(capacitor["affected_refdes"]) == 9

    diode_group = next(
        group for group in state["review_groups"] if group["check"] == "gate_driver_bootstrap"
    )
    assert diode_group["affected_refdes"] == ["D1", "U3"]
    assert diode_group["derived_task_count"] == 1


def test_review_decisions_persist_rerun_export_and_reopen() -> None:
    with TestClient(create_workbench_app(_context(), DummyChatService())) as client:  # type: ignore[arg-type]
        initial = client.get("/api/workbench/state").json()
        task = initial["review_tasks"][0]
        payload = {
            "stable_keys": [task["stable_key"]],
            "status": "waived",
            "reason": "Public fixture intentionally retains this fault for regression.",
        }
        updated = client.put("/api/workbench/review-decisions", json=payload)
        assert updated.status_code == 200
        current = updated.json()
        decided = next(
            item for item in current["review_tasks"] if item["stable_key"] == task["stable_key"]
        )
        assert decided["status"] == task["status"]
        assert decided["review_decision"]["status"] == "waived"
        assert current["review_decisions"]["waived"] == 1

        persisted = client.get("/api/workbench/state").json()
        assert persisted["review_decisions"]["waived"] == 1
        csv_export = client.get("/api/workbench/export?format=csv").text
        annotation_export = client.get("/api/workbench/export?format=annotations").text
        assert "review_status" in csv_export
        assert "waived" in csv_export
        assert "waived" in annotation_export

        rerun = client.post("/api/workbench/rerun")
        assert rerun.status_code == 200
        assert rerun.json()["review_decisions"]["waived"] == 1

        reopened = client.put(
            "/api/workbench/review-decisions",
            json={"stable_keys": [task["stable_key"]], "status": "open", "reason": ""},
        )
        assert reopened.status_code == 200
        assert reopened.json()["review_decisions"]["open"] == len(initial["review_tasks"])


def test_review_decision_requires_reason_and_known_key() -> None:
    with TestClient(create_workbench_app(_context(), DummyChatService())) as client:  # type: ignore[arg-type]
        state = client.get("/api/workbench/state").json()
        stable_key = state["review_tasks"][0]["stable_key"]
        missing_reason = client.put(
            "/api/workbench/review-decisions",
            json={"stable_keys": [stable_key], "status": "resolved", "reason": ""},
        )
        unknown = client.put(
            "/api/workbench/review-decisions",
            json={"stable_keys": ["missing|key"], "status": "accepted", "reason": "checked"},
        )

    assert missing_reason.status_code == 400
    assert unknown.status_code == 404
