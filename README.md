# Hardwise

[English](README.md) | [中文](README.zh-CN.md)

> A guardrailed design-validator workbench for public hardware projects: registry-verified refdes, evidence-gated findings, and a static project index / report workflow.

Hardwise is a two-week portfolio MVP for the **pre-layout design-validation** node in hardware R&D. It does not claim that an LLM can independently judge a complete hardware design. It proves a narrower and more important engineering loop: parse a public EDA project, build a component index, run deterministic validation rules, force every surfaced refdes through the parsed registry, attach evidence tokens to every finding, and let the agent answer schematic questions only through structured tools.

Architecture is inspired by [Wrench Board](https://github.com/Junkz3/wrench-board) (Anthropic *Build with Opus 4.7* hackathon, 2nd place, April 2026). Design ideas only, no code copied.

Built with AI assistance. All design decisions and final code are reviewed and owned by the author.

---

## Resume demo

If you only have 90 seconds, start here:

[![Hardwise product intro page screenshot](docs/assets/hardwise-product-intro-screenshot.png)](https://liwenjinchn.github.io/hardwise/product-intro.html)

GitHub shows HTML files as source. Use the screenshot above for a quick scan, or open the rendered GitHub Pages demos:

- **Product intro:** [https://liwenjinchn.github.io/hardwise/product-intro.html](https://liwenjinchn.github.io/hardwise/product-intro.html)
- **Hardware demo:** [https://liwenjinchn.github.io/hardwise/hardware-demo.html](https://liwenjinchn.github.io/hardwise/hardware-demo.html)
- **Technical snapshot:** [`docs/demo.html`](docs/demo.html)
- **Short read:** [`docs/demo.md`](docs/demo.md)
- **Reproduce locally:** `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component`

## What the MVP proves

Phase 4 is framed as one trust architecture across two public input tracks, not one board pretending to cover every command surface. The backbone is:

```text
Refdes Guard + Evidence Ledger + L1 deterministic validators + structured tools
```

The C3/C4 coverage loop is supporting evidence: C3 ranks profile gaps, and C4 moves selected groups from L3/manual rows into L1 deterministic rows. That proves the loop is repeatable, but the headline remains trust: the model is bounded by registry objects, evidence tokens, and tool returns.

The KiCad track proves the agent/review/evidence path:

```bash
$ uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component
report: reports/pic_programmer-YYYYMMDD.md (29 findings, 121 components reviewed)
store:  reports/pic_programmer.db (121 components, 77 NC pins)
```

On the public KiCad demo project `pic_programmer`, Hardwise runs deterministic schematic-review rules:

- R001: new-component candidate check
- R002: capacitor rated-voltage field completeness
- R003: NC-pin handling, with connector/socket aggregation
- DS001: L78 regulator Vin absolute-maximum evidence check

The current sample report has **29 findings**: 6 R002 capacitor-voltage-field findings, 22 R003 NC-pin findings after noise reduction, and one DS001 `U3` / L7805 finding that cites the reviewed profile token `datasheet:l78.pdf#p4`. DS001 stays `reviewer_to_confirm` because the current schematic path cannot infer the applied Vin rail; it does not guess. Each finding carries a source token; NC pins are coordinate-matched from KiCad `no_connect` markers rather than model-generated.

The L78 path also has a live retrieval smoke: `l78.pdf` is ingested into Chroma, `query-datasheet "absolute maximum input voltage"` returns `[l78.pdf p4 part=L7805]`, and `hardwise ask ... --vector` calls `search_datasheet` before citing page 4. See [`docs/evidence_chain_audit.md`](docs/evidence_chain_audit.md). Other C4 profile tokens are reviewed public profile evidence unless their PDFs have also been staged and queried.

The Allegro track proves the static project workbench:

```bash
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --output reports/controller-design-validator.html \
  --index-output reports/controller-design-validator-index.md \
  --index-json reports/controller-design-validator-index.json
```

That path auto-matches public datasheet profiles by BOM identity and writes a single static HTML workbench with a top summary, component list, validation section, and report detail. The current controller fixture reports **25 components, 4 validated targets, PASS/WARN/ERROR = 1/0/3, and 21 manual/no-profile rows**. U1/L7805 repeats the L78 evidence path in the workbench, while U12/XL1509, U3/EG2132, and U8/STM32G030 show deterministic topology/debug-interface errors. If a project has zero local profile matches, the same command still emits a coverage/gap workbench plus optional markdown / JSON index sidecars instead of inventing validation results.

The same Allegro workbench can render an optional Copilot panel. `design-validator-ui --ai-snapshot` bakes audited offline chat transcripts into the single HTML file (no server, no API key); `serve-workbench` runs a local FastAPI server whose `--fake-ai` mode drives the real agent loop with a deterministic fake client, and whose real mode talks to any Anthropic-format endpoint configured in `.env`. Every panel answer runs the same five-tool Runner and the same Refdes Guard, so an unknown refdes such as `U999` is wrapped as `⟨?U999⟩` rather than fabricated.

The public eval pack adds a wider smoke path:

```text
5 public repos / 6 component-bearing KiCad project directories
1707 parsed components
437 deterministic findings
0 project failures
10 empty KiCad directories skipped
0 unverified refdes wrapped
0 findings dropped for missing evidence
```

These are regression and reproducibility metrics, not expert gold-label accuracy claims.

## What it is

Hardwise is a design-validation assistant for the early hardware R&D node before PCB layout. It turns public EDA projects and public datasheets into review artifacts with two hard constraints:

1. Every reference designator shown to the user must come from the parsed EDA registry.
2. Every report finding must carry a source token such as `sch:<file>#<refdes>`, `datasheet:<pdf>#p<N>`, or `rule:<id>`.

It is designed around a practical anti-hallucination stance: first make the agent unable to invent board objects, then let it help organize review attention.

## What it is not

- Not a PCB layout, SI/PI, EMC, or thermal simulator
- Not a PLM or production BOM management system
- Not a Cadence/Allegro integration
- Not a board repair tool; Wrench Board is the reference project for that domain
- Not a production product; this is a portfolio MVP

All demo inputs are public. No company-internal hardware data is used.

## Core Proof

Hardwise's main claim is narrow: **the model is not allowed to invent board objects**. The MVP proves that claim with three live mechanisms:

| # | Mechanism | What it does | Status |
|---|-----------|--------------|--------|
| 1 | **Refdes Guard** | User-visible refdes-like tokens (`U1`, `R10`, `J5`) must hit the parsed EDA registry; unknowns are wrapped before output. | Live: `src/hardwise/guards/refdes.py` |
| 2 | **Evidence Ledger** | Findings without evidence tokens are dropped. No token, no claim. | Live: `src/hardwise/guards/evidence.py` |
| 3 | **Structured Tool Loop** | Agent answers through `list_components`, `get_component`, `get_nc_pins`, `search_datasheet`, and `run_component_validation`; unknown refdes/profile/design states return structured misses instead of fabricated facts. | Live: `src/hardwise/agent/runner.py`, `src/hardwise/agent/tools.py` |

Supporting mechanisms are present but secondary to the demo story: Sleep Consolidator records human-gated candidate rules, Tiered Model Routing keeps model IDs in env slots, and Prompt Caching has measured cache-read hits on the configured MiMo proxy. They are engineering completeness, not the core product claim.

## Quickstart

```bash
git clone <repo> hardwise
cd hardwise
uv sync
cp .env.example .env  # fill in ANTHROPIC_API_KEY for API-backed commands
```

The repository ships with a public KiCad sample under `data/projects/pic_programmer/`. Local inspect/review commands work after `uv sync`; API commands require `.env`.

### Review a schematic

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003,DS001 --report-style component
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html
```

Produces:

```text
report: reports/pic_programmer-YYYYMMDD.md   (29 findings, 121 components reviewed with DS001)
report: reports/pic_programmer-YYYYMMDD.html (28 finding R001/R002/R003 visual report with --format html)
store:  reports/pic_programmer.db            (121 components, 77 NC pins)
consolidator: 3 candidate rule(s) appended to memory/rules.md
trace:  reports/trace.jsonl                  (append-only run ledger)
```

### Ask the schematic through tools

```bash
uv run hardwise ask data/projects/pic_programmer "U4 has how many NC pins?"
uv run hardwise ask data/projects/pic_programmer "What is U999?"
```

The agent has five structured tools: `list_components`, `get_component`, `get_nc_pins`, `search_datasheet`, and `run_component_validation`. Unknown objects return structured misses such as `found=false` plus closest matches; validation without a loaded design or profile returns `not_configured` / `no_profile` instead of a fabricated verdict.

### Workbench with Copilot panel

```bash
# Offline single-file demo (no server, no API key):
uv run hardwise design-validator-ui \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --ai-snapshot --output reports/controller-workbench.html

# Local live server (deterministic fake model, no API key):
uv run hardwise serve-workbench \
  tests/fixtures/allegro/mixed_controller_power_stage.net \
  tests/fixtures/allegro/mixed_controller_power_stage_bom.csv \
  --fake-ai --port 8765
```

Both render the three-pane validator workbench plus a right-side Copilot panel. The offline snapshot bakes audited chat transcripts into the HTML; the live server exposes `POST /api/workbench/chat`. `--fake-ai` drives the real agent loop (real tools, real Refdes Guard) without an API key; drop it and set `.env` to use a live Anthropic-format model. Every answer carries a collapsed evidence/tool trace, and unverified refdes are wrapped before display.

### Datasheet ingest and semantic search

```bash
# Drop a public datasheet into data/datasheets/ first.
# For the ST resource URL, save CD00000444.pdf locally as l78.pdf.
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref L7805
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3

# After ingesting relevant public datasheets:
uv run hardwise review data/projects/pic_programmer --rules R003 --vector
```

Datasheet chunks carry provenance such as `[l78.pdf p4 part=L7805]`, which independently corroborates structured profile tokens such as `datasheet:l78.pdf#p4`. Rules such as DS001 read the reviewed profile JSON; they do not scrape Chroma text during `review`.

Current evidence-chain boundary: only the L78 datasheet is staged locally and smoke-tested through `ingest -> retrieve -> agent citation`. The remaining profile JSON files are reviewed deterministic inputs, not proof that every profile fact was retrieved live from Chroma.

### Run the eval pack

```bash
uv run hardwise eval --download
uv run hardwise eval --limit-projects 1
```

Outputs:

- `reports/eval/eval-summary.json`
- `reports/eval/eval-summary.html`

The eval gate is intentionally narrow for the MVP: fail on parser/project failures, new unverified refdes wrapping, or newly dropped evidence-less findings. Finding-count changes are reported as observations because useful rule changes can legitimately add or remove findings.

### Use PostgreSQL instead of SQLite

The relational store uses SQLAlchemy 2.0. Default is SQLite (`reports/<project>.db`); set `HARDWISE_DB_URL` for PostgreSQL or MySQL.

```bash
uv sync --extra postgres
export HARDWISE_DB_URL="postgresql+psycopg2://$USER@localhost:5432/hardwise"
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
```

## Prompt cache verification

`hardwise ask` reports token accounting from the Anthropic-format `usage` object.

Latest live cold-start probe on 2026-05-16 used the configured MiMo Anthropic-format proxy (`mimo-v2.5`) with a unique cacheable system prompt:

| Run | Input/output tokens | Cache create/read | Result |
|---|---:|---:|---|
| 1 | 5445 / 16 | `null` / `null` | cold prompt billed as normal input |
| 2 | 5 / 16 | `null` / **5440** | same prompt immediately hit cache |

MiMo demonstrably serves cached prompt reads (`cache_read_input_tokens` nonzero), but this endpoint currently leaves `cache_creation_input_tokens` null. Strict creation-accounting verification needs another Anthropic-format endpoint that exposes that field.

## Architecture

See [`docs/architecture.md`](docs/architecture.md). The EDA boundary uses an adapter pattern (`src/hardwise/adapters/`), so a future Cadence/Allegro path is one new adapter rather than a rewrite.

## MVP Boundary

Current MVP status:

| Slice | Status | Highlights |
|---|---|---|
| 0 — Frame | Done | Review-node profile, sprint plan, JD alignment |
| 1 — R001 + Guards | Done | Finding model, Refdes Guard, Evidence Ledger |
| 2 — R002 + Consolidator | Done | Capacitor-voltage-field check, candidate-rule memory |
| 3 — R003 + Dual Store + Router | Done | NC-pin parser, SQLite/Chroma, datasheet ingest, tiered routing |
| 4 — Agent Loop + Prompt Caching | Done | `hardwise ask`, structured tools, live prompt-cache read hit |
| 5 — Submission Closeout | Done | Phase 4 two-track demo narrative, README/demo/JD/interview closeout, final artifacts |
| Workbench — Allegro Copilot | Done | `serve-workbench` live agent loop + `design-validator-ui --ai-snapshot` offline; reuses the five-tool Runner + Refdes Guard |

The MVP intentionally stops here. R004/R005-style net-aware checks, a schematic-side net parser, a human-labeled calibration set, GitHub Action packaging, and Cadence/Allegro adapters are explicitly post-MVP. The current submission story is not "more rules"; it is a constrained design-validation workbench with registry-verified objects and evidence-gated findings.

## Interview Q&A

See [`docs/interview_qa.md`](docs/interview_qa.md) for concise answers to the six questions this project is meant to withstand in interview.

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgements

- [Wrench Board](https://github.com/Junkz3/wrench-board) for architectural inspiration.
- KiCad open-source ECAD project for public sample inputs.
- Anthropic for the Anthropic-format API protocol and Python SDK.
- MiMo (Xiaomi) for the `mimo-v2.5` upstream used through an Anthropic-compatible proxy.
