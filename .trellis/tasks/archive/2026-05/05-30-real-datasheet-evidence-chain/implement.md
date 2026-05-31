# Implementation Plan

## Checklist

- [x] Extend fast/hermetic coverage: generate a tiny multi-page PDF, run `extract_chunks()`, and assert page numbers plus `datasheet:<file>#pN` token shape. Do not invoke Chroma query in the fast subset.
- [x] Extend or reuse existing DS001/profile tests so `abs_max.vin` remains tied to `datasheet:l78.pdf#p4`; do not bind acceptance to a specific DS001 severity.
- [x] Add or adjust slow vector coverage only if needed: `ingest_chunks() -> query_chunks()` semantic ranking belongs under `@pytest.mark.slow`, consistent with `tests/store/test_vector.py`.
- [x] Review README / architecture examples for stale `--part-ref U3` wording and update active examples to `--part-ref L7805` where they describe datasheet identity.
- [x] Run a live local smoke with the official ST PDF staged at `data/datasheets/l78.pdf`:
  - `curl -L https://www.st.com/resource/en/datasheet/CD00000444.pdf -o data/datasheets/l78.pdf`
  - Verify page 4 still contains the L78 35 V absolute-maximum input-voltage fact before trusting the profile token. The downloaded resource id is saved as `l78.pdf` because `extract_l78_profile()` intentionally filename-gates that deterministic extractor.
  - `uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805 --extract-profile --persist-dir <tmp-or-data/chroma>`
  - `uv run hardwise query-datasheet "absolute maximum input voltage" --persist-dir <same> --top-k 3`
  - `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --no-consolidate --output <tmp-report>`
- [x] Update `docs/interview_qa.md` with the measured Phase 2 evidence-chain result.
- [x] Add a `docs/learning_log.md` entry with Symptom / Root cause / Fix / Takeaway.
- [x] Add a discharged-plan audit entry to `docs/PLAN.md`.
- [x] Run `uv run pytest -q` and `uv run ruff check .`.

## Live Smoke Result

The official PDF was staged from `/Users/liwenjin/Downloads/CD00000444.pdf` to gitignored `data/datasheets/l78.pdf`. `extract_chunks()` confirmed page 4 contains the L78 absolute-maximum table with VI = 35 V for VO = 5 to 18 V. Real ingest/query succeeded:

```bash
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805 --extract-profile --persist-dir /tmp/hardwise-l78-chroma
# ingest: l78.pdf -> /tmp/hardwise-l78-chroma (157 chunks, part_ref=L7805)

uv run hardwise query-datasheet "absolute maximum input voltage" --persist-dir /tmp/hardwise-l78-chroma --top-k 3
# 1. [l78.pdf p4 part=L7805] ... Absolute maximum ratings ... VO= 5 to 18 V 35 ...
```

## Risky Files

- `src/hardwise/cli.py`: avoid unnecessary CLI churn; existing commands are probably enough.
- `src/hardwise/store/vector.py`: Chroma behavior can be slow or embedding-dependent, so keep code changes small.
- `docs/PLAN.md`: append audit trail; avoid rewriting permanent decision records unless the current facts require it.

## Stop-and-Ask Conditions

- The official ST PDF no longer has L78 absolute-maximum ratings on page 4.
- Chroma cannot run in the local environment after dependency sync.
- A correct fix would require committing vendor PDF binaries or generated vector stores.
- DS001 needs runtime RAG parsing rather than profile evidence to pass acceptance.

## Verification Commands

```bash
uv run pytest -q
uv run ruff check .
curl -L https://www.st.com/resource/en/datasheet/CD00000444.pdf -o data/datasheets/l78.pdf
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805 --extract-profile --persist-dir /tmp/hardwise-l78-chroma
uv run hardwise query-datasheet "absolute maximum input voltage" --persist-dir /tmp/hardwise-l78-chroma --top-k 3
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component --no-consolidate --output /tmp/hardwise-phase2-ds001.md
```
