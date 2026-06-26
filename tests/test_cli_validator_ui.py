"""CLI tests for local validator UI generation."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app
from tests.xlsx_fixture import write_minimal_xlsx


def test_report_validator_ui_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui",
            "tests/fixtures/allegro/l78_regulator.net",
            "tests/fixtures/allegro/l78_regulator_bom.csv",
            "U1",
            "data/datasheet_profiles/l78.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui:" in result.output
    assert "(3 components, selected=U1, PASS, PASS/WARN/ERROR=3/0/0)" in result.output

    html = output.read_text(encoding="utf-8")
    assert "<title>Hardwise 原理图检验工具 - l78_regulator</title>" in html
    assert "器件索引" in html
    assert "U1" in html
    assert "下载报告" in html
    assert "Hardwise / 原理图检验工具" in html
    assert "电源输入" in html
    assert "boardview" in html
    assert "Download report" not in html
    assert "Component index" not in html


def test_report_validator_ui_writes_xl1509_dcdc_checks(tmp_path: Path) -> None:
    output = tmp_path / "xl1509-validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui",
            "tests/fixtures/allegro/xl1509_buck.net",
            "tests/fixtures/allegro/xl1509_buck_bom.csv",
            "U12",
            "data/datasheet_profiles/xl1509.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui:" in result.output
    assert "selected=U12, ERROR" in result.output

    html = output.read_text(encoding="utf-8")
    assert "Hardwise 原理图检验工具 - xl1509_buck" in html
    assert "U12" in html
    assert "ERROR" in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert "Buck 续流二极管" in html
    assert "Buck 电感" in html
    assert ".brd、boardview/板图、布局、走线、PCB 几何" in html
    assert "not a Schottky-style diode family" not in html


def test_report_validator_ui_batch_writes_multiple_validation_details(tmp_path: Path) -> None:
    output = tmp_path / "mixed-validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_regulators.net",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "U1=data/datasheet_profiles/l78.json",
            "U12=data/datasheet_profiles/xl1509.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=U1,U12" in result.output
    assert "PASS/WARN/ERROR=1/0/1" in result.output

    html = output.read_text(encoding="utf-8")
    assert "Hardwise / 原理图检验工具" in html
    assert 'class="left-stack" aria-label="器件与验证摘要"' in html
    assert html.index('aria-label="验证"') < html.index('aria-label="器件"')
    assert "验证完成 · PASS/WARN/ERROR=1/0/1" in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    for section in (
        "model-check",
        "pin-summary",
        "connection-path",
        "compliance-matrix",
        "evidence-details",
        "final-summary",
    ):
        assert f'data-section="{section}"' in html
    assert "data-detail-tab" not in html
    assert 'status pass">PASS' in html
    assert 'status error">ERROR' in html
    assert "下载报告" in html
    assert "外围/拓扑检查" in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert "本地原理图检验工具" in html
    assert ".brd、boardview/板图、布局、走线、PCB 几何" in html


def test_report_validator_ui_batch_accepts_targets_manifest(tmp_path: Path) -> None:
    output = tmp_path / "mixed-validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_regulators.net",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "--targets-manifest",
            "tests/fixtures/allegro/mixed_regulators_targets.yaml",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=U1,U12" in result.output
    assert "PASS/WARN/ERROR=1/0/1" in result.output

    html = output.read_text(encoding="utf-8")
    assert "Hardwise / 原理图检验工具" in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    assert 'status pass">PASS' in html
    assert 'status error">ERROR' in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert ".brd、boardview/板图、布局、走线、PCB 几何" in html


def test_report_validator_ui_batch_writes_eg2132_gate_driver_checks(
    tmp_path: Path,
) -> None:
    output = tmp_path / "eg2132-validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/eg2132_gate_driver.net",
            "tests/fixtures/allegro/eg2132_gate_driver_bom.csv",
            "U3=data/datasheet_profiles/eg2132.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=U3" in result.output
    assert "PASS/WARN/ERROR=0/0/1" in result.output

    html = output.read_text(encoding="utf-8")
    assert "Hardwise / 原理图检验工具" in html
    assert 'data-select-ref="U3"' in html
    assert '<article class="panel active" data-panel="U3">' in html
    assert "外围/拓扑检查" in html
    assert "gate_driver_bootstrap" in html
    assert "MBRA210LT3G" in html
    assert "低于所需 24 V" in html
    assert ".brd、boardview/板图、布局、走线、PCB 几何" in html


def test_report_validator_ui_batch_writes_stm32_mcu_checks(
    tmp_path: Path,
) -> None:
    output = tmp_path / "stm32-validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/stm32g030_mcu.net",
            "tests/fixtures/allegro/stm32g030_mcu_bom.csv",
            "U8=data/datasheet_profiles/stm32g030c8t6.json",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=U8" in result.output
    assert "PASS/WARN/ERROR=0/0/1" in result.output

    html = output.read_text(encoding="utf-8")
    assert "Hardwise / 原理图检验工具" in html
    assert 'data-select-ref="U8"' in html
    assert '<article class="panel active" data-panel="U8">' in html
    assert "外围/拓扑检查" in html
    assert "mcu_swdio" in html
    assert "mcu_swclk" in html
    assert "MCU SWDIO 连接到了 SWCLK，期望连接到 SWDIO" in html
    assert "MCU SWCLK 连接到了 SWDIO，期望连接到 SWCLK" in html
    assert ".brd、boardview/板图、布局、走线、PCB 几何" in html


def test_report_validator_ui_batch_writes_mixed_power_stage_manifest(
    tmp_path: Path,
) -> None:
    output = tmp_path / "mixed-power-stage-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_power_stage.net",
            "tests/fixtures/allegro/mixed_power_stage_bom.csv",
            "--targets-manifest",
            "tests/fixtures/allegro/mixed_power_stage_targets.yaml",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=U1,U12,U3" in result.output
    assert "PASS/WARN/ERROR=1/0/2" in result.output

    html = output.read_text(encoding="utf-8")
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert 'data-select-ref="U3"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    assert '<article class="panel" data-panel="U3">' in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert "MBRA210LT3G" in html
    assert "gate_driver_bootstrap" in html


def test_report_validator_ui_batch_writes_mixed_controller_manifest(
    tmp_path: Path,
) -> None:
    output = tmp_path / "mixed-controller-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--targets-manifest",
            "tests/fixtures/allegro/mixed_controller_power_stage_targets.yaml",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=U1,U12,U3,U8" in result.output
    assert "PASS/WARN/ERROR=1/0/3" in result.output

    html = output.read_text(encoding="utf-8")
    assert 'data-select-ref="U8"' in html
    assert '<article class="panel" data-panel="U8">' in html
    assert "MCU SWDIO 连接到了 SWCLK，期望连接到 SWDIO" in html
    assert "MCU SWCLK 连接到了 SWDIO，期望连接到 SWCLK" in html
    assert "MBRA210LT3G" in html


def test_report_validator_ui_batch_writes_ln2312lt1g_alias_manifest(
    tmp_path: Path,
) -> None:
    output = tmp_path / "ln2312lt1g-validator-ui.html"

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/ln2312lt1g_symbol_alias.net",
            "tests/fixtures/allegro/ln2312lt1g_symbol_alias_bom.csv",
            "--targets-manifest",
            "tests/fixtures/allegro/ln2312lt1g_symbol_alias_targets.yaml",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validator-ui-batch:" in result.output
    assert "validated=Q9" in result.output
    assert "PASS/WARN/ERROR=1/0/0" in result.output

    html = output.read_text(encoding="utf-8")
    assert 'data-select-ref="Q9"' in html
    assert '<article class="panel active" data-panel="Q9">' in html
    assert "LN2312LT1G" in html
    assert "gate 3.3 V - source 0 V" in html
    assert "原理图缺少引脚" not in html


def test_design_validator_ui_auto_matches_profiles_and_writes_index(
    tmp_path: Path,
) -> None:
    html_output = tmp_path / "design-validator.html"
    index_output = tmp_path / "validation-index.md"
    index_json = tmp_path / "validation-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mixed_power_stage.net",
            "tests/fixtures/allegro/mixed_power_stage_bom.csv",
            "--output",
            str(html_output),
            "--index-output",
            str(index_output),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "design-validator-ui:" in result.output
    assert "validated=18" in result.output
    assert "PASS/WARN/ERROR=5/10/3" in result.output
    assert "manual=0" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Hardwise / 原理图检验工具" in html
    assert "mixed_power_stage" in html
    assert 'class="left-stack" aria-label="器件与验证摘要"' in html
    assert 'data-row-ref="U12"' in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert 'data-select-ref="U3"' in html
    assert '<article class="panel active" data-panel="Q12">' in html
    assert "1N4007W" in html
    assert "MBRA210LT3G" in html
    assert "GENERIC_CAPACITOR" in html
    assert "GENERIC_RESISTOR" in html
    assert "GENERIC_INDUCTOR" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "# Hardwise Design Validator - mixed_power_stage" in index_text
    assert "| Validated components | 18 |" in index_text
    assert "| PASS / WARN / ERROR | 5 / 10 / 3 |" in index_text
    assert "Static schematic-side design validator" in index_text
    assert "`GENERIC_CAPACITOR`" in index_text
    assert "`GENERIC_RESISTOR`" in index_text
    assert "`GENERIC_INDUCTOR`" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"components_in_design": 18' in index_payload
    assert '"refdes": "D1"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mbra210lt3g.json"' in index_payload
    assert '"refdes": "D5"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/1n4007w.json"' in index_payload
    assert '"refdes": "Q1"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/jmtk3005a.json"' in index_payload
    assert '"refdes": "Q12"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/ss8050.json"' in index_payload
    assert '"refdes": "U12"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/xl1509.json"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/1n4007w.json"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mbra210lt3g.json"' in index_payload


def test_design_validator_ui_prints_risk_hints_counts(tmp_path: Path) -> None:
    html_output = tmp_path / "design-validator.html"
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        """
        {
          "hints": [
            {"refdes": "U1", "title": "Review input", "body": "Check U1 margin."},
            {"refdes": "U999", "title": "Bad anchor", "body": "Rejected."}
          ]
        }
        """,
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--risk-hints-json",
            str(risk_hints),
            "--output",
            str(html_output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "risk-hints: loaded (accepted=1, rejected=1)" in result.output
    html = html_output.read_text(encoding="utf-8")
    assert "外部提示附录" in html
    assert "Review input" in html
    assert "Check U1 margin." in html
    assert "已跳过 1 条无法安全锚定的外部提示。" in html
    assert "Bad anchor" not in html


def test_design_validator_ui_bad_risk_hints_json_exits_cleanly(tmp_path: Path) -> None:
    html_output = tmp_path / "design-validator.html"
    risk_hints = tmp_path / "bad-risk-hints.json"
    risk_hints.write_text('{"hints": [', encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--risk-hints-json",
            str(risk_hints),
            "--output",
            str(html_output),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "risk-hints JSON failed validation" in result.output
    assert "Traceback" not in result.output


def test_design_validator_ui_auto_matches_controller_power_stage(
    tmp_path: Path,
) -> None:
    html_output = tmp_path / "controller-design-validator.html"
    index_output = tmp_path / "controller-index.md"
    index_json = tmp_path / "controller-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--output",
            str(html_output),
            "--index-output",
            str(index_output),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "design-validator-ui:" in result.output
    assert "validated=22" in result.output
    assert "PASS/WARN/ERROR=5/13/4" in result.output
    assert "manual=3" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Hardwise / 原理图检验工具" in html
    assert html.index('aria-label="验证"') < html.index('aria-label="器件"')
    assert 'data-select-ref="U8"' in html
    assert "MCU SWDIO 连接到了 SWCLK，期望连接到 SWDIO" in html
    assert "MCU SWCLK 连接到了 SWDIO，期望连接到 SWCLK" in html
    for section in (
        "model-check",
        "pin-summary",
        "connection-path",
        "compliance-matrix",
        "evidence-details",
        "final-summary",
    ):
        assert f'data-section="{section}"' in html
    assert "data-detail-tab" not in html
    assert "1. 型号核对" in html
    assert "6. 综合总结" in html
    assert "L1 确定性" in html
    assert "evidence-chip" in html
    assert "data-evidence-token" in html
    assert 'href="#U8-evidence-details"' in html
    assert 'id="U8-evidence-details"' in html
    assert "recommended.swd" in html
    assert "datasheet:stm32g030.pdf#p33" in html
    assert "外围/拓扑检查" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "| Validated components | 22 |" in index_text
    assert "| PASS / WARN / ERROR | 5 / 13 / 4 |" in index_text
    assert "STM32G030C8T6" in index_text
    assert "JMTK3005A" in index_text
    assert "SS8050" in index_text
    assert "`GENERIC_CAPACITOR`" in index_text
    assert "`GENERIC_INDUCTOR`" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"components_in_design": 25' in index_payload
    assert '"refdes": "D1"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mbra210lt3g.json"' in index_payload
    assert '"refdes": "D5"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/1n4007w.json"' in index_payload
    assert '"refdes": "Q1"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/jmtk3005a.json"' in index_payload
    assert '"refdes": "Q12"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/ss8050.json"' in index_payload
    assert '"refdes": "U8"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/stm32g030c8t6.json"' in index_payload
    assert '"refdes": "Q1"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/jmtk3005a.json"' in index_payload
    assert '"refdes": "Q12"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/ss8050.json"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/1n4007w.json"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mbra210lt3g.json"' in index_payload
    assert "BJT emitter pin is not connected" in index_payload


def test_design_validator_ui_ai_snapshot_embeds_copilot_panel(tmp_path: Path) -> None:
    html_output = tmp_path / "controller-design-validator-ai.html"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--ai-snapshot",
            "--output",
            str(html_output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "ai-snapshot: enabled" in result.output
    html = html_output.read_text(encoding="utf-8")
    assert "__HARDWISE_OFFLINE_SNAPSHOT__" in html
    assert "Hardwise 离线工作台" in html
    assert "组件审查队列" in html
    assert "Project Prep Packet" in html
    assert '<div class="ai-msg assistant"><p>可以询问选中器件' not in html
    assert "run_component_validation" in html
    assert "search_datasheet" in html
    assert "wrapped_count" in html
    assert "trust_tier" in html
    assert "evidence_chain" in html
    assert "本轮检索" in html
    assert "已审档案" in html
    assert "L2 grounded" in html
    assert "datasheet:l78.pdf#p4" in html
    assert "查看 L7805 输入耐压的数据手册证据链" in html
    assert "没有配置向量数据手册搜索" in html
    assert "⟨?U999⟩" in html


def test_serve_workbench_fake_ai_dry_run_does_not_require_api_key() -> None:
    result = CliRunner().invoke(
        app,
        [
            "serve-workbench",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--fake-ai",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "serve-workbench:" in result.output
    assert "mode=fake" in result.output
    assert "validated=22" in result.output
    assert "datasheet-candidates=auto" in result.output


def test_serve_workbench_fake_ai_dry_run_accepts_document_index(tmp_path: Path) -> None:
    docs = tmp_path / "docs.csv"
    docs.write_text(
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

    result = CliRunner().invoke(
        app,
        [
            "serve-workbench",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--document-index",
            str(docs),
            "--fake-ai",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "serve-workbench:" in result.output
    assert "document-index=on document_index_matched=1" in result.output
    assert "no_result=14" in result.output

    disabled = CliRunner().invoke(
        app,
        [
            "serve-workbench",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--document-index",
            str(docs),
            "--no-auto-datasheet-candidates",
            "--fake-ai",
            "--dry-run",
        ],
    )

    assert disabled.exit_code == 0, disabled.output
    assert "datasheet-candidates=off" in disabled.output


def test_serve_workbench_dry_run_prints_risk_hints_counts(tmp_path: Path) -> None:
    risk_hints = tmp_path / "risk-hints.json"
    risk_hints.write_text(
        """
        [
          {"refdes": "U1", "title": "Review input", "body": "Check U1 margin."},
          {"refdes": "U999", "title": "Bad anchor", "body": "Rejected."}
        ]
        """,
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "serve-workbench",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--risk-hints-json",
            str(risk_hints),
            "--fake-ai",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "risk-hints=loaded accepted=1, rejected=1" in result.output


def test_design_validator_ui_matches_mpq8626_power_family_with_public_docs(
    tmp_path: Path,
) -> None:
    html_output = tmp_path / "mpq8626-design-validator.html"
    index_output = tmp_path / "mpq8626-index.md"
    index_json = tmp_path / "mpq8626-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mpq8626_sync_buck.net",
            "tests/fixtures/allegro/mpq8626_sync_buck_bom.csv",
            "--document-index",
            "data/document_indexes/power_v1_docs.csv",
            "--output",
            str(html_output),
            "--index-output",
            str(index_output),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "document-index: data/document_indexes/power_v1_docs.csv" in result.output
    assert "validated=2" in result.output
    assert "PASS/WARN/ERROR=2/0/0" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "MPQ8626 public MPS product page and datasheet" in html
    assert "GENERIC_INDUCTOR" in html
    assert 'data-section="model-check"' in html
    assert 'data-section="final-summary"' in html
    assert "doc:power_v1_docs.csv#line" in html
    assert "buck_inductor" in html
    assert "no external freewheel diode is required" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "## Component Group Coverage" in index_text
    assert "MPQ8626 public MPS product page and datasheet" in index_text
    assert "`doc:power_v1_docs.csv#line" in index_text
    assert "| Validated components | 2 |" in index_text
    assert "`GENERIC_INDUCTOR`" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"component_groups"' in index_payload
    assert '"identity": "MPQ8626GD"' in index_payload
    assert '"document_status": "matched"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mpq8626.json"' in index_payload


def test_mpq8626_html_chunks_feed_needs_review_profile_draft(
    tmp_path: Path,
) -> None:
    chunks = tmp_path / "mpq8626-html-chunks.jsonl"
    index_json = tmp_path / "mpq8626-index.json"
    draft = tmp_path / "mpq8626-draft.json"

    result = CliRunner().invoke(
        app,
        [
            "extract-datasheet-html",
            "tests/fixtures/datasheets/mpq8626_fulltext.html",
            "--source-name",
            "mpq8626.html",
            "--output",
            str(chunks),
            "--chunk-size",
            "1000",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "chunks=1" in result.output

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mpq8626_sync_buck.net",
            "tests/fixtures/allegro/mpq8626_sync_buck_bom.csv",
            "--document-index",
            "data/document_indexes/power_v1_docs.csv",
            "--output",
            str(tmp_path / "mpq8626-workbench.html"),
            "--index-json",
            str(index_json),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "validated=2" in result.output

    result = CliRunner().invoke(
        app,
        [
            "draft-datasheet-profile",
            str(index_json),
            "--identity",
            "MPQ8626GD",
            "--document-index",
            "data/document_indexes/power_v1_docs.csv",
            "--evidence-chunks",
            str(chunks),
            "--output",
            str(draft),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "review_status=needs_review" in result.output
    assert "evidence_chunks=on" in result.output

    text = draft.read_text(encoding="utf-8")
    assert '"part_number": "MPQ8626GD"' in text
    assert '"review_status": "needs_review"' in text
    assert '"document.source": "doc:power_v1_docs.csv#line2"' in text
    assert '"evidence.chunks.tokens": "datasheet:mpq8626.html#p1"' in text


def test_design_validator_ui_uses_document_mpn_for_l2n7002klt1g_profile(
    tmp_path: Path,
) -> None:
    l2_value = "N-MOS管 L2N7002KLT1G SOT23 1.5 LRC"
    ln_value = "N-MOS管 LN2312LT1G 5A SOT-23 LRC"
    pe_value = "P-MOS管 PE537BA PDFN -33 NIKO-SEM"
    netlist = tmp_path / "l2.net"
    netlist.write_text(
        """$PACKAGES
  ! 'SOT23' ! LOCAL_VALUE ; PQ10
  ! 'SOT23' ! LOCAL_VALUE ; PQ9
  ! 'PDFN' ! LOCAL_VALUE ; Q13
