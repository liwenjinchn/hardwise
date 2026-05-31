# Six-section report polish design

## Architecture Overview

This task deepens the presentation layer for existing deterministic validation
results. The source of truth remains unchanged:

```text
Design + DatasheetProfile
  -> validate_component_against_profile(...)
  -> ValidationReport
  -> validator_multi_ui / validator_project_ui / component_validation_markdown
```

The report layer may derive display-only topology paths from `Design.nets`, but
it must not write those paths back into `ValidationReport` or change validator
status decisions.

## Boundaries

### Validation Boundary

`src/hardwise/validation/*` verdict logic is out of scope. The implementation
may read `ValidationReport.pin_results`, `ValidationReport.component_checks`,
`Component.pins`, `Design.nets`, and profile evidence, but it must not change how
`PASS` / `WARN` / `ERROR` are produced or rolled up.

### Evidence Boundary

This task uses **Path A**: validated detail rendering loads and carries the
`DatasheetProfile` alongside `ValidationReport`.

Why this is required:

- `ValidationReport` carries per-pin and per-component-check evidence only.
- `DatasheetProfile` carries profile-level facts that make the report read like
  a datasheet review: `abs_max`, `recommended`, per-pin `limits`,
  `recommended_topology`, and the profile-level `evidence` mapping such as
  `recommended.inductor -> datasheet:xl1509.pdf#p9`.
- Rendering only `ValidationReport.evidence` would mostly repeat tokens already
  visible in the pin/compliance tables.

The evidence/details section should therefore render existing profile limits and
profile evidence tokens where available. If the profile does not carry a
thermal/package fact, the report should say that evidence is not available
rather than inventing thermal claims. Any future structured thermal schema
belongs in a separate evidence/profile task unless implementation proves it is
required for rendering existing data.

### LLM Boundary

No grounded-LLM path ships here. No new agent tool, Runner dispatch branch,
prompt tool count, or fake-client behavior should change in this task.

### No-profile Boundary

`Profile coverage gap` / no-profile rows remain coverage artifacts. They must not
receive electrical judgements in the detail panel, summary, or Copilot snapshot
because this task is only about validated rows.

## Proposed Module Changes

- `src/hardwise/report/validator_multi_ui_sections.py`
  - Add `pin_consistency(component, validation)`.
  - Add `evidence_details(validation, profile)` or an equivalent section that
    renders profile-level `abs_max`, `recommended`, pin limits/topology notes,
    and source tokens. Missing thermal/package facts must render as an explicit
    gap, not as inferred data.
  - Change `connectivity_table(...)` to accept enough context to derive a
    display path from `Component` + `Design`.
  - Keep helper functions private to the renderer.

- `src/hardwise/report/validator_multi_ui.py`
  - Extend `ValidatorUiResult` with
    `profile: DatasheetProfile | None = None` so detail rendering can access
    profile-level evidence. Keep it optional so existing tests/callers stay
    compatible while the project workbench and CLI paths can provide it.
  - Reorder `_detail_panel()` sections into the review-report sequence.
  - Pass `component` and `design` to section helpers.

- `src/hardwise/report/validator_project_ui.py`
  - When building `ValidatorUiResult` from `ProjectValidationRow`, load the
    profile for validated rows (`row.profile_path`) and pass it into the result.
    Preserve zero-profile behavior by never loading profiles for manual rows.

- `src/hardwise/report/component_validation_markdown.py`
  - Add markdown sections for pin consistency and evidence/details.
  - Accept `profile: DatasheetProfile | None = None` and render profile-level
    evidence when provided. Update CLI and UI download callers deliberately so
    markdown parity does not silently lag behind HTML.

- `src/hardwise/cli.py`
  - `report-component-validation` already loads `profile`; pass it to markdown
    rendering.

- `src/hardwise/report/validator_ui.py`
  - The single-component UI already receives a profile path and embeds a
    markdown download. Load/pass profile data for markdown parity if needed.

- Tests
  - Update renderer tests to assert new sections and path/evidence text.
  - Add or update CLI tests only for user-visible output changes.
  - Preserve no-profile/gap tests unchanged where possible.

## Connection Path Derivation

Connection paths are display hints, not proof of current direction or layout.
The helper should be conservative:

1. Start from the pin net name.
2. Prefer power/ground labels when the net name clearly identifies a rail.
3. Render a bounded list of neighboring refdes/pins from `Design.nets`.
4. End with the selected `REFDES-pin`.
5. If there are many neighbors, cap the list and indicate there are more.

Example shape:

```text
+24V -> C33.1 / C34.1 -> U12-1
```

If directionality is ambiguous, the UI should still present this as a schematic
connection path, not as current flow or PCB placement.

## Report Section Order

The "six-section" name refers to the canonical hardware-review report shape.
Supporting panels such as schematic topology and scope boundary can remain
separate. The canonical sections are:

1. Pin check summary.
2. Component basic information and model check.
3. Pin function and connectivity, including path.
4. Pin consistency.
5. Compliance checks, including component-level topology/peripheral checks.
6. Evidence / datasheet details and final summary.

Supporting panels:

- Schematic topology panel: full parsed net membership for deeper inspection.
- Scope boundary: unchanged schematic-side / no-PCB disclaimer.

The exact labels can remain Chinese in the product-like UI and English in
markdown, matching existing files.

## Compatibility

- Existing no-AI static project workbench remains Copilot-free unless the caller
  supplies `copilot_html`.
- Existing `ValidationReport` fixtures should still validate.
- Any added dataclass field must have a default to avoid breaking direct
  construction in tests.
- If profile loading for report rendering fails, the CLI should fail as it
  already would for invalid profiles rather than silently fabricating evidence.
- Project workbench profile loading is acceptable because only validated rows
  load profiles, and validated row counts are small relative to total component
  count.

## Risks and Mitigations

- Risk: path display looks like inferred electrical direction.
  - Mitigation: label as schematic path / topology path and keep scope boundary.
- Risk: thermal section overclaims missing facts.
  - Mitigation: render missing evidence explicitly; do not add unverified facts.
- Risk: presentation changes accidentally alter status counts.
  - Mitigation: tests should assert existing PASS/WARN/ERROR counts remain.
- Risk: profile loading in project UI adds overhead.
  - Mitigation: profiles are few for validated rows; keep loading local and
    optional, and avoid loading for manual rows.

## Rollback Shape

The change is isolated to report renderers and tests. If the report polish causes
regression pressure, keep pin consistency and evidence/details first, and defer
connection path heuristics to a follow-up.
