"""Tests for the local static validator UI renderer."""

from __future__ import annotations

import shutil
from pathlib import Path

from hardwise.bom import apply_bom_to_design, match_bom_to_design, parse_bom
from hardwise.ir.profile import DatasheetProfile
from hardwise.report.validator_project_ui import render_project_workbench
from hardwise.report.validator_multi_ui import ValidatorUiResult
from hardwise.report.validator_multi_ui import render as render_multi
from hardwise.report.validator_ui import render
from hardwise.validation import suggest_profile_candidates, validate_component_against_profile
from hardwise.validation.project_index import build_project_validation_index

import re


def _section_order(html: str, refdes: str) -> list[str]:
    """Return the ordered data-section keys within one component panel."""
    start = html.index(f'data-panel="{refdes}"')
    end = html.find('class="panel', start + 1)
    panel = html[start:] if end == -1 else html[start:end]
    return re.findall(r'data-section="([^"]+)"', panel)


def test_render_validator_ui_includes_index_detail_and_scope() -> None:
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.ir.build import build_design_from_netlist

    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/l78_regulator.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/l78_regulator_bom.csv"))
    bom_report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, bom_report)
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    validation = validate_component_against_profile(design.components["U1"], profile, design)

    html = render(
        design,
        validation,
        project_name="l78_regulator",
        netlist_source=Path("tests/fixtures/allegro/l78_regulator.net"),
        profile_path=Path("data/datasheet_profiles/l78.json"),
        profile=profile,
        bom_report=bom_report,
        generated_at="2026-05-27T00:00:00+00:00",
    )

    assert "<!doctype html>" in html
    assert "Hardwise local validator UI" in html
    assert 'id="component-index"' in html
    assert '<td class="ref">U1</td>' in html
    assert "Download report" in html
    assert "PASS/WARN/ERROR" in html
    assert "Pin 1 - -> +12V" in html
    assert "L1 deterministic" in html
    assert "evidence-chip" in html
    assert 'data-source="datasheet">datasheet:l78.pdf#p4' in html
    assert "datasheet:l78.pdf#p4" in html
    assert ".brd, boardview, placement, routing, PCB geometry" in html


def test_render_multi_validator_ui_includes_multiple_details() -> None:
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.ir.build import build_design_from_netlist

    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/mixed_regulators.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))
    bom_report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, bom_report)

    l78_profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    xl1509_profile = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
    u1 = validate_component_against_profile(design.components["U1"], l78_profile, design)
    u12 = validate_component_against_profile(design.components["U12"], xl1509_profile, design)

    html = render_multi(
        design,
        [
            ValidatorUiResult(
                validation=u1,
                profile_path=Path("data/datasheet_profiles/l78.json"),
                profile=l78_profile,
            ),
            ValidatorUiResult(
                validation=u12,
                profile_path=Path("data/datasheet_profiles/xl1509.json"),
                profile=xl1509_profile,
            ),
        ],
        project_name="mixed_regulators",
        netlist_source=Path("tests/fixtures/allegro/mixed_regulators.net"),
        bom_report=bom_report,
        generated_at="2026-05-27T00:00:00+00:00",
    )

    assert "Hardwise / 原理图检验工具" in html
    assert 'class="left-stack" aria-label="器件与验证摘要"' in html
    assert "验证完成 · PASS/WARN/ERROR=1/0/1" in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    # Six numbered top-level sections, fixed order, two validated panels.
    for section in (
        "model-check",
        "pin-summary",
        "connection-path",
        "compliance-matrix",
        "evidence-details",
        "final-summary",
    ):
        assert html.count(f'data-section="{section}"') == 2
    assert _section_order(html, "U12") == [
        "model-check",
        "pin-summary",
        "connection-path",
        "compliance-matrix",
        "evidence-details",
        "final-summary",
    ]
    # Old two-tab DOM must be gone.
    assert "data-detail-tab" not in html
    assert "data-detail-tab-panel" not in html
    assert 'status pass">PASS' in html
    assert 'status error">ERROR' in html
    assert "下载报告" in html
    assert "1. 型号核对" in html
    assert "2. 引脚检查汇总" in html
    assert "3. 连接路径" in html
    assert "4. 合规矩阵" in html
    assert "5. 证据详情" in html
    assert "6. 综合总结" in html
    assert "L1 确定性" in html
    assert "evidence-chip" in html
    assert 'data-source="datasheet">datasheet:xl1509.pdf#p9' in html
    assert "+24V" in html
    assert "U12-1" in html
    assert "recommended.inductor" in html
    assert "datasheet:xl1509.pdf#p9" in html
    assert "没有档案级热/封装来源 token" in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert "本地原理图检验工具" in html
    assert ".brd、boardview/板图、布局、走线、PCB 几何" in html


