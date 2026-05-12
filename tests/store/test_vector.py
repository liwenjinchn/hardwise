"""Tests for the Chroma vector store wrapper.

Uses Chroma in-memory mode (no persistence) so tests run hermetically.
Chromadb's default embedder (ONNX MiniLM) is bundled — no separate
sentence-transformers install needed. First test run may download the
ONNX model (~80 MB) into the chromadb cache.
"""

from pathlib import Path

import pytest

from hardwise.ingest.pdf import ChunkRecord
from hardwise.store.vector import create_collection, ingest_chunks, query_chunks


def _make_chunk(text: str, page: int = 1, idx: int = 0) -> ChunkRecord:
    return ChunkRecord(text=text, source_pdf="l78.pdf", page=page, chunk_index=idx)


@pytest.mark.slow
def test_ingest_then_query_returns_relevant_chunk() -> None:
    collection = create_collection(persist_dir=None, collection_name="t_slice3")
    chunks = [
        _make_chunk("The L78 series provides fixed positive voltage regulation.", page=1),
        _make_chunk("Absolute maximum input voltage is 35 V DC.", page=2),
        _make_chunk("Operating temperature range -40 to 125 degrees Celsius.", page=3),
    ]
    n = ingest_chunks(collection, chunks, part_ref="U3")
    assert n == 3
    results = query_chunks(collection, "maximum input voltage", top_k=1)
    assert results
    assert "35 V" in results[0]["text"] or "35V" in results[0]["text"]
    assert results[0]["metadata"]["part_ref"] == "U3"
    assert results[0]["metadata"]["page"] == 2


@pytest.mark.slow
def test_query_empty_collection_returns_empty_list() -> None:
    collection = create_collection(persist_dir=None, collection_name="t_empty")
    assert query_chunks(collection, "anything") == []


@pytest.mark.slow
def test_ingest_is_idempotent_upsert() -> None:
    collection = create_collection(persist_dir=None, collection_name="t_idem")
    chunk = _make_chunk("idempotent chunk text", page=1)
    ingest_chunks(collection, [chunk], part_ref="U3")
    ingest_chunks(collection, [chunk], part_ref="U3")
    assert collection.count() == 1


@pytest.mark.slow
def test_persist_dir_round_trip(tmp_path: Path) -> None:
    persist = tmp_path / "chroma"
    coll1 = create_collection(persist_dir=persist, collection_name="t_persist")
    ingest_chunks(coll1, [_make_chunk("persisted text", page=5)], part_ref="U3")
    coll2 = create_collection(persist_dir=persist, collection_name="t_persist")
    assert coll2.count() == 1
    results = query_chunks(coll2, "persisted", top_k=1)
    assert results
    assert results[0]["metadata"]["page"] == 5
