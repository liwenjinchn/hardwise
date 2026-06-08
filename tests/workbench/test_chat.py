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


def _write_docs(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "MPN,Manufacturer,Title,URL,Description",
                (
                    "XL1509-12E1,XLSEMI,XL1509 public datasheet,"
                    "https://example.test/xl1509.pdf,fixture"
                ),
            ]
        ),
        encoding="utf-8",
    )
    return path


def _context(document_index: Path | None = None):
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        document_index=document_index,
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
        assert {item.source_class for item in response.trace[1].evidence_classification} == {
            "reviewed_profile"
        }
    finally:
        context.session.close()


def test_fake_chat_drives_component_topology_tool() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(ChatRequest(question="U8 接了哪些关键网络?", selected_refdes="U8"))

        assert "U8" in response.answer
        assert "+3V3" in response.answer
        assert "NRST" in response.answer
        assert response.trace
        assert response.trace[0].tool == "get_component_context"
        assert response.trace[0].summary == "status=found"
        assert response.trace[0].status == "ERROR"
        assert response.trace[0].trust_tier == "l1"
        assert response.trace[0].trust_label == "L1 deterministic"
        assert "datasheet:stm32g030.pdf#p33" in response.trace[0].evidence
        assert {item.source_class for item in response.trace[0].evidence_classification} == {
            "reviewed_profile"
        }
    finally:
        context.session.close()


def test_fake_chat_searches_reset_related_nets() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(ChatRequest(question="RESET 相关网络有哪些?", selected_refdes="U8"))

        assert "NRST" in response.answer
        assert "U8.10" in response.answer
        assert response.trace
        assert response.trace[0].tool == "search_nets"
        assert response.trace[0].input["query"] == "RESET"
        assert response.trace[0].summary == "hits=1"
        assert response.trace[0].trust_tier == "l1"
    finally:
        context.session.close()


def test_fake_chat_summarizes_project_topology() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(
            ChatRequest(question="这张板大概有哪些已验证风险和待补 profile?", selected_refdes="U8")
        )

        assert "拓扑摘要只基于解析后的原理图/netlist" in response.answer
        assert "25 个器件" in response.answer
        assert "21 条网络" in response.answer
        assert "已验证 20 个" in response.answer
        assert "待人工补档案 5 个" in response.answer
        assert "PASS/WARN/ERROR=5/11/4" in response.answer
        assert "首个器件档案缺口: RES-10K" in response.answer
        assert response.trace
        assert response.trace[0].tool == "summarize_project_topology"
        assert response.trace[0].summary == "components=25, nets=21"
        assert response.trace[0].trust_tier == "l1"
    finally:
        context.session.close()


def test_fake_chat_uses_document_tool_for_component_coverage(tmp_path: Path) -> None:
    context = _context(_write_docs(tmp_path / "docs.csv"))
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(
            ChatRequest(question="这个 U12 有公开资料吗?", selected_refdes="U12")
        )

        assert "XL1509 public datasheet" in response.answer
        assert "不是电气规格结论" in response.answer
        assert [trace.tool for trace in response.trace] == ["get_component_documents"]
        assert response.trace[0].summary == "status=matched"
        assert response.trace[0].evidence == ["doc:docs.csv#line2"]
        assert [item.source_class for item in response.trace[0].evidence_classification] == [
            "document_index"
        ]
        assert response.trace[0].trust_tier == "l1"
        assert response.trace[0].trust_label == "L1 deterministic"
    finally:
        context.session.close()


def test_fake_chat_document_tool_fails_closed_without_index() -> None:
    context = _context()
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(
            ChatRequest(question="这个 U12 有公开资料吗?", selected_refdes="U12")
        )

        assert "没有配置公开资料索引" in response.answer
        assert [trace.tool for trace in response.trace] == ["get_component_documents"]
        assert response.trace[0].summary == "status=not_configured"
        assert response.trace[0].trust_tier == "l3"
    finally:
        context.session.close()


def test_fake_chat_uses_document_summary_for_gap_question(tmp_path: Path) -> None:
    context = _context(_write_docs(tmp_path / "docs.csv"))
    try:
        service = WorkbenchChatService(context, mode="fake")

        response = service.ask(ChatRequest(question="还有哪些 datasheet 缺口?"))

        assert "资料覆盖来自已配置的公开资料索引" in response.answer
        assert "no_result=" in response.answer
        assert [trace.tool for trace in response.trace] == ["summarize_document_coverage"]
        assert response.trace[0].summary.startswith("groups=")
        assert response.trace[0].trust_tier == "l1"
        assert response.trace[0].trust_label == "L1 deterministic"
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
        assert "l78.pdf 第 4 页" in response.answer
        assert "VI 输入耐压为 35 V" in response.answer
        assert "Absolute maximum ratings table" not in response.answer
        assert [trace.tool for trace in response.trace] == ["search_datasheet"]
        assert response.trace[0].summary == "hits=1"
        assert response.trace[0].evidence == ["datasheet:l78.pdf#p4"]
        assert [item.source_class for item in response.trace[0].evidence_classification] == [
            "live_retrieved"
        ]
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
