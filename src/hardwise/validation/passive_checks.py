"""Family-specific deterministic checks for generic passives."""

from __future__ import annotations

from hardwise.ir.types import Component, Design
from hardwise.validation.passive_helpers import (
    _current_rating_token_check,
    _known_pin_voltages,
    _package_check,
    _value_check,
)
from hardwise.validation.topology import parse_inductance_uh
from hardwise.validation.types import ComponentValidation
from hardwise.validation.value_parsing import (
    ParsedResistance,
    parse_capacitance_f,
    parse_current_rating_amps,
    parse_ferrite_impedance_ohms,
    parse_power_watts,
    parse_rated_voltage,
    parse_resistance_ohms,
)


def _capacitor_checks(
    component: Component,
    value: str,
    design: Design,
    evidence: list[str],
) -> list[ComponentValidation]:
    capacitance = parse_capacitance_f(value)
    rated_voltage = parse_rated_voltage(value)
    return [
        _value_check(
            component,
            "capacitor_value_parse",
            "Capacitance",
            value,
            capacitance is not None,
            evidence,
        ),
        _rated_voltage_check(component, value, rated_voltage, evidence),
        _package_check(component, "capacitor", evidence),
        _capacitor_voltage_margin(component, rated_voltage, design, evidence),
    ]


def _resistor_checks(
    component: Component,
    value: str,
    design: Design,
    evidence: list[str],
) -> list[ComponentValidation]:
    resistance = parse_resistance_ohms(value)
    power_rating = parse_power_watts(value)
    return [
        _value_check(
            component,
            "resistor_value_parse",
            "Resistance",
            value,
            resistance is not None,
            evidence,
        ),
        _package_check(component, "resistor", evidence),
        _resistor_power_check(component, resistance, power_rating, design, evidence),
    ]


def _inductor_checks(
    component: Component,
    value: str,
    evidence: list[str],
) -> list[ComponentValidation]:
    inductance = parse_inductance_uh(value)
    current_rating = parse_current_rating_amps(value)
    return [
        _value_check(
            component,
            "inductor_value_parse",
            "Inductance",
            value,
            inductance is not None,
            evidence,
        ),
        _package_check(component, "inductor", evidence),
        _current_rating_token_check(component, "inductor", value, current_rating, evidence),
    ]


def _ferrite_checks(
    component: Component,
    value: str,
    evidence: list[str],
) -> list[ComponentValidation]:
    impedance = parse_ferrite_impedance_ohms(value)
    current_rating = parse_current_rating_amps(value)
    return [
        _value_check(
            component,
            "ferrite_impedance_parse",
            "Ferrite impedance",
            value,
            impedance is not None,
            evidence,
        ),
        _package_check(component, "ferrite", evidence),
        _current_rating_token_check(component, "ferrite", value, current_rating, evidence),
    ]


def _rated_voltage_check(
    component: Component,
    value: str,
    rated_voltage: float | None,
    evidence: list[str],
) -> ComponentValidation:
    return ComponentValidation(
        check="capacitor_rated_voltage_parse",
        status="PASS" if rated_voltage is not None else "WARN",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V was parsed from '{value}'."
            if rated_voltage is not None
            else f"Capacitor rated voltage could not be parsed deterministically from '{value}'."
        ),
        evidence=evidence,
    )


def _capacitor_voltage_margin(
    component: Component,
    rated_voltage: float | None,
    design: Design,
    evidence: list[str],
) -> ComponentValidation:
    if rated_voltage is None:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="WARN",
            refdes=component.refdes,
            summary="Capacitor voltage margin cannot be checked because rated voltage is missing.",
            evidence=evidence,
        )

    voltages = _known_pin_voltages(component, design)
    if not voltages:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="PASS",
            refdes=component.refdes,
            summary=(
                "No deterministic rail voltage was inferred for this capacitor; "
                "voltage-margin comparison was skipped without guessing."
            ),
            evidence=evidence,
        )

    max_voltage = max(abs(voltage) for _, voltage in voltages)
    if rated_voltage < max_voltage:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Capacitor rated voltage {rated_voltage:g} V is below inferred "
                f"maximum terminal voltage {max_voltage:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="capacitor_voltage_margin",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V is not below inferred "
            f"maximum terminal voltage {max_voltage:g} V."
        ),
        evidence=evidence,
    )


def _resistor_power_check(
    component: Component,
    resistance: ParsedResistance | None,
    power_rating: float | None,
    design: Design,
    evidence: list[str],
) -> ComponentValidation:
    if resistance is None:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="WARN",
            refdes=component.refdes,
            summary="Resistor power cannot be estimated because resistance is missing.",
            evidence=evidence,
        )

    voltages = _known_pin_voltages(component, design)
    unique = sorted({voltage for _, voltage in voltages})
    if len(unique) < 2:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="PASS",
            refdes=component.refdes,
            summary=(
                "Resistor does not have two deterministic terminal voltages; "
                "power estimate was skipped without guessing current."
            ),
            evidence=evidence,
        )

    delta = abs(unique[-1] - unique[0])
    if resistance.ohms == 0:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="WARN" if delta else "PASS",
            refdes=component.refdes,
            summary=(
                f"Zero-ohm link bridges distinct inferred rails ({unique[0]:g} V to "
                f"{unique[-1]:g} V); confirm this is an intended stuffing option."
                if delta
                else "Zero-ohm link connects terminals with the same inferred voltage."
            ),
            evidence=evidence,
        )

    power = delta * delta / resistance.ohms
    if power_rating is not None and power > power_rating:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Estimated resistor power {power:g} W from {delta:g} V across "
                f"{resistance.token} exceeds parsed rating {power_rating:g} W."
            ),
            evidence=evidence,
        )

    rating_text = (
        f"parsed rating {power_rating:g} W"
        if power_rating is not None
        else "no explicit power rating in the BOM value"
    )
    return ComponentValidation(
        check="resistor_power_estimate",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Estimated resistor power {power:g} W from {delta:g} V across "
            f"{resistance.token}; {rating_text}."
        ),
        evidence=evidence,
    )
