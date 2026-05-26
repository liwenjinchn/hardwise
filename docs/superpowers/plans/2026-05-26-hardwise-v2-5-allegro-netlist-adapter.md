# Hardwise V2.5 — Allegro Netlist Adapter Implementation Plan

> **For agentic workers:** implement task-by-task. Keep the checkboxes current while executing. This plan is intentionally narrower than "Allegro integration": it accepts only text netlist exports as pre-Layout schematic-review evidence.

**Goal:** Add Allegro schematic-netlist adapters that parse Telesis-style third-party ASCII netlists and Capture/Allegro PST handoff files into Hardwise IR (`Design.components`, `Design.nets`, `Design.refdes_set`) so V2 proves the review core is EDA-agnostic, without parsing PCB layout or boardview data.

**Why this still serves the review node:** At the pre-Layout schematic-review node, a netlist is a schematic connectivity export: refdes, package/device names, nets, and pin endpoints. That is valid review evidence for "what is connected to what." A `.brd`, boardview canvas, pad geometry, routing, copper, placement, constraints, or post-layout DRC is not valid evidence for this node and is out of scope per `AGENTS.md` hard rule #5 and `docs/review_node.md`.

**Architecture:** Keep `adapters/` as the EDA boundary. `adapters/allegro_netlist.py` produces parse-level Telesis records; `adapters/allegro_pst.py` produces parse-level PST records; `ir/build.py` aggregates both into the existing `Component / Pin / Net / Design` IR. The existing KiCad path remains the reference implementation and must not regress.

**Format note from public research:** Allegro's third-party ASCII netlist path is commonly called **Telesis**. Public examples and exporter docs show more than the minimal `$PACKAGES/$NETS` shape: `$A_PROPERTIES` may appear between `$PACKAGES` and `$NETS`; node/refdes lists may be comma-separated; trailing commas can mean line continuation; names may be single-quoted when they contain hierarchy slashes or other special characters. V2.5 should parse the useful connectivity subset and explicitly skip/record unsupported property details instead of pretending the format is simpler than it is.

**Format note from public fixture testing:** Real Capture/Allegro handoff commonly appears as PST files: `pstxprt.dat` declares placed parts, `pstxnet.dat` declares net / `NODE_NAME` connectivity, and `pstchip.dat` carries primitive body properties such as `VALUE` and `JEDEC_TYPE`. This is still schematic-exported topology, not PCB layout evidence.

**Product-benchmark note from public research:** EDA.cn / 华秋 and CADY both expose a "netlist + BOM" path for non-native EDA uploads. The netlist supplies topology (refdes, pins, nets); the BOM supplies component identity (manufacturer part number / value / specs) so the reviewer can match the right datasheet. That BOM is a **component-matching aid**, not PLM-grade lifecycle/cost governance. Hardwise V2.5 should therefore leave BOM parsing out of `adapters/allegro_netlist.py`, but keep an explicit extension point for a later `bom_matcher` layer that joins BOM rows to `Design.components` by refdes.

**Scope boundary:**
- Input is either (a) a plain-text Allegro third-party ASCII / Telesis netlist containing `$PACKAGES`, `$NETS`, and `$END`, with optional `$A_PROPERTIES`, or (b) a Capture/Allegro PST directory/member file containing `pstxprt.dat` + `pstxnet.dat`, with optional `pstchip.dat`.
- No `.brd` parsing, no boardview, no PCB geometry, no layout/routing/placement interpretation.
- No EDIF, IPC-2581, OrCAD `.DSN`, EasyEDA, or Cadence Skill automation in V2.5.
- No new active schematic review rule. V2.5 is adapter + IR population + CLI inspection/review entry only.
- No datasheet auto-linking for Allegro netlists. If the netlist lacks datasheet paths, datasheet-driven checks skip instead of guessing.
- No BOM parser in V2.5. BOM support is a follow-on component-matching layer, not part of the netlist adapter itself.
- No Allegro device-file (`.dev`) import/emulation in V2.5. Device files can carry richer pin/package mapping and NC information for real Allegro import, but Hardwise V2.5 only needs the text netlist's refdes/package/net/pin facts. A net literally named `NC` is preserved as a net, not interpreted as datasheet no-connect semantics.
- If a public fixture cannot be found quickly, use a small synthetic fixture and label it as synthetic. Do not use company-internal data.

