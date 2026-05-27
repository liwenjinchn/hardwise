"""CLI tests for local validator UI generation."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


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
    assert "<title>Hardwise Validator UI - l78_regulator</title>" in html
    assert "Component index" in html
    assert "U1" in html
    assert "Download report" in html
    assert "boardview" in html


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
    assert "Hardwise Validator UI - xl1509_buck" in html
    assert "U12" in html
    assert "ERROR" in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert "buck_freewheel_diode" in html
    assert "buck_inductor" in html
    assert ".brd, boardview, placement, routing, PCB geometry" in html


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
    assert "Hardwise / 设计验证器" in html
    assert "验证完成 · PASS/WARN/ERROR=1/0/1" in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    assert 'status pass">PASS' in html
    assert 'status error">ERROR' in html
    assert "下载报告" in html
    assert "外围/拓扑检查" in html or "综合合规性检查" in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert "V3.7 is a local static multi-validation UI" in html
    assert ".brd, boardview, placement, routing, PCB geometry" in html


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
    assert "Hardwise / 设计验证器" in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    assert 'status pass">PASS' in html
    assert 'status error">ERROR' in html
    assert "1N4007W" in html
    assert "6.8 uH" in html
    assert ".brd, boardview, placement, routing, PCB geometry" in html


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
    assert "Hardwise / 设计验证器" in html
    assert 'data-select-ref="U3"' in html
    assert '<article class="panel active" data-panel="U3">' in html
    assert "外围/拓扑检查" in html
    assert "gate_driver_bootstrap" in html
    assert "MBRA210LT3G" in html
    assert "below required 24 V" in html
    assert ".brd, boardview, placement, routing, PCB geometry" in html


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
    assert "matched=2" in result.output
    assert "no_result=8" in result.output

    text = output.read_text(encoding="utf-8")
    assert "status: candidate" in text
    assert "refdes: U1" in text
    assert "profile: data/datasheet_profiles/l78.json" in text
    assert "refdes: U12" in text
    assert "profile: data/datasheet_profiles/xl1509.json" in text
    assert "refdes: D5" in text
    assert "match_status: no_result" in text


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
    assert "matched=1" in result.output

    text = output.read_text(encoding="utf-8")
    assert "refdes: U3" in text
    assert "profile: data/datasheet_profiles/eg2132.json" in text


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
