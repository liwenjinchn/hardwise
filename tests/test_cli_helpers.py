"""Tests for small CLI helper functions."""

from __future__ import annotations

from pathlib import Path

from hardwise.cli import _review_db_path


def test_review_db_path_defaults_to_reports_db() -> None:
    assert _review_db_path("pic_programmer", None) == Path("reports/pic_programmer.db")


def test_review_db_path_empty_string_skips_store() -> None:
    assert _review_db_path("pic_programmer", "") is None
    assert _review_db_path("pic_programmer", "   ") is None


def test_review_db_path_uses_explicit_path() -> None:
    assert _review_db_path("pic_programmer", "/tmp/pic.db") == Path("/tmp/pic.db")
