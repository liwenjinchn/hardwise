# D2b public document index completion

## Goal

Ship a reusable, family-scoped public document-index backfill workflow, with the
D2a-selected `transistor` family as the first real mainboard target. The next
mainboard workbench smoke should show document coverage for that family without
doing live supplier lookup, PLM lookup, or uncontrolled bulk downloads.

## User Value

Hardware reviewers get a bounded, reproducible document-coverage state:
Hardwise can say which BOM groups in the chosen family have a reviewed public
datasheet/product-document link, and which remain gaps, without pretending that
document presence proves electrical correctness.

The same workflow should also be reusable across projects and later D2-style
family slices: generate a review queue from grouped coverage, let a reviewer
fill public document links, then feed the reviewed CSV back into the existing
`--document-index` paths. If another project uses the same reviewed public MPN
or reviewer-confirmed BOM `Value` alias, it should be able to reuse the same
document-index row for document coverage.

## Confirmed Facts

- D2a selected `transistor` as the D2 family and `L2N7002KLT1G` as the first
  D2c implementation target.
- Existing document-index support is local CSV/TSV only:
  `parse_document_index()` reads reviewed rows and `match_documents_to_bom()`
  matches them to BOM item groups.
- `parse_document_index()` accepts part-number headers such as `MPN` or
  `part_number`, value headers such as `Value`, and manufacturer/title/URL/
  description fields.
- Existing CLI/workbench paths already accept `--document-index` and explicitly
  state that this is not live supplier search, PLM, lifecycle, pricing, or
  availability lookup.
- Existing document indexes live under `data/document_indexes/`; current rows
  include `power_v1_docs.csv` and `family_v1_3_docs.csv`.
- `build-document-index-candidates <validation-index.json>` already produces a
  reviewable CSV of unmatched non-passive/non-mechanical groups.
- The existing candidate CSV places the selected identity in `MPN` even when the
  grouped identity came from a part-like BOM `Value`; for Chinese BOM rows this
  blurs the "do not invent MPN" contract.
- The document-index parser already ignores extra columns and skips rows whose
  `URL`/`Path` is blank, so a candidate CSV can become a reviewed document index
  after a human fills the document link fields.
- The real public mainboard D1 smoke produced 195 component groups and 75
  document-index candidates.
- D2a identified three transistor BOM identities for D2b:
  `N-MOS管 L2N7002KLT1G SOT23 1.5 LRC` (106 refdes),
  `N-MOS管 LN2312LT1G 5A SOT– 23 LRC` (26 refdes), and
  `P-MOS管 PE537BA PDFN -33 NIKO-SEM` (11 refdes).
- The Chinese BOM `编号` remains a source item number and must not be used as an
  MPN/document part number.

## Requirements

- Keep D2b's real target limited to the D2a-selected `transistor` family, but
  implement the path in a family-parameterized way so future slices can reuse it
  for `diode`, narrow `ic`, or other eligible coverage families.
- Treat document-index rows as a cross-project reviewed library keyed by parsed
  MPN first and reviewer-confirmed BOM value aliases second. "Same family" alone
  is not enough to match; the row still needs a matching identity.
- Generalize candidate generation so review rows distinguish actual parsed MPNs
  from part-like BOM values:
  - actual `identity_kind=mpn` rows populate `MPN`;
  - `identity_kind=part_like_value` rows populate `Value`;
  - neither path may use Chinese BOM `编号` as MPN.
- Support family-scoped candidate output from a grouped validation index, so D2b
  can produce a transistor-only review queue without hand-filtering a broad CSV.
- Add or update a local public document index row set for the transistor family,
  using the generalized candidate/index schema and enough aliases/identities for
  the mainboard grouped coverage to match the intended BOM groups.
- Target rows:
  `L2N7002KLT1G` / `N-MOS管 L2N7002KLT1G SOT23 1.5 LRC`,
  `LN2312LT1G` / `N-MOS管 LN2312LT1G 5A SOT– 23 LRC`, and
  `PE537BA` / `P-MOS管 PE537BA PDFN -33 NIKO-SEM`.
- Prefer manufacturer product or datasheet pages when available; otherwise use a
  stable public document page that is directly relevant to the part identity.
- Keep each row human-reviewable: title and description must explain what the
  link is, not make validation claims.
