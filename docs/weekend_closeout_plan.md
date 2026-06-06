# Hardwise Weekend Closeout Plan

> Active handoff plan for the 2026-06-06 / 2026-06-07 closeout branch.
> This is an execution checklist, not a long-term product roadmap.

## Goal

Close Hardwise into a coherent resume/demo branch that can be continued from
another computer:

1. Add one generic high-coverage family slice: inductor + ferrite.
2. Add one low-risk MOSFET-profile completion slice: PE537BA P-MOS, only if
   public datasheet evidence is available.
3. Rerun real-board pressure-test summaries.
4. Update README/demo/product pages to reflect the latest measured capability.
5. Push the branch to GitHub for handoff.

The final story should stay:

> Hardwise is a trusted pre-Layout schematic-review workbench. It imports public
> schematic/netlist+BOM inputs, builds a registry-verified component/net table,
> runs deterministic family validators where evidence exists, leaves gaps as
> manual review, and lets Copilot explain tool-backed evidence without becoming
> the judge.

## Current Baseline

- Branch: `codex/mvp-review-workbench-scope`
- Main demo: small public/synthetic workbench remains the primary presentation.
- Real board imports: Switch/mainboard are pressure tests and coverage evidence,
  not the main public demo artifact.
- Do not commit huge generated HTML from real boards.
- Do not commit company-internal or non-public hardware data.
- Use public datasheets / public-safe reviewed profiles only.

Known measured pressure-test baseline:

| Input | Components | Validated | PASS | WARN | ERROR | Manual |
|---|---:|---:|---:|---:|---:|---:|
| Switch board | 4010 | 3738 | 3653 | 79 | 6 | 272 |
| Mainboard | 8180 | 6752 | 3906 | 2846 | 0 | 1428 |

Likely coverage movement from the two short slices:

| Slice | Switch expected manual reduction | Mainboard expected manual reduction | Why it matters |
|---|---:|---:|---|
| Generic inductor + ferrite | 56 rows | 84 rows | Biggest safe coverage gain; generic across boards. |
| PE537BA P-MOS profile | 0 rows | 11 rows | Shows one MOSFET validator handles new part profiles. |

## Workstream A - Generic Inductor + Ferrite

Implement this first.

Scope:

- Extend generic passive validation from resistor/capacitor to inductor/ferrite.
- Keep it evidence-honest:
  - two-terminal connectivity;
  - BOM value/package parse;
  - optional current/impedance token extraction when present;
  - no claim about ripple current, saturation margin, EMI sufficiency, or power
    topology unless schematic/profile evidence exists.
- Treat this as L1 deterministic only for simple facts visible in BOM/netlist.

Likely files:

- `src/hardwise/validation/generic_passive.py`
- `src/hardwise/validation/project_index.py`
- `src/hardwise/report/ui_terms.py`
- `tests/validation/test_generic_passive.py`
- `tests/test_cli_validator_ui.py` if project-level counts need locking

Acceptance:

- Generic inductor rows validate without per-MPN profile.
- Generic ferrite rows validate without per-MPN profile.
- Unsupported electrical claims remain absent or WARN/manual.
- Real-board rerun shows manual rows moved by roughly the expected amount.
- `uv run ruff check .` passes.
- `uv run pytest -q` passes.

Stop-and-ask / downscope:

- If an inductor/ferrite rule requires actual topology context to be meaningful,
  do not add it in this slice.
- If parsing Chinese BOM strings becomes messy, keep only connectivity/package
  plus conservative token extraction and document the limitation.

## Workstream B - PE537BA P-MOS Profile

Do this after Workstream A, if time remains and public evidence is available.

Scope:

- Add a reviewed public PE537BA datasheet profile.
- Reuse the existing MOSFET validator; do not add a board-specific rule.
- Support P-channel facts through the same Gate/Drain/Source and Vgs/Vds checks.
- Add document-index matching if the current mainboard pressure test needs it.

Likely files:

- `data/datasheet_profiles/pe537ba.json`
- `data/document_indexes/mainboard_d2_transistor_docs.csv`
- `tests/validation/test_mosfet.py`
- `tests/test_cli_validator_ui.py` if document matching/counts are locked

