# Hardwise Documentation Cleanup Handoff

This handoff is for the next-machine documentation cleanup pass. It records the
problem, the intended document architecture, and the safest cleanup sequence.

Do not treat this as another public story document. It is a working guide for
reducing documentation fragmentation and making Hardwise easier for both humans
and AI agents to continue.

## Problem Summary

The problem is not simply "too many docs." The deeper issue is that four
different kinds of material are mixed together and several of them look like the
current source of truth:

1. Current public story.
2. AI/agent operating rules.
3. Historical plans, journals, and old closeout notes.
4. Generated artifacts and one-off local reports.

That mix creates two failures:

- A human reviewer cannot tell which file is the latest project narrative.
- An AI agent may load stale plans or generated outputs as if they were current
  product facts.

The cleanup goal is context engineering, not cosmetic tidying: make it obvious
which file answers which question.

## Source Thread

This handoff summarizes the document-fragmentation analysis from Codex thread:

```text
019ea98f-7cc0-7de0-a560-cab0114b7782
```

That thread found the main risks below.

## High-Priority Risks

### P0: Current Fact Drift

Use one canonical current fixture fact set:

| Fact | Current value |
|---|---:|
| Components | 25 |
| BOM matched | 25 |
| Validated | 22 |
| PASS / WARN / ERROR | 5 / 13 / 4 |
| Manual | 3 |

Known drift to check during cleanup:

- English README and Chinese README may not agree on validated/manual counts.
- `docs/demo.md`, demo scripts, and older closeout docs may describe older
  profile-backed target counts.
- HTML pages under `docs/` are rendered views or historical artifacts unless
  explicitly designated as public entries.

### P0: Internal-Data Boundary

Hardwise must use only public hardware data. Any sentence implying use of
company-internal schematic standards, even "sanitized" or "desensitized," must
be removed or rewritten to public-source language.

Known area to inspect:

- `docs/rolling_log.md` previously mentioned a desensitized hardware-team
  schematic standard. That conflicts with the project rule that internal
  hardware data is disallowed even when sanitized.

### P1: AI Rule Drift

`AGENTS.md` and `CLAUDE.md` can drift if both contain full project rules.

Preferred end state:

- `AGENTS.md` is the canonical agent operating contract.
- `CLAUDE.md` either imports/points to `AGENTS.md` plus a short Claude-specific
  overlay, or the two files are generated from one source.
- Do not keep two independent copies of hard rules, model config, scope
  boundaries, and verification commands.

### P1: Historical Plans Still Look Current

`docs/PLAN.md`, `docs/rolling_log.md`, `docs/weekend_closeout_plan.md`, and old
midpoint/closeout docs are useful history, but they must not be mistaken for the
current public narrative.

Preferred end state:

- `PLAN.md` becomes ADR/history/why, not the first operational plan.
- Current handoffs live in focused handoff docs and are retired after use.
- Time-bound closeout files are marked historical once their branch/task is
  complete.

### P1: Generated and Source Docs Are Mixed

`docs/` contains Markdown sources, generated HTML views, old exploration pages,
and public entry pages in the same folder.

Preferred end state:

- Markdown source is the canonical source when both `.md` and `.html` exist.
- HTML is a rendered/public view unless explicitly documented otherwise.
- One-off generated reports should not become long-term product facts.

## Proposed Document Layers

Use this model during cleanup:

| Layer | Purpose | Examples |
|---|---|---|
| Public entry | What a reviewer or recruiter should read first | `README.md`, `README.zh-CN.md`, `docs/index.html`, `docs/demo.md`, `docs/demo_recording_script.md`, `docs/mvp_definition.md` |
| Current reference | Stable support docs for architecture, evidence boundaries, and setup | `docs/architecture.md`, `docs/review_node.md`, `docs/evidence_chain_audit.md`, `docs/closeout_pressure_summary.md`, `docs/windows.md` |
| AI rules | Always-loaded agent rules and workflow contracts | `AGENTS.md`, `CLAUDE.md` overlay if retained |
| Handoff | Short-lived or active continuation notes | `docs/workbench_spa_handoff.md`, this file |
| History/journal | Useful history that should not be treated as current product truth | `docs/PLAN.md`, `docs/rolling_log.md`, `docs/learning_log.md`, `docs/weekend_closeout_plan.md`, `docs/midpoint_review.md`, `docs/superpowers/**` |
| Interview/private drafts | Personal narrative, resume/social/interview support | `docs/interview_qa.md`, `docs/interview_narrative.md`, `docs/jd_alignment.md`, `docs/hardwise_*` |
| Generated/local output | Reproducible outputs or local one-off reports | `reports/**`, generated HTML, smoke screenshots |

