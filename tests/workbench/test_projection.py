"""Tests for context-owned workbench projection indexes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event
from typing import Iterator

import pytest

from hardwise.workbench import task_projection, view_model
from hardwise.workbench.context import WorkbenchContext, build_workbench_context


@pytest.fixture
def context(tmp_path: Path) -> Iterator[WorkbenchContext]:
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        '[{"refdes":"U1","title":"Review input","body":"Check input margin."}]',
        encoding="utf-8",
    )
    document_index = tmp_path / "documents.csv"
    document_index.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL,ReviewStatus,Source",
                (
                    "SS8050,Fixture,SS8050 public datasheet,"
                    "https://example.test/ss8050.pdf,approved,test"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    value = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=document_index,
        risk_hints_json=risk_hints,
        generated_at="2026-05-30T00:00:00+00:00",
    )
    try:
        yield value
    finally:
        value.session.close()


def test_projection_indexes_stable_context_inputs_and_replace_rebuilds(
    context: WorkbenchContext,
) -> None:
    projection = context.projection
    expected_group = next(
        group for group in context.index.component_groups if "Q12" in group.refdes
    )

    assert projection.rows_by_refdes["U8"] is next(
        row for row in context.index.rows if row.refdes == "U8"
    )
    assert projection.document_group_by_refdes["Q12"] is expected_group
    assert projection.risk_hints_by_refdes["U1"] == (context.risk_hints.accepted[0],)
    assert projection.risk_hint_counts["U1"] == 1
    assert projection.validated_count + projection.manual_count == len(context.index.rows)
    assert dict(projection.validation_totals) == context.index.totals

    replacement = replace(context, project_name="replacement")
    assert replacement.projection is not projection
    assert replacement.projection.rows_by_refdes["U8"].refdes == "U8"


def test_state_detail_and_public_tasks_share_one_equivalent_task_projection(
    context: WorkbenchContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uncached_tasks = task_projection._build_review_tasks_uncached(context)
    expected_tasks = [task.model_dump(mode="json") for task in uncached_tasks]
    original_builder = task_projection._build_review_tasks_uncached
    build_count = 0

    def counted_builder(value: WorkbenchContext) -> list[view_model.ReviewTask]:
        nonlocal build_count
        build_count += 1
        return original_builder(value)

    monkeypatch.setattr(task_projection, "_build_review_tasks_uncached", counted_builder)

    first_state = view_model.build_workbench_state(
        context,
        datasheet_search_enabled=False,
    )
    first_detail = view_model.build_component_detail(context, "U8")
    public_tasks = view_model.build_review_tasks(context)
    second_state = view_model.build_workbench_state(
        context,
        datasheet_search_enabled=False,
    )
    second_detail = view_model.build_component_detail(context, "U8")

    assert build_count == 1
    assert [task.model_dump(mode="json") for task in first_state.review_tasks] == expected_tasks
    assert [task.model_dump(mode="json") for task in public_tasks] == expected_tasks
    assert first_state.model_dump(mode="json") == second_state.model_dump(mode="json")
    assert first_detail.model_dump(mode="json") == second_detail.model_dump(mode="json")
    assert [task.model_dump(mode="json") for task in first_detail.tasks] == [
        task for task in expected_tasks if task["refdes"] == "U8"
    ]


def test_review_task_projection_build_is_thread_safe(context: WorkbenchContext) -> None:
    expected = task_projection._build_review_tasks_uncached(context)
    started = Event()
    release = Event()
    build_count = 0

    def builder() -> list[view_model.ReviewTask]:
        nonlocal build_count
        build_count += 1
        started.set()
        assert release.wait(timeout=2)
        return expected

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(context.projection.review_task_projection, builder)
        assert started.wait(timeout=2)
        second = executor.submit(context.projection.review_task_projection, builder)
        release.set()
        first_tasks, first_by_refdes = first.result(timeout=2)
        second_tasks, second_by_refdes = second.result(timeout=2)

    assert build_count == 1
    assert first_tasks is second_tasks
    assert first_by_refdes is second_by_refdes
    assert list(first_by_refdes["U8"]) == [task for task in expected if task.refdes == "U8"]
