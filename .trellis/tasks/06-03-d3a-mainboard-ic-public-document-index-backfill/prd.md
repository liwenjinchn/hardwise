# D3a MPQ8626 datasheet-contract golden path

## Goal

Pivot D3a from broad IC document-index backfill to one reproducible golden path:
resolve a public datasheet for the real mainboard `MPQ8626GD-Z` buck converter,
cache the PDF by SHA, materialize a structured datasheet contract, and run the
existing contract-driven buck topology checker against the parsed netlist.

The task directory name still mentions "document-index backfill" because it was
created before the pivot. The active scope is this golden path.

## Confirmed Facts

- The D2d mainboard advisory ranked ICs as the next actionable family, but the
  old D3a plan expanded into a per-MPN backfill queue.
- Competitor behavior suggests the stronger product loop is:
  `MPN -> datasheet -> pin contract -> netlist topology -> pin-level report`.
- For Hardwise, `MPQ8626GD-Z` is the right target because it is already present
  in the real public-safe mainboard flow and has an existing buck validator path.
- `data/datasheet_profiles/mpq8626.json` is the current materialized contract
  shape, but it is a manual profile. D3a should make the upstream document cache
  and extraction boundary auditable.
- Existing deterministic validation already checks the contract-driven topology:
  synchronous buck profile, switch-node to inductor path, and no external
  freewheel diode requirement.

## Source Strategy

1. Primary MVP discovery source: Datasheets.com API or a human-approved direct
   public PDF URL. Datasheets.com returns candidate `datasheetUrl` values via
   `GET /api/v1/search`, but those rows remain `candidate` until reviewed.
2. Fallback sources: manufacturer page, DigiKey/Mouser, LCSC/JLC for China
   ecosystem parts, and user-provided approved URLs.
3. Elecfans / `file.elecfans.com` are fallback evidence only. Opaque CDN paths
   are not a stable MPN lookup source.

Document lookup may propose candidates, but only reviewed rows enter the local
document cache.

## Requirements

1. Add a reviewed document fetch/cache step that reads local document-index CSV
   or TSV rows and fetches only approved direct public PDFs.
2. Cache fetched PDFs by SHA-256 under a local cache directory and append
   provenance metadata with source URL, source method, review status, hash,
   timestamp, and license/terms note.
3. Keep cache input auditable. Search/API discovery can happen before this step,
   but cache ingestion must use reviewed rows rather than opaque live scraping.
4. Reuse `DatasheetProfile` as the materialized `PinContract` for MVP. Do not
   introduce a parallel schema unless the current profile model becomes
   insufficient.
5. Treat vector chunks as evidence input, not the validation contract. The
   validator should read a materialized profile/contract JSON, not perform lazy
   retrieval during every topology check.
6. Use `MPQ8626GD-Z` as the golden-path target. The screenshot `XL1509-12E1`
   remains a reference example only.
7. Do not promote broad IC coverage, supplier lifecycle facts, pricing, stock,
   PLM data, PCB/layout, thermal simulation, or generic web scraping.

## Acceptance Criteria

- [x] A CLI command can fetch approved direct-PDF document-index rows into a
      SHA-addressed local cache.
- [x] Cache metadata records document provenance and review state.
- [x] Unapproved candidate rows are skipped rather than fetched.
- [x] A CLI command can query Datasheets.com and emit reviewable candidate
      document-index rows without making them cache-eligible.
- [ ] A D3a MPQ8626 reviewed document row records the source route
      (`datasheets.com` or manual approved URL) and can be cached locally.
- [ ] The cached PDF can be chunked with existing PDF ingest and evidence tokens.
- [ ] The materialized `DatasheetProfile` contract for MPQ8626 is tied to cached
      document provenance instead of being only an isolated manual profile.
- [ ] The MPQ8626 fixture or real mainboard smoke still validates through the
      existing contract-driven buck checker.
- [ ] `uv run pytest -q`, `uv run ruff check .`, and `git diff --check` pass
      before completion.

## Out Of Scope

- Building a giant datasheet scraper.
- Treating Elecfans CDN links as a primary lookup API.
- Lazy vector retrieval as the validation contract.
- Batch backfilling all 37 old D3a IC candidates.
- Adding new IC families beyond the MPQ8626 golden path.
- PCB review, boardview, layout geometry, PLM, lifecycle, pricing, stock, or
  availability claims.

## Stop Conditions

- A source URL returns a webpage rather than a direct PDF and no reviewed direct
  PDF URL is available.
- PDF text extraction cannot find enough evidence for pin table or topology
  contract fields.
- A generated contract lacks page-level evidence for pin functions or topology
  constraints.
- Any smoke changes validation verdicts without a materialized profile/contract
  and deterministic validator path.

## Notes

- The old IC batch research remains useful as a future source-routing appendix,
  especially for MPS, SGMICRO, Renesas, and LCSC-backed rows. It is no longer
  the main D3a product slice.
