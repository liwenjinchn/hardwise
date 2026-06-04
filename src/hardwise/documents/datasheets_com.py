"""Datasheets.com source adapter for reviewable document-index candidates."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

DATASHEETS_COM_BASE_URL = "https://www.datasheets.com"
DATASHEETS_COM_API_KEY_ENV = "DATASHEETS_API_KEY"
DATASHEETS_COM_API_KEY_ENV_LEGACY = "DATASHEETS_COM_API_KEY"
DatasheetsComLookupStatus = Literal[
    "found",
    "no_result",
    "not_configured",
    "rate_limited",
    "cloudflare_challenge",
    "provider_error",
]


class DatasheetsComError(ValueError):
    """Raised when Datasheets.com search cannot return structured candidates."""


class DatasheetsComHttpError(DatasheetsComError):
    """Raised for provider HTTP status responses."""

    def __init__(self, status_code: int, headers: Any) -> None:
        super().__init__(f"http_{status_code}")
        self.status_code = status_code
        self.headers = headers


class DatasheetsComSpec(BaseModel):
    """One name/value spec returned by Datasheets.com."""

    name: str
    value: str


class DatasheetsComPart(BaseModel):
    """One product search result returned by Datasheets.com."""

    model_config = ConfigDict(populate_by_name=True)

    mpn: str
    manufacturer: str | None = None
    title: str | None = None
    description: str | None = None
    url: str | None = None
    category1: str | None = None
    category2: str | None = None
    category3: str | None = None
    category4: str | None = None
    package_type: str | None = Field(default=None, alias="packageType")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    datasheet_url: str | None = Field(default=None, alias="datasheetUrl")
    primary_image_url: str | None = Field(default=None, alias="primaryImageUrl")
    specs: list[DatasheetsComSpec] = Field(default_factory=list)


class DatasheetsComRateLimits(BaseModel):
    """Rate-limit headers returned by Datasheets.com."""

    limit_minute: int | None = None
    limit_hour: int | None = None
    limit_month: int | None = None
    remaining_minute: int | None = None
    remaining_hour: int | None = None
    remaining_month: int | None = None
    retry_after: int | None = None


class DatasheetsComSearchReport(BaseModel):
    """Structured result for one Datasheets.com product search."""

    query: str
    page: int
    limit: int
    count: int
    results: list[DatasheetsComPart] = Field(default_factory=list)
    rate_limits: DatasheetsComRateLimits = Field(default_factory=DatasheetsComRateLimits)

    @property
    def direct_datasheet_count(self) -> int:
        """Return number of results with a direct datasheet URL."""

        return sum(1 for result in self.results if result.datasheet_url)


class DatasheetsComLookupReport(BaseModel):
    """Structured lookup result with explicit miss/error states."""

    status: DatasheetsComLookupStatus
    query: str
    page: int = 1
    limit: int = 5
    count: int = 0
    results: list[DatasheetsComPart] = Field(default_factory=list)
    rate_limits: DatasheetsComRateLimits = Field(default_factory=DatasheetsComRateLimits)
    reason: str | None = None

    @property
    def direct_datasheet_count(self) -> int:
        """Return number of results with a direct datasheet URL."""

        return sum(1 for result in self.results if result.datasheet_url)


@dataclass(frozen=True)
class _OpenedResponse:
    body: bytes
    headers: Any


UrlOpen = Callable[..., Any]


def search_datasheets_com(
    query: str,
    *,
    api_key: str,
    limit: int = 5,
    page: int = 1,
    timeout_seconds: int = 20,
    base_url: str = DATASHEETS_COM_BASE_URL,
    opener: UrlOpen = urlopen,
) -> DatasheetsComSearchReport:
    """Search Datasheets.com for public document-index candidates."""

    normalized_query = query.strip()
    if not normalized_query:
        raise DatasheetsComError("query must not be blank")
    if not api_key.strip():
        raise DatasheetsComError("api key must not be blank")
    if limit < 1 or limit > 10:
        raise DatasheetsComError("limit must be between 1 and 10")
    if page < 1:
        raise DatasheetsComError("page must be >= 1")
    if timeout_seconds < 1:
        raise DatasheetsComError("timeout must be >= 1")

    url = _search_url(base_url, normalized_query, limit, page)
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "User-Agent": "hardwise-datasheets-com/0.1",
        },
    )
    opened = _open_json(request, opener=opener, timeout_seconds=timeout_seconds)
    try:
        payload = json.loads(opened.body.decode("utf-8"))
        report = DatasheetsComSearchReport.model_validate(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DatasheetsComError("invalid JSON response") from exc
    report.rate_limits = _parse_rate_limits(opened.headers)
    return report


def lookup_datasheets_com(
    query: str,
    *,
    api_key: str | None,
    limit: int = 5,
    page: int = 1,
    timeout_seconds: int = 20,
    base_url: str = DATASHEETS_COM_BASE_URL,
    opener: UrlOpen = urlopen,
) -> DatasheetsComLookupReport:
    """Search Datasheets.com and return a structured status instead of raising."""

    if api_key is None or not api_key.strip():
        return DatasheetsComLookupReport(
            status="not_configured",
            query=query,
            page=page,
            limit=limit,
            reason=f"{DATASHEETS_COM_API_KEY_ENV} is not set",
        )
    try:
        report = search_datasheets_com(
            query,
            api_key=api_key,
            limit=limit,
            page=page,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
            opener=opener,
        )
    except DatasheetsComHttpError as exc:
        reason = str(exc)
        if exc.status_code == 429:
            status: DatasheetsComLookupStatus = "rate_limited"
        elif _is_cloudflare_challenge(exc.headers):
            status = "cloudflare_challenge"
        else:
            status = "provider_error"
        return DatasheetsComLookupReport(
            status=status,
            query=query,
            page=page,
            limit=limit,
            rate_limits=_parse_rate_limits(exc.headers),
            reason=reason,
        )
    except DatasheetsComError as exc:
        reason = str(exc)
        return DatasheetsComLookupReport(
            status="provider_error",
            query=query,
            page=page,
            limit=limit,
            reason=reason,
        )
    status = "found" if report.results else "no_result"
    return DatasheetsComLookupReport(
        status=status,
        query=report.query,
        page=report.page,
        limit=report.limit,
        count=report.count,
        results=report.results,
        rate_limits=report.rate_limits,
    )


def render_datasheets_com_document_index_csv(
    report: DatasheetsComSearchReport | DatasheetsComLookupReport,
) -> str:
    """Render Datasheets.com search results as reviewable document-index rows."""

    output = io.StringIO()
    columns = [
        "MPN",
        "Manufacturer",
        "Title",
        "URL",
        "Description",
        "Source",
        "ReviewStatus",
        "LicenseNote",
        "ProductURL",
        "LifecycleStatus",
        "PackageType",
        "SearchQuery",
    ]
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for result in report.results:
        writer.writerow(
            {
                "MPN": result.mpn,
                "Manufacturer": result.manufacturer or "",
                "Title": result.title or result.mpn,
                "URL": result.datasheet_url or "",
                "Description": result.description or "",
                "Source": "datasheets.com_api",
                "ReviewStatus": "candidate",
                "LicenseNote": "Candidate from Datasheets.com API; review Terms before caching.",
                "ProductURL": result.url or "",
                "LifecycleStatus": result.lifecycle_status or "",
                "PackageType": result.package_type or "",
                "SearchQuery": report.query,
            }
        )
    return output.getvalue()


def _search_url(base_url: str, query: str, limit: int, page: int) -> str:
    return (
        f"{base_url.rstrip('/')}/api/v1/search?"
        f"{urlencode({'q': query, 'limit': limit, 'page': page})}"
    )


def _open_json(
    request: Request,
    *,
    opener: UrlOpen,
    timeout_seconds: int,
) -> _OpenedResponse:
    try:
        with opener(request, timeout=timeout_seconds) as response:
            return _OpenedResponse(body=response.read(), headers=response.headers)
    except HTTPError as exc:
        raise DatasheetsComHttpError(exc.code, exc.headers) from exc
    except (OSError, URLError) as exc:
        raise DatasheetsComError("request_failed") from exc


def _parse_rate_limits(headers: Any) -> DatasheetsComRateLimits:
    return DatasheetsComRateLimits(
        limit_minute=_header_int(headers, "X-RateLimit-Limit-Minute"),
        limit_hour=_header_int(headers, "X-RateLimit-Limit-Hour"),
        limit_month=_header_int(headers, "X-RateLimit-Limit-Month"),
        remaining_minute=_header_int(headers, "X-RateLimit-Remaining-Minute"),
        remaining_hour=_header_int(headers, "X-RateLimit-Remaining-Hour"),
        remaining_month=_header_int(headers, "X-RateLimit-Remaining-Month"),
        retry_after=_header_int(headers, "Retry-After"),
    )


def _header_int(headers: Any, name: str) -> int | None:
    raw = headers.get(name) if headers is not None else None
    if raw is None:
        return None
    try:
        return int(str(raw))
    except ValueError:
        return None


def _is_cloudflare_challenge(headers: Any) -> bool:
    if headers is None:
        return False
    mitigated = headers.get("cf-mitigated")
    return str(mitigated).strip().lower() == "challenge"