def test_render_project_workbench_includes_zero_profile_gap(tmp_path: Path) -> None:
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.ir.build import build_design_from_netlist

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78.json")
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/stm32g030_mcu.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/stm32g030_mcu_bom.csv"))
    bom_report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, bom_report)
    candidate_report = suggest_profile_candidates(bom, profiles)
    index = build_project_validation_index(
        design=design,
        bom=bom,
        bom_report=bom_report,
        candidate_report=candidate_report,
        project_name="stm32g030_mcu",
        generated_at="2026-05-28T00:00:00+00:00",
        netlist_source="tests/fixtures/allegro/stm32g030_mcu.net",
        netlist_type="allegro_netlist",
    )

    html = render_project_workbench(
        design,
        index,
        project_name="stm32g030_mcu",
        netlist_source=Path("tests/fixtures/allegro/stm32g030_mcu.net"),
        bom_report=bom_report,
        generated_at="2026-05-28T00:00:00+00:00",
    )

    assert "<span>已验证</span><strong>3</strong>" in html
    assert 'class="left-stack" aria-label="器件与验证摘要"' in html
    assert "L3 manual" in html
    assert "L1 deterministic" in html
    assert "通用被动件检查" in html
    assert "GENERIC_CAPACITOR" in html
    assert "无本地档案" in html
    assert "待器件档案" in html
    assert '<td class="ref">U8<span class="sub">1 个位号</span></td>' in html
    assert "范围边界" in html


def test_render_project_workbench_accepts_optional_copilot_panel(tmp_path: Path) -> None:
    from hardwise.adapters.allegro_netlist import parse_allegro_netlist
    from hardwise.ir.build import build_design_from_netlist

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78.json")
    design = build_design_from_netlist(
        parse_allegro_netlist(Path("tests/fixtures/allegro/l78_regulator.net"))
    )
    bom = parse_bom(Path("tests/fixtures/allegro/l78_regulator_bom.csv"))
    bom_report = match_bom_to_design(bom, design)
    design = apply_bom_to_design(design, bom_report)
    candidate_report = suggest_profile_candidates(bom, profiles)
    index = build_project_validation_index(
        design=design,
        bom=bom,
        bom_report=bom_report,
        candidate_report=candidate_report,
        project_name="l78_regulator",
        generated_at="2026-05-30T00:00:00+00:00",
        netlist_source="tests/fixtures/allegro/l78_regulator.net",
        netlist_type="allegro_netlist",
    )

    plain = render_project_workbench(
        design,
        index,
        project_name="l78_regulator",
        netlist_source=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_report=bom_report,
        generated_at="2026-05-30T00:00:00+00:00",
    )
    with_panel = render_project_workbench(
        design,
        index,
        project_name="l78_regulator",
        netlist_source=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_report=bom_report,
        generated_at="2026-05-30T00:00:00+00:00",
        copilot_html="<div data-ai-root></div>",
    )

    assert "data-ai-root" not in plain
    assert "data-ai-root" in with_panel


def test_copilot_snapshot_fallback_uses_boundary_answer_only() -> None:
    from hardwise.report.copilot_panel_assets import COPILOT_SCRIPT, COPILOT_STYLE

    assert "return snapshots.__fallback__" in COPILOT_SCRIPT
    assert "item !== '__fallback__' && !/U999/i.test(item)" not in COPILOT_SCRIPT
    assert "ai-trace-field" in COPILOT_SCRIPT
    assert "Guard wraps" in COPILOT_SCRIPT
    assert "Trust" in COPILOT_SCRIPT
    assert "root.classList.add('ai-open')" in COPILOT_SCRIPT
    assert "root.classList.remove('ai-open')" in COPILOT_SCRIPT
    assert ".ai-root.ai-open .ai-fab{display:none}" in COPILOT_STYLE
    assert "input=${JSON.stringify" not in COPILOT_SCRIPT
