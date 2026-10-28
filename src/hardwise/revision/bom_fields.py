"""Compare declared BOM cells, not inferred electrical values or grouped row counts."""

from collections import defaultdict
import re

from hardwise.bom.identity_fields import identity_dimension
from hardwise.bom.types import BomRow
from hardwise.revision.models import Observation, SourceEvidence

# These describe the export's grouping/order, not an individual component parameter.
STRUCTURAL_COLUMNS = {
    "reference",
    "references",
    "refdes",
    "designator",
    "位号",
    "quantity",
    "qty",
    "数量",
    "item",
    "itemnumber",
    "序号",
    "编号",
    "no",
    "序",
}
ALIASES = {
    "value": "value",
    "part": "value",
    "名称": "value",
    "description": "description",
    "desc": "description",
    "描述": "description",
}


def column_key(name: str) -> str:
    return re.sub(r"[\s_/-]+", "", name).casefold()


def bom_observations(row: BomRow, sha256: str) -> dict[str, Observation]:
    columns = defaultdict(list)
    for field in row.source_fields:
        key = column_key(field.name)
        if key in STRUCTURAL_COLUMNS:
            continue
        canonical = identity_dimension(field.name) or ALIASES.get(key, key)
        columns["bom." + canonical].append(field)
    result = {}
    for key, fields in sorted(columns.items()):
        # A missing cell remains missing; source order does not select a winner.
        values = tuple(sorted({field.value.strip() for field in fields if field.value.strip()}))
        result[key] = Observation(
            state="ambiguous" if len(values) > 1 else "known" if values else "missing",
            values=values,
            evidence=tuple(
                SourceEvidence(
                    file=row.source_file.name,
                    sha256=sha256,
                    locator=f"line {row.source_line}; column {field.column} ({field.name}); {row.refdes}",
                )
                for field in fields
            ),
        )
    return result
