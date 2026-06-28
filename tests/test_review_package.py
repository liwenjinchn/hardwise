"""Tests for review-package evidence manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.review_package import (
    ReviewPackageParseError,
    load_review_package_manifest,
    render_review_package_markdown,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_load_review_package_yaml_computes_and_validates_sha256(tmp_path: Path) -> None:
    schematic = tmp_path / "schematic.pdf"
    schematic.write_text("public schematic pdf placeholder", encoding="utf-8")
    manifest = tmp_path / "review_package.yaml"
    manifest.write_text(
        "\n".join(
            [
                "artifacts:",
                "  - kind: schematic_pdf",
                "    path: schematic.pdf",
                "    required: true",
                f"    sha256: {_sha256('public schematic pdf placeholder')}",
                "    note: exported from Capture",
                "  - kind: review_notes",
                "    path: notes.md",
                "    required: false",
            ]
        ),
        encoding="utf-8",
    )

    report = load_review_package_manifest(manifest)

    assert report.source_path == str(manifest)
    assert report.counts == {
        "total": 2,
        "present": 1,
        "missing_required": 0,
        "missing_optional": 1,
        "hash_mismatch": 0,
    }
    schematic_row = report.artifacts[0]
    assert schematic_row.status == "present"
    assert schematic_row.sha256 == _sha256("public schematic pdf placeholder")
    assert schematic_row.expected_sha256 == schematic_row.sha256
    assert report.artifacts[1].status == "missing"
    assert report.artifacts[1].required is False


def test_load_review_package_json_reports_required_missing_and_hash_mismatch(
    tmp_path: Path,
) -> None:
    checklist = tmp_path / "checklist.csv"
    checklist.write_text("checked,refdes\ntrue,U1\n", encoding="utf-8")
    manifest = tmp_path / "review_package.json"
    manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "kind": "checklist",
                        "path": "checklist.csv",
                        "sha256": "0" * 64,
                    },
                    {
                        "kind": "erc_drc_report",
                        "path": "missing-erc.txt",
                        "required": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = load_review_package_manifest(manifest)

    assert report.counts == {
        "total": 2,
        "present": 0,
        "missing_required": 1,
        "missing_optional": 0,
        "hash_mismatch": 1,
    }
    assert report.artifacts[0].status == "hash_mismatch"
    assert report.artifacts[0].expected_sha256 == "0" * 64
    assert report.artifacts[1].status == "missing"


def test_load_review_package_rejects_unknown_kind(tmp_path: Path) -> None:
    manifest = tmp_path / "review_package.yaml"
    manifest.write_text(
        "artifacts:\n  - kind: layout_signoff\n    path: signoff.pdf\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewPackageParseError, match="unknown review artifact kind"):
        load_review_package_manifest(manifest)


def test_render_review_package_markdown_states_scope(tmp_path: Path) -> None:
    schematic = tmp_path / "schematic.pdf"
    schematic.write_text("schematic", encoding="utf-8")
    manifest = tmp_path / "review_package.yaml"
    manifest.write_text(
        "artifacts:\n  - kind: schematic_pdf\n    path: schematic.pdf\n",
        encoding="utf-8",
    )

    md = render_review_package_markdown(load_review_package_manifest(manifest))

    assert "# Review Package Evidence Manifest" in md
    assert "| schematic_pdf | present | True |" in md
    assert "does not parse these files into electrical findings" in md
    assert "does not replace formal hardware signoff" in md


def test_report_review_package_cli_writes_markdown(tmp_path: Path) -> None:
    schematic = tmp_path / "schematic.pdf"
    schematic.write_text("schematic", encoding="utf-8")
    manifest = tmp_path / "review_package.yaml"
    manifest.write_text(
        "artifacts:\n  - kind: schematic_pdf\n    path: schematic.pdf\n",
        encoding="utf-8",
    )
    output = tmp_path / "package.md"

    result = CliRunner().invoke(
        app,
        [
            "report-review-package",
            str(manifest),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "present=1" in result.output
    assert "missing_required=0" in result.output
    assert output.read_text(encoding="utf-8").startswith(
        "# Review Package Evidence Manifest"
    )


def test_report_review_package_cli_rejects_bad_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "bad.yaml"
    manifest.write_text("artifacts:\n  - kind: layout\n    path: x\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["report-review-package", str(manifest)])

    assert result.exit_code == 1
    assert "unknown review artifact kind" in result.output
