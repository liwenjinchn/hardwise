# Rolling Log Implementation Report

Date: 2026-06-12

## Summary

This pass audited `docs/rolling_log.md` against the current codebase, filled the
remaining low-risk implementation gap, and verified each roadmap area with tests
or CLI/browser workflow smoke checks.

New implementation shipped in this pass:

- KiCad schematic-side named-net extraction:
  `src/hardwise/adapters/kicad_schematic_nets.py`
- `BoardRegistry.schematic_nets` carrying `SchematicNetRecord` rows
- `inspect-kicad --schematic-net --check-net-names`, reusing
  `validation/net_naming.py` `NamingPolicy`
- Optional `inspect-kicad --naming-policy <yaml>` for stricter site policies
- Tests for schematic named-net parsing and CLI naming-policy warnings
- Optional Capture pin-table workbench intake via `--pin-table` and
  `pin_table_csv` upload
- R008/R009 pin-table findings mapped to registry-backed L1 review tasks without
  changing component validation PASS/WARN/ERROR totals
- Documentation updates in `docs/architecture.md`, `docs/faq.md`,
  `docs/learning_log.md`, and `docs/rolling_log.md`

## Plan Coverage

| Rolling-log area | Status | Evidence |
|---|---:|---|
| C0 Copilot workbench closeout | Implemented | `serve-workbench --fake-ai --dry-run`, `design-validator-ui --ai-snapshot`, Playwright e2e |
| C1 six-section report polish | Implemented | `component_validation_markdown.py` and `validator_multi_ui_sections.py` render model check, pin summary, connection path, compliance matrix, evidence details, final summary |
| C2 evidence-first UI | Implemented | validator UI evidence chips/trust labels/tool traces; workbench tests and browser smoke cover evidence columns and trace path |
| C3 coverage/profile loop | Implemented with human gate | document-index candidates, next-family advisory, `draft-datasheet-profile` `needs_review`; missing document correctly rejects draft |
| C4 deterministic family expansion | Implemented beyond one family | XL1509, EG2132, STM32G030, diode, MOSFET, BJT, connector, I2C, shift-register families present with tests |
| C5 grounded LLM long tail | Implemented at trace level | `tests/agent/test_runner.py` and `tests/agent/test_validation_bridge.py` prove L2 evidence gating and L1 non-override |
| C6 hosted shell | Not implemented | Intentionally remains outside local MVP; current work preserves local guard/tool contracts only |
| V2.8-V3.8 final validator roadmap | Implemented | CLI smoke covered report modes, document match, pin profiles, validation reports, single/batch UI, manifest targets, candidates, XL1509, EG2132 |
| KiCad R006 named-net bridge | Implemented in this pass | `inspect-kicad --schematic-net --check-net-names` on `.kicad_sch` names |
| KiCad R005 dangling/fanout topology | Not implemented | Still requires full schematic wire + endpoint topology parser; rolling log now keeps only this remaining staged work |
| Pin-table workbench intake | Implemented in this pass | Optional CLI/server/import pin-table path, R008/R009 L1 review tasks, unknown-refdes rejection tests |

## Verification Workflow

Core checks:

- `uv run pytest -q` → 666 passed, 7 deselected, 1 warning
- `uv run ruff check .` → all checks passed
- `npm run test:unit` → 51 passed
- `npm run build` → production workbench bundle built
- `npm run test:e2e` → 6 passed

Representative CLI smoke checks:

- V2.8: `report-allegro-bom --summary-only` →
  `/tmp/hardwise-goal-smoke/v28-summary.md`
- V2.9: `report-allegro-bom --document-index` →
  `/tmp/hardwise-goal-smoke/v29-doc-match.md`
- V3.0: `report-pin-profile data/datasheet_profiles/l78.json` →
  3 pins
- V3.1: `report-component-validation ... l78 ...` →
  PASS, PASS/WARN/ERROR=3/0/0
- V3.2: `report-validator-ui ... U1 l78 ...` →
  static HTML, selected U1 PASS
- V3.3: `report-component-validation ... xl1509 ...` →
  overall ERROR from component checks
- V3.4/V3.5/V3.7: `report-validator-ui-batch --targets-manifest ...` →
  validated U1/U12, issue-first batch UI
- V3.6: `suggest-validation-targets --matched-only` →
  matched target manifest
- V3.8: `report-component-validation ... eg2132 ...` →
  overall ERROR from gate-driver component checks
- C0: `serve-workbench --fake-ai --dry-run` and
  `design-validator-ui --ai-snapshot`
- C3/C4: `build-document-index-candidates`, `recommend-next-family`, and
  `draft-datasheet-profile`
- KiCad named-net bridge:
  `inspect-kicad data/projects/pic_programmer --schematic-net --check-net-names`
  → 19 named schematic nets, 0 naming warnings
- Pin-table workbench intake:
  `serve-workbench ... --fake-ai --dry-run --pin-table <csv>` reports loaded
  findings and rejected unknown refdes; `design-validator-ui ... --pin-table`
  writes a static artifact with the same context path

## Deviations From Plan

1. The C3/C4 downstream commands do not accept netlist/BOM directly. They consume
   a `design-validator-ui --index-json` sidecar. The verification workflow was
   adjusted to generate the index first.
2. `draft-datasheet-profile` correctly failed for identity `10k` because no
   matched public document was available. The successful draft smoke used a
   matched STM32 document-index row and produced `review_status=needs_review`.
3. KiCad R006 is implemented as an explicit named-net bridge, not a full
   schematic topology parser. This is deliberate: naming checks only need labels
   and power-symbol names, while R005 dangling/fanout checks need wire and pin
   endpoint topology.
4. C6 hosted shell remains unimplemented. The local MVP keeps server secrets out
   of the browser and preserves the same guard/ledger/tool contracts; hosted
   upload/login/persistence is still a separate product slice.
5. Pin-table findings ship as workbench `ReviewTask`s rather than
   `ValidationReport` rows. This keeps historical validation totals stable and
   treats the optional CSV as a separate deterministic evidence source.

## Remaining Risk

- KiCad named-net extraction is intentionally narrow. It catches explicit labels
  and power-symbol values, but it does not know whether a named net has zero,
  one, or many endpoints.
- Sentence-level specification-claim gating for C5 remains deferred, matching
  the existing DR-014 note. Current enforcement is trace-level plus Refdes Guard.
- Hosted shell behavior has no implementation or verification in this local-only
  workflow.
- Pin-table intake currently covers only R008/R009. NC-conflict, off-page-orphan,
  and pin-table-sourced net-naming checks remain staged follow-ons.
