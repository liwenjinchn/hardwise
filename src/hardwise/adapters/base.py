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


class BoardRegistry(BaseModel):
    """Refdes registry used by tools and guardrails."""

    project_dir: Path
    components: list[ComponentRecord] = Field(default_factory=list)
    schematic_records: list[ComponentRecord] = Field(default_factory=list)
    pcb_records: list[ComponentRecord] = Field(default_factory=list)

    @property
    def refdes_set(self) -> set[str]:
        return {component.refdes for component in self.components}

    def has_refdes(self, refdes: str) -> bool:
        return refdes in self.refdes_set
