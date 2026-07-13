from pathlib import Path

import pytest

from hardwise.guards.evidence_class import classify_evidence_token
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.workbench.view_model import build_workbench_state


def test_evidence_package_keeps_six_coverage_lanes_separate(tmp_path: Path) -> None:
    manifest = tmp_path / "review_package.yaml"
    manifest.write_text(
        "artifacts:\n  - kind: checklist\n    path: review_package.yaml\n",
        encoding="utf-8",
    )
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=Path("data/document_indexes/mixed_controller_power_stage_docs.csv"),
        pin_table=Path("tests/fixtures/capture/pin_table_demo.csv"),
        review_package_manifest=manifest,
        generated_at="2026-07-11T00:00:00+00:00",
    )
    try:
        state = build_workbench_state(context, datasheet_search_enabled=False)
        summary = state.evidence_package
        lanes = {lane.id: lane for lane in summary.lanes}

        assert summary.electrical_verdict == "not_applicable"
        assert list(lanes) == [
            "netlist",
            "bom",
            "validation",
            "documents",
            "pin_table",
            "review_package",
        ]
        assert _metric(lanes["netlist"], "components") == (25, None, "components")
        assert _metric(lanes["bom"], "matched_refdes") == (25, 25, "refdes")
        assert lanes["bom"].status == "present"
        assert _metric(lanes["validation"], "ready_profiles") == (9, 25, "components")
        assert _metric(lanes["validation"], "validated_components") == (
            22,
            25,
            "components",
        )
        assert _metric(lanes["documents"], "approved_groups") == (4, 15, "BOM groups")
        assert lanes["documents"].trust_boundary.startswith("Index rows stay L3")
        assert lanes["pin_table"].status == "partial"
        assert _metric(lanes["pin_table"], "rejected_rows") == (3, None, "rows")
        assert lanes["review_package"].status == "present"
        assert {
            lane.id: classify_evidence_token(lane.source_token or "").source_class
            for lane in summary.lanes
        } == {
            "netlist": "design_source",
            "bom": "design_source",
            "validation": "reviewed_profile",
            "documents": "document_index",
            "pin_table": "design_source",
            "review_package": "design_source",
        }
        assert state.summary.model_dump() == {
            "components": 25,
            "bom_matched": 25,
            "validated": 22,
            "manual": 3,
            "pass_count": 5,
            "warn_count": 13,
            "error_count": 4,
        }

        packet = build_project_review_prep_packet(context)
        assert packet.evidence_package == summary
        markdown = render_project_review_prep_packet_markdown(packet)
        assert "## Evidence Package Completeness" in markdown
        assert "not an electrical signoff" in markdown
    finally:
        close_workbench_context(context)


@pytest.mark.parametrize(
    ("review_status", "expected_status", "expected_group", "metric_key"),
    [
        ("needs_review", "partial", "manual", "review_pending_groups"),
        ("rejected", "gap", "manual", "rejected_groups"),
    ],
)
def test_document_lane_never_promotes_unapproved_rows(
    tmp_path: Path,
    review_status: str,
    expected_status: str,
    expected_group: str,
    metric_key: str,
) -> None:
    documents = tmp_path / "documents.csv"
    documents.write_text(
        "MPN,Manufacturer,Title,URL,ReviewStatus\n"
        f"L7805,ST,L7805 public datasheet,https://example.test/l7805.pdf,{review_status}\n"
        f"CAP-100N,Fixture,Capacitor profile,https://example.test/cap.pdf,{review_status}\n",
        encoding="utf-8",
    )
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_path=Path("tests/fixtures/allegro/l78_regulator_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=documents,
    )
    try:
        lane = next(
            item
            for item in build_workbench_state(
                context,
                datasheet_search_enabled=False,
            ).evidence_package.lanes
            if item.id == "documents"
        )
        assert lane.status == expected_status
        assert lane.status_group == expected_group
        assert _metric(lane, "approved_groups") == (0, 2, "BOM groups")
        assert _metric(lane, metric_key) == (2, None, "BOM groups")
    finally:
        close_workbench_context(context)


def test_profile_coverage_ignores_bom_only_refdes(tmp_path: Path) -> None:
    bom = tmp_path / "bom.csv"
    bom.write_text(
        Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv").read_text(
            encoding="utf-8"
        )
        + "\nU999,1,L7805,ST,L7805\n",
        encoding="utf-8",
    )
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=bom,
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        lanes = {
            lane.id: lane
            for lane in build_workbench_state(
                context,
                datasheet_search_enabled=False,
            ).evidence_package.lanes
        }
        assert _metric(lanes["validation"], "ready_profiles") == (9, 25, "components")
        assert _metric(lanes["bom"], "bom_only_refdes") == (1, None, "refdes")
        assert _metric(lanes["bom"], "quantity_mismatches") == (
            0,
            None,
            "BOM items",
        )
    finally:
        close_workbench_context(context)


def test_review_package_changes_no_validation_or_task_truth(tmp_path: Path) -> None:
    manifest = tmp_path / "review_package.yaml"
    manifest.write_text(
        "artifacts:\n  - kind: checklist\n    path: missing-checklist.md\n",
        encoding="utf-8",
    )
    kwargs = {
        "netlist_path": Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        "bom_path": Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        "profiles": Path("data/datasheet_profiles"),
        "generated_at": "2026-07-11T00:00:00+00:00",
    }
    baseline = build_workbench_context(**kwargs)
    packaged = build_workbench_context(**kwargs, review_package_manifest=manifest)
    try:
        baseline_state = build_workbench_state(baseline, datasheet_search_enabled=False)
        packaged_state = build_workbench_state(packaged, datasheet_search_enabled=False)

        assert packaged_state.summary == baseline_state.summary
        assert [task.id for task in packaged_state.review_tasks] == [
            task.id for task in baseline_state.review_tasks
        ]
        lane = next(
            item for item in packaged_state.evidence_package.lanes if item.id == "review_package"
        )
        assert lane.status == "gap"
        assert lane.status_group == "manual"
    finally:
        close_workbench_context(baseline)
        close_workbench_context(packaged)


def _metric(lane: object, key: str) -> tuple[int, int | None, str]:
    metric = next(item for item in getattr(lane, "metrics") if item.key == key)
    return metric.value, metric.total, metric.unit
