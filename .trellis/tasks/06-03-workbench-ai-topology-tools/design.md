# Workbench AI topology tools - Design

## Architecture

The existing workbench path already constructs the deterministic state needed
for topology answers:

`Allegro/PST input -> Design -> WorkbenchContext -> Runner -> tools -> chat`.

This task adds topology tools at the agent tool boundary. The model remains a
language layer over structured facts; it does not infer board objects from
memory or visual layout.

Grok Search research confirmed this direction before implementation. See
`research/topology-tooling-grok-search.md`: official tool-use docs support
structured client tools, EDA netlist APIs expose block/pin/net traversal, and
netlist graph/hypergraph literature supports component-pin-net topology as the
right factual substrate.

## Tool Surface

### `get_component_context(refdes, neighbor_limit=24)`

Returns a discriminated result:

- `status="found"` with component identity, profile/validation state,
  pin-to-net rows, and neighboring components grouped by net.
- `status="not_found"` with `closest_matches`.

The response should include:

- refdes, value, part number, manufacturer, package
- profile match status and validation status when available
- bounded pin rows: pin number/name/net
- bounded neighbor rows: net name, member count, sample `(refdes, pin, value)`
- important validation issues and evidence tokens when a validation report exists

### `get_net_context(net_name, member_limit=40)`

Returns:

- `status="found"` with exact net name, member count, bounded node list, and
  component identity summaries
- `status="not_found"` with closest net-name matches

Net facts come only from `Design.nets`. No PCB geometry or boardview facts are
introduced.

### `search_nets(query, limit=30)`

Performs case-insensitive name search over `Design.nets`. Matching should be
simple and deterministic: substring token matching first, with optional closest
matches for no-hit recovery. It returns bounded net summaries with member
counts and sample nodes.

### `summarize_project_topology(limit=...)`

Returns a bounded project overview:

- component count, net count, BOM matched count
- validated/manual counts and PASS/WARN/ERROR totals
- high-signal components: validated ERROR/WARN rows first, then U-prefixed ICs
- likely power-like nets by conservative name patterns
- likely interface/control nets by conservative name patterns
- grouped manual/no-profile gaps using existing `profile_gap_groups()`

This is a "facts inventory" tool, not a design-review verdict.

The first version deliberately does not emit module names or module groups.
Power/interface/control-like buckets are allowed as search aids, but they must
not be presented as confirmed schematic modules.

## Integration

Implementation options:

1. Add the tools to `agent/tools.py` and expose them through `TOOL_DEFINITIONS`.
   The tools should return `not_configured` when `Runner.design` is missing.
2. Extend `Runner._dispatch()` to route the new tool names when `design` and
   optional `ProjectValidationIndex` are available.
3. Add an optional `project_index` field to `Runner` so topology tools can use
   existing validation/profile status without recomputing.
4. Pass `context.index` from `WorkbenchChatService` into `Runner`.
5. Update `WORKBENCH_SYSTEM_PROMPT` to instruct the model to use topology tools
   for connectivity, net, project-overview, and onboarding-style questions.

The KiCad `ask` path may see the expanded tool manifest. For compatibility,
new tools must return structured `not_configured` / empty results when no
Allegro `Design.nets` or project index is loaded.

## Fake And Snapshot Mode

The fake workbench client currently decides between validation and datasheet
queries. Extend its routing heuristics so topology-looking questions call the
new tools:

- questions containing "接了哪些", "连接", "net", "网络", "拓扑" with a refdes
  call `get_component_context`
- questions about a named net or "RESET/SDA/BOOT/VIN/3V3 相关网络" call
  `search_nets` or `get_net_context`
- project-overview questions call `summarize_project_topology`

Fake answers only need to summarize the tool payload deterministically enough
for tests and offline snapshots.

## Trust Boundaries

- Refdes-shaped strings in user-visible answer and trace stay sanitized by the
  existing Refdes Guard.
- Net names are not refdes and are not wrapped by Refdes Guard; unknown nets
  must still return structured misses and closest matches.
- Topology tools are L1 schematic/netlist facts when the design is loaded.
- Validation facts remain L1 deterministic only when produced by
  `run_component_validation` or existing validation reports.
- Datasheet facts remain L2 only when retrieved from configured vector search.

## Compatibility

- Existing five tools and tests must continue to work.
- Existing static `design-validator-ui --ai-snapshot` should keep rendering.
- New suggestions may be added, but old audited suggestions should not vanish
  unless tests are updated deliberately.

## Rollback

The change can be rolled back by removing the new tool definitions, Runner
dispatch branches, prompt additions, and fake-mode routing. No data migration is
required.
