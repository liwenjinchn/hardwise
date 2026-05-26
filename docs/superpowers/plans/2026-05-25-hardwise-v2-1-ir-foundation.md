# Hardwise V2.1 — IR Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `src/hardwise/ir/` module containing `Pin / Component / Net / Design` types plus a `build_design()` aggregator that produces a `Design` from the existing `BoardRegistry`, without changing any user-facing CLI behavior.

**Architecture:** Layered IR — `adapters/` still parses KiCad/Allegro into parse-level records (`ComponentRecord`, `NcPinRecord`); new `ir/build.py` aggregates those records into semantic `Component` objects holding `Pin` lists and (eventually) `findings`. `Design.refdes_set` is a compatibility hook so `Refdes Guard` continues to work unchanged.

**Tech Stack:** Python 3.11+, pydantic 2 (`BaseModel`, matches existing codebase), pytest, uv.

**Scope boundary:**
- V2.1 only adds new modules. Zero existing files are modified.
- After V2.1, `hardwise review` output is byte-identical to V1 (no behavior change).
- `Component.pins` in V2.1 contains **only NC pins** (sourced from `BoardRegistry.nc_pins`). V2.4's plan will extend `adapters/kicad_pins.py` to parse non-NC pins for `DS001` lookup-by-name.
- `Design.nets` in V2.1 is always `{}`. V2.5's plan will populate it from the Allegro netlist parser.
- This plan covers V2.1 only. V2.2/V2.3/V2.4/V2.5 will each get their own plan after V2.1 ships, so reality informs the next step.

**Spec reference:** `docs/superpowers/specs/2026-05-24-hardwise-v2-design.md` §3.2 IR types + §4 V2.1 sub-slice.

**Estimated time:** ~1.5 day (per spec V2.1 line).

---

## File Structure

### Created by this plan

| File | Responsibility |
|---|---|
| `src/hardwise/ir/__init__.py` | Re-exports `Pin / Component / Net / Design` so callers do `from hardwise.ir import ...`. |
| `src/hardwise/ir/types.py` | `Pin / Component / Net / Design` pydantic `BaseModel` definitions. ~130 lines target. |
| `src/hardwise/ir/build.py` | `_build_pin_from_nc()` helper + `build_design(registry)` aggregator. ~50 lines target. |
| `tests/ir/__init__.py` | Empty package marker. |
| `tests/ir/test_types.py` | Unit tests for `Pin / Component / Net / Design` construction + helpers. |
| `tests/ir/test_build.py` | Unit + integration tests for `build_design()` (uses `pic_programmer` as the integration fixture). |

### NOT touched by this plan (locked)

- `src/hardwise/adapters/` — parse-level records unchanged; `BoardRegistry` semantics preserved.
- `src/hardwise/checklist/` — `Finding` and rules untouched.
- `src/hardwise/agent/`, `guards/`, `report/`, `store/`, `cli.py` — none touched.
- All V1 tests must continue to pass without modification.

---

## Task 1: Scaffold `ir/` module

**Files:**
- Create: `src/hardwise/ir/__init__.py` (empty)
- Create: `src/hardwise/ir/types.py` (empty)
- Create: `src/hardwise/ir/build.py` (empty)
- Create: `tests/ir/__init__.py` (empty)

- [ ] **Step 1: Verify the module does not already exist**

Run: `ls src/hardwise/ir 2>/dev/null; ls tests/ir 2>/dev/null; echo done`

Expected output:
```
done
```

(no listing — neither directory exists yet)

- [ ] **Step 2: Create directories and empty files**

Run:
```bash
mkdir -p src/hardwise/ir tests/ir
touch src/hardwise/ir/__init__.py src/hardwise/ir/types.py src/hardwise/ir/build.py tests/ir/__init__.py
```

- [ ] **Step 3: Verify existing test suite still passes**

Run: `uv run pytest -q`

Expected: `163 passed, 7 deselected` (V1 baseline). Empty new files do not affect anything.

- [ ] **Step 4: Commit**

```bash
git add src/hardwise/ir/__init__.py src/hardwise/ir/types.py src/hardwise/ir/build.py tests/ir/__init__.py
git commit -m "$(cat <<'EOF'
feat(ir): scaffold ir module structure

Empty __init__.py + types.py + build.py + tests/ir/. Module
exists in the tree but exports nothing yet. Subsequent tasks land
the Pin/Component/Net/Design types and build_design() aggregator.

Part of V2.1 (component-centric IR foundation).
See docs/superpowers/plans/2026-05-25-hardwise-v2-1-ir-foundation.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `Pin` BaseModel

**Files:**
- Modify: `src/hardwise/ir/types.py`
- Modify: `tests/ir/test_types.py` (create with first tests)

- [ ] **Step 1: Write the failing test**

Replace contents of `tests/ir/test_types.py` with:

```python
"""Tests for Pin / Component / Net / Design IR types."""