**Spec reference:** `docs/superpowers/specs/2026-05-24-hardwise-v2-design.md` §3.4, V2-D6.

**Estimated time:** 2-3 days. If format ambiguity stalls for more than 4 hours, downscope to the synthetic fixture parser and document the limitation.

---

## Acceptance Gate

V2.5 is complete only when all of these are true:

1. `parse_allegro_netlist()` parses a fixture with packages, optional properties, nets, quoted names, comma/space-separated node endpoints, and continued refdes/node lists.
2. `parse_allegro_pst()` parses a fixture and the public PST sample directory with placed parts, nets, pin names, primitive properties, and a validated `refdes_set`.
3. Unknown or malformed syntax fails with a clear `ValueError`; the parser never invents refdes, pins, packages, or nets.
4. `build_design_from_netlist()` and `build_design_from_pst()` return `Design(source_eda="allegro_netlist")` with populated `components`, `nets`, `Pin.net`, and `refdes_set`.
5. Refdes guard compatibility holds: every component surfaced by Allegro path is in `Design.refdes_set`; net members pointing to package-missing refdes are either rejected or recorded as parser diagnostics, not silently fabricated.
6. KiCad review baseline still passes: `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003` remains 28 findings.
7. `uv run pytest -q` and `uv run ruff check .` pass.
8. `docs/learning_log.md` records the format assumptions and any parser surprise.
9. `docs/interview_qa.md` gets one V2.5 answer update: "Allegro support means netlist adapter, not PCB parser."
10. `docs/rolling_log.md` or the next V2 plan records the follow-on BOM matcher idea: CSV/XLSX BOM rows joined by refdes to improve datasheet/profile matching for netlist-only inputs.

---

## File Structure

### Created

| File | Responsibility |
|---|---|
| `src/hardwise/adapters/allegro_netlist.py` | Parse Allegro third-party ASCII netlist into package/net records. |
| `src/hardwise/adapters/allegro_pst.py` | Parse Capture/Allegro PST `pstxprt.dat` / `pstxnet.dat` / optional `pstchip.dat` into part/net records. |
| `tests/adapters/test_allegro_netlist.py` | Parser unit tests and fixture coverage. |
| `tests/adapters/test_allegro_pst.py` | PST parser unit tests and fixture coverage. |
| `tests/ir/test_build_allegro_netlist.py` | `build_design_from_netlist()` tests. |
| `tests/ir/test_build_allegro_pst.py` | `build_design_from_pst()` tests. |
| `tests/fixtures/allegro/minimal_third_party.net` | Small synthetic legal fixture unless a public fixture is found quickly. |
| `tests/fixtures/allegro/telesis_with_properties.net` | Synthetic fixture covering `$A_PROPERTIES`, quoted names, commas, and continuation. |
| `tests/fixtures/allegro/pst/` | Synthetic PST fixture covering placed parts, nets, pin names, and primitive properties. |

### Modified

| File | Responsibility |
|---|---|
| `src/hardwise/ir/build.py` | Add `build_design_from_netlist()` and `build_design_from_pst()`. |
| `src/hardwise/ir/types.py` | Usually unchanged; only touch if a missing field is proven necessary. |
| `src/hardwise/cli.py` | Add low-risk inspect command first; review auto-detection is optional after parser is stable. |
| `docs/architecture.md` | Document the Allegro netlist adapter and explicitly exclude boardview/PCB parsing. |
| `docs/interview_qa.md` | Add V2.5 answer update. |
| `docs/learning_log.md` | Add V2.5 parser/format learning entry. |

