"""Tests for CSV/TSV formula-injection neutralization (`csv_safety`)."""

from __future__ import annotations

from hardwise.csv_safety import csv_safe_cell


def test_neutralizes_formula_leading_characters() -> None:
    assert csv_safe_cell("=cmd()") == "'=cmd()"
    assert csv_safe_cell("+1+1") == "'+1+1"
    assert csv_safe_cell("-2+3") == "'-2+3"
    assert csv_safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert csv_safe_cell("\tTAB") == "'\tTAB"
    assert csv_safe_cell("\rCR") == "'\rCR"


def test_protects_legitimate_rail_labels() -> None:
    # Real hardware values that start with +/- would otherwise become formulas.
    assert csv_safe_cell("+5V") == "'+5V"
    assert csv_safe_cell("-12V") == "'-12V"
    assert csv_safe_cell("-10%") == "'-10%"


def test_passes_through_safe_text_and_numbers() -> None:
    assert csv_safe_cell("EG2132") == "EG2132"
    assert csv_safe_cell("https://example.com/x.pdf") == "https://example.com/x.pdf"
    assert csv_safe_cell("") == ""
    assert csv_safe_cell(7) == "7"
    assert csv_safe_cell(0) == "0"
