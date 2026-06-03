# Document discovery provider

## Goal

Plan option B for document discovery: expose the existing public document-index
matching state to the workbench AI as a deterministic provider, so the user can
ask which public datasheets/documents are known, ambiguous, missing, or still
manual for a component or grouped BOM identity.

This is a provider over already-supplied public document evidence. It is not a
live web search, supplier lookup, PLM integration, or PDF fact-extraction task.

## Confirmed Facts

- This task is a child of
  `06-03-allegro-ai-topology-document-discovery` and is still in `planning`.
- Existing code already supports local CSV/TSV document indexes via
  `parse_document_index(path)`.
- Existing code already matches a parsed BOM to that local index via
  `match_documents_to_bom(bom, index)`, producing a `DocumentMatchReport` with
  `matched`, `no_result`, `ambiguous`, and `manual_needed` statuses.
- `build_workbench_context(..., document_index=...)` already accepts an
  optional document index and stores the resulting `DocumentMatchReport` on
  `WorkbenchContext.document_report`.
- `ProjectValidationIndex.component_groups` already carries document coverage
  fields (`document_status`, title, URL, source token, candidates, and reason)
  when a document report is present.
- `design-validator-ui` already has a `--document-index` option and prints
  document-match counts.
- `serve-workbench` does not currently expose `--document-index`, so live chat
  cannot load document coverage through the CLI path yet.
- Current agent tools include component lookup, NC pins, datasheet vector
  search, and deterministic component validation, but no first-class document
  coverage tool.
- Hardwise project rules require public inputs only. A document provider must
  never read company-internal hardware data or perform hidden supplier/PLM
  lookup.

## Requirements

1. Add a deterministic document-discovery provider that reads only existing
   `DocumentMatchReport` / `ProjectValidationIndex.component_groups` state.
2. Expose provider output through structured Pydantic tool results with
   explicit status fields and bounded candidate lists.
3. Support at least two user questions in the existing workbench AI panel:
   - "这个器件有没有匹配到公开资料?"
   - "哪些器件组还缺 datasheet/document?"
4. Add or wire a workbench chat tool surface such as:
   - `get_component_documents(refdes)` for the selected component's BOM identity
     and document match state.
   - `summarize_document_coverage(limit=...)` for grouped matched/missing/
     ambiguous/manual document coverage.
5. Unknown refdes must return a structured miss with closest matches; tools
   must not fabricate component IDs, document titles, URLs, or MPNs.
6. When no document index is configured, the provider must return
   `status="not_configured"` with a clear reason instead of falling back to
   model guesses.
7. `serve-workbench` should accept the same public `--document-index` input as
   `design-validator-ui`, so fake/live chat can exercise the provider from the
   same deterministic context.
8. The workbench system prompt must tell the model to use document provider
   tools for document-coverage questions, and to distinguish document coverage
   from datasheet fact retrieval.
9. Fake/snapshot chat must be extended enough for tests and offline demo
   answers to exercise the document provider without a live model or API key.
10. All document-provider answers must keep the trust boundary explicit:
    a matched URL/title proves that a public document link was reviewed/indexed;
    it does not prove any electrical specification unless a separate L1 profile
    or L2 datasheet-search fact supports that claim.

## Acceptance Criteria

- [ ] `prd.md`, `design.md`, and `implement.md` describe option B and are
      reviewable before `task.py start`.
- [ ] A fake or live workbench chat question such as "这个 U8 有公开资料吗?"
      calls a document-provider tool when a public `--document-index` is
      configured.
- [ ] A question such as "还有哪些 datasheet 缺口?" returns grouped document
      coverage from parsed BOM/index state, not free-form model memory.
- [ ] Running the workbench without a document index returns structured
      `not_configured` document-tool results; it does not invent document
      candidates.
- [ ] Unknown refdes returns structured miss data with closest matches and
      preserves existing Refdes Guard behavior.
- [ ] Existing document parser/matcher tests continue to pass.
- [ ] New tests cover configured and not-configured document-provider paths,
      plus at least one Runner-backed fake workbench chat path.
- [ ] `uv run pytest -q` and `uv run ruff check .` pass before implementation
      is declared complete.

## Out Of Scope

- Live internet datasheet search or download.
- Supplier, PLM, lifecycle, pricing, stock, or availability lookup.
- PDF text extraction, semantic retrieval, or LLM fact extraction.
- New datasheet profiles or new family validators.
- Treating document match status as PASS/WARN/ERROR electrical validation.
- Reading or embedding non-public hardware data.
- KiCad schematic-side document discovery.
- Boardview, `.brd`, placement, routing, simulation, or post-layout evidence.

## Decisions

- Option B means "deterministic local provider over reviewed/public document
  index state." It does not mean automatic discovery from the web.
- Provider output should reuse `DocumentMatchReport` and
  `ProjectValidationIndex.component_groups` rather than inventing a second
  document-coverage store.
- Live workbench mode should gain `--document-index` for parity with static
  workbench mode.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
