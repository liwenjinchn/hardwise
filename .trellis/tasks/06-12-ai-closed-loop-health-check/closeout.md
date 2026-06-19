# Closeout: AI Closed-Loop Health Check

Date: 2026-06-18

## Goal

Close the stale Trellis task metadata for the AI closed-loop health-check work
without moving or archiving the task directory.

## Implemented Fixes

- `6373756` landed the workbench health-check fixes, including Copilot answer
  trace placement, export/header polish, server prompt handling, and focused
  workbench tests.
- `221b265` landed the follow-up Trellis workflow/spec cleanup on top of the
  health-check branch and was the pre-closeout checkpoint for this branch.
- At that checkpoint, local `main`, `origin/main`, and
  `origin/codex/ai-closed-loop-health-check` all contained
  `221b265885c7ae3c0633b1a57f66efef8c7a76d3`.
- The U12 / XL1509 follow-up slice now proves the public PDF evidence chain
  without changing the deterministic U12 verdict: `xl1509.pdf` was ingested,
  queried, surfaced through workbench `search_datasheet` traces, and reconciled
  with the reviewed XL1509 profile evidence tokens.
- `43dddc57a3e3c5a2bfd96e94db1ede7155fa72ef` records the XL1509 evidence-chain
  profile and documentation update.
- Draft PR: https://github.com/liwenjinchn/hardwise/pull/4

## Verification Evidence

- `git status --short --branch`
  - Result: clean worktree at `codex/ai-closed-loop-health-check` before this
    closeout and XL1509 evidence-chain patch.
- `git rev-parse HEAD`
  - Result for the XL1509 evidence-chain commit:
    `43dddc57a3e3c5a2bfd96e94db1ede7155fa72ef`.
- `git branch --all --contains 221b265885c7ae3c0633b1a57f66efef8c7a76d3`
  - Result: local task branch, local `main`, `origin/main`, `origin/HEAD`, and
    `origin/codex/ai-closed-loop-health-check` contain the commit.
- `uv run pytest -q`
  - Result: 673 passed, 7 deselected, 1 warning.
- `uv run ruff check .`
  - Result: all checks passed.
- `npm --prefix frontend/workbench run test:unit`
  - Result: 3 test files passed, 60 tests passed.
- `npm --prefix frontend/workbench run build`
  - Result: Vite production bundle built successfully.
- `uv run hardwise verify-api`
  - Result: real Anthropic-format endpoint reachable via
    `https://ai.centos.hk`, model `claude-sonnet-4-6`.
- `uv run hardwise serve-workbench ... --fake-ai --dry-run --document-index ... --pin-table ...`
  - Result: 25 components, 22 validated rows, document index matched 4 groups,
    pin table loaded.
- `uv run hardwise design-validator-ui ... --ai-snapshot --document-index ...`
  - Result: wrote a static snapshot with 25 components, 22 validated rows,
    PASS/WARN/ERROR = 5/13/4, manual = 3.
- HTTP smoke against a fake workbench server:
  - `GET /api/workbench/state` returned HTTP 200 with 25 components, 22
    validated rows, 3 manual rows, and 41 review tasks.
  - `POST /api/workbench/chat` for `U8` returned HTTP 200 with a
    `locate_component_evidence` trace and no wrapped refdes.
  - `POST /api/workbench/chat` for `U999` returned HTTP 200, wrapped the
    unknown refdes as `⟨?U999⟩`, and traced `run_component_validation` as
    `not_found`.
- XL1509 / U12 public-PDF evidence chain:
  - `data/document_indexes/mixed_controller_power_stage_docs.csv` contains the
    approved XLSEMI PDF URL for `XL1509-12E1`.
  - `/tmp/xl1509.pdf` was verified as a 13-page public PDF with SHA-256
    `d0226589787aa1ec629f0a1365aec4e017799ae79594891fa48f7733b4c1ebc2`.
  - `uv run hardwise ingest-datasheet /tmp/xl1509.pdf --part-ref XL1509-12E1`
    created 38 chunks in a temporary Chroma directory.
  - `uv run hardwise query-datasheet "XL1509-12 output 12V feedback inductor 68uH 150uH"`
    returned page-level hits including `xl1509.pdf` p11, p7, p8, and p5.
  - `uv run hardwise query-datasheet "Schottky Diode Selection Table XL1509 1N5821"`
    returned page-level hits including `xl1509.pdf` p9.
  - `uv run hardwise serve-workbench ... --fake-ai --vector` plus two
    `POST /api/workbench/chat` calls for U12 returned HTTP 200 and L2
    `search_datasheet` trace evidence including `datasheet:xl1509.pdf#p11`
    and `datasheet:xl1509.pdf#p9`.
  - `uv run hardwise report-component-validation ... U12 ...` still reports
    `ERROR, PASS/WARN/ERROR=8/0/0`; the L1 inductor error is now tied to
    `datasheet:xl1509.pdf#p8`, and the freewheel-diode error is tied to
    `datasheet:xl1509.pdf#p9`.
  - Focused regression tests for XL1509 validation/reporting and workbench chat
    returned 17 passed.

## Completed Follow-up Slice

The highest-leverage evidence-chain follow-up was U12 / XL1509. It is the main
demo's canonical deterministic ERROR, has a direct approved public PDF URL in
`data/document_indexes/mixed_controller_power_stage_docs.csv`, and now has a
live retrieval smoke that corroborates the reviewed profile tokens for fixed
12 V output, inductor selection, Schottky freewheel diode selection, and the
12 V application topology.

Acceptance result for that follow-up:

- Public PDF saved outside git as `/tmp/xl1509.pdf`, matching the profile token
  filename.
- `ingest-datasheet` ran into a fresh temporary Chroma directory.
- `query-datasheet` confirmed page-level retrieval for fixed 12 V output,
  inductor selection, and Schottky freewheel diode selection.
- Workbench Copilot U12 datasheet-evidence questions with `--vector` produced
  L2 `search_datasheet` traces while the deterministic U12 ERROR remained
  unchanged.

## Remaining Risks

- This file records the closeout state; it does not re-run the product browser
  click-through screenshots for every SPA page.
- The original acceptance checklist in `prd.md` remains historical context; the
  task state is closed based on the landed commits and branch containment above.
- XL1509 / U12 uses a temporary `/tmp` PDF and Chroma store for proof; no
  vendor PDF or vector database is committed to git.
