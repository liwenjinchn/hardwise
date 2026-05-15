"""Common EDA adapter data shapes."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ComponentRecord(BaseModel):
    """A component-like item parsed from an EDA source."""

    refdes: str
    value: str = ""
    footprint: str = ""
    datasheet: str = ""
    source_file: Path
    source_kind: str


class NcPinRecord(BaseModel):
    """A pin that has a no_connect marker placed on it."""

    refdes: str
    pin_number: str
    pin_name: str
    pin_electrical_type: str
    source_file: Path


class NetMemberRecord(BaseModel):
    """One (refdes, pad) endpoint of a PCB net.

    PCB-side shape: pad numbers only exist after layout. The future
    schematic-side net record will reference symbol pin numbers, not pads.
    """

    refdes: str
    pad: str


class PcbNetRecord(BaseModel):
    """A net parsed from a ``.kicad_pcb`` file — name plus its pad members.

    PCB-side fact: includes both engineer-meaningful signals and KiCad's
    auto ``unconnected-(Ref-Pad)`` entries for dangling pads. **Not valid
    as pre-Layout schematic-review evidence** — a `.kicad_pcb` doesn't
    exist at the schematic-review node. Use this for diagnostics on
    already-laid-out demo projects, or feed it into post-layout rules.
    """

    name: str
    members: list[NetMemberRecord] = Field(default_factory=list)
    source_file: Path


class BoardRegistry(BaseModel):
    """Refdes registry used by tools and guardrails."""

    project_dir: Path
    components: list[ComponentRecord] = Field(default_factory=list)
    schematic_records: list[ComponentRecord] = Field(default_factory=list)
    pcb_records: list[ComponentRecord] = Field(default_factory=list)
    nc_pins: list[NcPinRecord] = Field(default_factory=list)
    pcb_nets: list[PcbNetRecord] = Field(default_factory=list)

    @property
    def refdes_set(self) -> set[str]:
        return {component.refdes for component in self.components}

    def has_refdes(self, refdes: str) -> bool:
        return refdes in self.refdes_set
