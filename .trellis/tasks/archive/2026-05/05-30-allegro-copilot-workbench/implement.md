# Allegro-first Copilot workbench implementation plan

## Pre-Implementation Gate

Before editing product code, load `trellis-before-dev` for the relevant backend
scope and then start this task with `task.py start` after the user approves this
plan.

## Ordered Checklist

1. Dependency and contract setup
   - Add FastAPI/uvicorn dependencies.
   - Add shared chat/request/response data models.
   - Add `board_registry_from_design(design)` as the only new Allegro-to-Agent
     ingest adapter.
   - Do not change the Runner `session` / `registry: BoardRegistry` contract.

2. Shared workbench context
   - Extract the common `design-validator-ui` setup into a reusable context
     builder.
   - Preserve existing CLI behavior and output for no-AI static generation.
   - Build `validation_targets` from the same profile matching already used by
     `build_project_validation_index()`; do not re-infer profile matches from
     BOM/profile candidates in a second local algorithm.
   - Build a BoardRegistry shim and in-memory relational Session from the
     Allegro-derived Design for Runner/tools by calling `create_store(":memory:")`
     and existing `populate_from_registry(session, registry)`.

3. Runner workbench compatibility
   - Keep BoardRegistry + Session unchanged.
   - Add scoped workbench system prompt support.
   - Keep the existing five-tool manifest available in live mode.
   - Add tests that an Allegro `Design` can drive Runner through the shim.

4. Deterministic chat service
   - Implement a deterministic fake Anthropic-compatible client.
   - Ensure fake mode drives real Runner tool calls instead of bypassing Runner.
   - Design fake content blocks so they round-trip through Runner's
     `messages.append({"role": "assistant", "content": response.content})`
     loop; simple attribute objects with `.type`, `.text`, `.name`, `.input`,
     and `.id` are sufficient.
   - Cover selected-component validation questions, evidence questions, explain
     questions, and unknown-refdes questions.
   - Normalize every answer into `ChatResponse` with trace.
   - Trust Runner-sourced `RunResult.text` and `ToolCallTrace` as already
     sanitized. Explicitly sanitize chat-layer fallback text, suggestions, and
     snapshot-only copy before returning/rendering them.

5. Copilot panel renderer and assets
   - Add right-bottom floating button, right-side panel, suggestions, input,
     messages, loading state, typewriter rendering, and collapsed trace.
   - Integrate selected-refdes updates from existing component-row/card
     activation.
   - Keep responsive layout stable on desktop and mobile.

6. Static snapshot path
   - Add `design-validator-ui --ai-snapshot`.
   - Generate baked offline transcripts by running Runner with the fake model at
     HTML-generation time.
   - Verify a `file://`-opened page can answer supported offline questions.
   - Verify default `design-validator-ui` remains Copilot-free.

7. Live server path
   - Add `serve-workbench` command.
   - Create FastAPI app with `GET /`, optional `GET /api/workbench/state`, and
     `POST /api/workbench/chat`.
   - Implement `--fake-ai` path first.
   - Implement real Runner path with the existing five tools, validation targets,
     and optional vector collection.
   - Add model-env error handling for real mode.

8. Tests
   - `Design` -> `BoardRegistry` shim tests, including component and NC-pin
     projection.
   - Context-builder tests proving the relational store is populated through
     `populate_from_registry()` rather than a second row writer.
   - Validation-target extraction tests proving targets come from the same
     matching output that powers the project validation index.
   - Runner-on-Allegro-shim tests.
   - Fake-client round-trip tests proving the fake blocks can be consumed across
     at least two Runner iterations.
   - Chat service fake-mode tests proving real Runner tool calls and `U999`
     wrapping.
   - Chat-layer sanitization tests for fallback/suggestion text that does not
     originate from Runner.
   - Report renderer tests for panel presence/absence and trace markup.
   - CLI tests for `design-validator-ui --ai-snapshot` and `serve-workbench
     --fake-ai` construction without live API calls.

9. Manual/browser QA
   - Generate the main static demo:
     `uv run hardwise design-validator-ui tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --ai-snapshot --output /tmp/hardwise-copilot-snapshot.html`
   - Start fake live demo:
     `uv run hardwise serve-workbench tests/fixtures/allegro/mixed_controller_power_stage.net tests/fixtures/allegro/mixed_controller_power_stage_bom.csv --fake-ai --port 8765`
   - Use browser QA to verify the AI button, panel, selected-refdes context,
     suggestions, send flow, trace expansion, and no UI overlap.

10. Documentation follow-up commit
   - After feature tests pass, update README, README.zh-CN, CLAUDE.md,
     AGENTS.md, docs/architecture.md, docs/interview_qa.md, and docs/PLAN.md to
     describe the Allegro-first workbench + Copilot panel story.
   - Keep code and docs as separate commits.

## Verification Commands

Focused checks during implementation:

```bash
uv run pytest tests/ir/test_types.py -q
uv run pytest tests/agent/test_runner.py -q
uv run pytest tests/report/test_validator_ui.py -q
uv run pytest tests/test_cli_validator_ui.py -q
```

Final gate:

```bash
uv run pytest -q
uv run ruff check .
```

If dependencies change:

```bash
uv sync
```

## Stop-and-Ask Conditions

- The feature cannot preserve the no-AI `design-validator-ui` path.
- Refdes guard compatibility would require changing the BoardRegistry-backed
  guard contract instead of using the shim.
- Real-time mode would require browser-direct model calls or exposing model
  secrets to JavaScript.
- Supporting the requested UX would require token streaming, backend
  persistence, auth, or internal hardware data.
- Existing component validators need semantic rule changes rather than simple
  reuse.

## Rollback Points

- After steps 1-3: revert prompt/shim changes if existing KiCad ask/review tests
  regress.
- After step 5: keep the panel renderer isolated so static UI can drop the
  optional panel argument.
- After step 6: if live server work is too broad, ship snapshot mode and defer
  `serve-workbench`.
- After step 7: if real-model path is unstable, keep `--fake-ai` and snapshot
  paths while marking real mode experimental in docs.