from __future__ import annotations

from hardwise.ir.types import Pin


def test_pin_minimal_construction() -> None:
    """Pin built with required fields only — optional fields default sensibly."""
    pin = Pin(
        number="1",
        name="Vin",
        electrical_type="power_in",
        is_nc=False,
    )
    assert pin.number == "1"
    assert pin.name == "Vin"
    assert pin.electrical_type == "power_in"
    assert pin.is_nc is False
    assert pin.net is None
    assert pin.datasheet_function is None
    assert pin.findings == []


def test_pin_with_all_optional_fields() -> None:
    """Pin built with every field set."""
    pin = Pin(
        number="A2",
        name="GPIO_A2",
        electrical_type="bidirectional",
        is_nc=False,
        net="LED_DRIVE",
        datasheet_function="GPIO with internal pull-up",
    )
    assert pin.net == "LED_DRIVE"
    assert pin.datasheet_function == "GPIO with internal pull-up"


def test_pin_nc_flag_true() -> None:
    """Pin marked as no-connect — schematic NC marker present."""
    pin = Pin(
        number="3",
        name="NC",
        electrical_type="no_connect",
        is_nc=True,
    )
    assert pin.is_nc is True


def test_pin_findings_default_is_independent_list() -> None:
    """Each Pin gets its own findings list (no shared-default-list bug)."""
    p1 = Pin(number="1", name="A", electrical_type="input", is_nc=False)
    p2 = Pin(number="2", name="B", electrical_type="input", is_nc=False)
    p1.findings.append("sentinel")  # type: ignore[arg-type]
    assert p2.findings == []
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: `ImportError` — `Pin` is not defined in `hardwise.ir.types`. Test collection fails before any test runs.

- [ ] **Step 3: Implement `Pin`**

Write to `src/hardwise/ir/types.py`:

```python
"""IR types: Pin / Component / Net / Design.

V2 architecture — Component is the first-class entity. Parse-level
records from ``adapters/`` get aggregated into Component objects via
``ir/build.py``. Compared to BoardRegistry (which is a bag of
parse-level records), a Design owns the per-component object graph
that reviews and reports work against.

Pydantic BaseModel is used here (not @dataclass) to stay consistent
with ``adapters/base.py`` and ``checklist/finding.py`` — both already
use BaseModel, and V2.4 will need JSON round-trip on DatasheetProfile,
so the IR layer commits to the same serialisation foundation.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from hardwise.checklist.finding import Finding


class Pin(BaseModel):
    """One pin of one Component instance.

    Schematic-side fields (``number``, ``name``, ``electrical_type``,
    ``is_nc``, ``net``) come from the KiCad / Allegro adapter at parse
    time. Datasheet-side ``datasheet_function`` is filled later by
    V2.4 datasheet-driven checks. ``findings`` accumulates pin-scoped
    review issues — the runner attaches them during V2.2.
    """

    number: str
    name: str
    electrical_type: str
    is_nc: bool
    net: Optional[str] = None
    datasheet_function: Optional[str] = None
    findings: list[Finding] = Field(default_factory=list)
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: `4 passed`.

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/hardwise/ir tests/ir && uv run ruff format src/hardwise/ir tests/ir`

Expected: `All checks passed!` for the lint pass; format may reformat to canonical style.

- [ ] **Step 6: Commit**

```bash
git add src/hardwise/ir/types.py tests/ir/test_types.py
git commit -m "$(cat <<'EOF'
feat(ir): add Pin BaseModel

Pin = one pin of one Component instance. Schematic-side fields
(number, name, electrical_type, is_nc, net) + datasheet-side
(datasheet_function, filled later by V2.4 checks) + findings
list for pin-scoped review issues.

Uses pydantic BaseModel to stay consistent with adapters/base.py
and checklist/finding.py — V2.4 DatasheetProfile will need JSON
round-trip on the IR layer.

Part of V2.1 (component-centric IR foundation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `Component` BaseModel

**Files:**
- Modify: `src/hardwise/ir/types.py`
- Modify: `tests/ir/test_types.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/ir/test_types.py`:

```python
from hardwise.ir.types import Component


def test_component_minimal_construction() -> None:
    """Component with only the required ``refdes`` and ``value``."""
    c = Component(refdes="U1", value="L7805")
    assert c.refdes == "U1"
    assert c.value == "L7805"
    assert c.package is None
    assert c.part_number is None
    assert c.manufacturer is None
    assert c.datasheet_path is None
    assert c.datasheet_profile is None
    assert c.pins == []
    assert c.properties == {}
    assert c.findings == []
    assert c.decision is None