---

## Task 0: Confirm Scope Gate Before Coding

- [ ] Read `docs/review_node.md` "节点之外" and `AGENTS.md` "Out of scope".
- [ ] Re-read this plan's "Why this still serves the review node" paragraph.
- [ ] Write one sentence in the implementation PR/commit body: "V2.5 parses schematic netlist text only; it does not parse Allegro PCB/boardview data."

Stop immediately if the work starts requiring `.brd`, board geometry, placement, copper, or boardview APIs.

---

## Task 1: Add Synthetic Fixture

**Files:**
- Create: `tests/fixtures/allegro/minimal_third_party.net`

Use a small fixture shaped like:

```text
$PACKAGES
  ! 'C0805' ! C0805 ; C1, C2
  ! 'SOIC8' ! SOIC8 ; U1
  ! 'CONN4' ! CONN4 ; J1
$NETS
  'VCC_5V' ; U1.8, C1.1, J1.1
  'GND' ; U1.4, C1.2, C2.2, J1.2
  'I2C_SCL' ; U1.1, J1.3
  'I2C_SDA' ; U1.2, J1.4
$END
```

- [ ] Keep the fixture synthetic and public-safe.
- [ ] Include one quoted net with an underscore and at least one connector refdes.
- [ ] Add a second fixture that includes `$A_PROPERTIES` between `$PACKAGES` and `$NETS`, plus a trailing-comma continuation line.
- [ ] Do not add any real company design data.

---

## Task 2: Parser Data Models

**Files:**
- Create: `src/hardwise/adapters/allegro_netlist.py`
- Create: `tests/adapters/test_allegro_netlist.py`

Implement Pydantic models, matching the repo's current style:

```python
class AllegroPackage(BaseModel):
    package_name: str
    device_name: str
    refdes_list: list[str] = Field(default_factory=list)


class AllegroNet(BaseModel):
    name: str
    nodes: list[tuple[str, str]] = Field(default_factory=list)


class AllegroNetlistRegistry(BaseModel):
    packages: list[AllegroPackage] = Field(default_factory=list)
    properties: list[AllegroProperty] = Field(default_factory=list)
    nets: list[AllegroNet] = Field(default_factory=list)
    source_file: Path

    @property
    def refdes_set(self) -> set[str]:
        ...
```

Tests first:

- [ ] Minimal models construct and JSON round-trip.
- [ ] `refdes_set` is the union of all package refdes.
- [ ] Empty package refdes lists are allowed only if the format really emits them; otherwise reject.

Add a minimal `AllegroProperty` model only if needed to preserve unsupported property rows as structured facts. V2.5 does not consume these properties for checks; preserving them prevents silent data loss and makes future extension clean.

Design choice: `refdes_set` comes from `$PACKAGES`, not from model text generation. If a `$NETS` endpoint references a refdes absent from `$PACKAGES`, the parser must make that explicit via `ValueError` or a diagnostics field before any review uses the data.

---

## Task 3: Parse `$PACKAGES`

**Files:**
- Modify: `src/hardwise/adapters/allegro_netlist.py`
- Modify: `tests/adapters/test_allegro_netlist.py`

Expected package line shape:

```text
! 'C0805' ! C0805 ; C1 C2 C3
```

Implementation notes:

- Use section scanning, not one giant regex over the whole file.
- Strip blank lines and comment-like noise only when format evidence supports it.
- Parse one line into `package_name`, `device_name`, and `refdes_list`.
- Accept comma-separated and whitespace-separated refdes lists.
- Handle trailing-comma continuation before finalizing the package row.
- Preserve deterministic order from the file.
- Raise `ValueError` with line number on malformed package rows.

Tests:

- [ ] Parses three package rows from the synthetic fixture.
- [ ] Handles quoted package names.
- [ ] Handles comma-separated refdes lists.
- [ ] Handles a package refdes list continued onto the next line with a trailing comma.
- [ ] Rejects a row with no `;`.
- [ ] Rejects duplicate refdes across package rows.

