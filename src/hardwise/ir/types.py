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

from pathlib import Path
from typing import Literal, Optional

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