def test_component_pin_by_number_returns_pin() -> None:
    """``pin_by_number()`` returns the Pin whose number matches."""
    c = Component(
        refdes="U1",
        value="L7805",
        pins=[
            Pin(number="1", name="Vin", electrical_type="power_in", is_nc=False),
            Pin(number="2", name="GND", electrical_type="power_in", is_nc=False),
            Pin(number="3", name="Vout", electrical_type="power_out", is_nc=False),
        ],
    )
    pin = c.pin_by_number("2")
    assert pin is not None
    assert pin.name == "GND"


def test_component_pin_by_number_returns_none_when_missing() -> None:
    """``pin_by_number()`` returns None when no pin matches."""
    c = Component(refdes="U1", value="L7805")
    assert c.pin_by_number("99") is None


def test_component_pin_by_name_returns_pin() -> None:
    """``pin_by_name()`` returns the Pin whose name matches (exact match)."""
    c = Component(
        refdes="U1",
        value="L7805",
        pins=[
            Pin(number="1", name="Vin", electrical_type="power_in", is_nc=False),
        ],
    )
    pin = c.pin_by_name("Vin")
    assert pin is not None
    assert pin.number == "1"


def test_component_pin_by_name_returns_none_when_missing() -> None:
    """``pin_by_name()`` returns None when no pin matches."""
    c = Component(refdes="U1", value="L7805")
    assert c.pin_by_name("VBUS") is None


def test_component_decision_literal_accepts_pass_warn_fail() -> None:
    """``decision`` field accepts only the three V2 verdicts."""
    Component(refdes="U1", value="L7805", decision="pass")
    Component(refdes="U1", value="L7805", decision="warn")
    Component(refdes="U1", value="L7805", decision="fail")
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: `ImportError` — `Component` is not defined yet. (Pin tests still pass; new tests fail at collection.)

- [ ] **Step 3: Implement `Component`**

Append to `src/hardwise/ir/types.py`:

```python
from typing import Literal


ComponentDecision = Literal["pass", "warn", "fail"]


class Component(BaseModel):
    """One component (refdes-keyed) on the schematic — V2 first-class entity.

    The Design holds a dict[refdes -> Component]. A Component owns its
    Pin list and accumulates findings (component-scoped) plus a rolled-up
    ``decision`` written by the V2.2 runner. V2.4 will attach
    ``datasheet_profile`` once an extracted profile JSON exists.

    ``datasheet_profile`` is left as Optional[object] in V2.1 — the
    actual ``DatasheetProfile`` BaseModel ships in V2.4. Typing it as
    Optional[object] here lets V2.1 round-trip JSON without depending
    on a type that does not exist yet.
    """

    refdes: str
    value: str = ""
    package: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer: Optional[str] = None
    datasheet_path: Optional[str] = None
    datasheet_profile: Optional[object] = None
    pins: list[Pin] = Field(default_factory=list)
    properties: dict[str, Optional[str]] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    decision: Optional[ComponentDecision] = None

    def pin_by_number(self, number: str) -> Optional[Pin]:
        """Return the Pin with ``number`` matching, else None."""
        return next((p for p in self.pins if p.number == number), None)

    def pin_by_name(self, name: str) -> Optional[Pin]:
        """Return the Pin with ``name`` matching exactly, else None.

        V2.1 note: only NC pins are populated — non-NC pins like "Vin"
        won't be found until V2.4 extends kicad pin parsing. This method
        already supports the V2.4 use-case so callers (DS001) don't have
        to change later.
        """
        return next((p for p in self.pins if p.name == name), None)
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: All Pin and Component tests pass (~10 tests passing).

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/hardwise/ir tests/ir && uv run ruff format src/hardwise/ir tests/ir`

Expected: `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add src/hardwise/ir/types.py tests/ir/test_types.py
git commit -m "$(cat <<'EOF'
feat(ir): add Component BaseModel + pin lookup helpers

Component = refdes-keyed first-class entity holding pins, findings,
and a rolled-up decision (pass/warn/fail). pin_by_number() and
pin_by_name() let checks look up pins without scanning. V2.1 keeps
datasheet_profile typed as Optional[object] so V2.4 can land the
real DatasheetProfile BaseModel without breaking imports.

Part of V2.1 (component-centric IR foundation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `Net` BaseModel

**Files:**
- Modify: `src/hardwise/ir/types.py`
- Modify: `tests/ir/test_types.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/ir/test_types.py`:

```python
from hardwise.ir.types import Net


def test_net_minimal_construction() -> None:
    """Net with only the required ``name`` and empty ``nodes``."""
    net = Net(name="+5V", nodes=[])
    assert net.name == "+5V"
    assert net.nodes == []
    assert net.is_power_rail is False
    assert net.voltage_hint is None