---

## Task 3.5: Parse or Preserve `$A_PROPERTIES`

**Files:**
- Modify: `src/hardwise/adapters/allegro_netlist.py`
- Modify: `tests/adapters/test_allegro_netlist.py`

Public examples show `$A_PROPERTIES` between `$PACKAGES` and `$NETS`. V2.5 does not need property semantics for review checks, but the parser should not fail on valid Telesis files just because this optional section exists.

Implementation options:

- Preferred: parse property rows into `AllegroProperty(name, value, targets)` and attach them to `AllegroNetlistRegistry.properties`.
- Acceptable downscope: skip the section while counting skipped rows, if the count is exposed in a diagnostics field and documented.

Tests:

- [ ] Accepts `$A_PROPERTIES` between `$PACKAGES` and `$NETS`.
- [ ] Handles quoted property names/values.
- [ ] Handles comma-separated target refdes lists and continuation.
- [ ] Rejects `$A_PROPERTIES` after `$NETS` unless a real source proves that ordering is valid.

---

## Task 4: Parse `$NETS`

**Files:**
- Modify: `src/hardwise/adapters/allegro_netlist.py`
- Modify: `tests/adapters/test_allegro_netlist.py`

Expected net line shape:

```text
'VCC' ; U1.8 C1.1 C2.1
```

Implementation notes:

- Parse net name left of `;`, trimming optional single quotes.
- Parse nodes as `(refdes, pin_number)` by splitting at the final `.` in each token.
- Accept comma-separated and whitespace-separated node lists.
- Handle trailing-comma continuation before finalizing the net row.
- Reject node tokens without a pin separator.
- Validate every node refdes against `$PACKAGES` before returning a registry.
- Preserve duplicate pin endpoints only if a real netlist can emit them; otherwise reject duplicates per net.

Tests:

- [ ] Parses `VCC_5V`, `GND`, `I2C_SCL`, `I2C_SDA`.
- [ ] Preserves node order.
- [ ] Parses quoted hierarchical/special names such as `'/SUBBLOCK1/PIN1'` or `'NET-(R1-PAD1)'`.
- [ ] Handles comma-separated nodes and trailing-comma continuation.
- [ ] Rejects `U9.1` when `U9` is absent from `$PACKAGES`.
- [ ] Rejects malformed node token `U1` with no pin.
- [ ] Rejects missing `$END`.

---

## Task 5: Public Entry Function

**Files:**
- Modify: `src/hardwise/adapters/allegro_netlist.py`
- Modify: `tests/adapters/test_allegro_netlist.py`

Add:

```python
def parse_allegro_netlist(path: Path) -> AllegroNetlistRegistry:
    ...
```

Tests:

- [ ] `parse_allegro_netlist(Path(...))` returns the expected counts.
- [ ] Missing file raises `FileNotFoundError`.
- [ ] File with `$NETS` before `$PACKAGES` raises `ValueError`.
- [ ] Lowercase or mixed-case section headers are either supported deliberately or rejected deliberately; document whichever choice is made.

Keep the function narrow. No CLI printing, no report rendering, no datasheet lookup.

---

## Task 6: Build IR From Allegro Netlist

**Files:**
- Modify: `src/hardwise/ir/build.py`
- Create: `tests/ir/test_build_allegro_netlist.py`

Add:

```python
def build_design_from_netlist(registry: AllegroNetlistRegistry) -> Design:
    ...
```

Mapping:

- Each refdes becomes one `Component`.
- `Component.value` can use `device_name`.
- `Component.package` can use `package_name`.
- Each net endpoint becomes one `Pin(number=pin_number, name="", electrical_type="", is_nc=False, net=net_name)`.
- `Design.nets[net_name] = Net(name=net_name, nodes=[...])`.
- `Design.project_path = registry.source_file.parent`.
- `Design.source_eda = "allegro_netlist"`.