## Cleanup Sequence

Do the cleanup in small commits. Avoid a giant docs rewrite.

### Step 1: Freeze Current Facts

Define a short canonical facts block and make every public-facing doc either
match it or link to the canonical source.

Suggested canonical source:

- `README.md` for public current facts.
- `docs/demo.md` for runnable technical narrative.

Do not copy long metric paragraphs into every doc.

### Step 2: Fix P0 Internal-Data Language

Search for risky phrases:

```bash
rg -n "脱敏|内部|internal|saniti[sz]ed|desensiti[sz]ed|公司|team standard|硬件团队" \
  AGENTS.md CLAUDE.md README* docs
```

Any internal-data sentence must be removed or rewritten to public-data-only
language.

### Step 3: Normalize AI Rule Files

Compare:

```bash
diff -u AGENTS.md CLAUDE.md
```

Then choose one policy:

1. `AGENTS.md` canonical, `CLAUDE.md` short overlay.
2. One generated from the other.

Do not leave both as full independent rulebooks.

### Step 4: Update `docs/docs_inventory.md`

Make `docs/docs_inventory.md` the context router:

- list every tracked doc that a future agent might touch;
- label each file as public entry, current reference, handoff, historical,
  interview/private draft, or generated view;
- mark which file is canonical when there is a Markdown/HTML pair.

This is where "what should I read first?" should be answered.

### Step 5: Demote Historical Docs

Do not delete useful history first. Instead:

- mark historical files clearly in `docs/docs_inventory.md`;
- add a short top note only when a file is especially likely to mislead;
- move only when the repo owner is ready for a larger docs restructure.

Candidate future folders:

```text
docs/archive/
docs/handoffs/
docs/private/
docs/generated/
```

Moving files is optional. Clear routing is more important than perfect folders.

### Step 6: Keep Generated Outputs Out of Canonical Story

Generated HTML may stay for GitHub Pages, but it should not become a second
truth source.

Rules:

- If `.md` and `.html` both exist, edit the `.md` source first.
- Re-render HTML only when the page is still part of the public path.
- Do not quote one-off `reports/` output as durable facts unless summarized in a
  current reference doc.

## AI-First Context Rules

For future Codex/Claude sessions:

1. Do not ask the model to "read all docs."
2. Start from `docs/docs_inventory.md`.
3. Load only the layer needed for the task.
4. Treat `docs/learning_log.md` as a journal, not as a current instruction file.
5. Treat old plans as history unless `docs/docs_inventory.md` says they are
   active.
6. Use subagents for broad docs audits so the main context does not get flooded.

## Suggested Docs-Lint Checks

A lightweight docs lint script would be useful later. For now, run manual scans.

Useful checks:

```bash
rg -n "17 validated|8 manual|25 components|22 validated|5/13/4|PASS/WARN/ERROR" README* docs
rg -n "/Users/|/Volumes/|C:\\\\|localhost:[0-9]+|127\\.0\\.0\\.1:[0-9]+" README* docs reports
rg -n "脱敏|内部|internal|saniti[sz]ed|desensiti[sz]ed" README* docs AGENTS.md CLAUDE.md
rg -n "current|active|submission|closeout|weekend" docs/PLAN.md docs/rolling_log.md docs/weekend_closeout_plan.md
```

Do not blindly replace matches. Each match is a review candidate.

## Done When

The documentation cleanup pass is done when:

- public entry docs agree on the current Hardwise story and numbers;
- `AGENTS.md` / `CLAUDE.md` no longer contain unsynchronized full rulebooks;
- internal-data-risk language is removed or rewritten;
- `docs/docs_inventory.md` routes every tracked doc by role;
- generated HTML and old plans are clearly not canonical facts;
- another agent can answer "which doc should I read for this task?" without
  loading the whole repo.