def test_net_with_nodes() -> None:
    """Net carries refdes/pin tuples as nodes."""
    net = Net(
        name="VCC",
        nodes=[("U1", "8"), ("C1", "1"), ("C2", "1")],
        is_power_rail=True,
        voltage_hint=5.0,
    )
    assert len(net.nodes) == 3
    assert ("U1", "8") in net.nodes
    assert net.is_power_rail is True
    assert net.voltage_hint == 5.0
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: `ImportError` — `Net` not yet defined.

- [ ] **Step 3: Implement `Net`**

Append to `src/hardwise/ir/types.py`:

```python
class Net(BaseModel):
    """A schematic / netlist net.

    V2.1 only builds Designs from KiCad pre-Layout parsing which does
    not yet expose schematic nets — so ``Design.nets`` is empty in V2.1.
    V2.5's Allegro netlist adapter is the first path that actually
    populates nets. Power-rail metadata (``is_power_rail``,
    ``voltage_hint``) is reserved for V3 power-rail-audit work.
    """

    name: str
    nodes: list[tuple[str, str]] = Field(default_factory=list)
    is_power_rail: bool = False
    voltage_hint: Optional[float] = None
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: All tests pass (~12 tests passing).

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/hardwise/ir tests/ir && uv run ruff format src/hardwise/ir tests/ir`

Expected: `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add src/hardwise/ir/types.py tests/ir/test_types.py
git commit -m "$(cat <<'EOF'
feat(ir): add Net BaseModel

Net carries name + nodes (list of (refdes, pin_number) tuples) plus
optional power-rail metadata reserved for V3. V2.1 leaves Design.nets
empty; V2.5 Allegro netlist adapter is the first populator.

Part of V2.1 (component-centric IR foundation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `Design` BaseModel + `__init__.py` exports

**Files:**
- Modify: `src/hardwise/ir/types.py`
- Modify: `src/hardwise/ir/__init__.py`
- Modify: `tests/ir/test_types.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/ir/test_types.py`:

```python
from pathlib import Path

from hardwise.ir.types import Design


def test_design_minimal_construction() -> None:
    """Design with empty components and nets."""
    d = Design(
        components={},
        nets={},
        project_path=Path("/tmp/foo"),
        source_eda="kicad",
    )
    assert d.components == {}
    assert d.nets == {}
    assert d.source_eda == "kicad"


def test_design_refdes_set_property() -> None:
    """``refdes_set`` returns the set of component refdes — Refdes Guard hook."""
    d = Design(
        components={
            "U1": Component(refdes="U1", value="L7805"),
            "C1": Component(refdes="C1", value="0.33uF"),
        },
        nets={},
        project_path=Path("/tmp/foo"),
        source_eda="kicad",
    )
    assert d.refdes_set == {"U1", "C1"}


def test_design_refdes_set_empty() -> None:
    """``refdes_set`` is empty when no components are loaded."""
    d = Design(
        components={},
        nets={},
        project_path=Path("/tmp/foo"),
        source_eda="kicad",
    )
    assert d.refdes_set == set()


def test_design_source_eda_literal_accepts_kicad_and_allegro() -> None:
    """``source_eda`` only accepts the two adapters Hardwise ships."""
    Design(components={}, nets={}, project_path=Path("/tmp"), source_eda="kicad")
    Design(
        components={},
        nets={},
        project_path=Path("/tmp"),
        source_eda="allegro_netlist",
    )
```

Then add to the same test file a test verifying the top-level import works:

```python
def test_ir_package_exports() -> None:
    """``from hardwise.ir import Pin, Component, Net, Design`` works."""
    from hardwise.ir import Component as ImpComponent
    from hardwise.ir import Design as ImpDesign
    from hardwise.ir import Net as ImpNet
    from hardwise.ir import Pin as ImpPin

    assert ImpPin is Pin
    assert ImpComponent is Component
    assert ImpNet is Net
    assert ImpDesign is Design
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: `ImportError` on the new Design tests; `test_ir_package_exports` also fails because `__init__.py` is empty.

- [ ] **Step 3: Implement `Design`**

Append to `src/hardwise/ir/types.py`:

```python
from pathlib import Path


SourceEda = Literal["kicad", "allegro_netlist"]


class Design(BaseModel):
    """The whole component-centric view of one schematic / netlist.

    ``components`` is keyed by refdes for O(1) lookup. ``refdes_set``
    is the compatibility hook the Refdes Guard uses — it must keep the
    same semantics as BoardRegistry.refdes_set so the guard does not
    need to learn about Design.
    """

    components: dict[str, Component] = Field(default_factory=dict)
    nets: dict[str, Net] = Field(default_factory=dict)
    project_path: Path
    source_eda: SourceEda

    @property
    def refdes_set(self) -> set[str]:
        """Set of refdes for guard / sanitizer compatibility."""
        return set(self.components.keys())
```

