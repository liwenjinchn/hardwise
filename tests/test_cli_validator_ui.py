"""CLI tests for local validator UI generation."""

from __future__ import annotations

import shutil
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
    assert "Hardwise / 设计验证器" in html
    assert 'data-select-ref="U8"' in html
    assert '<article class="panel active" data-panel="U8">' in html
    assert "外围/拓扑检查" in html
    assert "mcu_swdio" in html
    assert "mcu_swclk" in html
    assert "SWDIO is connected to SWCLK" in html
    assert "SWCLK is connected to SWDIO" in html
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
    assert "SWDIO is connected to SWCLK" in html
    assert "SWCLK is connected to SWDIO" in html
    assert "MBRA210LT3G" in html


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
    assert "validated=3" in result.output
    assert "PASS/WARN/ERROR=1/0/2" in result.output
    assert "manual=15" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Hardwise / 设计验证器" in html
    assert "mixed_power_stage" in html
    assert 'data-select-ref="U1"' in html
    assert 'data-select-ref="U12"' in html
    assert 'data-select-ref="U3"' in html
    assert '<article class="panel active" data-panel="U12">' in html
    assert "1N4007W" in html
    assert "MBRA210LT3G" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "# Hardwise Design Validator - mixed_power_stage" in index_text
    assert "| Validated components | 3 |" in index_text
    assert "| PASS / WARN / ERROR | 1 / 0 / 2 |" in index_text
    assert "Static schematic-side design validator" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"components_in_design": 18' in index_payload
    assert '"refdes": "U12"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/xl1509.json"' in index_payload


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
    assert "validated=4" in result.output
    assert "PASS/WARN/ERROR=1/0/3" in result.output
    assert "manual=21" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Hardwise / 设计验证器" in html
    assert 'data-select-ref="U8"' in html
    assert "SWDIO is connected to SWCLK" in html
    assert "SWCLK is connected to SWDIO" in html
    assert "引脚一致性检查" in html
    assert "证据 / Datasheet 详情" in html
    assert "L1 deterministic" in html
    assert "evidence-chip" in html
    assert "recommended.swd" in html
    assert "datasheet:stm32g030.pdf#p33" in html
    assert "外围/拓扑检查" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "| Validated components | 4 |" in index_text
    assert "| PASS / WARN / ERROR | 1 / 0 / 3 |" in index_text
    assert "STM32G030C8T6" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"components_in_design": 25' in index_payload
    assert '"refdes": "U8"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/stm32g030c8t6.json"' in index_payload


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
    assert "data-ai-root" in html
    assert "hardwise-copilot-config" in html
    assert "Offline audited snapshot" in html
    assert "run_component_validation" in html
    assert "search_datasheet" in html
    assert "Guard wraps" in html
    assert "没有配置向量 datasheet search" in html
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
    assert "validated=4" in result.output


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
    assert "validated=1" in result.output
    assert "PASS/WARN/ERROR=1/0/0" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "MPQ8626 public MPS product page and datasheet" in html
    assert "buck_inductor" in html
    assert "no external freewheel diode is required" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "## Component Group Coverage" in index_text
    assert "MPQ8626 public MPS product page and datasheet" in index_text
    assert "| Validated components | 1 |" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"component_groups"' in index_payload
    assert '"identity": "MPQ8626GD"' in index_payload
    assert '"document_status": "matched"' in index_payload
    assert '"profile_path": "data/datasheet_profiles/mpq8626.json"' in index_payload


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
    assert "validated=28" in result.output
    assert "manual=38" in result.output
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
    assert "families=4" in result.output
    assert "try_existing=1" in result.output
    assert "triage_new=3" in result.output
    text = output.read_text(encoding="utf-8")
    assert "| inductor | 5 | 2 | 2.5 | - | 6.8uH, 10uH" in text
    assert "| diode | 1 | 1 | 0.8 | diode | BAV99" in text
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
    assert "validated=0" in result.output
    assert "PASS/WARN/ERROR=0/0/0" in result.output
    assert "manual=7" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Profile coverage gap" in html
    assert "validated 0" in html
    assert "no_result" in html
    assert "待 profile" in html
    assert '<td class="ref">U8<span class="sub">1 refs</span></td>' in html
    assert "does not convert no-profile rows into electrical judgements" in html

    index_text = index_output.read_text(encoding="utf-8")
    assert "| Validated components | 0 |" in index_text
    assert "| PASS / WARN / ERROR | 0 / 0 / 0 |" in index_text
    assert "## Profile Gap Summary" in index_text
    assert "| U8 | no_result |" in index_text

    index_payload = index_json.read_text(encoding="utf-8")
    assert '"components_in_design": 7' in index_payload
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
    assert "BOM matched=3" in result.output
    assert "validated=0" in result.output

    html = html_output.read_text(encoding="utf-8")
    assert "Hardwise Validator UI - switch_clean" in html
    assert "FOO-IC datasheet" in html
    assert "Profile Gap Groups" in html
    assert "Component Group Coverage" in html
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
    assert "matched=1" in result.output

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
