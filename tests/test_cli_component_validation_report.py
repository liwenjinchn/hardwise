"""CLI tests for single-component validation reports."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_report_component_validation_writes_report(tmp_path: Path) -> None:
    output = tmp_path / "u1-validation.md"

    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/l78_regulator.net",
            "U1",
            "data/datasheet_profiles/l78.json",
            "--bom",
            "tests/fixtures/allegro/l78_regulator_bom.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-validation:" in result.output
    assert "(PASS, PASS/WARN/ERROR=3/0/0)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise 器件验证报告 - U1" in md
    assert "| 器件 MPN | L7805 |" in md
    assert "引脚一致性" in md
    assert "5. 证据详情" in md
    assert "| 3 | VO | 电源输出 | +5V | PASS |" in md


def test_report_component_validation_writes_xl1509_dcdc_errors(tmp_path: Path) -> None:
    output = tmp_path / "u12-validation.md"

    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/xl1509_buck.net",
            "U12",
            "data/datasheet_profiles/xl1509.json",
            "--bom",
            "tests/fixtures/allegro/xl1509_buck_bom.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-validation:" in result.output
    assert "(ERROR, PASS/WARN/ERROR=8/0/0)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise 器件验证报告 - U12" in md
    assert "| 综合判定 | ERROR |" in md
    assert "| 器件级检查 PASS/WARN/ERROR | 0 / 0 / 2 |" in md
    assert "引脚检查汇总" in md
    assert "器件基本信息" in md
    assert "型号核对" in md
    assert "3. 连接路径" in md
    assert "引脚一致性" in md
    assert "4. 合规矩阵" in md
    assert "5. 证据详情" in md
    assert "电感选型" in md
    assert "datasheet:xl1509.pdf#p9" in md
    assert "6. 综合总结" in md
    assert "D5（1N4007W）" in md
    assert "不是肖特基类型" in md
    assert "电感 L1 为 6.8 uH" in md
    assert "低于器件档案下限 68 uH" in md


def test_report_component_validation_writes_eg2132_gate_driver_errors(
    tmp_path: Path,
) -> None:
    output = tmp_path / "u3-validation.md"

    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/eg2132_gate_driver.net",
            "U3",
            "data/datasheet_profiles/eg2132.json",
            "--bom",
            "tests/fixtures/allegro/eg2132_gate_driver_bom.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-validation:" in result.output
    assert "(ERROR, PASS/WARN/ERROR=8/0/0)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise 器件验证报告 - U3" in md
    assert "| 器件档案 | EG2132 |" in md
    assert "| 综合判定 | ERROR |" in md
    assert "| 器件级检查 PASS/WARN/ERROR | 6 / 0 / 1 |" in md
    assert "栅极驱动自举路径" in md
    assert "MBRA210LT3G" in md
    assert "低于所需 24 V" in md
    assert "自举二极管" in md
    assert "datasheet:eg2132.pdf#p6" in md


def test_report_component_validation_writes_stm32_mcu_errors(
    tmp_path: Path,
) -> None:
    output = tmp_path / "u8-validation.md"

    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/stm32g030_mcu.net",
            "U8",
            "data/datasheet_profiles/stm32g030c8t6.json",
            "--bom",
            "tests/fixtures/allegro/stm32g030_mcu_bom.csv",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-validation:" in result.output
    assert "(ERROR, PASS/WARN/ERROR=9/0/0)" in result.output

    md = output.read_text(encoding="utf-8")
    assert "# Hardwise 器件验证报告 - U8" in md
    assert "| 器件档案 | STM32G030C8T6 |" in md
    assert "| 综合判定 | ERROR |" in md
    assert "MCU SWDIO 调试线" in md
    assert "MCU SWCLK 调试线" in md
    assert "MCU SWDIO 连接到了 SWCLK" in md
    assert "MCU SWCLK 连接到了 SWDIO" in md
    assert "SWD 调试接口" in md
    assert "datasheet:stm32g030.pdf#p33" in md
    assert "SWDIO is connected to SWCLK" not in md


def test_report_component_validation_rejects_unknown_refdes() -> None:
    result = CliRunner().invoke(
        app,
        [
            "report-component-validation",
            "tests/fixtures/allegro/l78_regulator.net",
            "U9",
            "data/datasheet_profiles/l78.json",
        ],
    )

    assert result.exit_code == 1
    assert "error: refdes not found in design: U9" in result.output
