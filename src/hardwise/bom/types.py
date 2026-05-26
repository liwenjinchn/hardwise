"""BOM data models for schematic component matching."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field


REFDES_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{0,15}\b")


class BomParseError(ValueError):
    """Raised when a BOM file cannot be parsed as a schematic BOM."""


class BomRow(BaseModel):
    """One expanded BOM identity row for exactly one refdes."""

    refdes: str
    quantity: int | None = 1
    value: str | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    description: str | None = None
    source_file: Path
    source_line: int
    item_number: str | None = None
    item_quantity: int | None = None


class BomItem(BaseModel):
    """One grouped BOM line item before refdes expansion."""

    item_number: str | None = None
    quantity: int | None = None
    refdes_list: list[str] = Field(default_factory=list)
    value: str | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    description: str | None = None
    source_file: Path
    source_line: int
    raw_refdes: str = ""

    def rows(self) -> list[BomRow]:
        """Expand a grouped item into one row per refdes."""
        return [
            BomRow(
                refdes=refdes,
                quantity=1,
                value=self.value,
                manufacturer=self.manufacturer,
                part_number=self.part_number,
                description=self.description,
                source_file=self.source_file,
                source_line=self.source_line,
                item_number=self.item_number,
                item_quantity=self.quantity,
            )
            for refdes in self.refdes_list
        ]


class Bom(BaseModel):
    """Parsed schematic BOM with grouped items and expanded refdes rows."""

    source_file: Path
    items: list[BomItem] = Field(default_factory=list)

    @property
    def rows(self) -> list[BomRow]:
        return [row for item in self.items for row in item.rows()]

    @property
    def refdes_set(self) -> set[str]:
        return {row.refdes for row in self.rows}

    @property
    def non_refdes_items(self) -> list[BomItem]:
        """Items that carry no schematic refdes and should not join to Design."""
        return [item for item in self.items if not item.refdes_list]


class BomQuantityMismatch(BaseModel):
    """A BOM item whose declared quantity does not match its refdes list."""

    item_number: str | None
    quantity: int
    refdes_count: int
    refdes_list: list[str]
    source_file: Path
    source_line: int


class BomMatchReport(BaseModel):
    """Result of joining a BOM to a schematic ``Design`` by refdes."""

    bom_file: Path
    design_refdes_count: int
    bom_item_count: int
    non_refdes_item_count: int
    bom_row_count: int
    bom_refdes_count: int
    matched_refdes: list[str] = Field(default_factory=list)
    bom_only_refdes: list[str] = Field(default_factory=list)
    design_only_refdes: list[str] = Field(default_factory=list)
    duplicate_bom_refdes: list[str] = Field(default_factory=list)
    quantity_mismatches: list[BomQuantityMismatch] = Field(default_factory=list)
    rows_by_refdes: dict[str, BomRow] = Field(default_factory=dict)

    @property
    def is_clean(self) -> bool:
        """True when BOM and Design refdes registries match without ambiguity."""
        return not (
            self.bom_only_refdes
            or self.design_only_refdes
            or self.duplicate_bom_refdes
            or self.quantity_mismatches
        )


def split_refdes(text: str) -> list[str]:
    """Extract refdes-looking tokens from a BOM Reference cell."""
    return REFDES_PATTERN.findall(text.upper())


def sort_refdes_key(refdes: str) -> tuple[str, int, str]:
    """Human-friendly refdes sort key: C2 before C10."""
    match = re.fullmatch(r"([A-Z_]+)(\d+)(.*)", refdes)
    if match is None:
        return (refdes, -1, "")
    prefix, number, suffix = match.groups()
    return (prefix, int(number), suffix)
