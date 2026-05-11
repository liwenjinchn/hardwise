# Hardwise Rolling Log

> Scheduled improvements queued behind specific code milestones. When the trigger ships, knock the corresponding TODO off this file and move the content to its destination (usually CLAUDE.md or docs/architecture.md).
>
> This file exists because the editorial rule on CLAUDE.md and README.md forbids "TODO: add later" placeholders — those would be temporal framing. Park the TODOs here instead.
>
> Format per entry: **Trigger** / **Where it lands** / **What to add**.

---

## Triggered by Day 2–3 — KiCad parser shipping

**Where it lands**: `CLAUDE.md` → new "Layout" section (between Stack and Models).

**What to add**: A directory tree like Wrench Board's, one line per directory. Should cover at minimum:

```
src/hardwise/
  adapters/          EDA boundary; one file per format. KiCad first, Cadence later.
  ingest/            File → store glue (PDF chunk, EDA → SQL).
  store/             Two stores: relational (refdes/nets/BOM/DRC) + vector (datasheet chunks).
  agent/             Tool-use loop, tier routing, prompts, tool manifest.
  guards/            Two-layer anti-hallucination: refdes guard + evidence ledger.
  memory/            Sleep Consolidator + candidate-rule pool (rules.md).
data/                Local input — KiCad projects + datasheet PDFs (gitignored except .gitkeep).
docs/                architecture.md / interview_qa.md / learning_log.md / rolling_log.md.
reports/             Generated review reports (markdown, gitignored).
```

Move the trigger off this file once shipped.

---

## Triggered by first tool registered in `agent/tools.py`

**Where it lands**: `CLAUDE.md` → new "Tool manifest" section (between Models and Run/test/lint).

**What to add**: Enumerate each tool by name with a one-line input/output contract. Example shape (from Wrench Board's lead):

```
| Tool | Input | Output | Notes |
|---|---|---|---|
| list_components | filter? | list[Component] | refdes, value, footprint, datasheet ref |
| get_net          | net_name | Net or {found:false, closest:[...]} | refuses unknown nets |
| search_datasheet | query, part_no? | list[Chunk(page, text, score)] | vector search |
| check_bom        | refdes | BomRow or {found:false} | qty, manufacturer, MPN |
| lookup_drc       | severity? | list[Finding] | from KiCad ERC/DRC report |
```

The tool count and exact names are deferred until the first tool actually ships — names always drift in the first iteration.

---

## Triggered by Day 4 — both stores wired up

**Where it lands**: `CLAUDE.md` → new "On-disk layout" section (after Layout).

**What to add**: Mirror Wrench Board's `memory/{device_slug}/` schema for Hardwise:

```
data/projects/{project_slug}/   # KiCad project files (input, gitignored)
data/datasheets/                # Public PDFs (input, gitignored, shared across projects)
data/hardwise.db                # SQLite — schema in src/hardwise/store/relational.py
data/chroma/                    # Chroma local persistence
reports/{project_slug}-{YYYYMMDD}.md     # Generated review report
src/hardwise/memory/rules.md             # Candidate rule pool (committed; small)
```

Document the slug rule, the timestamp format, and which files are gitignored vs committed.

---

## Triggered by Day 5 — CLI commands beyond `hello`

**Where it lands**: `CLAUDE.md` → new "CLI surface" section (after Run/test/lint).

**What to add**: Subcommand table.

```
| Command | What it does |
|---|---|
| hardwise ingest <project_path> | Parse KiCad + datasheets, populate both stores. |
| hardwise review <project_slug> | Run agent loop, write markdown report to reports/. |
| hardwise consolidate <report> | Extract candidate rules into memory/rules.md. |
| hardwise hello | Sanity check the install. |
```

Lock command names only after the third subcommand ships; renaming early is cheap, late is expensive.

---

## Triggered by Day 7 — first review report generated end-to-end

**Where it lands**: `CLAUDE.md` → new "Architectural anti-rules" subsection inside "Hard rules".

**What to add**: Concrete "do not" rules learned from running the loop in anger. Candidate items to watch for:

- "Do not let the agent generate refdes without a tool call." (You'll see it try.)
- "Do not put datasheet content in the relational DB; do not put refdes in the vector store." (The temptation is to denormalize when something is slow.)
- "Do not promote candidate rules without the human gate." (The Sleep Consolidator will look so reliable you'll want to skip review.)
- "Do not let the report exceed N pages." (Whatever N turns out to be when reviewers actually read it.)

Each anti-rule must reference a real moment when reality tried to violate it. Anti-rules pulled out of thin air are noise; anti-rules from a near-miss are gold.

---

## Discharged improvements (keep for audit)

> When an item moves out of this file, leave a one-line entry below noting where it landed.

(none yet — this file was created on Day 1)
