# D3a Implementation Notes

## Pivot

D3a no longer treats the D2d IC queue as a broad per-MPN backfill task. The
active slice is the MPQ8626 datasheet-contract golden path:

```text
MPN / approved URL
  -> reviewed direct PDF row
  -> SHA-addressed document cache
  -> PDF chunks with evidence tokens
  -> materialized DatasheetProfile contract
  -> contract-driven buck topology validation
  -> pin/component report
```

The old IC batch review remains a useful future source-routing appendix, but it
is not the implementation target for this slice.

## Implemented In This Pass

### Document index schema extension

`DocumentIndexEntry` now accepts optional provenance/cache columns:

- `Source`
- `ReviewStatus`
- `LicenseNote`
- `LocalPath`
- `SHA256`

The parser remains backward-compatible with existing indexes. Existing
`MPN,Manufacturer,Title,URL,Description` rows still parse and still match BOM
groups as before.

### Approved document cache

Added `hardwise.documents.cache.fetch_approved_documents()`:

- Reads a parsed local document index.
- Accepts rows with `ReviewStatus` in `approved/ready/reviewed/verified/yes/true/1`.
- Accepts blank status as `legacy_unset` for old reviewed indexes.
- Skips explicit candidate/unapproved rows.
- Fetches only direct PDFs from `http(s)`, `file://`, or local paths.
- Verifies the bytes start with `%PDF-`.
- Stores PDFs as `<sha256>.pdf`.
- Appends JSONL provenance metadata when requested.
- Skips rather than fabricates on fetch failure, content-type mismatch,
  non-PDF bytes, unsupported scheme, or SHA mismatch.

### CLI

Added:

```bash
uv run hardwise fetch-approved-documents <docs.csv> \
  --cache-dir data/datasheets/cache \
  --metadata data/datasheets/documents.jsonl
```

This is intentionally a cache step, not a live supplier lookup. Datasheets.com,
Mouser, DigiKey, LCSC/JLC, or manual research can propose candidate URLs before
this command, but only reviewed direct PDF rows enter the cache.

### Datasheets.com candidate lookup

Added `hardwise.documents.datasheets_com` and:

```bash
uv run hardwise search-datasheets-com "MPQ8626" \
  --output reports/mpq8626-datasheets-com-candidates.csv
```

Official docs currently define `GET /api/v1/search` with
`Authorization: Bearer <api-key>`, required `q`, optional `limit` (max 10) and
`page`, and result fields including `datasheetUrl`. The documented default
limits are `60/min`, `500/hour`, and `5,000/month`; no public pricing table was
found, and higher limits/broader rights require contacting Datasheets.com.

The command reads `DATASHEETS_API_KEY` (or legacy `DATASHEETS_COM_API_KEY`) from
the server-side environment, never browser/static UI code. It writes
document-index CSV rows with `ReviewStatus=candidate`, so the existing approved
cache step will skip them until a reviewer changes the row to an approved
status.

## MPQ8626 Source Probe

Tried likely public MPQ8626 routes:

- Datasheets.com API was configured with `DATASHEETS_API_KEY`, but the live
  request returned `cloudflare_challenge` (`http_403`, `cf-mitigated:
  challenge`). The adapter now reports this as a structured provider state.
- MPS product/documentview URLs returned HTML / guarded download, not direct
  PDF bytes.
- Mouser direct-looking PDF URL returned an Akamai HTML error page on retry:
  `https://www.mouser.com/datasheet/2/277/MPQ8626GD_Z-3435265.pdf`
- AllDatasheet's direct-looking viewer PDF returned `%PDF-` and was accepted by
  `fetch-approved-documents`, producing SHA
  `91f6c7bc0c519b22fbeb61924ca3bd9cfbf52f923100d5d5f5351f6e57924e64`.
  However, `extract_chunks()` returned `0` chunks because the cached file is a
  25KB, 1-page image/preview PDF.
- AllDatasheet's 23-page HTML view has a text layer with useful evidence
  snippets, including the pinout on page 3 and application text on later pages.
  This is a useful human/parser fallback, but it is not a direct PDF and was not
  promoted into the PDF evidence cache.

Conclusion: the code path is ready, and the MPQ8626 fixture validation works
with the existing materialized profile. The missing piece is a direct,
text-extractable public PDF, or a future explicit HTML-page extractor with its
own provenance shape. The slice should not scrape guarded MPS/Mouser pages or
force image-only PDFs into the contract extraction path.

## Live Golden-Path Smoke

Local approved document row:

```text
data/datasheets/mpq8626-approved-docs.csv
```

Fetch result:

```bash
uv run hardwise fetch-approved-documents \
  data/datasheets/mpq8626-approved-docs.csv \
  --cache-dir data/datasheets/cache \
  --metadata data/datasheets/documents.jsonl
```

