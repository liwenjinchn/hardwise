# Document discovery provider - Design

## Boundary

Option B is a deterministic provider over existing document coverage. The
provider answers "what public document coverage is known for this component or
group?" It does not answer "what does the datasheet say?" unless a separate
datasheet-search/profile mechanism provides that evidence.

The source of truth remains the reviewed local document index supplied by the
user:

`DocumentIndex CSV/TSV -> match_documents_to_bom() -> DocumentMatchReport -> ProjectValidationIndex.component_groups -> workbench AI tools`

No live network lookup, supplier lookup, or hidden document fetch is part of
this task.

## Existing Contracts To Reuse

- `DocumentIndexEntry.source_token` provides `doc:<file>#line<N>` provenance
  for matched document-index rows.
- `DocumentMatchReport.counts_by_status` already provides matched/no-result/
  ambiguous/manual counts.
- `DocumentMatchReport.match_for_item(item)` resolves a BOM item group to its
  document match.
- `ProjectComponentGroup` already carries grouped coverage fields:
  `document_status`, `document_title`, `document_url`, `document_source`,
  `document_candidates`, and `document_reason`.
- `WorkbenchContext.document_report` already stores the optional document
  report; `WorkbenchContext.index.component_groups` is already built with
  document coverage when configured.

## Tool Surface

### `get_component_documents(refdes)`

Returns a discriminated result:

- `status="matched"` with component identity, BOM item key, selected document
  title/URL/source token, and group status.
- `status="ambiguous"` with bounded candidate titles/URLs/source tokens.
- `status="no_result"` when a BOM identity exists but no local document-index
  row matched.
- `status="manual_needed"` when the BOM identity is missing or unusable for
  document matching.
- `status="not_found"` with closest refdes matches when the component is not in
  the registry.
- `status="not_configured"` when no document index was loaded.

The lookup should join through existing BOM/component group data, not by
guessing from the raw model prompt. If a component maps to a BOM item with
multiple refdes, the response can include refdes count and a small sample.

### `summarize_document_coverage(limit=30)`

Returns:

- `status="configured"` with document index path, counts by status, and bounded
  grouped rows.
- `status="not_configured"` with a clear reason.

Grouped rows should be ordered for reviewer triage:

1. profile gaps with missing/ambiguous documents;
2. active/high-signal families before passives/mechanical rows;
3. larger refdes groups before one-off rows;
4. stable identity ordering as a final tie-breaker.

Each row should include identity, identity kind, family, profile status,
validation status, document status, reason, refdes count/sample, and selected
or candidate document summary.

## Integration

1. Add document-provider output models and helper functions in the agent/tool
   boundary, reusing existing document and component-group models.
2. Extend `TOOL_DEFINITIONS` with the new tool schemas.
3. Extend `Runner` with optional `document_report` and/or use the existing
   `project_index` once topology-tools work adds it. If this child starts
   before topology tools, pass the minimum required context explicitly.
4. Pass `context.document_report` and `context.index` from
   `WorkbenchChatService` into `Runner`.
5. Add `--document-index` to `serve-workbench`, matching static
   `design-validator-ui`.
6. Update `WORKBENCH_SYSTEM_PROMPT` so document coverage questions use document
   tools, while datasheet specification questions still use profile validation
   or vector datasheet search.
7. Extend fake workbench routing:
   - "公开资料", "document", "datasheet 缺口", "资料缺口" -> document tools.
   - selected refdes questions -> `get_component_documents`.
   - project coverage questions -> `summarize_document_coverage`.

## Trust Boundaries

- A document-provider match is coverage evidence: "this public document link is
  indexed for this BOM identity."
- It is not electrical evidence for voltage/current/pin claims.
- Refdes-shaped strings in answers and traces remain protected by the existing
  Refdes Guard.
- Document URLs/titles come only from the local public document index; unknown
  rows remain missing/ambiguous/manual.
- Without `--document-index`, the provider fails closed with `not_configured`.

## Compatibility

- Existing static `design-validator-ui --document-index` behavior should remain
  unchanged except for any new AI snapshot suggestion/trace rows.
- Existing document parser/matcher/candidate tests must continue to pass.
- Workbench runs without `--document-index` remain valid and show no document
  coverage tools as configured.

## Rollback

Rollback is local: remove the new document tool definitions, Runner dispatch
branches, prompt/fake-mode additions, and `serve-workbench --document-index`
wiring. No data migration is required.
