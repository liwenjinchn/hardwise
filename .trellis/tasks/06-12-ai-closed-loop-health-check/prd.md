# AI 闭环体检与修复循环：全页面/交互/在线AI/真实项目命中率/产品有用性

## Goal

Run a product-level closed-loop health check for the Hardwise workbench: inspect
the real UI, exercise key workflows, verify live online-AI chat, import a real
public project, and fix the highest-impact issues that make the tool less useful
to a hardware reviewer.

## Requirements

- Cover the live `serve-workbench` SPA, not only static HTML.
- Capture screenshot evidence for Review, Import, Parse, Copilot, Findings, and
  Export surfaces where reachable.
- Click the primary user actions: queue filtering/search, component selection,
  Copilot entry, chat send, import, findings resolve toggle, and export buttons.
- Use real online AI mode when API credentials/connectivity work; otherwise
  record the blocker and continue with deterministic fake-AI smoke coverage.
- Import a real public Allegro/PST or fixture project and evaluate whether rule
  hits, document hits, and prep packets are clear enough for a hardware engineer.
- Fix high-impact frontend or product-clarity defects discovered during the
  health check, especially evidence/trace layout that buries useful answers or
  leaves blank space after hiding evidence.

## Acceptance Criteria

- [ ] Browser screenshots cover the main workbench pages and key states.
- [ ] Key click paths complete without console errors or broken UI states.
- [ ] Copilot answers a valid refdes question and an invalid-refdes guard question.
- [ ] Imported public project updates summary counts, queue contents, document
      coverage, and prep/export surfaces without server restart.
- [ ] Findings include a product judgment: useful signal, noisy signal, missing
      context, and reviewer cost.
- [ ] Any shipped fixes have focused tests plus `uv run pytest -q` and
      `uv run ruff check .` evidence, or a clear explanation if full verification
      is blocked.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