$NETS
  'P3V3' ; PQ10.1
  'GND' ; PQ10.2
  'P12V' ; PQ10.3
  'P3V3' ; PQ9.G
  'GND' ; PQ9.S
  'P12V' ; PQ9.D
  'P12V' ; Q13.1
  'P12V' ; Q13.2
  'P12V' ; Q13.3
  'P3V3' ; Q13.4
  'LOAD' ; Q13.5
  'LOAD' ; Q13.6
  'LOAD' ; Q13.7
  'LOAD' ; Q13.8
$END
""",
        encoding="utf-8",
    )
    bom = tmp_path / "bom.csv"
    bom.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        f"PQ10,1,{l2_value},LRC,\n"
        f"PQ9,1,{ln_value},LRC,\n"
        f"Q13,1,{pe_value},NIKO-SEM,\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs.csv"
    docs.write_text(
        "MPN,Manufacturer,Title,URL,Value\n"
        f"L2N7002KLT1G,LRC,L2 public datasheet,https://example.test/l2.pdf,{l2_value}\n"
        f"LN2312LT1G,LRC,LN public datasheet,https://example.test/ln.pdf,{ln_value}\n"
        f"PE537BA,NIKO-SEM,PE public datasheet,https://example.test/pe.pdf,{pe_value}\n",
        encoding="utf-8",
    )
    index_json = tmp_path / "index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            str(netlist),
            str(bom),
            "--document-index",
            str(docs),
            "--output",
            str(tmp_path / "workbench.html"),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validated=3" in result.output
    assert "PASS/WARN/ERROR=2/1/0" in result.output

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"refdes": "PQ10"' in index_payload
    assert '"match_status": "matched"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/l2n7002klt1g.json"' in index_payload
    assert '"document_source": "doc:docs.csv#line2"' in index_payload
    assert '"refdes": "PQ9"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/ln2312lt1g.json"' in index_payload
    assert '"refdes": "Q13"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/pe537ba.json"' in index_payload
    assert '"profile_part_number": "PE537BA"' in index_payload
    assert "Vds cannot be statically inferred" in index_payload
    assert '"document_source": "doc:docs.csv#line3"' in index_payload
    assert '"document_source": "doc:docs.csv#line4"' in index_payload


def test_design_validator_ui_matches_pca9548a_i2c_mux_family_with_public_docs(
    tmp_path: Path,
) -> None:
    html_output = tmp_path / "pca9548a-design-validator.html"
    index_json = tmp_path / "pca9548a-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/pca9548a_i2c_mux.net",
            "tests/fixtures/allegro/pca9548a_i2c_mux_bom.csv",
            "--document-index",
            "data/document_indexes/family_v1_3_docs.csv",
            "--output",
            str(html_output),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validated=1" in result.output
    assert "PASS/WARN/ERROR=1/0/0" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "PCA9548A public NXP product page and datasheet" in html
    assert "i2c_mux_channel_pairs" in html
    assert "upstream SCL/SDA are connected" in html

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"identity": "PCA9548APW"' in index_payload
    assert '"document_status": "matched"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/pca9548a.json"' in index_payload


def test_build_document_index_candidates_writes_review_csv(tmp_path: Path) -> None:
    index_json = tmp_path / "project-index.json"
    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--document-index",
            "data/document_indexes/family_v1_3_docs.csv",
            "--output",
            str(tmp_path / "workbench.html"),
            "--index-json",
            str(index_json),
        ],
    )
    assert result.exit_code == 0, result.output
    candidates = tmp_path / "document-candidates.csv"

    result = CliRunner().invoke(
        app,
        ["build-document-index-candidates", str(index_json), "--output", str(candidates)],
    )

    assert result.exit_code == 0, result.output
    assert "document-index-candidates:" in result.output
    text = candidates.read_text(encoding="utf-8")
    assert text.startswith("MPN,Manufacturer,Title,URL,Path,Description")
    assert text.splitlines()[0].endswith(",Notes,Priority")
    assert "STM32G030C8T6" in text
    assert "EG2132" in text
    assert ",high" in text
    assert ",medium" in text
    assert "PCA9548APW" not in text
    assert "MPQ8626GD" not in text
    assert "100R" not in text

    transistor_candidates = tmp_path / "transistor-document-candidates.csv"
    result = CliRunner().invoke(
        app,
        [
            "build-document-index-candidates",
            str(index_json),
            "--family",
            "transistor",
            "--output",
            str(transistor_candidates),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "families=transistor" in result.output
    transistor_text = transistor_candidates.read_text(encoding="utf-8")
    assert transistor_text.startswith("MPN,Manufacturer,Title,URL,Path,Description,")
    assert "ReviewStatus" in transistor_text.splitlines()[0]
    assert ",Value," in transistor_text.splitlines()[0]
    assert "EG2132" not in transistor_text


def test_document_candidate_smoke_cli_writes_summary_and_candidates(tmp_path: Path) -> None:
    candidate_csv = tmp_path / "document-candidate-smoke.csv"
    summary_json = tmp_path / "document-candidate-smoke-summary.json"

    result = CliRunner().invoke(
        app,
        [
            "document-candidate-smoke",
            "tests/fixtures/allegro/mixed_controller_power_stage.net",
            "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
            "--candidate-csv",
            str(candidate_csv),
            "--summary-json",
            str(summary_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "document-candidate-smoke:" in result.output
    assert "unchanged=True" in result.output
    assert candidate_csv.read_text(encoding="utf-8").startswith("MPN,Manufacturer,Title,URL")
    summary_text = summary_json.read_text(encoding="utf-8")
    assert '"candidate_rows":' in summary_text
    assert '"pass_warn_error_unchanged": true' in summary_text


def test_recommend_next_family_writes_markdown(tmp_path: Path) -> None:
    index_json = tmp_path / "motor-index.json"
    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/motor_sensor_controller.net",
            "tests/fixtures/allegro/motor_sensor_controller_bom.csv",
            "--document-index",
            "data/document_indexes/family_v1_3_docs.csv",
            "--output",
            str(tmp_path / "motor-workbench.html"),
            "--index-json",
            str(index_json),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "66 components" in result.output
    assert "validated=55" in result.output
    assert "manual=11" in result.output
    index_payload = index_json.read_text(encoding="utf-8")
    assert '"refdes": "D10"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/ltst-c190kgkt.json"' in index_payload
    assert '"refdes": "Q10"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mmbt3904.json"' in index_payload
    assert '"refdes": "U20"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/lmv358.json"' in index_payload
    assert '"refdes": "D20"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/smbj24ca.json"' in index_payload
    assert '"refdes": "D21"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/bas316.json"' in index_payload

    output = tmp_path / "next-family.md"
    result = CliRunner().invoke(
        app,
        ["recommend-next-family", str(index_json), "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert "next-family:" in result.output
    assert "families=2" in result.output
    assert "try_existing=1" in result.output
    assert "triage_new=1" in result.output
    text = output.read_text(encoding="utf-8")
    assert "| diode | 1 | 1 | 0.8 | diode | BAV99" in text
    # Crystals classified as `unknown` before the 2026-06 family expansion;
    # the two oscillator MPNs now group under `crystal`.
    assert "| crystal | 2 | 2 | 0.6 | - | ABM8-8.000MHZ, ECS-2520MV" in text
    assert "| inductor |" not in text
    assert "| ferrite |" not in text
    assert "LTST-C190KGKT" not in text
    assert "MMBT3904" not in text
    assert "SMBJ24CA" not in text
    assert "BAS316" not in text
    assert "LMV358" not in text
    assert "LM393" not in text
    assert "INA180A1" not in text
    assert "TLV9062" not in text
    assert "triage_for_new_validator" in text
    assert "try_existing_validator_profile" in text
    assert "PASS" not in text
    assert "WARN" not in text
    assert "ERROR" not in text


def test_draft_datasheet_profile_writes_needs_review_json(tmp_path: Path) -> None:
    index_json = tmp_path / "project-index.json"
    docs = tmp_path / "docs.csv"
    docs.write_text(
        "MPN,Manufacturer,Title,URL\n"
        "STM32G030C8T6,ST,STM32G030 public datasheet,https://example.test/stm32.pdf\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/stm32g030_mcu.net",
            "tests/fixtures/allegro/stm32g030_mcu_bom.csv",
            "--document-index",
            str(docs),
            "--output",
            str(tmp_path / "workbench.html"),
            "--index-json",
            str(index_json),
        ],
    )
    assert result.exit_code == 0, result.output
    draft = tmp_path / "stm32-draft.json"

    result = CliRunner().invoke(
        app,
        [
            "draft-datasheet-profile",
            str(index_json),
            "--identity",
            "STM32G030C8T6",
            "--document-index",
            str(docs),
            "--output",
            str(draft),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "review_status=needs_review" in result.output
    text = draft.read_text(encoding="utf-8")
    assert '"part_number": "STM32G030C8T6"' in text
    assert '"review_status": "needs_review"' in text
    assert "STM32G030 public datasheet" in text


def test_design_validator_ui_writes_gap_workbench_when_no_profiles_match(
    tmp_path: Path,
) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78.json")
    html_output = tmp_path / "no-profile-design-validator.html"
    index_output = tmp_path / "no-profile-index.md"
    index_json = tmp_path / "no-profile-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            "tests/fixtures/allegro/stm32g030_mcu.net",
            "tests/fixtures/allegro/stm32g030_mcu_bom.csv",
            "--profiles",
            str(profiles),
            "--output",
            str(html_output),
            "--index-output",
            str(index_output),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "design-validator-ui:" in result.output
    assert "validated=3" in result.output
    assert "PASS/WARN/ERROR=0/3/0" in result.output
    assert "manual=4" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "<span>已验证</span><strong>3</strong>" in html
    assert "通用被动件检查" in html
    assert "GENERIC_CAPACITOR" in html
    assert "无本地档案" in html
    assert "待器件档案" in html
    assert '<td class="ref">U8<span class="sub">1 个位号</span></td>' in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "| Validated components | 3 |" in index_text
    assert "| PASS / WARN / ERROR | 0 / 3 / 0 |" in index_text
    assert "## Profile Gap Summary" in index_text
    assert "| U8 | no_result |" in index_text
    assert "`GENERIC_CAPACITOR`" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"components_in_design": 7' in index_payload
    assert '"profile_part_number": "GENERIC_CAPACITOR"' in index_payload
    assert '"validation": null' in index_payload
    assert '"match_status": "no_result"' in index_payload
    assert '"profile_gap_groups"' in index_payload


def test_design_validator_ui_auto_selects_bom_from_pst_project_dir(
    tmp_path: Path,
) -> None:
    project = tmp_path / "allegro"
    shutil.copytree(Path("tests/fixtures/allegro/pst"), project)
    (project / "bad.BOM").write_text("not\ta\tcadence\tbom\n", encoding="utf-8")
    (project / "mismatch.csv").write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\nU999,1,BOGUS,Fixture,BOGUS\n",
        encoding="utf-8",
    )
    (project / "switch_clean.csv").write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U1,1,FOO-IC,Fixture,FOO-IC\n"
        "C1,1,100nF,Fixture,CAP-100N\n"
        "R1,1,10K,Fixture,RES-10K\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs.csv"
    docs.write_text(
        "MPN,Manufacturer,Title,URL\n"
        "FOO-IC,Fixture,FOO-IC datasheet,https://example.test/foo-ic.pdf\n",
        encoding="utf-8",
    )
    html_output = tmp_path / "project-design-validator.html"
    index_output = tmp_path / "project-index.md"
    index_json = tmp_path / "project-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            str(project),
            "--output",
            str(html_output),
            "--index-output",
            str(index_output),
            "--index-json",
            str(index_json),
            "--document-index",
            str(docs),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "selected-bom:" in result.output
    assert "switch_clean.csv" in result.output
    assert "bom-candidates: 3" in result.output
    assert "design-validator-ui:" in result.output
    assert "bom_rows_matched=3" in result.output
    assert "validated=2" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Hardwise 原理图检验工具 - switch_clean" in html
    assert "FOO-IC datasheet" in html
    assert "通用被动件检查" in html
    assert "GENERIC_CAPACITOR" in html
    assert "GENERIC_RESISTOR" in html
    assert "无本地档案" in html
    assert "FOO-IC" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "| Netlist source |" in index_text
    assert "switch_clean.csv" in index_text
    assert "## Component Group Coverage" in index_text
    assert "FOO-IC datasheet" in index_text
    assert "## Profile Gap Summary" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"component_groups"' in index_payload
    assert '"profile_gap_groups"' in index_payload
    assert '"identity": "FOO-IC"' in index_payload
    assert '"document_status": "matched"' in index_payload


def test_design_validator_ui_auto_selects_chinese_xlsx_bom_from_pst_project_dir(
    tmp_path: Path,
) -> None:
    project = tmp_path / "allegro"
    shutil.copytree(Path("tests/fixtures/allegro/pst"), project)
    write_minimal_xlsx(
        project / "switch_clean.xlsx",
        [
            ["序号", "名称", "编号", "层级", "标识", "数量", "位号", "状态"],
            ["1", "IC FOO-IC Fixture", "123456", "1", "", "1.0", "U1", "发行"],
            ["2", "贴片瓷介 100nF 16V", "CAP100", "1", "", "1.0", "C1", "发行"],
            ["3", "贴片电阻 10K", "RES10K", "1", "", "1.0", "R1", "发行"],
        ],
    )
    html_output = tmp_path / "project-design-validator.html"
    index_json = tmp_path / "project-index.json"

    result = CliRunner().invoke(
        app,
        [
            "design-validator-ui",
            str(project),
            "--output",
            str(html_output),
            "--index-json",
            str(index_json),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "selected-bom:" in result.output
    assert "switch_clean.xlsx" in result.output
    assert "bom_rows_matched=3" in result.output

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"bom_source":' in index_payload
    assert "switch_clean.xlsx" in index_payload
    assert '"components_in_design": 3' in index_payload


def test_suggest_validation_targets_writes_candidate_manifest(tmp_path: Path) -> None:
    output = tmp_path / "target-candidates.yaml"

    result = CliRunner().invoke(
        app,
        [
            "suggest-validation-targets",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "--profiles",
            "data/datasheet_profiles",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "target-candidates:" in result.output
    assert "profile_targets_matched=4" in result.output
    assert "no_result=6" in result.output

    text = output.read_text(encoding="utf-8")
    assert "status: candidate" in text
    assert "refdes: U1" in text
    assert "profile: data/datasheet_profiles/l78.json" in text
    assert "refdes: U12" in text
    assert "profile: data/datasheet_profiles/xl1509.json" in text
    assert "refdes: Q12" in text
    assert "profile: data/datasheet_profiles/ss8050.json" in text
    assert "refdes: D5" in text
    assert "profile: data/datasheet_profiles/1n4007w.json" in text
    assert "match_status: matched" in text


def test_suggest_validation_targets_matches_eg2132_profile(tmp_path: Path) -> None:
    output = tmp_path / "eg2132-targets.yaml"

    result = CliRunner().invoke(
        app,
        [
            "suggest-validation-targets",
            "tests/fixtures/allegro/eg2132_gate_driver_bom.csv",
            "--profiles",
            "data/datasheet_profiles",
            "--matched-only",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "profile_targets_matched=4" in result.output

    text = output.read_text(encoding="utf-8")
    assert "refdes: U3" in text
    assert "profile: data/datasheet_profiles/eg2132.json" in text
    assert "refdes: Q1" in text
    assert "refdes: Q2" in text
    assert "profile: data/datasheet_profiles/jmtk3005a.json" in text
    assert "refdes: D1" in text
    assert "profile: data/datasheet_profiles/mbra210lt3g.json" in text


def test_suggest_validation_targets_matches_stm32_profile(tmp_path: Path) -> None:
    output = tmp_path / "stm32-targets.yaml"

    result = CliRunner().invoke(
        app,
        [
            "suggest-validation-targets",
            "tests/fixtures/allegro/stm32g030_mcu_bom.csv",
            "--profiles",
            "data/datasheet_profiles",
            "--matched-only",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "profile_targets_matched=1" in result.output

    text = output.read_text(encoding="utf-8")
    assert "refdes: U8" in text
    assert "profile: data/datasheet_profiles/stm32g030c8t6.json" in text


def test_suggest_validation_targets_matched_only_writes_v35_manifest(tmp_path: Path) -> None:
    output = tmp_path / "targets.yaml"

    result = CliRunner().invoke(
        app,
        [
            "suggest-validation-targets",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "--profiles",
            "data/datasheet_profiles",
            "--matched-only",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    text = output.read_text(encoding="utf-8")
    assert "project: mixed_regulators_bom" in text
    assert "targets:" in text
    assert "status:" not in text
    assert "unmatched:" not in text
    assert "refdes: U1" in text
    assert "refdes: U12" in text


def test_suggest_validation_targets_rejects_missing_profile_dir(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "suggest-validation-targets",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "--profiles",
            str(tmp_path / "missing"),
            "--output",
            str(tmp_path / "target-candidates.yaml"),
        ],
    )

    assert result.exit_code == 1
    assert "profile candidate generation failed" in result.output
    assert "profile directory not found" in result.output


def test_report_validator_ui_batch_rejects_bad_target(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_regulators.net",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "U1",
            "--output",
            str(tmp_path / "mixed-validator-ui.html"),
        ],
    )

    assert result.exit_code == 1
    assert "expected REFDES=profile.json" in result.output


def test_report_validator_ui_batch_rejects_targets_plus_manifest(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_regulators.net",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "U1=data/datasheet_profiles/l78.json",
            "--targets-manifest",
            "tests/fixtures/allegro/mixed_regulators_targets.yaml",
            "--output",
            str(tmp_path / "mixed-validator-ui.html"),
        ],
    )

    assert result.exit_code == 1
    assert "not both" in result.output


def test_report_validator_ui_batch_rejects_malformed_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "bad-targets.yaml"
    manifest.write_text(
        """
project: bad
targets:
  - refdes: U1
""".strip(),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui-batch",
            "tests/fixtures/allegro/mixed_regulators.net",
            "tests/fixtures/allegro/mixed_regulators_bom.csv",
            "--targets-manifest",
            str(manifest),
            "--output",
            str(tmp_path / "mixed-validator-ui.html"),
        ],
    )

    assert result.exit_code == 1
    assert "invalid validation targets" in result.output
    assert "targets[1].profile" in result.output


def test_report_validator_ui_rejects_unknown_refdes(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-validator-ui",
            "tests/fixtures/allegro/l78_regulator.net",
            "tests/fixtures/allegro/l78_regulator_bom.csv",
            "U9",
            "data/datasheet_profiles/l78.json",
            "--output",
            str(tmp_path / "validator-ui.html"),
        ],
    )

    assert result.exit_code == 1
    assert "error: refdes not found in design: U9" in result.output
