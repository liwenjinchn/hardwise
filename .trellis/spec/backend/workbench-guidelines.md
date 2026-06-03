# Workbench Copilot Guidelines

> Contracts for the Allegro-first validator workbench Copilot panel.

---

## Scenario: Offline Snapshot and Fake Live Chat

### 1. Scope / Trigger

Applies when changing `src/hardwise/workbench/*`,
`src/hardwise/report/copilot_panel*.py`, or the Copilot wiring in `cli.py`.

### 2. Signatures

- Static entrypoint:
  `design-validator-ui <netlist/pst> <bom> --ai-snapshot`
- Live entrypoint:
  `serve-workbench <netlist/pst> <bom> [--fake-ai] [--vector]`
- Live API:
  `POST /api/workbench/chat` with `ChatRequest`
- Service:
  `WorkbenchChatService.ask(request: ChatRequest) -> ChatResponse`

### 3. Contracts

- `ChatRequest.question` is browser text; `selected_refdes` may be absent or
  stale and must be normalized against the registry.
- `ChatResponse.answer` and `trace` are user-visible and must already be safe to
  render.
- `EvidenceTrace` already separates `tool`, `input`, `summary`, `status`,
  `evidence`, and `wrapped`. The Copilot panel should render these as separate
  fields; do not collapse them into a raw `input=... evidence=... wrapped=...`
  string.
- Runner-sourced text and traces are already sanitized by the Refdes Guard.
  Chat-layer fallback/suggestion/snapshot copy must be sanitized before embed or
  return.
- Snapshot mode may answer only audited precomputed questions plus explicit
  aliases such as the `U999` guard demo. Unsupported questions must use the
  embedded fallback response, not a nearby snapshot transcript.
- Fake mode must still drive real Runner tool calls. It may be deterministic,
  but it must not fabricate tool outputs in the chat layer.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Exact snapshot question | Return matching embedded `ChatResponse` |
| Unknown snapshot question | Return `__fallback__` boundary response |
| `U999` snapshot question variant | Return the audited unknown-refdes response |
| Datasheet question without vector store | Call `search_datasheet`, report unavailable, then fall back to validation/profile evidence |
| Unknown refdes in any answer/trace | Show the guard-wrapped token |
| Trace has evidence tokens | Render tokens as visible text chips near the trace row |
| Trace has wrapped refdes count | Render the `wrapped` count explicitly as guard evidence |

### 5. Good/Base/Bad Cases

- Good: `datasheet 里 U12 的关键限制是什么?` in fake mode produces
  `search_datasheet` plus `run_component_validation` traces and states that
  vector search is not configured.
- Good: A trace row separately shows tool/status, summary, evidence tokens,
  guard wraps, and JSON input.
- Base: `这个 U12 为什么是 ERROR/WARN?` produces a validation trace only.
- Bad: A random offline snapshot question returns the first component-validation
  transcript.
- Bad: The trace UI hides evidence inside one raw code string that users cannot
  scan field-by-field.

### 6. Tests Required

- Workbench chat fake-mode test for datasheet-unavailable fallback.
- Snapshot-response test proving the datasheet boundary answer is embedded.
- Renderer/asset regression proving static fallback returns `__fallback__`
  rather than selecting a non-matching transcript.
- CLI snapshot test asserting the generated HTML contains both
  `search_datasheet` and the unavailable-vector wording.
- Copilot asset/CLI tests assert the structured trace labels such as
  `Guard wraps` remain embedded and the old raw trace string does not return.

### 7. Wrong vs Correct

#### Wrong

```javascript
const key = Object.keys(snapshots).find((item) => item !== '__fallback__');
return snapshots[key];
```

#### Correct

```javascript
if (snapshots[question]) return snapshots[question];
return snapshots.__fallback__;
```

#### Wrong

```python
return _FakeToolUseBlock(name="run_component_validation", input={"refdes": refdes})
```

for every fake-mode question, including datasheet questions.

#### Correct