```text
documents-fetch: data/datasheets/cache (fetched=1, skipped=0, metadata=data/datasheets/documents.jsonl)
sha=91f6c7bc0c519b22fbeb61924ca3bd9cfbf52f923100d5d5f5351f6e57924e64
extract_chunks(...91f6c7bc...pdf) -> 0 chunks
```

Component validation smoke:

```bash
uv run hardwise report-component-validation \
  tests/fixtures/allegro/mpq8626_sync_buck.net \
  U13 \
  data/datasheet_profiles/mpq8626.json \
  --bom tests/fixtures/allegro/mpq8626_sync_buck_bom.csv \
  --output /tmp/hardwise-mpq8626-validation.md
```

```text
component-validation: /tmp/hardwise-mpq8626-validation.md (PASS, PASS/WARN/ERROR=14/0/0)
component checks PASS/WARN/ERROR=2/0/0
```

## Verification So Far

Focused tests:

```bash
uv run pytest tests/documents/test_cache.py tests/documents/test_index.py -q
```

Result:

```text
5 passed
```

Focused lint:

```bash
uv run ruff check \
  src/hardwise/documents/cache.py \
  src/hardwise/documents/index.py \
  src/hardwise/documents/types.py \
  src/hardwise/cli.py \
  tests/documents/test_cache.py
```

Result:

```text
All checks passed!
```

CLI smoke:

```bash
uv run hardwise --help
```

Result: `fetch-approved-documents` appears in the command list.

Additional focused verification after Datasheets.com adapter:

```bash
uv run pytest tests/documents/test_datasheets_com.py \
  tests/documents/test_cache.py \
  tests/documents/test_index.py -q
uv run ruff check src/hardwise/documents/datasheets_com.py \
  tests/documents/test_datasheets_com.py \
  src/hardwise/cli.py
```

Result:

```text
12 passed
All checks passed!
```

## D3b Minimal Adapter: HTML Fulltext Extraction

Added `hardwise.ingest.html` and:

```bash
uv run hardwise extract-datasheet-html \
  tests/fixtures/datasheets/mpq8626_fulltext.html \
  --source-name mpq8626.html \
  --output /tmp/mpq8626-html-chunks.jsonl
```

This is the smallest safe adapter after the MPQ8626 source probe: it handles
public HTML fulltext pages, including AllDatasheet-style page markers, without
pretending those pages are direct PDF cache artifacts. The command writes
chunk JSONL with `datasheet:<html-source>#p<N>` evidence tokens and can ingest
to Chroma only when `--part-ref` is explicit.

Focused verification:

```bash
uv run pytest tests/ingest/test_html.py -q
uv run ruff check src/hardwise/ingest/html.py tests/ingest/test_html.py src/hardwise/cli.py
```

Result:

```text
5 passed
All checks passed!
```

## Evidence-To-Draft Contract Step

Added `draft-datasheet-profile --evidence-chunks`:

```bash
uv run hardwise draft-datasheet-profile \
  /tmp/hardwise-mpq8626-index.json \
  --identity MPQ8626GD \
  --document-index data/document_indexes/power_v1_docs.csv \
  --evidence-chunks /tmp/hardwise-mpq8626-html-chunks.jsonl \
  --output /tmp/hardwise-mpq8626-needs-review-profile.json
```

This keeps the human-review gate intact:

- The output profile stays `review_status=needs_review`.
- Existing document provenance stays in `document.source`, for example
  `doc:power_v1_docs.csv#line2`.
- PDF/HTML chunk rows contribute page-level evidence tokens under
  `evidence.chunks.*`, for example `datasheet:mpq8626.html#p1`.
- The command accepts chunk JSONL from `extract-datasheet-html` or PDF ingest;
  it does not promote the draft to `ready`, infer pin facts, or run validation
  from raw chunks.

MPQ8626 smoke:

```text
html-datasheet-extract: /tmp/hardwise-mpq8626-html-chunks.jsonl (chunks=1, source=mpq8626.html, page=1, ingested=off)
design-validator-ui: /tmp/hardwise-mpq8626-workbench.html (4 components, validated=1, BOM matched=4, PASS/WARN/ERROR=1/0/0, manual=3)
profile-draft: /tmp/hardwise-mpq8626-needs-review-profile.json (part_number=MPQ8626GD, review_status=needs_review, evidence_chunks=on)
datasheet-profile-store: /tmp/hardwise-mpq8626-profiles.db (part=MPQ8626GD, aliases=0, pins=0, status=needs_review)
component-validation: /tmp/hardwise-mpq8626-validation.md (PASS, PASS/WARN/ERROR=14/0/0)
```

