# Real datasheet evidence chain

## Goal

Close `docs/PLAN.md` DR-011 Phase 2 by turning Hardwise's L78 datasheet provenance from a profile-only claim into a reproducible, independently checked evidence pair:

1. DS001 continues to cite the static, deterministic profile token (`datasheet:l78.pdf#p4`) for `abs_max.vin`, and
2. the real public L78 PDF is independently ingested through `pdfplumber -> Chroma`, where `search_datasheet` returns the same page for the absolute-maximum input-voltage fact.

This is credibility work, not feature expansion. The honest shipped story is: the profile's page-token claim is independently corroborated by a real public PDF ingest/query run; DS001 does not scrape arbitrary PDF text at runtime.

## Confirmed Facts

- `docs/PLAN.md` DR-011 defines Phase 2 as "Real datasheet evidence chain" and explicitly ranks it above adding more validation families.
- `data/datasheet_profiles/l78.json` already contains `abs_max.vin = 35.0` with `datasheet:l78.pdf#p4`.
- `src/hardwise/ir/profile.py` has a deterministic `extract_l78_profile()` that emits the L78 profile and validates the filename.
- `src/hardwise/ingest/pdf.py` extracts page-level PDF chunks and formats `datasheet:<filename>#p<page>` evidence tokens.
- `src/hardwise/store/vector.py` can upsert chunks into Chroma and query them.
- `src/hardwise/agent/tools.py` exposes `search_datasheet` against the vector store.
- `src/hardwise/checklist/checks/ds001_vin_abs_max.py` emits a DS001 finding whose evidence token comes from `profile.evidence["abs_max.vin"]`.
- `data/datasheets/` and `data/chroma/` are gitignored demo inputs/outputs, so the repository should not commit vendor PDFs or Chroma persistence.
- A current official ST public PDF URL is available at `https://www.st.com/resource/en/datasheet/CD00000444.pdf`.

## Requirements

- Use only public datasheet data. No company-internal hardware data, supplier portals, PLM data, or private PDFs.
- Prefer the existing L78 path because DS001 and the L78 profile already exist.
- Keep PDF and Chroma artifacts out of git; provide a reproducible CLI command path instead.
- Add or update automated coverage so Phase 2 is not only a manual demo. Keep fast tests hermetic; Chroma semantic query coverage remains `@pytest.mark.slow` because the default ONNX embedder may download model data on first run.
- Preserve existing evidence token shape: `datasheet:<filename>#p<page>`.
- Preserve existing tool discipline: search misses return structured empty results, never inferred datasheet facts.
- Update project-facing docs that record what was proven (`docs/interview_qa.md`, `docs/learning_log.md`, and likely the discharged plan audit trail).

## Acceptance Criteria

- [ ] A command path downloads or otherwise stages the official public L78 PDF as `data/datasheets/l78.pdf` without committing the PDF.
- [ ] `uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805 --extract-profile ...` succeeds and reports nonzero chunks.
- [ ] Before relying on profile tokens, a live smoke confirms the current official ST PDF still places the L78 35 V absolute-maximum input-voltage fact on page 4.
- [ ] `uv run hardwise query-datasheet "absolute maximum input voltage" ...` returns a hit from `l78.pdf` on page 4.
- [ ] `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component ...` produces a DS001 finding for `U3` citing `datasheet:l78.pdf#p4`. This review command intentionally does not need `--vector`; DS001 reads the structured profile, not Chroma.
- [ ] Fast automated tests cover the deterministic evidence-token contract without requiring a committed binary PDF, Chroma semantic ranking, or network during normal `pytest`.
- [ ] Slow automated coverage may exercise Chroma `query_chunks()` semantic ranking and should be marked `@pytest.mark.slow`, consistent with existing vector-store tests.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass.
- [ ] Documentation records the measured command/results and the boundary that public PDFs remain external demo inputs.

## Out of Scope

- New component families such as BJT or P-channel MOSFET.
- Automatic PDF download during ordinary tests.
- Live supplier search, PLM, pricing, availability, lifecycle, or private datasheet lookup.
- Changing the validation/profile architecture beyond the small hooks needed to make the evidence chain reproducible.
- Committing vendor PDF binaries or Chroma vector-store contents.
