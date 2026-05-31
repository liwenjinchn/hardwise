# C3 Coverage Profile Loop Analytics

## Goal

Turn the existing coverage/profile loop from "lists gaps" into "ranks what to
fix next" without changing deterministic validator verdicts.

## Context

C3 in `docs/rolling_log.md` expects:

- unready profile drafts are marked `needs_review` and excluded from automatic
  validation
- candidate generation prioritizes frequent, safety-relevant, likely
  deterministic-validator families
- public document indexes and public datasheets remain the only inputs
- the loop helps choose the next deterministic family without becoming supplier,
  lifecycle, PLM, price, availability, or PCB scope

The plumbing already exists:

- `DatasheetProfile.review_status` exists and defaults to `ready`
- `profile_candidates` excludes `needs_review` drafts
- `build-document-index-candidates`, `draft-datasheet-profile`, and
  `suggest-validation-targets` already exist

## Requirements

1. Harden `DatasheetProfile.review_status` to
   `Literal["ready", "needs_review"]` and write explicit `"ready"` status into
   bundled ready profiles.
2. Add per-candidate priority score and priority band to document-index
   candidates, with profile-gap rows sorted ahead of matched-profile document
   backfill rows.
3. Add a coverage analytics module that recommends which uncovered
   `suggested_family` to handle next, based on uncovered refdes count and
   family safety weight.
4. Add a `recommend-next-family` CLI command that renders Markdown advisory
   output.
5. Add a larger public Allegro fixture with covered anchors and uncovered active
   long-tail families.
6. Add unit and CLI tests for priority scoring, mixed-group uncovered counting,
   CSV output, Markdown output, and the new command.
7. Update `docs/interview_qa.md` with the new measured C3 fact after shipping.

## Non-Goals

- Do not change `validation/component.py` dispatch, any `validate_*` module, or
  `ValidationReport` / PASS-WARN-ERROR semantics.
- Do not auto-promote drafts, auto-validate new profiles, or introduce L2
  grounded-LLM claims.
- Do not key control flow by MPN.
- Do not use supplier, PLM, lifecycle, price, availability, PCB, vendor PDF, or
  private hardware data.
- Do not import the advisory family-to-validator map into dispatch.

## Acceptance Criteria

- `build-document-index-candidates` appends a `Priority` column and true
  profile gaps are sorted before matched-profile document backfill rows.
- `recommend-next-family` emits Markdown with advisory actions
  `try_existing_validator_profile` and `triage_for_new_validator`.
- Diode-family output covers LEDs/TVS/Schottky as `diode`; no separate `LED`
  family is introduced.
- Mixed component groups count only unmatched refdes as uncovered.
- Recommendation Markdown surfaces uncovered refdes impact, validator families
  to check, identity samples, and advisory action.
- No `PASS`, `WARN`, or `ERROR` tokens appear in the recommendation Markdown.
- `uv run pytest -q` and `uv run ruff check .` pass.

