"""Chroma vector store — local persistent mode for datasheet chunks.

Slice 3 minimum: ingest chunks with `part_ref` and page metadata, query by
natural-language string. Uses Chroma's default embedder (no separate
sentence-transformers dep needed for the demo).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hardwise.ingest.pdf import ChunkRecord


def create_collection(persist_dir: Path | None, collection_name: str = "datasheets") -> Any:
    """Open (or create) a Chroma collection.

    `persist_dir=None` runs in-memory (used in tests). A directory path
    runs in local persistent mode.
    """
    import chromadb

    if persist_dir is None:
        client = chromadb.Client()
    else:
        persist_dir = persist_dir.expanduser().resolve()
        persist_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(persist_dir))
    return client.get_or_create_collection(name=collection_name)


def ingest_chunks(collection: Any, chunks: list[ChunkRecord], part_ref: str) -> int:
    """Add chunks to the collection with `part_ref` + page metadata.

    Returns the number of chunks actually upserted.
    """
    if not chunks:
        return 0
    ids = [f"{part_ref}:{c.source_pdf}:p{c.page}:c{c.chunk_index}" for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [
        {
            "part_ref": part_ref,
            "source_pdf": c.source_pdf,
            "page": c.page,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def query_chunks(collection: Any, query: str, top_k: int = 5) -> list[dict]:
    """Retrieve top-k chunks by semantic similarity.

    Each result row is a dict with `text`, `metadata`, and `distance` fields.
    """
    if collection.count() == 0:
        return []
    result = collection.query(query_texts=[query], n_results=top_k)
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
