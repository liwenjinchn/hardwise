"""End-to-end CLI tests for Allegro BOM intake report generation."""

from __future__ import annotations

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
