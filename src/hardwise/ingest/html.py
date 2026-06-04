"""HTML datasheet fulltext extractor.

This is a fallback for public datasheet mirrors that expose useful HTML text
while their direct PDF bytes are image-only or guarded. It produces the same
ChunkRecord shape as the PDF extractor so callers can send raw text chunks to
the vector store without pretending the source was a PDF.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from hardwise.ingest.pdf import ChunkRecord, _split_text

BLOCK_TAGS = {
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "li",
    "p",
    "table",
    "td",
    "th",
    "tr",
}

ALLDATASHEET_END_MARKERS = (
    "similar part no.",
    "similar description",
    "html pages",
    "datasheet download",
    "link url",
)


class HtmlDatasheetExtractError(ValueError):
    """Raised when an HTML datasheet source cannot be read."""


def extract_html_chunks(
    source: str | Path,
    *,
    source_name: str | None = None,
    page: int | None = None,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[ChunkRecord]:
    """Extract text chunks from one local or HTTP(S) HTML datasheet page."""

    html_text, inferred_source_name = _read_html_source(source)
    resolved_source_name = source_name or inferred_source_name
    page_number = page or infer_page_number(source, html_text) or 1
    text = extract_datasheet_text(html_text)
    if not text:
        return []
    return [
        ChunkRecord(
            text=chunk_text,
            source_pdf=resolved_source_name,
            page=page_number,
            chunk_index=idx,
        )
        for idx, chunk_text in enumerate(_split_text(text, chunk_size, overlap))
    ]


def extract_datasheet_text(html_text: str) -> str:
    """Return normalized datasheet text from one HTML page."""

    parser = _TextExtractor()
    parser.feed(html_text)
    lines = _normalize_lines(parser.fragments)
    lines = _trim_known_datasheet_boilerplate(lines)
    return "\n".join(lines).strip()


def infer_page_number(source: str | Path, text: str) -> int | None:
    """Infer a 1-indexed datasheet page number from HTML text or source URL/path."""

    for pattern in (
        r"\b(\d+)\s*/\s*\d+\s*page\b",
        r"datasheet\s*\(\s*html\s*\)\s*(\d+)\s*page",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))

    parsed = urlparse(str(source))
    path = unquote(parsed.path if parsed.scheme else str(source))
    match = re.search(r"/(\d+)/[^/]+\.html?$", path, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _read_html_source(source: str | Path) -> tuple[str, str]:
    value = str(source)
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        request = Request(value, headers={"User-Agent": "hardwise-html-datasheet/0.1"})
        try:
            with urlopen(request, timeout=20) as response:
                content_type = response.headers.get_content_type()
                data = response.read()
        except (OSError, URLError) as e:
            raise HtmlDatasheetExtractError(f"html fetch failed: {value}") from e
        if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
            raise HtmlDatasheetExtractError(f"unsupported html content type: {content_type}")
        return data.decode("utf-8", errors="replace"), _source_name_from_url(value)

    path = Path(value).expanduser()
    try:
        return path.read_text(encoding="utf-8", errors="replace"), path.name
    except OSError as e:
        raise HtmlDatasheetExtractError(f"html file unreadable: {path}") from e


def _source_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    return name or parsed.netloc or "datasheet.html"


def _normalize_lines(fragments: list[str]) -> list[str]:
    lines: list[str] = []
    for fragment in fragments:
        for line in fragment.splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if normalized:
                lines.append(normalized)
    return lines


def _trim_known_datasheet_boilerplate(lines: list[str]) -> list[str]:
    page_marker_idx = next(
        (
            idx
            for idx, line in enumerate(lines)
            if re.search(r"\b\d+\s*/\s*\d+\s*page\b", line, flags=re.IGNORECASE)
        ),
        None,
    )
    if page_marker_idx is not None:
        lines = lines[page_marker_idx + 1 :]

    lines = [
        line
        for line in lines
        if not re.search(r"^(zoom in|zoom out|scroll/zoom)$", line, flags=re.IGNORECASE)
        and not re.search(r"^(background image|image:)", line, flags=re.IGNORECASE)
    ]

    end_idx = next(
        (
            idx
            for idx, line in enumerate(lines)
            if any(marker in line.lower() for marker in ALLDATASHEET_END_MARKERS)
        ),
        None,
    )
    if end_idx is not None:
        lines = lines[:end_idx]
    return lines


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag in BLOCK_TAGS:
            self.fragments.append("\n")
        for name, value in attrs:
            if name.lower() == "alt" and value:
                self.fragments.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in BLOCK_TAGS:
            self.fragments.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self.fragments.append(data)
