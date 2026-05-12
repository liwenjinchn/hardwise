"""Tests for the PDF chunk extractor.

Pure unit tests for the splitter (no PDF dependency). A real-PDF end-to-end
test is intentionally avoided here because we do not ship a fixture PDF in
the repo — `data/datasheets/` is gitignored. The CLI smoke test in
`tests/test_e2e_slice3.py` provides the live-data check.
"""

from hardwise.ingest.pdf import ChunkRecord, _split_text


def test_split_returns_single_chunk_when_text_under_limit() -> None:
    out = _split_text("hello world", chunk_size=500, overlap=100)
    assert out == ["hello world"]


def test_split_slices_with_overlap() -> None:
    text = "abcdefghij" * 100  # 1000 chars
    out = _split_text(text, chunk_size=500, overlap=100)
    assert len(out) >= 2
    # Step = 500 - 100 = 400, so chunk 1 starts at 0, chunk 2 starts at 400
    assert out[0] == text[:500]
    assert out[1] == text[400:900]


def test_split_step_floor_one_when_overlap_too_large() -> None:
    out = _split_text("abcdefghij", chunk_size=5, overlap=10)
    assert all(out)
    assert len(out) >= 1


def test_evidence_token_format() -> None:
    chunk = ChunkRecord(text="x", source_pdf="l78.pdf", page=7, chunk_index=0)
    assert chunk.evidence_token == "datasheet:l78.pdf#p7"
