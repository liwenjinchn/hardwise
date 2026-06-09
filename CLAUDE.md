# CLAUDE.md

> Claude Code overlay for Hardwise. The canonical project contract lives in
> `AGENTS.md`; do not maintain a second full rulebook here.

## Canonical Rules

Before doing repo work, read and follow `AGENTS.md`. It owns the hard rules,
scope boundaries, model configuration, workbench invariants, run/test commands,
and commit hygiene.

If a feature reaches into the rejected Wrench Board feature list, push back with
"out of MVP scope per AGENTS.md."

## Claude-Specific Notes

- Use the same command set as `AGENTS.md`: `uv run pytest -q` and
  `uv run ruff check .` before declaring code complete.
- Keep personal Claude memory under `~/.claude/projects/.../memory/` when
  needed. Durable project lessons belong in `docs/learning_log.md`; staged
  future work belongs in `docs/rolling_log.md`.
- When changing repo rules, edit `AGENTS.md` first. Update this file only for
  Claude-specific execution behavior.

## Drift Guard

This file should stay short. If a sentence is also true for Codex or another
agent, it probably belongs in `AGENTS.md` or a focused project doc instead.
