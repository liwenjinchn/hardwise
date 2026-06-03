# Grok Search Research: Workbench AI Topology Tools

Date: 2026-06-03

## Question

Before implementation, verify whether exposing parsed Allegro schematic/netlist
facts as structured agent tools is a sound design pattern for the Hardwise
right-bottom AI panel.

## Sources Checked

- Anthropic Claude tool-use documentation:
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- VTR netlist API documentation:
  https://docs.verilogtorouting.org/en/latest/api/vpr/netlist/
- DE-HNN circuit netlist representation paper:
  https://arxiv.org/html/2404.00477v1
- LLM-aided hardware design automation survey/paper:
  https://arxiv.org/html/2410.18582v1
- Cadence/OrCAD netlist generation article:
  https://resources.pcb.cadence.com/blog/2024-how-to-generate-a-netlist-in-orcad-x
- EMA OrCAD Capture netlisting article found via Grok Search:
  https://www.ema-eda.com/how-to-page/how-to-netlist-a-design-in-orcad-capture/

## Findings

1. Official LLM tool-use guidance supports this architecture. Anthropic
   documents the loop where the model emits structured tool calls, application
   code executes client tools, then returns `tool_result` blocks. This matches
   Hardwise's existing Runner and supports adding domain-specific topology
   tools instead of asking the model to infer connectivity from prompt text.

2. Netlists are naturally structured around blocks/components, pins, and nets.
   VTR's public API documentation explicitly describes netlists as Blocks,
   Ports, Pins, and Nets, and shows cross-reference traversal such as
   `net_pins()`, `pin_net()`, `pin_block()`, and block-to-net lookup. This maps
   directly to planned tools:
   `get_component_context`, `get_net_context`, and `search_nets`.

3. EDA research treats netlist topology as graph/hypergraph structure. The
   DE-HNN paper states that netlists describe elements and how they are
   connected, and models them as directed hypergraphs where cells are nodes and
   nets are directed hyperedges. This supports using component-pin-net graph
   queries as the factual substrate for schematic topology assistance.

4. Cadence/OrCAD public material confirms that netlisting is the bridge from
   schematic to layout and carries components plus electrical connections. The
   OrCAD X article describes the netlist as a textual representation with all
   components and associated electrical connections. EMA's article specifically
   describes Capture-to-Allegro netlist generation; Grok summarized the PST
   package as `pstxnet.dat` for net connectivity, `pstxprt.dat` for parts, and
   `pstchip.dat` for primitive/footprint linkage. This supports treating
   schematic-exported PST/Telesis inputs as pre-layout connectivity evidence,
   while still avoiding layout claims.

5. LLM-for-EDA literature reinforces the guardrail stance. The hardware
   automation paper notes both opportunities and challenges for LLMs in EDA,
   including hallucination, tool integration, verification loops, and privacy.
   For Hardwise, this supports keeping the LLM as an explanation layer over
   deterministic tools and avoiding unsupported module/layout/PLM claims.

## Impact On Plan

The planned A implementation is confirmed with small refinements:

- Keep topology tools as structured client tools in `agent/tools.py` and
  dispatch them through the existing Runner.
- Model topology as component/pin/net traversal over `Design`, not as a
  free-form natural-language summary in the prompt.
- Keep bounded result lists and structured misses with closest matches.
- Treat topology tool results as L1 schematic/netlist facts only when a
  `Design` is loaded.
- Continue excluding module naming/grouping, layout, boardview, `.brd`,
  placement/routing, PLM, price, lifecycle, and datasheet web search from this
  child task.

## Decision

Proceed with A as planned: add `get_component_context`, `get_net_context`,
`search_nets`, and `summarize_project_topology` to the existing workbench AI
tool surface. No separate newcomer mode and no first-version module grouping.
