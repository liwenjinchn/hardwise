# Workbench AI topology tools

## Goal

Improve the right-bottom Hardwise AI panel so a user can ask natural questions
about an Allegro schematic's topology without entering a separate onboarding
mode.

The workbench already loads Allegro/Telesis or Capture/Allegro PST topology,
BOM identity, profile matches, and deterministic validation results. This task
exposes more of that structured state to the agent as bounded tools, so answers
about "what is this component connected to?", "what is on this net?", and "how
is this project organized?" come from parsed netlist facts instead of free-form
model guessing.

## Confirmed Facts

- This task is scoped to the existing Allegro workbench AI panel, not a new UI
  mode.
- KiCad schematic-net parsing is not part of this task.
- The current workbench chat path uses `WorkbenchChatService -> Runner` with
  the real tool dispatcher and Refdes Guard.
- Current workbench tools cover component listing, component lookup, NC pins,
  optional datasheet vector search, and deterministic component validation.
- The underlying `Design` already contains Allegro/PST components, pins, and
  nets, but the agent does not yet have first-class net/topology tools.
- All answers must keep the existing scope boundary: schematic-exported
  topology, BOM identity, public/profile evidence, and deterministic validation
  only. No `.brd`, boardview, placement, routing, lifecycle, price, or PLM
  claims.

## Requirements

- Add topology-focused agent tools usable from the existing workbench AI panel:
  - `get_component_context(refdes)` for component identity, validation/profile
    state, pin-to-net list, and bounded neighboring components.
  - `get_net_context(net_name)` for net membership, component identities, and
    closest-match recovery when the net name is not found.
  - `search_nets(query)` for finding nets by name such as `SDA`, `RESET`,
    `BOOT`, `VIN`, `3V3`, or interface/power keywords.
  - `summarize_project_topology()` for a bounded project overview covering
    component/net counts, validation coverage, high-signal ICs, likely power or
    interface nets, and manual/no-profile coverage gaps.
- Keep all tool outputs structured Pydantic models with explicit found/status
  fields and bounded lists.
- Preserve Refdes Guard behavior for every user-visible trace and answer.
- Update the workbench system prompt so the model prefers topology tools for
  connectivity and project-overview questions.
- Update fake/snapshot chat behavior enough for tests and offline demo answers
  to exercise at least one topology tool.
- Keep the implementation provider-neutral; it must not depend on a live model
  or API key for tests.
- Do not read or embed any non-public hardware data in tests or docs.

## Acceptance Criteria

- [x] A live or fake workbench chat question such as "U8 接了哪些关键网络?"
      calls a topology tool and returns parsed schematic/netlist facts.
- [x] A question such as "RESET 相关网络有哪些?" can search net names without
      requiring the user to know the exact net spelling.
- [x] A question such as "这张板大概有哪些已验证风险和待补 profile?" can use a
      bounded project summary rather than relying on free-form model memory.
- [x] Unknown refdes and unknown net names return structured misses with
      closest matches; neither the tool nor model fabricates identifiers.
- [x] Existing validation and datasheet chat tests continue to pass.
- [x] New unit tests cover each topology tool and at least one Runner-backed
      fake workbench chat path.
- [x] `uv run pytest -q` and `uv run ruff check .` pass before completion.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.

## Out Of Scope

- A separate "newcomer guide" mode or page.
- KiCad schematic-side wire/label parsing.
- Automatic module-boundary inference from visual schematic layout.
- First-version module naming/grouping. The project summary may expose
  conservative power/interface/control-like net buckets, but it must not label
  them as confirmed schematic modules.
- Datasheet web search, document discovery provider, or PLM integration.
- New family validator implementation.
- Any conclusions based on PCB layout, placement, routing, boardview, `.brd`,
  simulation, supplier lifecycle, pricing, or availability.

## Decisions

- `summarize_project_topology()` first version will not include module naming
  or module grouping. Module-aware output waits for a later explicit grouping
  source such as `modules.yaml` or a deliberately reviewed heuristic design.
