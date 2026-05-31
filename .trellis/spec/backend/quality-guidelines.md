# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

<!--
Document your project's quality standards here.

Questions to answer:
- What patterns are forbidden?
- What linting rules do you enforce?
- What are your testing requirements?
- What code review standards apply?
-->

(To be filled by the team)

---

## Forbidden Patterns

<!-- Patterns that should never be used and why -->

(To be filled by the team)

---

## Required Patterns

<!-- Patterns that must always be used -->

(To be filled by the team)

---

## Testing Requirements

### Datasheet Evidence Tests

Fast tests must keep datasheet provenance deterministic:

- Generate tiny local fixtures when possible; do not commit vendor PDFs.
- Assert `extract_chunks()` page numbers, `ChunkRecord.evidence_token`, and the
  metadata handed to store boundaries.
- Do not run Chroma semantic ranking in the default pytest subset. Chroma's
  default ONNX MiniLM embedder may download model data on first use, so tests
  that call `query_chunks()` must be marked `@pytest.mark.slow`.

```python
# Fast: deterministic contract, no embedding model.
chunks = extract_chunks(pdf_path)
assert chunks[1].evidence_token == "datasheet:l78.pdf#p2"
assert captured_metadata["part_ref"] == "L7805"

# Slow: semantic retrieval / embedding-backed ranking.
@pytest.mark.slow
def test_ingest_then_query_returns_relevant_chunk() -> None:
    results = query_chunks(collection, "maximum input voltage", top_k=1)
    assert results[0]["metadata"]["page"] == 2
```

This split prevents default tests from depending on network/model-cache state
while still preserving a place for the full vector-store smoke.

---

## Code Review Checklist

<!-- What reviewers should check -->

(To be filled by the team)
