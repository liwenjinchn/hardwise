"""Tests for Runner-backed workbench chat."""

from __future__ import annotations

from pathlib import Path

from hardwise.workbench.chat import ChatRequest, WorkbenchChatService
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


def test_chat_layer_sanitizes_fallback_suggestions() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.fallback_response("", "U12")

        assert any("⟨?U999⟩" in item for item in response.suggestions)
    finally:
        context.session.close()
