"""Tests for the PDF chunk extractor.

Fast tests stay hermetic: no vendor PDF, no network, and no Chroma semantic
query. The vector-store ranking path lives in `tests/store/test_vector.py`
under `@pytest.mark.slow` because Chroma's default embedder may download its
ONNX model on first use.
"""

from pathlib import Path

from hardwise.ingest.pdf import ChunkRecord, _split_text
from hardwise.ingest.pdf import extract_chunks
from hardwise.store.vector import ingest_chunks


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


def test_extract_pdf_preserves_page_tokens_and_ingest_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "l78.pdf"
    _write_minimal_text_pdf(
        pdf_path,
        [
            "L78 positive voltage regulator cover page.",
            "Absolute maximum input voltage is 35 V DC.",
        ],
    )

    chunks = extract_chunks(pdf_path)

    assert [chunk.page for chunk in chunks] == [1, 2]
    assert chunks[1].source_pdf == "l78.pdf"
    assert chunks[1].evidence_token == "datasheet:l78.pdf#p2"
    assert "35 V" in chunks[1].text

    collection = _CaptureCollection()
    assert ingest_chunks(collection, chunks, part_ref="L7805") == 2
    assert collection.metadatas[1] == {
        "part_ref": "L7805",
        "source_pdf": "l78.pdf",
        "page": 2,
        "chunk_index": 0,
    }


class _CaptureCollection:
    def __init__(self) -> None:
        self.metadatas: list[dict] = []

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        self.metadatas = metadatas


def _write_minimal_text_pdf(path: Path, pages: list[str]) -> None:
    objects: list[str] = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = [f"{3 + idx * 2} 0 R" for idx in range(len(pages))]
    objects.append(f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>")

    for idx, text in enumerate(pages):
        page_obj = 3 + idx * 2
        content_obj = page_obj + 1
        stream = f"BT /F1 12 Tf 72 720 Td ({_pdf_escape(text)}) Tj ET"
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
            f"/BaseFont /Helvetica >> >> >> /Contents {content_obj} 0 R >>"
        )
        objects.append(f"<< /Length {len(stream.encode('ascii'))} >>\nstream\n{stream}\nendstream")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_num, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{obj_num} 0 obj\n{obj}\nendobj\n".encode("ascii")

    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for offset in offsets[1:]:
        output += f"{offset:010d} 00000 n \n".encode("ascii")
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    path.write_bytes(output)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