Acceptance:

- PE537BA matched rows use `recommended.topology_family: mosfet`.
- Mainboard pressure test moves the 11 PE537BA rows out of manual/no-result.
- The validator output remains WARN when static rail inference is impossible;
  it must not assume source is ground.
- Public evidence token is present for pinout and Vgs/Vds absolute maximum.

Stop-and-ask / downscope:

- If the datasheet cannot be verified from public sources quickly, skip this
  slice and keep PE537BA in the next-family plan.
- Do not invent ratings from search snippets or distributor tables.

## Workstream C - Real-Board Summary Artifact

Rerun the two pressure tests after Workstreams A/B.

Use local-only paths and keep outputs under `/tmp`:

```bash
uv run hardwise design-validator-ui <switch_allegro_dir> \
  --document-index data/document_indexes/power_v1_docs.csv \
  --output /tmp/hardwise-switch-closeout-workbench.html \
  --index-output /tmp/hardwise-switch-closeout-index.md \
  --index-json /tmp/hardwise-switch-closeout-index.json

uv run hardwise recommend-next-family /tmp/hardwise-switch-closeout-index.json \
  --output /tmp/hardwise-switch-closeout-next-family.md

uv run hardwise design-validator-ui <mainboard_allegro_dir> \
  --document-index data/document_indexes/mainboard_d2_transistor_docs.csv \
  --output /tmp/hardwise-mainboard-closeout-workbench.html \
  --index-output /tmp/hardwise-mainboard-closeout-index.md \
  --index-json /tmp/hardwise-mainboard-closeout-index.json

uv run hardwise recommend-next-family /tmp/hardwise-mainboard-closeout-index.json \
  --output /tmp/hardwise-mainboard-closeout-next-family.md
```

Commit only a small summary artifact or README facts, not the huge HTML/JSON
outputs and not local absolute input paths.

Summary should include:

- component count;
- BOM matched count;
- validated/manual count before vs after;
- PASS/WARN/ERROR count after;
- which family slice caused the change;
- top remaining gaps and why they are deferred.

## Workstream D - Documentation + Demo Closeout

After code and pressure-test results are stable, update the public-facing docs.

Primary docs:

- `README.md`
- `README.zh-CN.md`
- `docs/demo.md`
- `docs/demo.html`
- `docs/product-intro.html`
- `docs/index.html`
- `docs/mvp_definition.md`
- `docs/interview_qa.md`
- `docs/learning_log.md`

Narrative rules:

- Lead with trust architecture and pre-Layout review workflow, not coverage
  vanity metrics.
- Keep the small demo as the main presentation.
- Describe Switch/mainboard as pressure tests and coverage-planning evidence.
- Say L78 has the full ingest/retrieve/agent-citation smoke.
- Say other profiles are reviewed public profile evidence unless live retrieval
  has been separately smoked.
- Do not imply PLM, supplier lookup, online auto-download, layout review, or
  whole-board automatic correctness judgement are already done.

Demo page direction:

- Keep `docs/hardware-demo.html` as the primary offline Copilot workbench.
- Keep `docs/hardware-demo-review-queue.html` as vNext/product exploration unless
  the final README explicitly promotes it.
- Do not publish giant real-board HTML pages as the main demo.

## Workstream E - Documentation Inventory

Do this after the implementation/demo docs are updated, before final push.

Problem:

- The repo now contains several generations of docs:
  - early KiCad/question-answer framing;
  - Allegro/Cadence workbench framing;
  - AI agent/Copilot framing;
  - current pre-Layout review-queue framing;
  - historical planning and staged roadmap docs.
- Too many equally visible docs can confuse a reviewer or a future Codex session.

Goal:

- Make `README.md`, `README.zh-CN.md`, `docs/demo.md`, and
  `docs/product-intro.html` the public-facing entry path.
- Keep long-term architecture/decision records where they help.
- Move stale exploratory docs out of the reader's first path, or delete them if
  they no longer describe a reproducible current state.

Audit process:

