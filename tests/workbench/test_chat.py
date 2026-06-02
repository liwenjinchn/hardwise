"""Tests for Runner-backed workbench chat."""

from __future__ import annotations

from pathlib import Path

from hardwise.workbench.chat import (
    C5_L2_SNAPSHOT_QUESTION,
    ChatRequest,
    WorkbenchChatService,
    build_snapshot_responses,
)
from hardwise.workbench.context import build_workbench_context


def _context():
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )


def test_fake_chat_drives_real_runner_validation_tool() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(ChatRequest(question="这个器件为什么 ERROR?", selected_refdes="U12"))

        assert response.mode == "fake"
        assert "U12" in response.answer
        assert response.trace
        assert response.trace[0].tool == "run_component_validation"
        assert response.trace[0].status == "ERROR"
        assert len(service.client.messages.calls) == 2
    finally:
        context.session.close()


def test_fake_chat_wraps_unknown_refdes_through_runner_guard() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(ChatRequest(question="板上有没有 U999?", selected_refdes="U12"))

        assert "⟨?U999⟩" in response.answer
        assert response.wrapped_count >= 1
        assert response.trace[0].input["refdes"] == "⟨?U999⟩"
    finally:
        context.session.close()


def test_fake_chat_reports_datasheet_search_unavailable_and_uses_validation() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(
            ChatRequest(
                question="datasheet 里 U12 的绝对最大额定值是什么?",
                selected_refdes="U12",
            )
        )

        assert "没有配置向量数据手册搜索" in response.answer
        assert "U12" in response.answer
        assert [trace.tool for trace in response.trace] == [
            "search_datasheet",
            "run_component_validation",
        ]
        assert response.trace[0].summary == "skipped: vector store not configured"
        assert response.trace[0].trust_tier == "l3"
        assert response.trace[0].trust_label == "L3 manual"
        assert response.trace[0].evidence == []
        assert response.trace[1].status == "ERROR"
        assert response.trace[1].trust_tier == "l1"
        assert response.trace[1].trust_label == "L1 deterministic"
    finally:
        context.session.close()


def test_snapshot_responses_include_datasheet_boundary_answer() -> None:
    context = _context()
    try:
        responses = build_snapshot_responses(context)

        datasheet_questions = [key for key in responses if key.startswith("数据手册")]
        assert datasheet_questions
        response = responses[datasheet_questions[0]]
        assert "没有配置向量数据手册搜索" in response.answer
        assert [trace.tool for trace in response.trace] == [
            "search_datasheet",
            "run_component_validation",
        ]
    finally:
        context.session.close()


def test_snapshot_responses_include_l2_grounded_datasheet_smoke() -> None:
    context = _context()
    try:
        responses = build_snapshot_responses(context)

        response = responses[C5_L2_SNAPSHOT_QUESTION]
        assert "l78.pdf" in response.answer
        assert "35 V" in response.answer
        assert [trace.tool for trace in response.trace] == ["search_datasheet"]
        assert response.trace[0].summary == "hits=1"
        assert response.trace[0].evidence == ["datasheet:l78.pdf#p4"]
        assert response.trace[0].trust_tier == "l2"
        assert response.trace[0].trust_label == "L2 grounded"
        assert C5_L2_SNAPSHOT_QUESTION in responses["__fallback__"].suggestions
    finally:
        context.session.close()


def test_chat_layer_sanitizes_fallback_suggestions() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.fallback_response("", "U12")

        assert any("⟨?U999⟩" in item for item in response.suggestions)
    finally:
        context.session.close()
