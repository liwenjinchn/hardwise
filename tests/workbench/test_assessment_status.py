"""Cross-surface assessment tests use the real public fixture and projections."""

import json

import pytest
from pathlib import Path

from hardwise.agent.tools import ValidationRan
from hardwise.report.project_validation_markdown import render, write_json
from hardwise.validation.types import ComponentValidation, ValidationReport
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.projection import WorkbenchProjectionIndex
from hardwise.workbench.view_model import build_workbench_state


def _context():
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
    )


def test_unknown_is_manual_attention_and_survives_offline_export(tmp_path):
    context = _context()
    try:
        state = build_workbench_state(context, datasheet_search_enabled=False)
        assert state.summary.unknown_count == 12
        assert sum(context.index.totals.values()) == state.summary.validated
        tasks = [task for task in state.review_tasks if task.refdes == "R1"]
        assert any(task.status == "UNKNOWN" and task.status_group == "manual" for task in tasks)
        assert not any(task.kind == "cleared_summary" for task in tasks)
        unknown = next(task for task in tasks if task.status == "UNKNOWN")
        assert "重新评估" in unknown.recommended_action
        assert "未评估" in unknown.status_label
        output = tmp_path / "index.json"
        write_json(context.index, output)
        payload = json.loads(output.read_text())
        assert payload["schema_version"] == "hardwise.validation_index.v2"
        resistor = next(row for row in payload["rows"] if row["refdes"] == "R1")
        assert resistor["validation"]["status"] == "UNKNOWN"
        assert resistor["validation"]["component_counts_by_status"]["UNKNOWN"] == 1
        assert "| UNKNOWN / NOT_APPLICABLE | 12 / 0 |" in render(context.index)
    finally:
        close_workbench_context(context)


def test_empty_check_set_creates_unassessed_task_instead_of_cleared_summary():
    context = _context()
    try:
        row = next(row for row in context.index.rows if row.refdes == "U1")
        row.validation = ValidationReport(
            refdes="U1",
            component_value="L7805",
            profile_part_number="L7805",
        )
        # Rebuild the context-owned immutable projection, as a real rerun does.
        context.projection = WorkbenchProjectionIndex.from_context(context)
        state = build_workbench_state(context, datasheet_search_enabled=False)
        queue_row = next(item for item in state.queue if item.refdes == "U1")
        assert queue_row.deterministic_status == "UNKNOWN"
        assert queue_row.status_group == "manual"
        tasks = [task for task in state.review_tasks if task.refdes == "U1"]
        assert len(tasks) == 1
        assert tasks[0].kind == "unassessed"
        assert tasks[0].status == "UNKNOWN"
        assert "没有可执行" in tasks[0].title
    finally:
        close_workbench_context(context)


def test_agent_result_contract_accepts_unknown_without_relabeling():
    result = ValidationRan(
        refdes="U1",
        profile_part_number="Fixture",
        overall="UNKNOWN",
        counts={"PASS": 0, "UNKNOWN": 1},
        checks=[{"check": "supply", "status": "UNKNOWN", "summary": "Missing supply range"}],
    )
    assert result.model_dump()["checks"][0]["status"] == "UNKNOWN"


@pytest.mark.parametrize("status", ["UNKNOWN", "NOT_APPLICABLE"])
def test_unassessed_and_inapplicable_rows_never_join_pass_queue(status):
    context = _context()
    try:
        row = next(row for row in context.index.rows if row.refdes == "U1")
        row.validation = ValidationReport(
            refdes="U1",
            component_value="Fixture",
            profile_part_number="Fixture",
            component_checks=[
                ComponentValidation(
                    check="scope", status=status, summary="Public scope restriction"
                )
            ],
        )
        context.projection = WorkbenchProjectionIndex.from_context(context)
        state = build_workbench_state(context, datasheet_search_enabled=False)
        queue_row = next(item for item in state.queue if item.refdes == "U1")
        assert queue_row.deterministic_status == status
        assert queue_row.deterministic_status_group == "manual"
        assert not any(
            task.kind == "cleared_summary" for task in state.review_tasks if task.refdes == "U1"
        )
        if status == "NOT_APPLICABLE":
            assert "不适用" in queue_row.title
    finally:
        close_workbench_context(context)