1. List every file under `docs/` and classify it as one of:
   - `public_entry`: linked from README or GitHub Pages index.
   - `current_reference`: accurate current design/architecture/reference.
   - `historical_record`: useful history but not a public entry.
   - `stale_or_confusing`: obsolete, duplicate, or misleading.
2. For each `stale_or_confusing` doc, choose one action:
   - merge key facts into a current doc;
   - move to an archive folder with a dated note;
   - delete if it adds no durable value.
3. Update README/index links so the reader sees one coherent path.
4. Do not delete docs that are still linked by README, tests, GitHub Pages, or
   a reproducible command without first replacing the link.

Likely cleanup candidates to inspect carefully:

- Early product or midpoint review docs that predate the workbench framing.
- Duplicated HTML/Markdown pairs where only one is still linked.
- Large historical plan/spec docs under `docs/superpowers/`.
- Old review-queue exploration pages if they are not promoted as vNext material.

Acceptance:

- Add or update a small docs inventory table, either in this file or a dedicated
  `docs/docs_inventory.md`.
- README has one clear public demo path.
- A fresh Codex session can follow the handoff prompt below without reading the
  wrong historical docs first.
- No current reproducible command/document link is broken.

## New-Computer Continuation Prompt

After this branch is pushed, use this prompt on the new computer:

```text
请在这个 Hardwise 仓库继续周末收束任务。先不要随便读所有 docs，避免被旧文档误导。

请优先读取这些入口，按顺序：
1. AGENTS.md
2. docs/weekend_closeout_plan.md
3. README.md 和 README.zh-CN.md
4. docs/demo.md
5. docs/evidence_chain_audit.md

当前目标：
- 先实现 docs/weekend_closeout_plan.md 里的 Workstream A：generic inductor + ferrite validation。
- 然后如果公共证据足够，再做 Workstream B：PE537BA P-MOS profile。
- 每个实现后跑测试，再重跑 Switch/mainboard pressure-test summary。
- 不要提交巨大的真实板 HTML/JSON，不要提交本地绝对路径或非公开硬件数据。
- 小 demo 仍然是主展示；Switch/mainboard 只是压力测试和覆盖计划证据。
- 完成代码和数据后，按 Workstream D/E 更新 README/demo/展示页，并做 docs inventory，判断哪些文档合并、归档或删除。

请先汇报：
1. 当前 branch 和 git status；
2. 你从 docs/weekend_closeout_plan.md 读到的下一步；
3. 你准备修改的文件；
4. 你会如何验证。

确认后再开始实现。
```

## Verification Gate

Before saying the branch is ready:

```bash
uv run ruff check .
uv run pytest -q
git status --short
```

If frontend/demo pages changed:

- run a local HTTP server;
- screenshot desktop and mobile;
- check no obvious horizontal overflow;
- verify the AI/Copilot button remains visible where expected.

## GitHub Handoff

Use conventional commits and push the branch, not `main`:

```bash
git status --short --branch
git add <cohesive files>
git commit -m "docs(closeout): add weekend execution plan"
git push -u origin codex/mvp-review-workbench-scope
```

After implementation slices, prefer separate commits:

- `feat(validation): add generic inductor ferrite checks`
- `feat(validation): add pe537ba mosfet profile`
- `docs(demo): record closeout coverage results`

Do not push to `main` unless explicitly requested.

## Time Budget

| Block | Estimate | Exit condition |
|---|---:|---|
| Plan doc + branch handoff | 0.5-1 h | Plan committed and pushed. |
| Generic inductor/ferrite | 3-5 h | Tests pass; pressure-test delta measured. |
| PE537BA P-MOS | 1.5-3 h | Public evidence verified; 11 rows move or slice is deferred. |
| Real-board summary artifact | 1.5-3 h | Before/after counts recorded without huge committed files. |
| README/demo/page closeout | 3-5 h | Public story matches measured capability. |
| Final verification/push | 1-2 h | Ruff/pytest green; branch pushed. |

This is feasible in two days if Workstream A stays conservative and Workstream B
is skipped quickly when public evidence is not available.
