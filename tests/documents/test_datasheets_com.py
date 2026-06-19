"""Tests for Datasheets.com document source adapter."""

from __future__ import annotations

import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.documents import fetch_approved_documents, parse_document_index
from hardwise.documents.datasheets_com import (
    DatasheetsComLookupReport,
    DatasheetsComPart,
    lookup_datasheets_com,
    render_datasheets_com_document_index_csv,
    search_datasheets_com,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object], headers: dict[str, str] | None = None) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_search_datasheets_com_sends_bearer_auth_and_maps_results() -> None:
    seen: dict[str, object] = {}

    def opener(request, *, timeout: int):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse(
            {
                "query": "MPQ8626",
                "page": 1,
                "limit": 10,
                "count": 1,
                "results": [
                    {
                        "mpn": "MPQ8626GD-Z",
                        "manufacturer": "MPS",
                        "title": "High efficiency synchronous buck converter",
                        "description": "Buck regulator.",
                        "url": "https://www.datasheets.com/mps/mpq8626gd-z",
                        "packageType": "QFN",
                        "lifecycleStatus": "Active",
                        "datasheetUrl": "https://static.datasheets.com/doc/mpq8626.pdf",
                        "specs": [{"name": "Output Current", "value": "12A"}],
                    }
                ],
            },
            headers={
                "X-RateLimit-Remaining-Month": "4999",
                "X-RateLimit-Limit-Month": "5000",
            },
        )

    report = search_datasheets_com(
        "MPQ8626",
        api_key="test-key",
        limit=10,
        timeout_seconds=7,
        opener=opener,
    )

    assert seen["auth"] == "Bearer test-key"
    assert "q=MPQ8626" in str(seen["url"])
    assert "limit=10" in str(seen["url"])
    assert seen["timeout"] == 7
    assert report.results[0].mpn == "MPQ8626GD-Z"
    assert report.results[0].datasheet_url == "https://static.datasheets.com/doc/mpq8626.pdf"
    assert report.results[0].package_type == "QFN"
    assert report.results[0].specs[0].name == "Output Current"
    assert report.rate_limits.remaining_month == 4999
    assert report.direct_datasheet_count == 1


def test_lookup_datasheets_com_reports_not_configured_without_network() -> None:
    def opener(*_args, **_kwargs):
        raise AssertionError("network should not be called")

    report = lookup_datasheets_com("MPQ8626", api_key=None, opener=opener)

    assert report.status == "not_configured"
    assert report.results == []
    assert report.reason == "DATASHEETS_API_KEY is not set"


def test_lookup_datasheets_com_maps_empty_results_to_no_result() -> None:
    def opener(_request, *, timeout: int):
        return FakeResponse({"query": "missing", "page": 1, "limit": 5, "count": 0, "results": []})

    report = lookup_datasheets_com("missing", api_key="test-key", opener=opener)

    assert report.status == "no_result"
    assert report.results == []


def test_lookup_datasheets_com_maps_429_with_retry_after() -> None:
    headers = Message()
    headers["Retry-After"] = "42"
    headers["X-RateLimit-Remaining-Minute"] = "0"

    def opener(_request, *, timeout: int):
        raise HTTPError(
            url="https://www.datasheets.com/api/v1/search",
            code=429,
            msg="rate limited",
            hdrs=headers,
            fp=None,
        )

    report = lookup_datasheets_com("MPQ8626", api_key="test-key", opener=opener)

    assert report.status == "rate_limited"
    assert report.reason == "http_429"
    assert report.rate_limits.retry_after == 42
    assert report.rate_limits.remaining_minute == 0


def test_lookup_datasheets_com_maps_cloudflare_challenge() -> None:
    headers = Message()
    headers["cf-mitigated"] = "challenge"

    def opener(_request, *, timeout: int):
        raise HTTPError(
            url="https://www.datasheets.com/api/v1/search",
            code=403,
            msg="forbidden",
            hdrs=headers,
            fp=None,
        )

    report = lookup_datasheets_com("MPQ8626", api_key="test-key", opener=opener)

    assert report.status == "cloudflare_challenge"
    assert report.reason == "http_403"


def test_render_datasheets_com_csv_is_candidate_and_cache_ineligible(tmp_path: Path) -> None:
    report = DatasheetsComLookupReport(
        status="found",
        query="MPQ8626",
        page=1,
        limit=5,
        count=1,
        results=[
            DatasheetsComPart(
                mpn="MPQ8626GD-Z",
                manufacturer="MPS",
                title="MPQ8626 datasheet",
                datasheetUrl="https://static.datasheets.com/doc/mpq8626.pdf",
            )
        ],
    )
    csv_text = render_datasheets_com_document_index_csv(report)
    docs_path = tmp_path / "candidates.csv"
    docs_path.write_text(csv_text, encoding="utf-8")

    index = parse_document_index(docs_path)
    entry = index.entries[0]
    assert entry.part_number == "MPQ8626GD-Z"
    assert entry.url == "https://static.datasheets.com/doc/mpq8626.pdf"
    assert entry.review_status == "candidate"
    assert entry.source == "datasheets.com_api"

    fetch_report = fetch_approved_documents(index, tmp_path / "cache")
    assert fetch_report.fetched == []
    assert [skipped.reason for skipped in fetch_report.skipped] == [
        "review_status_not_approved"
    ]


def test_render_datasheets_com_csv_neutralizes_formula_injection() -> None:
    # Result fields come straight from an external API and are untrusted; a
    # title/manufacturer beginning with =/@ must be quote-prefixed so it cannot
    # execute as a formula when the candidate CSV is opened in a spreadsheet.
    report = DatasheetsComLookupReport(
        status="found",
        query="EVIL",
        page=1,
        limit=5,
        count=1,
        results=[
            DatasheetsComPart(
                mpn="EVIL1",
                manufacturer="@evilcorp",
                title="=HYPERLINK(\"http://evil\")",
                datasheetUrl="https://static.datasheets.com/doc/evil.pdf",
            )
        ],
    )

    csv_text = render_datasheets_com_document_index_csv(report)

    assert "'=HYPERLINK" in csv_text
    assert "'@evilcorp" in csv_text
    assert ",=HYPERLINK" not in csv_text


def test_search_datasheets_com_cli_writes_candidate_csv(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "mpq8626-candidates.csv"

    def fake_lookup(query: str, **_kwargs) -> DatasheetsComLookupReport:
        return DatasheetsComLookupReport(
            status="found",
            query=query,
            page=1,
            limit=5,
            count=1,
            results=[
                DatasheetsComPart(
                    mpn="MPQ8626GD-Z",
                    manufacturer="MPS",
                    title="MPQ8626 datasheet",
                    datasheetUrl="https://static.datasheets.com/doc/mpq8626.pdf",
                )
            ],
        )

    monkeypatch.setenv("DATASHEETS_API_KEY", "test-key")
    monkeypatch.setattr("hardwise.documents.datasheets_com.lookup_datasheets_com", fake_lookup)

    result = CliRunner().invoke(
        app,
        ["search-datasheets-com", "MPQ8626", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert "datasheets-com-lookup:" in result.output
    assert "direct_pdfs=1" in result.output
    assert output.exists()
    csv_text = output.read_text(encoding="utf-8")
    assert "ReviewStatus" in csv_text
    assert "candidate" in csv_text
    assert "https://static.datasheets.com/doc/mpq8626.pdf" in csv_text
