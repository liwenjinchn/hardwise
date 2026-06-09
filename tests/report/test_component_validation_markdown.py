"""Tests for single-component validation markdown reports."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin
from hardwise.report.component_validation_markdown import render
from hardwise.validation import validate_component_against_profile


def test_render_component_validation_markdown() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    component = Component(
        refdes="U1",
        value="L7805",
        part_number="L7805",
        pins=[
            Pin(number="1", name="VI", electrical_type="", is_nc=False, net="+12V"),
            Pin(number="2", name="GND", electrical_type="", is_nc=False, net="GND"),
            Pin(number="3", name="VO", electrical_type="", is_nc=False, net="+5V"),
        ],
    )
    design = Design(
        components={"U1": component},
        nets={
            "+12V": Net(name="+12V", nodes=[("U1", "1")]),
            "GND": Net(name="GND", nodes=[("U1", "2")]),
            "+5V": Net(name="+5V", nodes=[("U1", "3")]),
        },
        project_path=Path("tests/fixtures/allegro"),
        source_eda="allegro_netlist",
    )
    report = validate_component_against_profile(component, profile, design)
    report.pin_results[0].evidence.append("doc:docs.csv#line2")
    report.pin_results[0].evidence.append("pdf:missing.pdf#p7")

    md = render(
        report,
        profile_path=Path("data/datasheet_profiles/l78.json"),
        profile=profile,
        component=component,
        design=design,
    )

    assert "# Hardwise 器件验证报告 - U1" in md
    assert "| 可信度 | L1 deterministic |" in md
    assert "| 综合判定 | PASS |" in md
    assert "| 引脚 PASS/WARN/ERROR | 3 / 0 / 0 |" in md
    assert "单器件原理图引脚与外围/拓扑验证" in md
    assert "不解析 PCB layout、boardview/板图" in md
    assert "### 引脚一致性" in md
    assert "| 引脚数量 | 3 | 3 | PASS |" in md
    assert "## 5. 证据详情" in md
    assert "| 绝对最大额定 | 结温 | 125 | `datasheet:l78.pdf#p4` (reviewed_profile" in md
    assert "missing_local_source" in md
    assert "`doc:docs.csv#line2` (document_index)" in md
    assert "### 器件档案证据账本" in md
    assert "| 1 | VI | 电源输入 | +12V | PASS |" in md
    assert "| 1 | VI | 电源输入 | +12V | +12V -> U1-1 |" in md
    assert "`datasheet:l78.pdf#p4`" in md
    assert "power_input" not in md
    assert "Input net voltage" not in md
