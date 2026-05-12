# Hardwise

> AI Agent embedded in the **schematic review** node of hardware R&D — **anti-hallucination by design**, **provenance-first**, **memory-consolidating**.

> Architecture inspired by [Wrench Board](https://github.com/Junkz3/wrench-board) (Anthropic *Build with Opus 4.7* hackathon, 2nd place, April 2026). No code copied; design ideas only. Wrench Board is for board-level *repair*; Hardwise is for hardware *design review* — different domain, same agent-engineering primitives.

> Built with AI assistance. All design decisions and final code reviewed and owned by the author.

---

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
| 5 | **Prompt Caching** | Datasheet + EDA registry shared across review turns are cached. | ⏳ Slice 4 |

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
(KiCad official demo). All commands below should work out of the box.

### Review a schematic

```bash
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --format html
```

Produces three artifacts:

```
report: reports/pic_programmer-YYYYMMDD.md   (84 findings, 121 components reviewed)
report: reports/pic_programmer-YYYYMMDD.html (same data, Chinese visual report when --format html)
store:  reports/pic_programmer.db            (121 components, 77 NC pins)
memory: memory/rules.md                      (2 candidate rule(s) appended)
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
block for `datasheet:<pdf>#p<N>` evidence tokens in Slice 4 R003 upgrade.

### Other commands

```bash
uv run hardwise hello                                           # install smoke test
uv run hardwise verify-api --tier normal                        # tiered router
uv run hardwise inspect-kicad data/projects/pic_programmer      # registry dump
```

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
| 4 — R004 + Prompt caching | ⏳ | I2C address collision (first cross-store rule using vector datasheet evidence); prompt-cache hit observable in run log |
| 5 — R005 + Report polish | ⏳ | Dangling-net detection; report visually aligns with SCH_review_feedback_list |
| 6 — Demo closeout | ⏳ | 3-min screencast, finalized interview answers, README polish |

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
