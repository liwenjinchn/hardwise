"""Tests for HTML datasheet fulltext extraction."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.ingest.html import (
    extract_datasheet_text,
    extract_html_chunks,
    infer_page_number,
)


HTML_FIXTURE = """
<html>
  <head>
    <title>MPQ8626 Datasheet</title>
    <style>.hidden { display: none; }</style>
    <script>window.noise = true;</script>
  </head>
  <body>
    <div>MPQ8626 Datasheet HTML Preview</div>
    <div>1 / 23 page</div>
    <div>Pin 1 PGND1 Power ground return.</div>
    <div>Pin 2 SW1 Switch node output for the integrated synchronous buck power stage.</div>
    <table>
      <tr><th>Pin</th><th>Name</th><th>Description</th></tr>
      <tr><td>3</td><td>VIN</td><td>Supply input range 2.85 V to 16 V.</td></tr>
    </table>
    <p>Typical application connects SW pins to the output inductor.</p>
    <div>Zoom In</div>
    <div>Similar Part No.</div>
    <div>Distributor and advertising boilerplate should not survive.</div>
  </body>
</html>
"""


def test_extract_datasheet_text_trims_html_boilerplate() -> None:
    text = extract_datasheet_text(HTML_FIXTURE)

    assert "Pin 1 PGND1 Power ground return." in text
    assert "Supply input range 2.85 V to 16 V." in text
    assert "Typical application connects SW pins to the output inductor." in text
    assert "MPQ8626 Datasheet HTML Preview" not in text
    assert "Zoom In" not in text
    assert "Similar Part No." not in text
    assert "Distributor and advertising boilerplate" not in text
    assert "window.noise" not in text


def test_extract_html_chunks_preserves_page_token_and_source_name(tmp_path: Path) -> None:
    html_path = tmp_path / "MPQ8626.html"
    html_path.write_text(HTML_FIXTURE, encoding="utf-8")

    chunks = extract_html_chunks(html_path, source_name="mpq8626.html", chunk_size=180, overlap=20)

    assert len(chunks) >= 2
    assert chunks[0].source_pdf == "mpq8626.html"
    assert chunks[0].page == 1
    assert chunks[0].evidence_token == "datasheet:mpq8626.html#p1"
    assert "Pin 1 PGND1" in chunks[0].text


def test_infer_page_number_from_alldatasheet_style_url() -> None:
    source = "https://www.alldatasheet.com/html-pdf/1697732/MPS/MPQ8626/342/17/MPQ8626.html"

    assert infer_page_number(source, "Application information") == 17


def test_extract_html_chunks_infers_page_before_trimming_header(tmp_path: Path) -> None:
    html_path = tmp_path / "MPQ8626.html"
    html_path.write_text(HTML_FIXTURE.replace("1 / 23 page", "17 / 23 page"), encoding="utf-8")

    chunks = extract_html_chunks(html_path, source_name="mpq8626.html")

    assert chunks[0].page == 17


def test_extract_datasheet_html_cli_writes_chunk_jsonl(tmp_path: Path) -> None:
    html_path = tmp_path / "MPQ8626.html"
    html_path.write_text(HTML_FIXTURE, encoding="utf-8")
    output = tmp_path / "chunks.jsonl"

    result = CliRunner().invoke(
        app,
        [
            "extract-datasheet-html",
            str(html_path),
            "--source-name",
            "mpq8626.html",
            "--output",
            str(output),
            "--chunk-size",
            "1000",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "html-datasheet-extract:" in result.output
    assert "chunks=1" in result.output
    assert "ingested=off" in result.output

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["source_pdf"] == "mpq8626.html"
    assert rows[0]["page"] == 1
    assert rows[0]["evidence_token"] == "datasheet:mpq8626.html#p1"
    assert "Supply input range 2.85 V to 16 V." in rows[0]["text"]