- [ ] **Step 4: Implement `__init__.py` exports**

Replace `src/hardwise/ir/__init__.py` with:

```python
"""V2 component-centric intermediate representation.

Re-exports the four core types so callers can do
``from hardwise.ir import Pin, Component, Net, Design``.
"""

from hardwise.ir.types import Component, Design, Net, Pin

__all__ = ["Component", "Design", "Net", "Pin"]
```

- [ ] **Step 5: Run the test, verify it passes**

Run: `uv run pytest tests/ir/test_types.py -v`

Expected: All tests pass (~17 tests passing).

- [ ] **Step 6: Lint and format**

Run: `uv run ruff check src/hardwise/ir tests/ir && uv run ruff format src/hardwise/ir tests/ir`

Expected: `All checks passed!`.

- [ ] **Step 7: Verify V1 test suite still green**

Run: `uv run pytest -q`

Expected: `163 + 17 = 180 passed, 7 deselected` (V1 baseline + new IR tests; exact added count depends on prior tasks, target is ≥180).

- [ ] **Step 8: Commit**

```bash
git add src/hardwise/ir/types.py src/hardwise/ir/__init__.py tests/ir/test_types.py
git commit -m "$(cat <<'EOF'
feat(ir): add Design BaseModel + package exports

Design = the whole component-centric view, keyed by refdes for O(1)
lookup. refdes_set property mirrors BoardRegistry.refdes_set semantics
so the Refdes Guard keeps working with no change. __init__.py exports
Pin / Component / Net / Design at package level.

V1 test suite still green (180 passed).

Part of V2.1 (component-centric IR foundation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `_build_pin_from_nc()` helper

**Files:**
- Modify: `src/hardwise/ir/build.py`
- Modify: `tests/ir/test_build.py` (create)

- [ ] **Step 1: Write the failing test**

Write to `tests/ir/test_build.py`:

```python
"""Tests for the build_design aggregator."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.base import NcPinRecord
from hardwise.ir.build import _build_pin_from_nc
from hardwise.ir.types import Pin


def test_build_pin_from_nc_record_marks_is_nc_true() -> None:
    """NcPinRecord → Pin always carries is_nc=True (because the record only
    exists when the schematic explicitly placed a no_connect marker)."""
    nc = NcPinRecord(
        refdes="U2",
        pin_number="5",
        pin_name="NC",
        pin_electrical_type="no_connect",
        source_file=Path("/tmp/example.kicad_sch"),
    )
    pin = _build_pin_from_nc(nc)
    assert isinstance(pin, Pin)
    assert pin.number == "5"
    assert pin.name == "NC"
    assert pin.electrical_type == "no_connect"
    assert pin.is_nc is True
    assert pin.net is None  # NC pins are not connected to any net
    assert pin.datasheet_function is None
    assert pin.findings == []


def test_build_pin_from_nc_preserves_non_default_pin_name() -> None:
    """NcPinRecord with a meaningful pin_name (e.g. 'FB-') survives the
    conversion — name is not forced to 'NC'."""
    nc = NcPinRecord(
        refdes="U4",
        pin_number="3",
        pin_name="FB-",
        pin_electrical_type="passive",
        source_file=Path("/tmp/example.kicad_sch"),
    )
    pin = _build_pin_from_nc(nc)
    assert pin.name == "FB-"
    assert pin.electrical_type == "passive"
    assert pin.is_nc is True
```

- [ ] **Step 2: Run the test, verify it fails**

Run: `uv run pytest tests/ir/test_build.py -v`

Expected: `ImportError` — `_build_pin_from_nc` not yet defined.

- [ ] **Step 3: Implement the helper**

Write to `src/hardwise/ir/build.py`:

```python
"""Aggregator from parse-level records to V2 IR Design.

KiCad path (V2.1): ``build_design(registry)`` — pulls components +
NC pin records out of the BoardRegistry the parser already populates.

