"""End-to-end CLI tests for schematic BOM matching."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app


def test_inspect_bom_match_pst_fixture_clean_match(tmp_path: Path) -> None:
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
        ["inspect-bom-match", "tests/fixtures/allegro/pst", str(bom_path)],
    )

    assert result.exit_code == 0, result.output
    assert "scope: component identity match only" in result.output
    assert "design refdes: 3" in result.output
    assert "bom refdes rows: 3" in result.output
    assert "matched refdes: 3" in result.output
    assert "status: clean refdes match" in result.output


def test_inspect_bom_match_reports_mismatches(tmp_path: Path) -> None:
    bom_path = tmp_path / "pst-mismatch.csv"
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
        ["inspect-bom-match", "tests/fixtures/allegro/pst", str(bom_path), "--limit", "5"],
    )

    assert result.exit_code == 0, result.output
    assert "bom-only refdes: 1" in result.output
    assert "design-only refdes: 2" in result.output
    assert "status: mismatch found" in result.output
    assert "bom-only sample: R999" in result.output
    assert "design-only sample: R1, U1" in result.output
