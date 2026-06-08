"""Tests for the append-only external hint appendix renderer."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.types import Component, Design
from hardwise.report.validator_project_risk_hints import render_project_risk_hints
from hardwise.report.validator_project_ui import render_project_workbench
from hardwise.validation.project_index import ProjectValidationIndex
from hardwise.validation.risk_hints import RejectedRiskHint, RiskHint, RiskHintReport


def _design() -> Design:
    return Design(
        components={
            "U8": Component(
                refdes="U8",
                value="STM32G030C8T6",
                part_number="STM32G030C8T6",
                package="LQFP48",
            ),
            "U12": Component(
                refdes="U12",
                value="Gate driver",
                part_number="EG2132",
                package="SOP8",
            ),
        },
        nets={},
        project_path=Path("tests/fixtures/risk-hints"),
        source_eda="allegro_netlist",
    )


def test_render_empty_state_when_report_is_missing() -> None:
    html = render_project_risk_hints(None, _design())

    assert "外部提示附录" in html
    assert "只读" in html
    assert "未提供外部提示报告；本地 PASS/WARN/ERROR 结论不受影响。" in html


def test_render_accepted_hints_with_source_chip_and_html_escape() -> None:
    report = RiskHintReport(
        accepted=[
            RiskHint(
                refdes="U8",
                title="Reset <path>",
                body="Check <script>alert(1)</script> reset network.",
                source="datasheet:stm32g030.pdf#p33",
                input_index=0,
            )
        ]
    )

    html = render_project_risk_hints(report, _design())

    assert "本节仅展示调用方提供并已通过位号锚定的外部提示；不会改变本地 PASS/WARN/ERROR 结论。" in html
    assert "U8 · Reset &lt;path&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "evidence-chip" in html
    assert 'data-evidence-token="datasheet:stm32g030.pdf#p33"' in html


def test_render_rejected_hints_only_shows_count_not_rejected_text() -> None:
    report = RiskHintReport(
        rejected=[
            RejectedRiskHint(
                input_index=0,
                reason="unknown_refdes",
                refdes="U999",
                title="Skipped sensitive text",
            )
        ]
    )

    html = render_project_risk_hints(report, _design())

    assert "已跳过 1 条无法安全锚定的外部提示。" in html
    assert "Skipped sensitive text" not in html
    assert "unknown_refdes" not in html
    assert "U999" not in html


def test_render_wraps_unknown_refdes_but_not_identity_tokens() -> None:
    report = RiskHintReport(
        accepted=[
            RiskHint(
                refdes="U12",
                title="EG2132 SOP8 placement",
                body="Compare EG2132 in SOP8 near U12, not U999.",
                source="external:EG2132#SOP8",
                input_index=0,
            )
        ]
    )

    html = render_project_risk_hints(report, _design())

    assert "EG2132 SOP8 placement" in html
    assert "Compare EG2132 in SOP8 near U12, not ⟨?U999⟩." in html
    assert "⟨?EG2132⟩" not in html
    assert "⟨?SOP8⟩" not in html


def test_project_workbench_appends_external_hint_section() -> None:
    design = _design()
    index = ProjectValidationIndex(
        project_name="risk_hints",
        generated_at="2026-06-08T00:00:00+08:00",
        netlist_source="tests/fixtures/risk-hints/mock.net",
        netlist_type="allegro_netlist",
        bom_source="tests/fixtures/risk-hints/mock.csv",
        profiles_dir="data/datasheet_profiles",
        components_in_design=2,
        bom_matched=0,
        rows=[],
    )
    report = RiskHintReport(
        accepted=[
            RiskHint(
                refdes="U8",
                title="Caller supplied note",
                body="Review reset topology.",
                input_index=0,
            )
        ]
    )

    html = render_project_workbench(
        design,
        index,
        project_name="risk_hints",
        netlist_source=Path("tests/fixtures/risk-hints/mock.net"),
        generated_at="2026-06-08T00:00:00+08:00",
        risk_hints=report,
    )

    assert html.index("范围边界") < html.index("外部提示附录")
    assert "Caller supplied note" in html
