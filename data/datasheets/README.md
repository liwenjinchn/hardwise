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

## Verifying the ingest pipeline once a PDF is here

```bash
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3
uv run hardwise query-datasheet "absolute maximum input voltage"
```

The first command extracts text chunks page-by-page, embeds them with the
ONNX MiniLM model that ships with Chromadb, and writes the persistent
vector store to `data/chroma/`. The second command runs a semantic query
and prints the top-k chunks with `[source_pdf pN part=Ux]` provenance.