Focused regression:

```bash
uv run pytest tests/test_cli_validator_ui.py::test_mpq8626_html_chunks_feed_needs_review_profile_draft \
  tests/test_cli_validator_ui.py::test_design_validator_ui_matches_mpq8626_power_family_with_public_docs \
  tests/ir/test_profile_archetypes.py \
  tests/ingest/test_html.py -q
uv run ruff check src/hardwise/ir/profile_draft.py src/hardwise/cli.py \
  tests/ir/test_profile_archetypes.py tests/test_cli_validator_ui.py
```

Result:

```text
13 passed
All checks passed!
```

Full verification:

```bash
uv run pytest -q
uv run ruff check .
git diff --check
```

Result:

```text
519 passed, 7 deselected
All checks passed!
git diff --check passed
```

## Remaining Gap Table

| Area | Current state | MVP next action | Deferred |
|---|---|---|---|
| Datasheet source/discovery | `search-datasheets-com` can propose candidate direct-PDF rows, but live Datasheets.com may return Cloudflare challenge; local document index remains the trust boundary. | Keep using candidate CSV + reviewer-approved rows; add source-specific adapters only for public APIs that return stable document URLs without anti-bot bypass. | Broad web crawling, PLM integration, supplier lifecycle/price/availability. |
| Document bytes/text extraction | Direct PDFs enter SHA cache only after `%PDF-` verification; PDF text extraction works when the PDF has a text layer; HTML fulltext pages now produce `ChunkRecord` JSONL/vector chunks. | Keep explicit source-shape handling; use HTML chunks only when PDF bytes are image-only or guarded. | Multi-page HTML crawler, OCR for image PDFs, guarded-download bypass. |
| Contract generation/provenance | `DatasheetProfile` can be stored in the relational profile contract store; `draft-datasheet-profile --evidence-chunks` ties document provenance and page-level chunk tokens to a `needs_review` draft; MPQ8626 still validates through the existing reviewed ready contract. | Human-review the draft fields before any `ready` promotion. | Fully automatic promotion to `ready`, unconstrained LLM pin facts, whole-BOM profile generation. |

## Next Step

Review the MPQ8626 needs-review draft against public page-level evidence, then
promote only confirmed fields into the ready contract if the evidence supports
each pin/topology claim.

## Parallel Session 3: MPQ8626 Contract Review Audit

Reproduced the public evidence path:

```bash
uv run hardwise extract-datasheet-html \
  tests/fixtures/datasheets/mpq8626_fulltext.html \
  --source-name mpq8626.html \
  --output /tmp/hardwise-mpq8626-html-chunks.jsonl \
  --chunk-size 1000
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mpq8626_sync_buck.net \
  tests/fixtures/allegro/mpq8626_sync_buck_bom.csv \
  --document-index data/document_indexes/power_v1_docs.csv \
  --output /tmp/hardwise-mpq8626-workbench.html \
  --index-output /tmp/hardwise-mpq8626-index.md \
  --index-json /tmp/hardwise-mpq8626-index.json
uv run hardwise draft-datasheet-profile \
  /tmp/hardwise-mpq8626-index.json \
  --identity MPQ8626GD \
  --document-index data/document_indexes/power_v1_docs.csv \
  --evidence-chunks /tmp/hardwise-mpq8626-html-chunks.jsonl \
  --output /tmp/hardwise-mpq8626-needs-review-profile.json
```

Results:

```text
html-datasheet-extract: chunks=1, source=mpq8626.html, page=1
design-validator-ui: validated=1, PASS/WARN/ERROR=1/0/0, manual=3
profile-draft: part_number=MPQ8626GD, review_status=needs_review, evidence_chunks=on
```

Audit decision: do not promote the MPQ8626 draft to `ready` from this evidence
set. The only reproduced public page token is `datasheet:mpq8626.html#p1`, and
the fixture contains a compact excerpt, not the full datasheet pages referenced
by the existing reviewed profile (`datasheet:mpq8626.pdf#p1/#p3/#p5/#p17`).

