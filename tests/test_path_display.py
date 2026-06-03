"""Tests for portable path display helpers."""

from pathlib import Path

from hardwise.path_display import display_path


def test_display_path_uses_posix_separators_for_path_values() -> None:
    assert display_path(Path("data") / "datasheet_profiles" / "l78.json") == (
        "data/datasheet_profiles/l78.json"
    )


def test_display_path_normalizes_windows_string_paths() -> None:
    assert display_path(r"data\document_indexes\power_v1_docs.csv") == (
        "data/document_indexes/power_v1_docs.csv"
    )


def test_display_path_preserves_none() -> None:
    assert display_path(None) is None
