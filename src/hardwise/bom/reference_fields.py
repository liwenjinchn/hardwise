"""Retain all reference declarations and quarantine their unresolved candidate union."""

import re

from hardwise.bom.types import BomSourceField, split_refdes


def reference_columns(fields: list[BomSourceField]) -> list[BomSourceField]:
    return [
        field
        for field in fields
        if field.value.strip()
        and (
            field.name.strip() == "位号"
            or re.sub(r"[^a-z0-9]+", "_", field.name.strip().lower()).strip("_")
            in {"reference", "references", "refdes", "designator", "refs"}
        )
    ]


def has_reference_conflict(fields: list[BomSourceField]) -> bool:
    declarations = [frozenset(split_refdes(field.value)) for field in reference_columns(fields)]
    return len(set(declarations)) > 1


def reference_candidates(fields: list[BomSourceField]) -> list[str]:
    declarations = [split_refdes(field.value) for field in reference_columns(fields)]
    if not declarations:
        return []
    if not has_reference_conflict(fields):
        # Equivalent aliases do not multiply rows; preserve legacy within-cell duplicates.
        return declarations[0]
    return list(dict.fromkeys(ref for declaration in declarations for ref in declaration))


def reference_conflict_reason(record) -> str | None:
    if not has_reference_conflict(record.source_fields):
        return None
    declarations = "; ".join(
        f"column{field.column} [{field.name}={field.value}]"
        for field in reference_columns(record.source_fields)
    )
    return (
        "同一 BOM 行的位号声明互相不一致；隔离全部候选位号，不选择列优先级，"
        "不向候选器件套用该行身份或额定值。"
        f"来源：{record.source_file}#line{record.source_line}；{declarations}"
    )


def continued_reference_columns(previous, incoming):
    """Cadence continuation cells extend one declaration at the same column."""
    fields = {field.column: field for field in previous}
    for field in reference_columns(incoming):
        prior = fields.get(field.column)
        value = prior.value + " " + field.value if prior else field.value
        fields[field.column] = field.model_copy(update={"value": value})
    return list(fields.values())