| Field area | Current ready value | Reproduced evidence | Audit | Action |
|---|---|---|---|---|
| Document provenance | MPS public MPQ8626 product page row | `doc:power_v1_docs.csv#line2` | Pass | Keep draft provenance. |
| Draft evidence token | Chunk source/page available | `datasheet:mpq8626.html#p1` | Pass | Keep draft `needs_review`. |
| Identity | `MPQ8626GD` group matched from BOM/index | `/tmp/hardwise-mpq8626-index.json`, group `1` | Pass | Draft identity is reviewable. |
| `recommended.vin_min/max` and pin 3 `VIN` range | `2.85` to `16.0` | `datasheet:mpq8626.html#p1` | Pass for this value only | Can be manually transferred only if using the HTML token. |
| Pin 1 `PGND1`, pin 2 `SW1`, pin 10 `BST` names/functions | Present in existing ready profile | `datasheet:mpq8626.html#p1` | Partial pass | Only these pin facts are supported by reproduced evidence. |
| Switch-node to inductor topology | Existing ready profile uses `recommended.inductor` | `datasheet:mpq8626.html#p1` | Partial pass | Supports a generic SW-to-inductor claim, not the full existing token set. |
| Full 14-pin map | Pins 1-14 populated | Existing profile cites `datasheet:mpq8626.pdf#p3`; not reproduced here | Fail | Missing public page-level evidence for pins 4-9, 11-14. |
| Synchronous buck / no external diode | Existing profile cites `datasheet:mpq8626.pdf#p1` | HTML excerpt only says integrated synchronous buck power stage for SW1 | Partial/fail | Not enough to confirm every ready field. |
| Existing PDF evidence tokens | `datasheet:mpq8626.pdf#p1/#p3/#p5/#p17` | No local text-extractable public PDF in this worktree | Fail | Do not rewrite or newly certify the ready contract. |

Required evidence to promote later:

- A public text-extractable PDF or public HTML page set covering the full pin
  description table, with stable page-level tokens for pins 1-14.
- Public page evidence for recommended input voltage, output current, topology,
  synchronous rectification, and typical SW/inductor application.
- A reviewed profile update that changes evidence tokens to the actually
  reproduced public source shape instead of carrying unverified token names.

## Stop Conditions

- If the source is only a product page or guarded HTML page, do not cache it as
  a datasheet PDF.
- If PDF extraction cannot produce enough pin/table/topology evidence, keep the
  contract as `needs_review`.
- If the profile/contract has no page-level evidence for a field, the validator
  should not use that field as a deterministic claim.

## D3c Coverage Pack: Internal-PN Value Bridge

D3c did not add a new validator family. The ranked high-value candidates showed
a simpler blocker: several already had reviewed profiles and existing
deterministic families, but BOM `MPN` fields were internal numeric PNs while the
public MPN appeared in BOM value/description text.

Implemented a narrow fallback:

- `profile_candidates.py` still tries direct BOM identity first.
- Reviewed document-index MPNs still take precedence when present.
- `profile_candidate_text.py` then scans BOM value/description text for exact
  normalized ready profile part numbers or aliases.
- The fallback emits `identity_kind=value_mpn`.
- When a `Design` is available, profile pin numbers must fit the local symbol
  pin IDs before the candidate becomes `matched`.

Safe coverage pack proved by tests/smoke:

| Candidate | Profile | Validator family | Action |
|---|---|---|---|
| `MPQ8626GD-Z` | `mpq8626.json` | `buck` | matched from BOM value text with internal PN |
| `PCA9617ADP` | `pca9617a.json` | `i2c_level_shift_repeater` | matched from BOM value text with internal PN |
| `1.5SMC15A` | `1_5smc15a.json` | `diode` | matched from BOM value text with internal PN |
| `SM340AF` | `sm340af.json` | `diode` | matched from BOM value text with internal PN |
| `SD103AWS-7-F` | `sd103aws_7_f.json` | `diode` | matched from BOM value text with internal PN |

Skipped candidates and reasons:

| Candidate | Reason |
|---|---|
| `L2N7002KLT1G` | Already completed in D2c/D2d; no new D3c action needed. |
| `LN2312LT1G` | Ready profile exists, but local symbol pin IDs are `D/G/S`; needs deliberate mapping, not fallback matching. |
| `PE537BA` | Public mirror row exists but no reviewed P-MOS profile yet. |
| `74LVC1G125GW`, `MP87000`, `MP5991`, `AZ5123`, `LBAV99` | Evidence/profile/family work still needed; skipped rather than inventing coverage. |

Also updated advisory coverage metadata so `recommend-next-family` knows
`shift_register_piso` and `i2c_level_shift_repeater` are existing deterministic
families under the broad `ic` bucket. This changes ranking hints only; validator
dispatch remains controlled by `validation/component.py`.

Focused verification:

```bash
uv run pytest tests/validation/test_coverage_priority.py \
  tests/validation/test_profile_candidates.py \
  tests/workbench/test_context.py -q
uv run ruff check src/hardwise/validation/profile_candidates.py \
  src/hardwise/validation/profile_candidate_text.py \
  src/hardwise/validation/coverage_priority.py \
  tests/validation/test_profile_candidates.py \
  tests/workbench/test_context.py \
  tests/validation/test_coverage_priority.py
```

Result:

```text
20 passed
All checks passed!
```
