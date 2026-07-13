# Datasheets — user-supplied artifacts

Hardwise's vector-store demo uses public datasheets. Files in this directory
are **not committed** (`.gitignore` excludes `*.pdf` here).

## Recommended demo set (matches `data/projects/pic_programmer`)

| File | Refdes | Part | Source |
|---|---|---|---|
| `l78.pdf` | U3 | 7805 (L78xx series) | https://www.st.com/resource/en/datasheet/l78.pdf |
| `24C16.pdf` | U1 | 24C16 EEPROM | https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA16-24LC16B-Data-Sheet-20001703F.pdf |

Some vendor sites reject `curl`/`wget`. If the bash download fails, open the
URL in a browser, save the PDF here, and rename if needed.

## High-risk evidence pack pilot

The three-row public pilot is pinned in
`data/document_indexes/high_risk_evidence_pilot.csv`. Fetching it verifies the
official PDF bytes against the reviewed SHA256 values, keeps the content-
addressed copies under `cache/`, and materializes the local filenames used by
the reviewed profiles:

```bash
uv run hardwise fetch-approved-documents \
  data/document_indexes/high_risk_evidence_pilot.csv \
  --cache-dir data/datasheets/cache \
  --metadata data/datasheets/documents.jsonl
```

The PDF files and retrieval metadata remain local and gitignored. A changed
vendor PDF fails closed as `sha256_mismatch`; review the new revision before
updating the pinned hash. A pre-existing local alias is hash-audited first and
removed if it does not match the manifest. `LocalPath` is restricted to a PDF path below this
datasheet directory, so a reviewed index cannot write outside the evidence
cache boundary.

## Verifying the ingest pipeline once a PDF is here

```bash
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3
uv run hardwise query-datasheet "absolute maximum input voltage"
```

The first command extracts text chunks page-by-page, embeds them with the
ONNX MiniLM model that ships with Chromadb, and writes the persistent
vector store to `data/chroma/`. The second command runs a semantic query
and prints the top-k chunks with `[source_pdf pN part=Ux]` provenance.
