"""PDF chunk extractor — pdfplumber → list[ChunkRecord].

Slice 3 minimum: page-level extraction with optional sliding-window splitting.
Each chunk carries enough metadata for the join-key story:
  - source_pdf:  filename only (no path)
  - page:        1-indexed page number
  - chunk_index: 0-indexed within a page
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ChunkRecord(BaseModel):
    """One ingestion chunk — text + provenance metadata."""

    text: str
    source_pdf: str
    page: int
    chunk_index: int

    @property
    def evidence_token(self) -> str:
        """Format: `datasheet:<filename>#p<page>`."""
        return f"datasheet:{self.source_pdf}#p{self.page}"


def extract_chunks(
    pdf_path: Path,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[ChunkRecord]:
    """Extract text from a PDF, page by page, split into overlapping chunks.

    A page becomes one or more chunks: if the page's text fits in `chunk_size`
    characters, it stays a single chunk; otherwise it's sliced with `overlap`
    characters of overlap between adjacent chunks.
    """
    import pdfplumber

    chunks: list[ChunkRecord] = []
    pdf_path = pdf_path.expanduser().resolve()

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            page_chunks = _split_text(text, chunk_size, overlap)
            for idx, chunk_text in enumerate(page_chunks):
                chunks.append(
                    ChunkRecord(
                        text=chunk_text,
                        source_pdf=pdf_path.name,
                        page=page_num,
                        chunk_index=idx,
                    )
                )
    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Sliding-window split of one page's text."""
    if len(text) <= chunk_size:
        return [text]
    step = max(1, chunk_size - overlap)
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        out.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return out
