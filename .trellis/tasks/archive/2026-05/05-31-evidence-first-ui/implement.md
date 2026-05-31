# Evidence-first UI implementation plan

## Pre-Implementation Gate

Do not edit product code until the task is activated with `task.py start`.
Before implementation, load `trellis-before-dev` for backend/reporting specs.

## Ordered Checklist

1. [x] Renderer inventory
   - Re-read `validator_multi_ui_sections.py`,
     `component_validation_details.py`, `validator_project_ui.py`,
     `component_validation_markdown.py`, and `copilot_panel_assets.py`.
   - Re-read `workbench/chat.py` `EvidenceTrace` and existing trace tests.
   - Search for tests asserting exact trace/evidence text.

2. [x] Shared evidence/trust display helpers
   - Add report-only helpers for trust labels and HTML evidence chips if doing
     so avoids duplicated formatting.
   - Keep helpers pure and side-effect-free.
   - Do not add a new validation model or backend trust-tier schema.

3. [x] Validator detail evidence-first polish
   - Add visible `L1 deterministic` labels to deterministic pin/check sections
     or rows.
   - Render evidence tokens as text chips in HTML while preserving raw token
     text.
   - Keep topology path labels honest: schematic topology/display path only.

4. [x] Project gap/manual polish
   - Add visible `L3 manual` or equivalent coverage trust state for no-profile
     rows and gap groups.
   - Preserve existing text that no-profile rows are not converted into
     electrical judgements.

5. [x] Markdown parity
   - Keep markdown evidence tokens as inline code.
   - Add a small trust-tier line/table only if HTML trust labeling would
     otherwise create a meaningful information gap.

6. [x] Copilot trace polish
   - Update `COPILOT_STYLE` and `COPILOT_SCRIPT` to render trace fields as
     structured UI instead of one raw code string.
   - Keep snapshot fallback matching unchanged.
   - Keep wrapped-refdes count and evidence tokens visible.

7. [x] Tests
   - Update `tests/report/test_validator_ui.py` for trust labels and evidence
     chip/token text.
   - Update markdown tests if trust text is added there.
   - Update or add Copilot panel/CLI snapshot tests proving trace markup is
     structured and `U999` guard behavior remains visible.
   - Keep no-AI static path tests proving no Copilot UI is embedded by default.

8. [x] Verification
   - Run focused report/workbench tests first.
   - Run final project gates.

## Verification Commands

Focused checks:

```bash
uv run pytest tests/report/test_validator_ui.py -q
uv run pytest tests/report/test_component_validation_markdown.py -q
uv run pytest tests/workbench/test_chat.py -q
uv run pytest tests/test_cli_validator_ui.py -q
```

Final gate:

```bash
uv run pytest -q
uv run ruff check .
```

Optional artifact smoke:

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot \
  --output /tmp/hardwise-evidence-first-ui.html
```

## Stop-and-Ask Conditions

- A trust label would require changing validation status semantics.
- Evidence chips would require hiding or transforming source tokens so they are
  no longer copyable/searchable.
- Copilot trace polish would require changing Runner dispatch, adding tools, or
  changing fake-client behavior.
- No-profile rows would need electrical PASS/WARN/ERROR to satisfy a UI
  expectation.
- Any implementation would imply PCB layout, current direction, placement,
  routing, PLM, supplier, lifecycle, price, or availability scope.

## Follow-Up Tasks

- C3 coverage/profile loop: document-index candidates -> draft profile ->
  human review -> ready profile -> validation target.
- C5 grounded-LLM long tail: L2 claim schema, datasheet retrieval requirement,
  evidence downgrade path, and report trust labels backed by actual grounded
  claims.
