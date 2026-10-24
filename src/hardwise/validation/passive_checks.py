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
    if len(component.pins) != 2 or len(voltages) != 2:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="WARN",
            refdes=component.refdes,
            summary=(
                "Capacitor voltage margin cannot be checked without two terminal voltages; "
                "missing terminal data is not a passing comparison."
            ),
            evidence=evidence,
        )

    dc_stress = abs(voltages[0][1] - voltages[1][1])
    if rated_voltage < dc_stress:
        return ComponentValidation(
            check="capacitor_voltage_margin",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Capacitor rated voltage {rated_voltage:g} V is below inferred "
                f"terminal-to-terminal DC voltage {dc_stress:g} V "
                "(net-name/metadata inference; reference domains and transient stress "
                "are not verified)."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="capacitor_voltage_margin",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V is not below inferred "
            f"terminal-to-terminal DC voltage {dc_stress:g} V "
            "(net-name/metadata inference; reference domains and transient stress "
            "are not verified)."
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
    if len(component.pins) != 2 or len(voltages) != 2:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="WARN",
            refdes=component.refdes,
            summary=(
                "Resistor power cannot be estimated without two terminal voltages; "
                "missing terminal data is not a passing comparison."
            ),
            evidence=evidence,
        )

    terminal_voltages = sorted(voltage for _, voltage in voltages)
    delta = abs(terminal_voltages[-1] - terminal_voltages[0])
    if resistance.ohms == 0:
        return ComponentValidation(
            check="resistor_power_estimate",
            status="WARN" if delta else "PASS",
            refdes=component.refdes,
            summary=(
                f"Zero-ohm link bridges distinct inferred rails ({terminal_voltages[0]:g} V to "
                f"{terminal_voltages[-1]:g} V); confirm this is an intended stuffing option."
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
        else "power margin not evaluated: no explicit power rating in the BOM value"
    )
    return ComponentValidation(
        check="resistor_power_estimate",
        status="PASS" if power_rating is not None else "WARN",
        refdes=component.refdes,
        summary=(
            f"Estimated resistor power {power:g} W from {delta:g} V across "
            f"{resistance.token}; {rating_text}."
        ),
        evidence=evidence,
    )