Tests:

- [ ] Component count equals refdes count from packages.
- [ ] `Design.nets` has four nets from the fixture.
- [ ] `U1.pin_by_number("8").net == "VCC_5V"`.
- [ ] `Design.refdes_set == registry.refdes_set`.
- [ ] Components with multiple connected pins get multiple `Pin` objects.
- [ ] No NC pins are invented; `is_nc` is `False` for netlist-connected pins.

Important limitation: this path cannot infer unconnected NC pins from a connectivity netlist. R003 should not claim Allegro netlist NC evidence unless the export includes explicit NC markers in a future format.

---

## Task 7: CLI Inspection Command

**Files:**
- Modify: `src/hardwise/cli.py`

Add a small command before touching `review`:

```bash
uv run hardwise inspect-allegro-netlist tests/fixtures/allegro/minimal_third_party.net
```

Output should include:

```text
source: tests/fixtures/allegro/minimal_third_party.net
components: 4
nets: 4
VCC_5V 3 members
GND 4 members
```

Tests can be Typer runner tests if the project already has a CLI test pattern; otherwise keep unit coverage on parser/build and manually verify the command.

This command is intentionally named `inspect-allegro-netlist`, not `inspect-allegro`, to avoid implying enterprise Allegro PCB integration.

---

## Task 8: Optional Review Input Detection

Only do this after Tasks 1-7 are green.

**Files:**
- Modify: `src/hardwise/cli.py`
- Add tests if CLI patterns exist.

Behavior:

- If `review` input is a directory, keep existing KiCad path.
- If input is a file with `.net`, parse it through `parse_allegro_netlist()` and `build_design_from_netlist()`.
- For V2.5, only component-centric report should be considered for netlist input; classic report depends on `BoardRegistry` evidence tokens.
- If requested rules need KiCad-only context (`R001`, `R003` NC markers, datasheet vector evidence), print a clear skip/warning rather than producing misleading findings.

Downscope option: skip this task and ship `inspect-allegro-netlist` + IR tests only. The adapter proof is still valid if review integration would distort evidence semantics.

---

## Task 9: Documentation Closeout

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/interview_qa.md`
- Modify: `docs/learning_log.md`

Add concise updates:

- `architecture.md`: `adapters/allegro_netlist.py` reads schematic netlist text and populates IR nets; `.brd` / boardview remains out of scope.
- `interview_qa.md`: V2.5 answer says "Allegro support means third-party netlist adapter, not PCB parser; it proves EDA-agnostic IR while staying inside pre-Layout schematic review."
- `learning_log.md`: record the exact fixture choice, parser assumptions, and any line-format surprise.

Do not rewrite `AGENTS.md` or `README.md` unless the implementation changes public claims.

---

## Verification Commands

Run these before declaring V2.5 complete:

```bash
uv run pytest tests/adapters/test_allegro_netlist.py -q
uv run pytest tests/ir/test_build_allegro_netlist.py -q
uv run pytest tests/adapters/test_allegro_pst.py tests/ir/test_build_allegro_pst.py tests/test_cli_helpers.py -q
uv run pytest -q
uv run ruff check .
uv run hardwise inspect-allegro-netlist tests/fixtures/allegro/minimal_third_party.net
uv run hardwise inspect-allegro-netlist tests/fixtures/allegro/pst
uv run hardwise inspect-allegro-netlist "<public PST sample>/allegro" --limit 10
uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003 --no-consolidate --db-path '' --no-run-trace
```

Expected KiCad regression line remains:

```text
findings: 28
components reviewed: 121
```

---

## Commit Plan

Keep commits narrow:

1. `test(adapters): add allegro netlist fixture`
2. `feat(adapters): parse allegro ascii netlist`
3. `feat(ir): build design from allegro netlist`
4. `feat(cli): inspect allegro netlist input`
5. `docs(architecture): document allegro netlist boundary`

Do not push without explicit authorization.