```python
if _needs_datasheet_search(question):
    return [
        _FakeToolUseBlock(name="search_datasheet", input={"query": question}),
        _FakeToolUseBlock(name="run_component_validation", input={"refdes": refdes}),
    ]
```

#### Wrong

```javascript
body.textContent = `input=${JSON.stringify(item.input)} evidence=${evidence}`;
```

#### Correct

```javascript
row.appendChild(traceField('Evidence', evidenceChips(item.evidence)));
row.appendChild(traceField('Guard wraps', String(item.wrapped || 0)));
row.appendChild(traceField('Input', inputBlock));
```

## Scenario: Document Coverage Provider

### 1. Scope / Trigger

Applies when exposing local public document-index coverage through the workbench
Copilot, Runner tools, or `serve-workbench` CLI.

### 2. Signatures

- Live entrypoint:
  `serve-workbench <netlist/pst> <bom> [--document-index docs.csv] [--fake-ai]`
- Runner tools:
  `get_component_documents(refdes, candidate_limit=5)`
  `summarize_document_coverage(limit=30, candidate_limit=3)`
- Source flow:
  `DocumentIndex -> DocumentMatchReport -> ProjectValidationIndex.component_groups -> Runner`

### 3. Contracts

- `--document-index` accepts only a local CSV/TSV public document index. It is
  not live web discovery, supplier lookup, PLM lookup, PDF download, or PDF fact
  extraction.
- Component document lookup returns `status` as one of `matched`, `no_result`,
  `ambiguous`, `manual_needed`, `not_found`, or `not_configured`.
- Summary lookup returns `status="configured"` with grouped coverage rows, or
  `status="not_configured"` when no index is loaded.
- A matched `title` / `url` / `doc:<file>#line<N>` token proves only that the
  local public index contains a reviewed document link for the BOM identity. It
  does not prove voltage, current, pinout, lifecycle, price, or availability.
- Configured document-provider results are L1 deterministic trace facts because
  they come from parsed local inputs. `EvidenceTrace.evidence` may still be
  empty for a gap-focused summary if the bounded rows contain no matched
  document candidates.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| No `--document-index` | Tool returns `status="not_configured"`; fake/live chat must not guess documents |
| Unknown refdes | Tool returns `status="not_found"` plus closest registry/group matches |
| One matching index row | Tool returns `status="matched"` with selected title/url/source token |
| Multiple matching rows | Tool returns `status="ambiguous"` with bounded candidates |
| Missing or unusable BOM identity | Tool returns `status="manual_needed"` with the matcher reason |
| Coverage summary asks for gaps | Return grouped `no_result` / `ambiguous` / `manual_needed` rows from component groups |

### 5. Good/Base/Bad Cases

- Good: `这个 U12 有公开资料吗?` in fake mode calls
  `get_component_documents` through the real Runner and says the match is
  coverage evidence, not an electrical spec claim.
- Good: `还有哪些 datasheet 缺口?` calls `summarize_document_coverage` and reports
  grouped counts from parsed BOM/index state.
- Base: Running without `--document-index` still starts the workbench; document
  questions return `not_configured`.
- Bad: Falling back from `not_configured` to model memory or a web search.
- Bad: Treating a matched document URL as proof that a component is electrically
  correct.

### 6. Tests Required

- Provider unit tests for matched, unknown-refdes, not-configured, and grouped
  summary paths.
- Workbench fake-mode tests proving document questions use the new Runner tools
  and answer with the coverage-vs-spec boundary.
- CLI dry-run test for `serve-workbench --document-index ... --fake-ai --dry-run`
  asserting document counts appear in stdout.

### 7. Wrong vs Correct

#### Wrong

```python
if user_asks_for_datasheet_gap:
    return "U12 probably has a datasheet online"
```

#### Correct

```python
if _needs_document_coverage(question):
    return _FakeToolUseBlock(
        name="get_component_documents",
        input={"refdes": refdes, "candidate_limit": 5},
    )
```
