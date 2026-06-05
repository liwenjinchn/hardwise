# C1 six-section validation report polish

## Goal

Restructure the validator workbench detail panel into a clean **six numbered
top-level sections** that read like a hardware-review form, and add an explicit
evidence-gap marker for uncited numeric datasheet specs. This is a
presentation-layer follow-on to the completed `05-31-six-section-report-polish`
task, which established the section *content*; C1 establishes the section
*structure* and the gap signal.

Presentation-only: no validator verdicts, status rollups, profile matching, or
agent-tool behavior change.

## Context

`05-31-six-section-report-polish` added pin-consistency, connection-path, and
evidence/detail content but rendered ~10 section functions in a flat sequence
behind a two-tab (报告 / 原理图连接) layout. For interview demos the panel should
present as six obvious, ordered review sections, and profile facts that lack a
datasheet page token should say so rather than rendering a bare dash.

## Requirements

- Six numbered top-level `<section data-section=...>` blocks per validated
  component, in fixed order:
  1. 型号核对 (`model-check`) — basic info + BOM-vs-profile identity
  2. 引脚检查汇总 (`pin-summary`) — pin feed + pin consistency
  3. 连接路径 (`connection-path`) — connectivity table + schematic net grid
  4. 合规矩阵 (`compliance-matrix`) — all pin + component checks
  5. 证据详情 (`evidence-details`) — profile facts, tokens, gap markers
  6. 综合总结 (`final-summary`) — overall status, issues, scope boundary
- Remove the two-tab DOM (`data-detail-tab` / `data-detail-tab-panel`); fold
  topology into section 3 and scope into section 6.
- Evidence-gap chip (`evidence-gap`, "⚠ 无页码证据"): shown only for **numeric**
  `abs_max.*` / `recommended.*` facts with no covering evidence token. Coverage
  is exact-key OR first-segment grouping (`recommended.inductor` backs
  `recommended.inductor_min_uh`). Text descriptors (`topology_family=buck`) and
  facts covered by grouped tokens are never flagged. `sch:` / `rule:` / `doc:`
  tokens are legitimate sources.
- Markdown parity: `component_validation_markdown.py` uses the same numbered
  section order; tokens stay as inline code.
- Keep existing legacy section functions exported for backward compat.

## Acceptance Criteria

- [x] Each validated panel in `report-validator-ui-batch` /
      `design-validator-ui` output has exactly six `data-section` blocks in the
      fixed order above.
- [x] No `data-detail-tab` / `data-detail-tab-panel` DOM remains.
- [x] `mixed_controller_power_stage` still reports `25 components`,
      `validated=U1,U12,U3,U8`, `PASS/WARN/ERROR=1/0/3`.
- [x] U12 (`1N4007W`, `6.8 uH`), U3 (`MBRA210LT3G` … `below required 24 V`),
      U8 (`SWDIO/SWCLK` swap) hard errors still visible, verdicts unchanged.
- [x] Evidence-gap chip appears for genuinely-uncited numeric specs only
      (xl1509 `abs_max.vin`/`on_off`/`vin_max`/`vin_min`, stm32 `abs_max.vdd`);
      grouped-token facts (`inductor_min_uh`) are not flagged; eg2132 has zero
      false gaps.
- [x] `uv run pytest -q` and `uv run ruff check .` pass.

## Out of Scope

- Grounded-LLM review, new agent tools, Runner dispatch changes.
- Validator logic, new deterministic families, trust-tier data-model changes.
- New vendor PDFs or claimed thermal facts.
- Hosted shell, `.brd`/boardview/PCB/PLM/supplier scope.

## Notes

- Builds directly on `05-31-six-section-report-polish` (completed 2026-05-31).
- Gap-coverage heuristic lives in
  `report/component_validation_details.py:evidence_gap_chip` +
  `_fact_has_evidence`, unit-tested independently of HTML.
