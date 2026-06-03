# D2b Design

## Scope

D2b generalizes the public document-index backfill path at the candidate/workflow
layer, then uses the D2a-selected `transistor` family as the first real
mainboard smoke.

The generalized asset is a cross-project reviewed document library, not a
project-local note. A row reviewed for one project can be reused in another
project when the BOM identity matches by parsed MPN or reviewer-confirmed exact
`Value` alias.

It does not add live search, automatic crawling, PLM/supplier fields,
datasheet profiles, or validator verdicts.

## Architecture

The reusable path is:

1. `design-validator-ui --index-json` produces grouped coverage rows.
2. `build-document-index-candidates --family <family>` emits a review CSV for
   one or more selected families.
3. A human reviewer fills public document fields (`Title`, `URL`/`Path`,
   `Description`) and, when known, a public `MPN`.
4. The reviewed CSV is passed back through existing `--document-index` paths.
5. Workbench/report output shows `document_status`, selected title, URL, and
   `doc:<file>#line<N>` source tokens.

Matching remains identity-based. Family labels (`transistor`, `diode`, `ic`,
etc.) are used to scope the review queue, not to claim that every same-family
component shares the same datasheet.

## Data Contracts

`DocumentCandidateRow` should preserve identity semantics:

- `identity_kind=mpn`: put the parsed BOM MPN in `MPN`.
- `identity_kind=part_like_value`: put the exact BOM value in `Value`; leave
  `MPN` blank until a reviewer adds a public part number.
- Never place Chinese BOM `编号` / item number in `MPN`.

The candidate CSV should remain a valid document-index input after review. Rows
with blank `URL`/`Path` continue to be ignored by `parse_document_index()`, so
unreviewed candidate rows do not create false coverage.

For the D2a transistor rows, the reviewed index should keep:

- `MPN`: public part number (`L2N7002KLT1G`, `LN2312LT1G`, `PE537BA`)
- `Value`: exact Chinese BOM `名称` string used by the current matcher
- `URL`/`Title`/`Description`: reviewed public document coverage only

For cross-project reuse, an index row must not depend on refdes, project paths,
or BOM source item numbers. Project-specific exact `Value` aliases are allowed
only as reviewed aliases for matching document coverage; they are not public MPN
claims.

## CLI Shape

Add family filtering to the existing command:

```bash
uv run hardwise build-document-index-candidates index.json \
  --family transistor \
  --output reports/mainboard-d2b-transistor-candidates.csv
```

`--family` may be repeated. With no `--family`, the command preserves the
current broad candidate behavior.

## Compatibility

- Existing candidate CSV readers should continue to see all old columns, with
  `Value` added near `MPN`.
- Existing document-index CSV files remain valid.
- Existing parser/matcher behavior remains valid; code changes are limited to
  candidate generation and CLI filtering unless implementation discovers a
  parser-backed need.

## Evidence Boundaries

A matched document row is coverage evidence only. It must not change
`PASS`/`WARN`/`ERROR`, profile status, or any electrical validation result.

Having a datasheet/document available also does not create a validation profile
by itself. D2c or later stages may reuse that public evidence to create a
reviewed profile, but only after pin mapping and limits are explicitly reviewed.

All document links must be public and explicitly reviewed. D2b may use stable
manufacturer or public datasheet/product pages, but must not perform live
supplier lookup, PLM lookup, lifecycle/pricing/availability checks, or bulk
downloads.
