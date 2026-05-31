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

### 5. Good/Base/Bad Cases

- Good: `datasheet 里 U12 的关键限制是什么?` in fake mode produces
  `search_datasheet` plus `run_component_validation` traces and states that
  vector search is not configured.
- Base: `这个 U12 为什么是 ERROR/WARN?` produces a validation trace only.
- Bad: A random offline snapshot question returns the first component-validation
  transcript.

### 6. Tests Required

- Workbench chat fake-mode test for datasheet-unavailable fallback.
- Snapshot-response test proving the datasheet boundary answer is embedded.
- Renderer/asset regression proving static fallback returns `__fallback__`
  rather than selecting a non-matching transcript.
- CLI snapshot test asserting the generated HTML contains both
  `search_datasheet` and the unavailable-vector wording.

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
