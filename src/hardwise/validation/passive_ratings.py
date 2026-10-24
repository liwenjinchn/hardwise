"""Resolve passive ratings from all explicit Value tokens and named BOM columns."""

from dataclasses import dataclass
from fractions import Fraction
import math
import re
import json

from hardwise.bom.types import BomRow
from hardwise.bom.source_fields import RATING_SOURCES, rating_field_unit, is_value_source
from hardwise.validation.types import ComponentValidation

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:/\d+(?:\.\d*)?)?"
_TOKEN = re.compile(rf"(?<![\w.])({_NUMBER})\s*([mkM]?[VvWw])\b")
_CELL = re.compile(rf"^\s*({_NUMBER})\s*([mkM]?[VvWw])?\s*$")
_UNITS = {
    "V": ("voltage", Fraction(1)),
    "v": ("voltage", Fraction(1)),
    "mV": ("voltage", Fraction(1, 1000)),
    "kV": ("voltage", Fraction(1000)),
    "W": ("power", Fraction(1)),
    "w": ("power", Fraction(1)),
    "mW": ("power", Fraction(1, 1000)),
}


def _quantity(number, unit, dimension):
    if unit not in _UNITS or _UNITS[unit][0] != dimension:
        raise ValueError("missing or unsupported unit")
    if "/" in number and dimension != "power":
        raise ValueError("ambiguous voltage fraction")
    if "/" in number:
        numerator, denominator = number.split("/")
        amount = Fraction(numerator) / Fraction(denominator)
    else:
        amount = Fraction(number)
    amount *= _UNITS[unit][1]
    if amount <= 0 or not math.isfinite(float(amount)):
        raise ValueError("rating must be finite and positive")
    return amount


@dataclass
class PassiveRating:
    dimension: str
    value: float | None
    values: tuple[str, ...]
    invalid: tuple[str, ...]
    origins: list[str]
    evidence: list[str]
    issue: str

    def signature(self):
        # Raw field names/ordinals and unrelated notes are provenance, not
        # electrical dependencies. Exact rational quantities avoid float aliases.
        return {"dimension": self.dimension, "values": self.values, "invalid": self.invalid}


def resolve_passive_rating(
    value: str, row: BomRow | None, dimension: str, component=None
) -> PassiveRating:
    amounts, invalid, origins, evidence = set(), [], [], []

    def add_tokens(text, origin):
        matched = False
        for match in _TOKEN.finditer(text):
            number, unit = match.groups()
            if unit[-1].casefold() != ("v" if dimension == "voltage" else "w"):
                continue
            matched = True
            origins.append(f"{origin}={match.group(0)}")
            try:
                amounts.add(_quantity(number, unit, dimension))
            except (ValueError, ZeroDivisionError, OverflowError):
                invalid.append(match.group(0).strip())
        return matched

    add_tokens(value, "Value")
    rows = [row] if row is not None else []
    preserved = component.properties.get(RATING_SOURCES) if component is not None else None
    if preserved:
        try:
            rows.append(BomRow.model_validate(json.loads(preserved)))
        except (ValueError, TypeError):
            invalid.append("unreadable preserved BOM rating sources")
            origins.append("unreadable preserved BOM rating sources")
    seen = set()
    for source in rows:
        for field in source.source_fields:
            key = (
                str(source.source_file),
                source.source_line,
                field.column,
                field.name,
                field.value,
            )
            if key in seen:
                continue
            seen.add(key)
            if is_value_source(field.name):
                if field.value != value and add_tokens(
                    field.value, f"column {field.column} {field.name}"
                ):
                    evidence.append(
                        f"bom:{source.source_file.name}#line{source.source_line};column{field.column}"
                    )
                continue
            recognized, default_unit = rating_field_unit(field.name, dimension)
            if not recognized or not field.value.strip():
                continue
            origins.append(f"column {field.column} {field.name}={field.value}")
            evidence.append(
                f"bom:{source.source_file.name}#line{source.source_line};column{field.column}"
            )
            match = _CELL.fullmatch(field.value)
            try:
                if match is None:
                    raise ValueError("unparsed rating cell")
                number, explicit_unit = match.groups()
                if default_unit and (
                    default_unit not in _UNITS or _UNITS[default_unit][0] != dimension
                ):
                    raise ValueError("header unit has wrong dimension")
                amounts.add(_quantity(number, explicit_unit or default_unit, dimension))
            except (ValueError, ZeroDivisionError, OverflowError):
                invalid.append(field.value.strip())
    label = "额定电压" if dimension == "voltage" else "额定功率"
    issue = ""
    if invalid or len(amounts) > 1:
        issue = f"{label}来源未确认（冲突或单位/数值不可解析）：" + "；".join(origins)
    canonical = tuple(sorted(str(number) for number in amounts))
    return PassiveRating(
        dimension,
        float(next(iter(amounts))) if len(amounts) == 1 and not invalid else None,
        canonical,
        tuple(sorted(invalid)),
        origins,
        evidence,
        issue,
    )


def attach_rating_sources(check: ComponentValidation, rating: PassiveRating) -> ComponentValidation:
    data = {key: getattr(check, key) for key in ComponentValidation.model_fields}
    data["rule_version"] = "2"
    data["evidence"] = list(dict.fromkeys([*check.evidence, *rating.evidence]))
    if rating.issue:
        data.update(result="UNKNOWN", severity="INFO", needs_review=True)
        if check.check == "resistor_power_estimate":
            old = "power margin not evaluated: no explicit power rating in the BOM value"
            data["summary"] = check.summary.replace(old, rating.issue)
            if rating.issue not in data["summary"]:
                data["summary"] += "; " + rating.issue
        else:
            data["summary"] = "Capacitor rating/margin unresolved: " + rating.issue
    elif check.check == "capacitor_rated_voltage_parse" and rating.value is not None:
        data["summary"] = f"Capacitor rated voltage {rating.value:g} V resolved from " + "; ".join(
            rating.origins
        )
    elif rating.evidence:
        data["summary"] += " Rating sources: " + "; ".join(rating.origins)
    return ComponentValidation(**data)
