# Hardwise

> AI Agent embedded in the **schematic review** node of hardware R&D — **anti-hallucination by design**, **provenance-first**, **memory-consolidating**.

> Architecture inspired by [Wrench Board](https://github.com/Junkz3/wrench-board) (Anthropic *Build with Opus 4.7* hackathon, 2nd place, April 2026). No code copied; design ideas only. Wrench Board is for board-level *repair*; Hardwise is for hardware *design review* — different domain, same agent-engineering primitives.

> Built with AI assistance. All design decisions and final code reviewed and owned by the author.

---

## Resume demo

If you only have 90 seconds, start here:

- **Product intro:** [`docs/product-intro.html`](docs/product-intro.html) — polished Chinese landing page for resume reviewers.
- **Visual demo:** [`docs/hardware-demo.html`](docs/hardware-demo.html) — Chinese one-page view for hardware reviewers.
- **Technical snapshot:** [`docs/demo.html`](docs/demo.html) — one-page snapshot of the review output and engineering mechanisms.
- **Short read:** [`docs/demo.md`](docs/demo.md) — what the demo proves, in resume-reviewer language.
- **Reproduce locally:** `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html`

## At a glance

```bash
$ uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
report: reports/pic_programmer-20260512.md (84 findings, 121 components reviewed)
store:  reports/pic_programmer.db (121 components, 77 NC pins)
consolidator: 2 candidate rule(s) appended to memory/rules.md
```

Three rules running over the public KiCad demo `pic_programmer`: 7 R002 cap-voltage findings (6 medium for missing `/V` suffix, 1 info on `22uF/25V`) + 77 R003 NC-pin findings (J1 DB9 + U4/LT1373 + 71 PIC-socket pins). Every finding carries a `sch:<file>#<refdes>` evidence token; refdes are coordinate-matched from `no_connect` markers, never model-generated. The Sleep Consolidator emits 2 candidate rules to `memory/rules.md` for human review.

## What it is

Hardwise is an AI Agent for the schematic review node of hardware R&D. It reads a KiCad project and relevant datasheet PDFs, then produces a review report where every conclusion carries a source token (`sch:` / `datasheet:` / `rule:`) and every reference designator is verified against the parsed board, never fabricated.

It compresses the slow link of "翻 datasheet → 对位号 → 写报告" into a tool-use loop with two anti-hallucination guards and a memory consolidation loop.

> A note on BOM: schematic review happens *before* PCB layout, so the only "BOM" available at this node is the refdes list exported from the schematic — not a PLM-grade BOM with manufacturer part numbers, supplier lifecycle, etc. That BOM appears later in the flow (post-Gerber) and is out of scope. See [`docs/review_node.md`](docs/review_node.md) for the input-data contract at the review node.

## What it isn't

- Not a PCB layout / EMC simulator
- Not a PLM / BOM management system
- Not a board repair tool (that's Wrench Board's domain)
- Not a complete product. This is a **2-week MVP** built for portfolio + interview, not production.

## Why

Initial schematic review on a real board takes a hardware engineer 1–2 days, mostly information shuffling: cross-checking refdes against datasheets, walking pin lists, writing the review note. The judgment work — *is this design correct?* — is a small fraction. Hardwise automates the shuffle so the human spends time judging, not searching.

## Five mechanisms

| # | Mechanism | What it does | Status |
|---|-----------|--------------|--------|
| 1 | **Refdes Guard** | Output refdes (U1, R10, J5...) must hit the EDA registry. Unverified tokens are wrapped before reaching the user. | ✅ live (`src/hardwise/guards/refdes.py`) |
| 2 | **Evidence Ledger** | Every claim carries a source token: `sch:<file>#<refdes>` / `datasheet:<pdf>#p<N>` / `rule:R001` etc. No token, no claim. | ✅ live (`src/hardwise/guards/evidence.py`) |
| 3 | **Sleep Consolidator** | Each review session deposits *candidate* rules to `memory/rules.md`. Human gate before any rule activates. | ✅ live (`src/hardwise/memory/consolidator.py`) |
| 4 | **Tiered Model Routing** | Three runtime slots (`fast` / `normal` / `deep`) read from env vars; agent code never hard-codes a model id. | ✅ live (`src/hardwise/agent/router.py`) |
| 5 | **Prompt Caching** | Static agent prompt is cache-controlled; live `ask` runs report nonzero `cache_read_input_tokens`; current MiMo proxy does not expose nonzero `cache_creation_input_tokens`. | ✅ live (`src/hardwise/agent/prompts.py` + `runner.py`) |

Mechanisms 1, 2, 4 are direct architectural borrows from Wrench Board's "defense in depth, two layers" + tiered runtime. Mechanism 3 is a scope-shrunk cousin of Wrench Board's `microsolder-evolve` overnight loops — they auto-commit patches against an oracle benchmark; we sediment review feedback into human-gated rule candidates. Same direction, MVP-fit scope.

## Data & compliance

- All demo input is **public**: KiCad demo projects and publicly available datasheets.
- **No company-internal hardware data** is used in this project, ever.
- The author is a working hardware engineer; this project is a personal portfolio MVP and does not touch employer IP.

## Quickstart

```bash
git clone <repo> hardwise
cd hardwise
uv sync
cp .env.example .env  # then fill in ANTHROPIC_API_KEY
```

The repo ships with a public KiCad sample under `data/projects/pic_programmer/`
(KiCad official demo). Local review / inspect commands work after `uv sync`; API commands require `.env`, and datasheet search requires a public PDF you add locally.

### Review a schematic

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html
# After ingesting public datasheets for the relevant parts:
uv run hardwise review data/projects/pic_programmer --rules R003 --vector
```

Produces four artifacts:

```
report: reports/pic_programmer-YYYYMMDD.md   (84 findings, 121 components reviewed)
report: reports/pic_programmer-YYYYMMDD.html (same data, Chinese visual report when --format html)
store:  reports/pic_programmer.db            (121 components, 77 NC pins)
memory: memory/rules.md                      (2 candidate rule(s) appended)
trace:  reports/trace.jsonl                  (append-only machine-readable run ledger)
```

Each finding carries `evidence_tokens` like `sch:pic_programmer.kicad_sch#J1`
that resolve back to the parsed board. Unverified refdes are wrapped as
`⟨?Xnnn⟩` before the report is written; findings with no evidence are dropped.
Markdown is the default output for diffable archives; HTML is a self-contained
Chinese report tuned for hardware-review reading: severity chips, refdes/net
chips, collapsible rule groups, and evidence-token blocks.

### Datasheet ingest + semantic search

```bash
# Drop a public datasheet into data/datasheets/ first (see data/datasheets/README.md)
uv run hardwise ingest-datasheet data/datasheets/l78.pdf --part-ref U3
uv run hardwise query-datasheet "absolute maximum input voltage" --top-k 3
```

Returns chunks with `[<pdf> p<N> part=<refdes>]` provenance — the building
block for `datasheet:<pdf>#p<N>` evidence tokens. Add `--vector` to `review`
after ingesting relevant public datasheets to attach R003 `evidence_chain` and
`decision` fields.

### Use PostgreSQL instead of SQLite

The relational store goes through SQLAlchemy 2.0, so any backend with a
SQLAlchemy driver works. Default is SQLite (`reports/<project>.db`); set
`HARDWISE_DB_URL` to override.

```bash
# 1. install the Postgres driver (optional dep group)
uv sync --extra postgres

# 2a. start Postgres via Homebrew (Mac, no Docker needed)
brew install postgresql@16
brew services start postgresql@16
createdb hardwise
export HARDWISE_DB_URL="postgresql+psycopg2://$USER@localhost:5432/hardwise"

# 2b. ...or via Docker (cross-platform)
# docker run -d --name hardwise-pg \
#   -e POSTGRES_PASSWORD=hardwise -e POSTGRES_DB=hardwise \
#   -p 5432:5432 postgres:16
# export HARDWISE_DB_URL="postgresql+psycopg2://postgres:hardwise@localhost:5432/hardwise"

# 3. re-run review against PG
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
# store: postgresql+psycopg2://... (121 components, 77 NC pins)

# 4. verify directly with psql
psql -d hardwise -c "SELECT COUNT(*) FROM components; SELECT COUNT(*) FROM nc_pins;"
# 121, 77
```

MySQL works the same way — install `pymysql` and set `HARDWISE_DB_URL=mysql+pymysql://...`.

### Other commands

```bash
uv run hardwise hello                                           # install smoke test
uv run hardwise verify-api --tier normal                        # tiered router
uv run hardwise inspect-kicad data/projects/pic_programmer      # registry dump
```

### Prompt cache verification

`hardwise ask` reports token accounting from the Anthropic-format `usage`
object, including `cache_creation_input_tokens` and
`cache_read_input_tokens` when the upstream returns them.

Latest live cold-start probe on 2026-05-16 used the configured MiMo
Anthropic-format proxy (`mimo-v2.5`) with a unique cacheable system prompt:

| Run | Input/output tokens | cache create/read | Result |
|---|---:|---:|---|
| 1 | 5445 / 16 | `null` / `null` | cold prompt billed as normal input |
| 2 | 5 / 16 | `null` / **5440** | same prompt immediately hit cache |

Conclusion: MiMo demonstrably serves cached prompt reads (`cache_read_input_tokens`
nonzero), but this endpoint currently leaves `cache_creation_input_tokens` null
instead of reporting a nonzero write count. A strict "creation nonzero, then read
hit" audit needs the same probe against Anthropic's official API or another
Anthropic-compatible endpoint that exposes creation accounting.

## Architecture

See [`docs/architecture.md`](docs/architecture.md). Adapter pattern at the EDA boundary (`src/hardwise/adapters/`) means a future Cadence/Allegro adapter is one new file, not a rewrite.

## Roadmap

The 2-week MVP is sliced vertically — each slice ends in a runnable demo. See [`docs/PLAN.md`](docs/PLAN.md) for the full plan + decision records.

| Slice | Status | Highlights |
|---|---|---|
| 0 — Frame | ✅ | Sprint plan, decision records, review-node profile, JD alignment table |
| 1 — R001 + Guards | ✅ | New-component candidate check; Refdes Guard + Evidence Ledger; markdown report aligned to《SCH_review_feedback_list 汇总表》 |
| 2 — R002 + Consolidator | ✅ | Cap rated-voltage field check; Sleep Consolidator with human gate |
| 3 — R003 + Dual store + Router | ✅ | NC pin handling (coordinate-matched 77 NC pins); SQLite + Chroma live; PDF ingest + semantic search; tiered ModelRouter |
| 4 — Agent loop + Prompt caching | ✅ | `hardwise ask` command; tool-use loop with 4 tools; cache hit measured on live API |
| 5 — Submission closeout | ⏳ | README/GitHub hygiene, resume bullet, final interview answers |
| 6 — Follow-up polish | ⏳ | 3-min screencast, stronger report polish, schematic-side net parser exploration |

Beyond MVP: Cadence/Allegro adapter (one new file, not a rewrite), evaluation set for the consolidator's promotion gate, EMC/DFM rule packs.

## Interview Q&A

[`docs/interview_qa.md`](docs/interview_qa.md) — six questions the project must be able to answer in 80 字 each.

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgements

- [Wrench Board](https://github.com/Junkz3/wrench-board) — architectural inspiration. Read their README; it's worth your time.
- KiCad open-source ECAD project — sample inputs.
- Anthropic — Anthropic-format API protocol (`messages.create`, tool use, prompt caching) and the `anthropic` Python SDK.
- MiMo (Xiaomi) — upstream language model `mimo-v2.5` served via Anthropic-format proxy.
