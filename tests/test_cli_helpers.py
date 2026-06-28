"""Tests for small CLI helper functions."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import _review_db_path
from hardwise.cli import app


def test_review_db_path_defaults_to_reports_db() -> None:
    assert _review_db_path("pic_programmer", None) == Path("reports/pic_programmer.db")


def test_review_db_path_empty_string_skips_store() -> None:
    assert _review_db_path("pic_programmer", "") is None
    assert _review_db_path("pic_programmer", "   ") is None


def test_review_db_path_uses_explicit_path() -> None:
    assert _review_db_path("pic_programmer", "/tmp/pic.db") == Path("/tmp/pic.db")


def test_legacy_kicad_commands_are_framed_as_appendix_paths() -> None:
    runner = CliRunner()

    root = runner.invoke(app, ["--help"])
    ask = runner.invoke(app, ["ask", "--help"])
    review = runner.invoke(app, ["review", "--help"])

    assert root.exit_code == 0
    assert ask.exit_code == 0
    assert review.exit_code == 0
    assert "Ask about the KiCad appendix path" in root.output
    assert "Run the KiCad appendix schematic-review path" in review.output
    assert "appendix/regression project" in ask.output
    assert "appendix/regression project" in review.output
    assert "exported Allegro/PST + BOM" in ask.output
    assert "exported Allegro/PST + BOM" in review.output
    assert "Ask the agent a question about a KiCad project" not in root.output
    assert "Run a schematic review on a KiCad project" not in root.output
