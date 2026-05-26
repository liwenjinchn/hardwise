"""End-to-end CLI tests for Allegro BOM intake report generation."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_report_allegro_bom_writes_component_intake_report(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    output_path = tmp_path / "pst-intake.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--output",
            str(output_path),
            "--net-limit",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "report:" in result.output
    assert "(3/3 matched, 0 mismatches)" in result.output
    assert output_path.exists()

    md = output_path.read_text(encoding="utf-8")
    assert "# Hardwise Allegro BOM Intake - pst" in md
    assert "| Scope | Component identity and connectivity facts only |" in md
    assert "## Component Prefix Summary" in md
    assert "## BOM Item Groups" in md
    assert "This report does not perform PLM, lifecycle, pricing, supplier-risk" in md
    assert "layout, boardview, or electrical-rule review" in md
    assert "| C1 | matched | fixture identity | PN-123 | Acme | C0402 | 2 | GND, VCC_3V3 |" in md
    assert "| U1 | matched | fixture identity | PN-123 | Acme | TSSOP8 | 3 | CTRL, GND, +1 more |" in md
    assert "`bom:pst.csv#line2`" in md
    assert "`design:pst#U1`" in md


def test_report_allegro_bom_summary_only_omits_component_table(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    output_path = tmp_path / "pst-summary.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--output",
            str(output_path),
            "--summary-only",
        ],
    )

    assert result.exit_code == 0, result.output
    md = output_path.read_text(encoding="utf-8")
    assert "## Component Prefix Summary" in md
    assert "## BOM Item Groups" in md
    assert "## BOM / Design Registry Mismatches" in md
    assert "## Component Summary" not in md


def test_report_allegro_bom_accepts_document_index(tmp_path: Path) -> None:
    output_path = tmp_path / "pst-docs.md"

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            "tests/fixtures/allegro/document_match/bom.csv",
            "--output",
            str(output_path),
            "--summary-only",
            "--document-index",
            "tests/fixtures/allegro/document_match/docs.csv",
        ],
    )

    assert result.exit_code == 0, result.output
    md = output_path.read_text(encoding="utf-8")
    assert "## Datasheet / Document Match Summary" in md
    assert "| 1 | 0 | 0 | 0 |" in md
    assert "[PN-123 datasheet](https://example.test/pn-123.pdf)" in md
    assert "`doc:docs.csv#line2`" in md
    assert "live supplier data" in md


def test_report_allegro_bom_writes_component_index_json(tmp_path: Path) -> None:
    output_path = tmp_path / "pst-docs.md"
    index_path = tmp_path / "component-index.json"

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            "tests/fixtures/allegro/document_match/bom.csv",
            "--output",
            str(output_path),
            "--summary-only",
            "--document-index",
            "tests/fixtures/allegro/document_match/docs.csv",
            "--component-index-json",
            str(index_path),
            "--net-limit",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "component-index:" in result.output
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["scope"] == "component identity and connectivity facts only"
    assert payload["counts"]["components"] == 3
    assert payload["counts"]["matched_refdes"] == 3

    rows = {row["refdes"]: row for row in payload["components"]}
    assert rows["U1"]["match_status"] == "matched"
    assert rows["U1"]["value"] == "fixture identity"
    assert rows["U1"]["part_number"] == "PN-123"
    assert rows["U1"]["pin_count"] == 3
    assert rows["U1"]["nets"] == ["CTRL", "GND"]
    assert rows["U1"]["bom_source"] == "bom:bom.csv#line2"
    assert rows["U1"]["design_source"] == "design:pst#U1"
    assert rows["U1"]["document"]["status"] == "matched"
    assert rows["U1"]["document"]["source_token"] == "doc:docs.csv#line2"


def test_report_allegro_bom_rejects_document_index_in_mismatch_only_mode(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "pst-mismatch.md"

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            "tests/fixtures/allegro/document_match/bom.csv",
            "--output",
            str(output_path),
            "--mismatch-only",
            "--document-index",
            "tests/fixtures/allegro/document_match/docs.csv",
        ],
    )

    assert result.exit_code == 1
    assert "error: --document-index cannot be used with --mismatch-only" in result.output
    assert not output_path.exists()


def test_report_allegro_bom_mismatch_only_omits_indexes_and_component_table(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "pst-mismatch.csv"
    output_path = tmp_path / "pst-mismatch.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R999",2,fixture identity',
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--output",
            str(output_path),
            "--mismatch-only",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "(1/3 matched, 3 mismatches)" in result.output
    md = output_path.read_text(encoding="utf-8")
    assert "## BOM / Design Registry Mismatches" in md
    assert "### BOM-Only Refdes" in md
    assert "R999" in md
    assert "## Component Prefix Summary" not in md
    assert "## BOM Item Groups" not in md
    assert "## Component Summary" not in md


def test_report_allegro_bom_rejects_invalid_net_limit(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R1 U1",3,fixture identity',
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--net-limit",
            "0",
        ],
    )

    assert result.exit_code == 1
    assert "error: --net-limit must be >= 1" in result.output


def test_report_allegro_bom_rejects_conflicting_output_modes(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R1 U1",3,fixture identity',
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-bom",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--summary-only",
            "--mismatch-only",
        ],
    )

    assert result.exit_code == 1
    assert "error: --summary-only and --mismatch-only cannot be used together" in result.output


def test_report_allegro_pin_profile_writes_single_component_report(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    profile_path = tmp_path / "u1_profile.json"
    output_path = tmp_path / "u1-pin-profile.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PN-123",
                "abs_max": {},
                "recommended": {},
                "pin_function": {
                    "1": "CTRL input",
                    "4": "GND ground",
                    "8": "VDD supply",
                },
                "evidence": {
                    "pin_function.1": "datasheet:pn-123.pdf#p1",
                    "pin_function.4": "datasheet:pn-123.pdf#p1",
                    "pin_function.8": "datasheet:pn-123.pdf#p1",
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
                "schema_version": "v1",
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-pin-profile",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--refdes",
            "U1",
            "--profile",
            str(profile_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "report:" in result.output
    assert "(U1, PASS=3, WARN=0, ERROR=0, manual_needed=0)" in result.output
    md = output_path.read_text(encoding="utf-8")
    assert "# Hardwise Pin Profile Report - U1" in md
    assert "| Scope | Pin profile comparison only; no voltage-margin" in md
    assert "| BOM value | fixture identity |" in md
    assert "`bom:pst.csv#line2`" in md
    assert "| 1 | CTRL input | CTRL | CTRL | PASS |" in md
    assert "| 4 | GND ground | GND | GND | PASS |" in md
    assert "| 8 | VDD supply | VDD | VCC_3V3 | PASS |" in md
    assert "`datasheet:pn-123.pdf#p1`" in md
    assert "`design:pst#U1.8`" in md


def test_report_allegro_pin_profile_rejects_unknown_refdes(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    profile_path = tmp_path / "u1_profile.json"
    output_path = tmp_path / "missing.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R1 U1",3,fixture identity',
            ]
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PN-123",
                "pin_function": {"1": "CTRL input"},
                "evidence": {"pin_function.1": "datasheet:pn-123.pdf#p1"},
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "report-allegro-pin-profile",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--refdes",
            "U999",
            "--profile",
            str(profile_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1
    assert "error: unknown refdes 'U999' in design registry" in result.output
    assert not output_path.exists()


def test_validate_allegro_component_writes_validation_report(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    profile_path = tmp_path / "pca9548a_profile.json"
    output_path = tmp_path / "u1-validation.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"C1 R1 U1",3,fixture identity,Acme,PCA9548A',
            ]
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PCA9548A",
                "abs_max": {},
                "recommended": {"vdd_min": 2.3, "vdd_max": 5.5},
                "pin_function": {
                    "1": "SCL (upstream serial clock input)",
                    "4": "VSS (ground)",
                    "8": "VDD (supply voltage)",
                },
                "evidence": {
                    "recommended.vdd_min": "datasheet:pca9548a.pdf#p15",
                    "recommended.vdd_max": "datasheet:pca9548a.pdf#p15",
                    "pin_function.1": "datasheet:pca9548a.pdf#p4",
                    "pin_function.4": "datasheet:pca9548a.pdf#p4",
                    "pin_function.8": "datasheet:pca9548a.pdf#p4",
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
                "schema_version": "v1",
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "validate-allegro-component",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--refdes",
            "U1",
            "--profile",
            str(profile_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "report:" in result.output
    assert "(U1, PASS=2, WARN=2, ERROR=1, manual_needed=0)" in result.output
    md = output_path.read_text(encoding="utf-8")
    assert "# Hardwise Component Validation Report - U1" in md
    assert "| Scope | Deterministic component validation only; no layout" in md
    assert "| VDD_VOLTAGE_RANGE | PASS | VDD pin 8 is on VCC_3V3" in md
    assert "parsed as 3.3 V, within recommended 2.3 V to 5.5 V" in md
    assert "`rule:net_voltage_name#VCC_3V3`" in md
    assert "`bom:pst.csv#line2`" in md
    assert "`datasheet:pca9548a.pdf#p15`" in md
    assert "`design:pst#U1.8`" in md


def test_validate_allegro_component_rejects_unsupported_profile(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "pst.csv"
    profile_path = tmp_path / "unsupported_profile.json"
    output_path = tmp_path / "unsupported.md"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value",
                '"C1 R1 U1",3,fixture identity',
            ]
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PN-123",
                "pin_function": {"8": "VDD supply"},
                "evidence": {"pin_function.8": "datasheet:pn-123.pdf#p1"},
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "validate-allegro-component",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--refdes",
            "U1",
            "--profile",
            str(profile_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1
    assert "error: unsupported profile part 'PN-123'" in result.output
    assert not output_path.exists()


def test_validate_allegro_project_writes_index_json_and_details(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst.csv"
    profile_path = tmp_path / "pca9548a_profile.json"
    catalog_path = tmp_path / "profile_catalog.json"
    output_path = tmp_path / "validation-index.md"
    index_json_path = tmp_path / "validation-index.json"
    detail_dir = tmp_path / "details"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                "U1,1,PCA9548APW,NXP,1318724",
                '"C1 R1",2,fixture identity,Acme,PN-123',
            ]
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PCA9548A",
                "abs_max": {},
                "recommended": {"vdd_min": 2.3, "vdd_max": 5.5},
                "pin_function": {
                    "1": "SCL (upstream serial clock input)",
                    "4": "VSS (ground)",
                    "8": "VDD (supply voltage)",
                },
                "evidence": {
                    "recommended.vdd_min": "datasheet:pca9548a.pdf#p15",
                    "recommended.vdd_max": "datasheet:pca9548a.pdf#p15",
                    "pin_function.1": "datasheet:pca9548a.pdf#p4",
                    "pin_function.4": "datasheet:pca9548a.pdf#p4",
                    "pin_function.8": "datasheet:pca9548a.pdf#p4",
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
                "schema_version": "v1",
            }
        ),
        encoding="utf-8",
    )
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "profile_part_number": "PCA9548A",
                    "accepted_bom_values": ["PCA9548A", "PCA9548APW"],
                    "manufacturer": "NXP",
                    "profile_path": str(profile_path),
                    "validation_template": "pca9548a",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "validate-allegro-project",
            "tests/fixtures/allegro/pst",
            str(bom_path),
            "--profile-catalog",
            str(catalog_path),
            "--output",
            str(output_path),
            "--index-json",
            str(index_json_path),
            "--detail-dir",
            str(detail_dir),
            "--manual-limit",
            "1",
            "--candidate-limit",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "validation-index:" in result.output
    assert "(1 validated, PASS=2, WARN=2, ERROR=1, manual_needed=0)" in result.output
    assert "validation-index-json:" in result.output
    assert "validation-details:" in result.output

    md = output_path.read_text(encoding="utf-8")
    assert "# Hardwise Project Validation Index - pst" in md
    assert "| Components in design | 3 |" in md
    assert "| Validated components | 1 |" in md
    assert "| U1 | PCA9548APW | PCA9548A | pca9548a | 2 | 2 | 1 | 0 |" in md
    assert "## Profile Candidate Summary" in md
    assert "Showing first 1 of 2 manual / unsupported rows" in md
    assert "| C1 | no_profile | No profile catalog entry matched" in md
    assert "| R1 | no_profile |" not in md

    payload = json.loads(index_json_path.read_text(encoding="utf-8"))
    rows = {row["refdes"]: row for row in payload["rows"]}
    assert rows["U1"]["status"] == "validated"
    assert rows["U1"]["profile_part_number"] == "PCA9548A"
    assert rows["U1"]["counts"] == {"PASS": 2, "WARN": 2, "ERROR": 1, "manual_needed": 0}
    assert rows["C1"]["status"] == "no_profile"
    assert rows["R1"]["status"] == "no_profile"
    assert payload["totals"] == {"PASS": 2, "WARN": 2, "ERROR": 1, "manual_needed": 0}
    assert payload["candidate_groups"][0]["count"] == 2

    detail = detail_dir / "U1.md"
    assert detail.exists()
    detail_md = detail.read_text(encoding="utf-8")
    assert "# Hardwise Component Validation Report - U1" in detail_md
    assert "| VDD_VOLTAGE_RANGE | PASS | VDD pin 8 is on VCC_3V3" in detail_md


def test_explain_component_writes_stored_validation_explanation(tmp_path: Path) -> None:
    index_path = tmp_path / "validation-index.json"
    output_path = tmp_path / "u1-explain.md"
    index_path.write_text(
        json.dumps(
            {
                "project_name": "pst",
                "generated_at": "2026-05-26T00:00:00+00:00",
                "netlist_source": "tests/fixtures/allegro/pst",
                "netlist_type": "fixture",
                "profile_catalog": "profile_catalog.json",
                "components_in_design": 1,
                "bom_matched": 1,
                "rows": [
                    {
                        "refdes": "U1",
                        "bom_value": "PCA9548APW",
                        "part_number": "1318724",
                        "manufacturer": "NXP",
                        "bom_source": "bom:pst.csv#line2",
                        "design_source": "design:pst#U1",
                        "profile_part_number": "PCA9548A",
                        "profile_path": "pca9548a.json",
                        "validation_template": "pca9548a",
                        "status": "validated",
                        "reason": "Deterministic validator completed.",
                        "counts": {"PASS": 1, "WARN": 0, "ERROR": 0, "manual_needed": 0},
                        "detail_report": "details/U1.md",
                        "checks": [
                            {
                                "check_id": "VDD_VOLTAGE_RANGE",
                                "status": "PASS",
                                "message": "VDD pin 8 is on VCC_3V3, parsed as 3.3 V.",
                                "evidence_tokens": [
                                    "bom:pst.csv#line2",
                                    "datasheet:pca9548a.pdf#p15",
                                    "design:pst#U1.8",
                                    "rule:net_voltage_name#VCC_3V3",
                                ],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "explain-component",
            str(index_path),
            "U1",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "explanation:" in result.output
    assert "(U1, status=validated)" in result.output
    md = output_path.read_text(encoding="utf-8")
    assert "# Hardwise Component Explanation - U1" in md
    assert "| Scope | Explanation of existing deterministic validation results only" in md
    assert "- Result counts: PASS=1, WARN=0, ERROR=0, manual_needed=0." in md
    assert "not creating new findings or inferring missing design intent" in md
    assert "| VDD_VOLTAGE_RANGE | PASS | VDD pin 8 is on VCC_3V3" in md
    assert "`datasheet:pca9548a.pdf#p15`" in md
    assert "`design:pst#U1.8`" in md
    assert "`rule:net_voltage_name#VCC_3V3`" in md


def test_explain_component_rejects_unknown_refdes(tmp_path: Path) -> None:
    index_path = tmp_path / "validation-index.json"
    index_path.write_text(
        json.dumps(
            {
                "project_name": "pst",
                "generated_at": "2026-05-26T00:00:00+00:00",
                "netlist_source": "tests/fixtures/allegro/pst",
                "netlist_type": "fixture",
                "profile_catalog": "profile_catalog.json",
                "components_in_design": 1,
                "bom_matched": 1,
                "rows": [
                    {
                        "refdes": "U1",
                        "design_source": "design:pst#U1",
                        "status": "validated",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["explain-component", str(index_path), "U999"])

    assert result.exit_code == 1
    assert "error: unknown refdes 'U999' in validation index" in result.output
