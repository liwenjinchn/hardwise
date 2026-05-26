"""BOM parsing and component identity matching."""

from hardwise.bom.matcher import apply_bom_to_design, match_bom_to_design
from hardwise.bom.parser import parse_bom
from hardwise.bom.types import (
    Bom,
    BomParseError,
    BomItem,
    BomMatchReport,
    BomQuantityMismatch,
    BomRow,
)

__all__ = [
    "Bom",
    "BomItem",
    "BomMatchReport",
    "BomParseError",
    "BomQuantityMismatch",
    "BomRow",
    "apply_bom_to_design",
    "match_bom_to_design",
    "parse_bom",
]