Allegro netlist path (V2.5): ``build_design_from_netlist()`` lands in
a separate plan; this module will grow a second top-level function.
"""

from __future__ import annotations

from hardwise.adapters.base import NcPinRecord
from hardwise.ir.types import Pin


def _build_pin_from_nc(nc: NcPinRecord) -> Pin:
    """Convert one ``NcPinRecord`` (parse-level) into a Pin (IR-level).

    ``is_nc`` is always True because an NcPinRecord only exists when the
    schematic placed an explicit ``no_connect`` marker. ``net`` is left
    as None — NC pins are not connected to any net.
    """
    return Pin(
        number=nc.pin_number,
        name=nc.pin_name,
        electrical_type=nc.pin_electrical_type,
        is_nc=True,
        net=None,
    )
```

- [ ] **Step 4: Run the test, verify it passes**

Run: `uv run pytest tests/ir/test_build.py -v`

Expected: `2 passed`.

- [ ] **Step 5: Lint and format**

Run: `uv run ruff check src/hardwise/ir tests/ir && uv run ruff format src/hardwise/ir tests/ir`

Expected: `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add src/hardwise/ir/build.py tests/ir/test_build.py
git commit -m "$(cat <<'EOF'
feat(ir): add _build_pin_from_nc helper

Converts one NcPinRecord (parse-level) into a Pin (IR-level). is_nc
is hard-coded True because an NcPinRecord only exists when the
schematic placed an explicit no_connect marker. net is None because
NC pins are not connected to anything.

Part of V2.1 (component-centric IR foundation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `build_design()` main + `pic_programmer` integration

**Files:**
- Modify: `src/hardwise/ir/build.py`
- Modify: `tests/ir/test_build.py`

- [ ] **Step 1: Write the failing unit test (pure data, no fixture file)**

Append to `tests/ir/test_build.py`:

```python
from hardwise.adapters.base import BoardRegistry, ComponentRecord
from hardwise.ir.build import build_design
from hardwise.ir.types import Design


def _make_registry(
    project_dir: Path,
    components: list[ComponentRecord],
    nc_pins: list[NcPinRecord],
) -> BoardRegistry:
    """Build a minimal BoardRegistry for unit tests — no parser calls."""
    return BoardRegistry(
        project_dir=project_dir,
        components=components,
        nc_pins=nc_pins,
    )


def test_build_design_returns_design_with_correct_source_eda() -> None:
    """Empty registry produces an empty kicad-source Design."""
    registry = _make_registry(Path("/tmp/project"), [], [])
    design = build_design(registry)
    assert isinstance(design, Design)
    assert design.source_eda == "kicad"
    assert design.project_path == Path("/tmp/project")
    assert design.components == {}
    assert design.nets == {}


def test_build_design_keys_components_by_refdes() -> None:
    """Each ComponentRecord becomes one Component, keyed by refdes."""
    components = [
        ComponentRecord(
            refdes="U1",
            value="L7805",
            footprint="TO-220",
            datasheet="datasheets/l78.pdf",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
        ComponentRecord(
            refdes="C1",
            value="0.33uF",
            footprint="C_0805",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
    ]
    registry = _make_registry(Path("/tmp/proj"), components, [])
    design = build_design(registry)
    assert set(design.components.keys()) == {"U1", "C1"}
    u1 = design.components["U1"]
    assert u1.value == "L7805"
    assert u1.package == "TO-220"
    assert u1.datasheet_path == "datasheets/l78.pdf"
    assert u1.pins == []  # no NC pins in this registry


def test_build_design_attaches_nc_pins_to_correct_component() -> None:
    """NcPinRecord rows route to the matching Component by refdes."""
    components = [
        ComponentRecord(
            refdes="U4",
            value="LT1373",
            footprint="",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
        ComponentRecord(
            refdes="U2",
            value="PIC16F876",
            footprint="DIP-28",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        ),
    ]
    nc_pins = [
        NcPinRecord(
            refdes="U4",
            pin_number="3",
            pin_name="FB-",
            pin_electrical_type="passive",
            source_file=Path("/tmp/proj/main.kicad_sch"),
        ),
        NcPinRecord(
            refdes="U4",
            pin_number="6",
            pin_name="S/S",
            pin_electrical_type="passive",
            source_file=Path("/tmp/proj/main.kicad_sch"),
        ),
    ]
    registry = _make_registry(Path("/tmp/proj"), components, nc_pins)
    design = build_design(registry)
    assert len(design.components["U4"].pins) == 2
    assert design.components["U2"].pins == []  # no NC pin for U2


def test_build_design_refdes_set_matches_registry() -> None:
    """``Design.refdes_set`` equals ``BoardRegistry.refdes_set`` — Refdes
    Guard compatibility invariant."""
    components = [
        ComponentRecord(
            refdes=r,
            value="",
            footprint="",
            datasheet="",
            source_file=Path("/tmp/proj/main.kicad_sch"),
            source_kind="schematic",
        )
        for r in ["U1", "U2", "C1", "R1"]
    ]
    registry = _make_registry(Path("/tmp/proj"), components, [])
    design = build_design(registry)
    assert design.refdes_set == registry.refdes_set
```

- [ ] **Step 2: Write the failing integration test against `pic_programmer`**

Append to `tests/ir/test_build.py`:

```python
import pytest

from hardwise.adapters.kicad import parse_project


@pytest.fixture(scope="module")
def pic_programmer_design() -> Design:
    """Real integration: parse pic_programmer → build Design."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    return build_design(registry)


