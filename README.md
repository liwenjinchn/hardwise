# Hardwise

> AI Agent embedded in the **schematic review** node of hardware R&D — **anti-hallucination by design**, **provenance-first**, **memory-consolidating**.

> Architecture inspired by [Wrench Board](https://github.com/Junkz3/wrench-board) (Anthropic *Build with Opus 4.7* hackathon, 2nd place, April 2026). No code copied; design ideas only. Wrench Board is for board-level *repair*; Hardwise is for hardware *design review* — different domain, same agent-engineering primitives.

> Built with AI assistance. All design decisions and final code reviewed and owned by the author.

---

## What it is

Hardwise is an AI Agent for the schematic review node of hardware R&D. It reads a KiCad project plus BOM and relevant datasheet PDFs, then produces a review report where every conclusion carries a source token (EDA / BOM / datasheet page / checklist rule) and every reference designator is verified against the parsed board, never fabricated.

It compresses the slow link of "翻 datasheet → 对位号 → 查 BOM → 写报告" into a tool-use loop with two anti-hallucination guards and a memory consolidation loop.

## What it isn't

- Not a PCB layout / EMC simulator
- Not a PLM / BOM management system
- Not a board repair tool (that's Wrench Board's domain)
- Not a complete product. This is a **2-week MVP** built for portfolio + interview, not production.

## Why

Initial schematic review on a real board takes a hardware engineer 1–2 days, mostly information shuffling: cross-checking refdes against datasheets, validating BOM, writing the review note. The judgment work — *is this design correct?* — is a small fraction. Hardwise automates the shuffle so the human spends time judging, not searching.

## Five mechanisms

| # | Mechanism | What it does | Frontier topic |
|---|-----------|--------------|----------------|
| 1 | **Refdes Guard** | Output refdes (U1, R10, J5...) must hit the EDA registry. Unverified tokens are wrapped before reaching the user. | Anti-hallucination by design |
| 2 | **Evidence Ledger** | Every claim carries a source token: `EDA` / `BOM` / `datasheet:p12` / `rule:R001`. No token, no claim. | Provenance |
| 3 | **Sleep Consolidator** | Each review session deposits *candidate* rules to `memory/rules.md`. Human gate before any rule activates. | Memory consolidation |
| 4 | **Tiered Model Routing** | Three runtime slots (`fast` / `normal` / `deep`) are reserved even when all currently route to `mimo-v2.5`. | Cost-aware orchestration |
| 5 | **Prompt Caching** | Datasheet + EDA registry shared across review turns are cached. | Cache-warmed long context |

Mechanisms 1, 2, 4 are direct architectural borrows from Wrench Board's "defense in depth, two layers" + tiered runtime. Mechanism 3 is a scope-shrunk cousin of Wrench Board's `microsolder-evolve` overnight loops — they auto-commit patches against an oracle benchmark, we sediment review feedback into human-gated rule candidates. Same direction, MVP-fit scope.

## Data & compliance

- All demo input is **public**: KiCad demo projects and publicly available datasheets.
- **No company-internal hardware data** is used in this project, ever.
- The author is a working hardware engineer; this project is a personal portfolio MVP and does not touch employer IP.

## Quickstart

> Stub — `make demo` lands once Day 7 closes the loop.

```bash
git clone <repo> hardwise
cd hardwise
uv sync
cp .env.example .env  # then fill in ANTHROPIC_API_KEY
uv run hardwise hello
uv run hardwise verify-api
uv run hardwise inspect-kicad data/projects/pic_programmer --limit 25
```

## Architecture

See [`docs/architecture.md`](docs/architecture.md). Adapter pattern at the EDA boundary (`src/hardwise/adapters/`) means a future Cadence/Allegro adapter is one new file, not a rewrite.

## Roadmap

- **v0.1 (week 1)** — KiCad → registry, datasheet → vector store, single-tool agent loop
- **v0.2 (week 2)** — Refdes Guard, Evidence Ledger, Sleep Consolidator, Tiered Routing, prompt caching
- **Future** — Cadence adapter, EMC rule pack, Anthropic Managed Agents runtime, evaluation set

## Interview Q&A

[`docs/interview_qa.md`](docs/interview_qa.md) — six questions the project must be able to answer in 80 字 each.

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgements

- [Wrench Board](https://github.com/Junkz3/wrench-board) — architectural inspiration. Read their README; it's worth your time.
- KiCad open-source ECAD project — sample inputs.
- Anthropic — Anthropic-format API protocol (`messages.create`, tool use, prompt caching) and the `anthropic` Python SDK.
- MiMo (Xiaomi) — upstream language model `mimo-v2.5` served via Anthropic-format proxy.
