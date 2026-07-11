"""Compatibility entrypoint for deterministic generic-passive validation."""

from __future__ import annotations

from hardwise.bom.types import BomRow
from hardwise.ir.types import Component, Design
from hardwise.validation.passive_checks import (
    _capacitor_checks,
    _ferrite_checks,
    _inductor_checks,
    _resistor_checks,
)
from hardwise.validation.passive_contracts import (
    GENERIC_PASSIVE_REASON as GENERIC_PASSIVE_REASON,
    PROFILE_PART_BY_FAMILY,
    PassiveFamily,
)
from hardwise.validation.passive_helpers import (
    _bom_evidence,
    _component_value,
    _terminal_connectivity,
)
from hardwise.validation.types import ValidationReport
from hardwise.validation.value_parsing import (
    ParsedCurrentRating,
    ParsedImpedance,
    ParsedResistance,
    parse_capacitance_f,
    parse_current_rating_amps,
    parse_ferrite_impedance_ohms,
    parse_power_watts,
    parse_rated_voltage,
    parse_resistance_ohms,
)

__all__ = [
    "GENERIC_PASSIVE_REASON",
    "PassiveFamily",
    "ParsedCurrentRating",
    "ParsedImpedance",
    "ParsedResistance",
    "parse_capacitance_f",
    "parse_current_rating_amps",
    "parse_ferrite_impedance_ohms",
    "parse_power_watts",
    "parse_rated_voltage",
    "parse_resistance_ohms",
    "validate_generic_passive",
]


def validate_generic_passive(
    component: Component,
    bom_row: BomRow | None,
    design: Design,
    family: PassiveFamily,
) -> ValidationReport:
    """Validate common passive value/package facts without a per-MPN profile."""

    value = _component_value(component, bom_row)
    evidence = _bom_evidence(bom_row)
    pin_results = _terminal_connectivity(component, family, evidence)
    if family == "capacitor":
        checks = _capacitor_checks(component, value, design, evidence)
    elif family == "resistor":
        checks = _resistor_checks(component, value, design, evidence)
    elif family == "inductor":
        checks = _inductor_checks(component, value, evidence)
    else:
        checks = _ferrite_checks(component, value, evidence)
    return ValidationReport(
        refdes=component.refdes,
        component_value=value,
        part_number=component.part_number,
        profile_part_number=PROFILE_PART_BY_FAMILY[family],
        pin_results=pin_results,
        component_checks=checks,
    )