- Validate by running the existing document-index parser/matcher path and a
  focused workbench/index smoke against the mainboard validation index or
  project input used by D2a.

## Acceptance Criteria

- [x] The D2a-selected family is named in this PRD or a linked planning artifact
      before implementation starts.
- [x] The document-index candidate workflow can emit a family-scoped review CSV.
- [x] Candidate rows preserve identity semantics: parsed MPNs go in `MPN`,
      part-like BOM values go in `Value`, and Chinese BOM `编号` is not promoted
      to MPN.
- [x] A reviewed document-index row can be reused by another BOM/project when
      the parsed MPN or reviewer-confirmed `Value` alias matches, without
      relying on project-specific refdes or source item numbers.
- [x] A reviewed public document index contains rows for the selected family's
      relevant mainboard BOM identities.
- [x] The selected family shows `document_status=matched` for the intended
      grouped coverage rows in the generated validation index.
- [x] The generated workbench/report output displays the matched public document
      title(s), URL(s), and `doc:<file>#line<N>` source token(s).
- [x] No command path performs live supplier lookup, PLM lookup, lifecycle,
      pricing, availability lookup, or uncontrolled bulk PDF/document download.
- [x] Focused tests or smoke commands are recorded in the final task summary.

## Out Of Scope

- Choosing the target family; D2a owns that decision.
- Adding a new family validator or new datasheet profile.
- Live supplier search, PLM integration, lifecycle/pricing/availability checks,
  or automatic crawling/downloading of many documents.
- Claiming electrical PASS/WARN/ERROR from the presence of a document link.
- Broadly filling every remaining document-index candidate from the mainboard.
- Treating Chinese BOM `编号` as MPN.
- Building a generic internet search, scraping, or supplier-discovery engine.
- Changing validator verdicts or profile matching for D2c.
- Matching document rows by family name alone without an MPN or reviewed value
  alias.

## Open Questions

- None blocking planning.

## Notes

- This is no longer PRD-only: the generalized candidate workflow requires
  `design.md` and `implement.md` before `task.py start`.

## Completion Evidence

Artifacts:

- `/tmp/hardwise-mainboard-d2b-transistor-candidates.csv`
- `/tmp/hardwise-mainboard-d2b-transistor-after-docs-candidates.csv`
- `/tmp/hardwise-mainboard-d2b-workbench.html`
- `/tmp/hardwise-mainboard-d2b-index.md`
- `/tmp/hardwise-mainboard-d2b-index.json`

Mainboard smoke:

```text
build-document-index-candidates /tmp/hardwise-mainboard-d1-auto-index.json --family transistor
groups=195, candidates=3, families=transistor, skipped_family_filter=192

design-validator-ui <mainboard-allegro-folder> --document-index data/document_indexes/mainboard_d2_transistor_docs.csv
document-index: matched=3, no_result=189, ambiguous=0, manual_needed=0
8180 components, validated=6573, BOM matched=7248
PASS/WARN/ERROR=3867/2706/0, manual=1607

build-document-index-candidates /tmp/hardwise-mainboard-d2b-index.json --family transistor
groups=195, candidates=0, skipped_matched=3, skipped_family_filter=192
```

Matched transistor document rows:

- `N-MOS管 L2N7002KLT1G SOT23 1.5 LRC` -> `doc:mainboard_d2_transistor_docs.csv#line2`
- `N-MOS管 LN2312LT1G 5A SOT– 23 LRC` -> `doc:mainboard_d2_transistor_docs.csv#line3`
- `P-MOS管 PE537BA PDFN -33 NIKO-SEM` -> `doc:mainboard_d2_transistor_docs.csv#line4`

Verification:

```text
uv run pytest tests/test_cli_validator_ui.py::test_design_validator_ui_matches_mpq8626_power_family_with_public_docs \
  tests/test_cli_validator_ui.py::test_build_document_index_candidates_writes_review_csv \
  tests/documents/test_candidates.py tests/documents/test_matcher.py -q
9 passed

uv run pytest tests/report/test_validator_ui.py::test_render_project_workbench_includes_zero_profile_gap -q
1 passed

uv run pytest -q
485 passed, 7 deselected

uv run ruff check .
All checks passed!

git diff --check
clean
```