def test_build_design_pic_programmer_component_count(
    pic_programmer_design: Design,
) -> None:
    """pic_programmer has 121 parsed components — Design must preserve count."""
    assert len(pic_programmer_design.components) == 121


def test_build_design_pic_programmer_refdes_set_compatible(
    pic_programmer_design: Design,
) -> None:
    """Refdes Guard compatibility: Design.refdes_set is unchanged shape."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    assert pic_programmer_design.refdes_set == registry.refdes_set


def test_build_design_pic_programmer_some_components_have_nc_pins(
    pic_programmer_design: Design,
) -> None:
    """pic_programmer has 77 NC pins across components — at least U4 has some."""
    u4 = pic_programmer_design.components.get("U4")
    assert u4 is not None
    assert len(u4.pins) > 0  # U4 = LT1373 has FB-, S/S NC pins
    assert all(p.is_nc for p in u4.pins)  # all V2.1 pins are NC pins
```

- [ ] **Step 3: Run all build tests, verify they fail**

Run: `uv run pytest tests/ir/test_build.py -v`

Expected: `ImportError` on `build_design` not defined; unit tests + integration tests all fail at collection.

- [ ] **Step 4: Implement `build_design()`**

Append to `src/hardwise/ir/build.py`:

```python
from hardwise.adapters.base import BoardRegistry
from hardwise.ir.types import Component, Design


def build_design(registry: BoardRegistry) -> Design:
    """Aggregate a KiCad-parsed BoardRegistry into a V2 Design.

    Each ComponentRecord becomes one Component. NcPinRecord rows are
    grouped by refdes and attached as ``Pin`` objects on the matching
    Component. V2.1 leaves ``Design.nets`` empty — schematic-side net
    parsing is V2.5+. Components whose refdes has no NcPinRecord get
    an empty pin list (no shared mutable default).
    """
    nc_by_refdes: dict[str, list] = {}
    for nc in registry.nc_pins:
        nc_by_refdes.setdefault(nc.refdes, []).append(nc)

    components: dict[str, Component] = {}
    for record in registry.components:
        pins = [_build_pin_from_nc(nc) for nc in nc_by_refdes.get(record.refdes, [])]
        components[record.refdes] = Component(
            refdes=record.refdes,
            value=record.value,
            package=record.footprint or None,
            datasheet_path=record.datasheet or None,
            pins=pins,
        )

    return Design(
        components=components,
        nets={},
        project_path=registry.project_dir,
        source_eda="kicad",
    )
```

- [ ] **Step 5: Run all build tests, verify they pass**

Run: `uv run pytest tests/ir/test_build.py -v`

Expected: All 7 tests pass (4 unit + 3 integration).

- [ ] **Step 6: Run the full suite, verify V1 baseline still green**

Run: `uv run pytest -q`

Expected: `~187 passed, 7 deselected` (163 V1 + ~17 type tests + 7 build tests).

- [ ] **Step 7: Lint and format**

Run: `uv run ruff check . && uv run ruff format --check src/hardwise/ir tests/ir`

Expected: `All checks passed!`.

- [ ] **Step 8: Commit**

```bash
git add src/hardwise/ir/build.py tests/ir/test_build.py
git commit -m "$(cat <<'EOF'
feat(ir): add build_design() KiCad aggregator

Aggregates BoardRegistry + NcPinRecord rows into a Design.
Each ComponentRecord becomes one Component, NC pins route by refdes,
Design.nets stays empty until V2.5 Allegro netlist adapter.

Integration test on pic_programmer: 121 components, refdes_set
matches BoardRegistry's exactly (Refdes Guard compatibility),
U4 carries its NC pins through (LT1373 FB-, S/S).

V1 test suite still green.

Part of V2.1 (component-centric IR foundation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: V2.1 closeout — regression + learning log

**Files:**
- Modify: `docs/learning_log.md`

- [ ] **Step 1: Run full test suite and capture exact counts**

Run: `uv run pytest -q 2>&1 | tail -5`

Expected output (exact number depends on intermediate task test counts):
```
~187 passed, 7 deselected in <time>s
```

Record the actual counts — they go into the learning_log entry.

- [ ] **Step 2: Run ruff full check**

Run: `uv run ruff check . && uv run ruff format --check .`

Expected: `All checks passed!`.

- [ ] **Step 3: Verify the new module loads cleanly from a shell**

Run:
```bash
uv run python -c "
from hardwise.ir import Pin, Component, Net, Design
from hardwise.ir.build import build_design
from hardwise.adapters.kicad import parse_project
from pathlib import Path

registry = parse_project(Path('data/projects/pic_programmer'))
design = build_design(registry)
print(f'components={len(design.components)}, source_eda={design.source_eda}')
print(f'refdes_set size={len(design.refdes_set)}')
u4 = design.components.get('U4')
if u4:
    print(f'U4 pins (NC only in V2.1): {len(u4.pins)}')
"
```

Expected output:
```
components=121, source_eda=kicad
refdes_set size=121
U4 pins (NC only in V2.1): 2
```

- [ ] **Step 4: Add learning_log entry**

Append to `docs/learning_log.md` (top of the file under any header, following the existing format):

```markdown
## 2026-05-25 — V2.1 IR foundation closed

**Symptom:** none (greenfield slice).

**What shipped:** `src/hardwise/ir/{__init__.py, types.py, build.py}` plus `tests/ir/{test_types.py, test_build.py}`. `Pin / Component / Net / Design` BaseModels + `build_design(registry)` KiCad aggregator. ~187 tests pass, ruff clean. `hardwise review` CLI behavior unchanged (V2.1 only adds new modules).

**Two reconciliations with the V2 spec made during planning:**

1. Spec used `@dataclass` for IR types; existing codebase (`adapters/base.py`, `checklist/finding.py`) uses pydantic `BaseModel`. Plan chose BaseModel for codebase consistency + JSON round-trip headroom V2.4 will need.
2. Spec §3.7 DS001 example referenced `Finding.pin_number`, which doesn't exist on the `Finding` BaseModel. V2.1 deferred this — V2.2 plan will add `pin_number: str | None = None` to `Finding` as a backward-compatible optional field (mirrors the DR-009 extension pattern).

**Takeaway:** When the brainstorm uses informal `@dataclass` sketches, the implementation plan should reconcile against the codebase's actual model framework. Carrying the inconsistency forward would force a mid-sub-slice refactor.

**Next:** V2.2 plan (per-component check flip + `Finding.pin_number` extension + R001-R003 outer-loop rewrite). To be drafted in a fresh planning session.
```

- [ ] **Step 5: Commit closeout**

```bash
git add docs/learning_log.md
git commit -m "$(cat <<'EOF'
docs(learning-log): V2.1 IR foundation closed

187 tests pass, ruff clean, hardwise review CLI behavior unchanged.

Two reconciliations with the V2 spec captured: BaseModel vs dataclass
(picked BaseModel for codebase consistency), Finding.pin_number
deferred to V2.2 plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Final git status check**

Run: `git log --oneline -10 && echo "---" && git status --short | head -20`

Expected: 8 new commits on top of `2021bac` (`docs(spec): land V2 component-centric design`), each scoped to one task. Pre-existing dirty working tree (PLAN.md, README.md, etc.) untouched.

---

## V2.1 acceptance gate

V2.1 is closed when:

1. `uv run pytest -q` passes with ≥187 passing tests (163 V1 baseline + ≥24 new).
2. `uv run ruff check . && uv run ruff format --check .` returns `All checks passed!`.
3. `uv run hardwise review data/projects/pic_programmer --rules R001,R002,R003` produces **the same 28 findings** as V1 (V2.1 does not change CLI behavior — proves the new modules are dormant from the runner's perspective).
4. `from hardwise.ir import Pin, Component, Net, Design` works.
5. `build_design(registry)` on `pic_programmer` returns a `Design` with 121 components, `refdes_set` matches `BoardRegistry.refdes_set` exactly, `U4` carries its 2 NC pins.
6. `docs/learning_log.md` has a `2026-05-25 — V2.1 IR foundation closed` entry.
7. Eight new commits land on `main`, each isolated to one task.

---

## Out of scope for this plan

The following are explicitly deferred to subsequent V2.* plans:

- **V2.2 plan** — Add `Finding.pin_number` field. Define `ComponentCheck` protocol + `CheckSpec`. Rewrite R001 / R002 / R003 outer loops into the new protocol. Update CLI runner to per-component dispatch. V1 finding-count snapshot test (lock 28 findings).
- **V2.3 plan** — `report/component_centric.py` 6-section markdown template + HTML companion + `--report-style` flag.
- **V2.4 plan** — `DatasheetProfile` BaseModel + JSON load/save. Extend `adapters/kicad_pins.py` to parse non-NC pins (needed for `pin_by_name("Vin")` lookup). `ingest-datasheet --extract-profile` CLI. `DS001` check.
- **V2.5 plan** — `adapters/allegro_netlist.py` ASCII parser + `build_design_from_netlist()` + CLI input detection.

Each gets its own brainstorming + writing-plans session once V2.1 ships.
