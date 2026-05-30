# Real Datasheet Evidence Chain Design

## Architecture

This task closes a gap between three existing mechanisms rather than adding a new subsystem:

- PDF extraction: `src/hardwise/ingest/pdf.py` reads a real PDF and preserves page numbers.
- Vector evidence store: `src/hardwise/store/vector.py` indexes chunks with `part_ref`, `source_pdf`, `page`, and `chunk_index`.
- Structured profile finding: `DS001` reads `DatasheetProfile.evidence["abs_max.vin"]` and emits the page token in a `Finding`.

The intended evidence relationship is:

```text
line A: l78 profile evidence["abs_max.vin"] = datasheet:l78.pdf#p4
  -> DS001 finding for U3 cites datasheet:l78.pdf#p4

line B: official public ST PDF
  -> data/datasheets/l78.pdf (gitignored local demo input)
  -> extract_chunks()
  -> Chroma metadata {part_ref: L7805, source_pdf: l78.pdf, page: 4}
  -> query-datasheet "absolute maximum input voltage"
  -> independent hit on datasheet:l78.pdf#p4
```

The two lines converge on the same page token. Line B corroborates Line A; Line A is not dynamically produced by Line B during `review`.

## Boundaries

The profile JSON remains the structured fact source for deterministic validation. Chroma search proves the page provenance and supports agent/tool evidence lookup, but DS001 should not parse arbitrary RAG text at runtime. That keeps the rule deterministic: profile extraction/fact review is one layer, component validation is another.

The real PDF is a public demo input and stays out of git. The repository can include scripts/tests/docs that prove how to reproduce the local artifact, but not the vendor binary or generated Chroma files.

## Contracts

- Evidence token format remains `datasheet:<pdf basename>#p<1-indexed page>`.
- L78 profile extraction remains deterministic and filename-gated.
- `part_ref` should use component identity (`L7805`) for Phase 2 demos, not KiCad refdes (`U3`). Refdes is still the schematic join key in findings; part identity is the datasheet-store filter key.
- Fast automated tests should avoid network, binary fixtures, and Chroma semantic ranking. They can generate a small synthetic PDF in `tmp_path`, exercise `pdfplumber` extraction, and assert page/token metadata that would be passed into `ingest_chunks()`.
- Slow automated tests can exercise `ingest_chunks() -> query_chunks()` semantic ranking and must stay marked `@pytest.mark.slow`, matching the existing vector-store tests whose first run may fetch Chroma's default ONNX MiniLM model.

## Compatibility

Existing tests and docs mention older `--part-ref U3` examples. Phase 2 should update user-facing examples toward `--part-ref L7805` where they describe datasheet identity. Avoid broad rewrites of historical log entries unless appending a new measured result.

`data/datasheet_profiles/l78.json` already has the right page token. If the current official PDF has shifted page numbers, update the profile and tests together, and log the correction in `docs/learning_log.md`.

## Rollback

If Chroma query ranking is unstable on the real PDF, keep the profile token and DS001 path intact, then add a deterministic PDF extraction check for page text as the acceptance evidence. Do not widen scope into an LLM extractor to rescue a ranking issue.
