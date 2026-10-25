"""Family-specific deterministic checks for generic passives."""

from __future__ import annotations

from hardwise.validation.assessment import result_for_attention, severity_for_attention

from hardwise.ir.types import Component, Design
from hardwise.validation.passive_helpers import (
    _current_rating_token_check,
    _package_check,
    _value_check,
)
from hardwise.validation.topology import parse_inductance_uh
from hardwise.validation.types import ComponentValidation
from hardwise.validation.value_parsing import (
    parse_capacitance_f,
    parse_current_rating_amps,
    parse_ferrite_impedance_ohms,
    parse_resistance_ohms,
)
from hardwise.validation.passive_ratings import (
    PassiveRating,
    attach_rating_sources,
    resolve_passive_rating,
)
from hardwise.validation.passive_stress_checks import (
    _capacitor_voltage_margin,
    _resistor_power_check,
)


def _capacitor_checks(
    component: Component,
    value: str,
    design: Design,
    evidence: list[str],
    rating: PassiveRating | None = None,
) -> list[ComponentValidation]:
    capacitance = parse_capacitance_f(value)
    rating = rating or resolve_passive_rating(value, None, "voltage", component)
    rated_voltage = rating.value
    checks = [
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
        _capacitor_voltage_margin(component, rating, design, evidence),
    ]
    return [
        attach_rating_sources(check, rating)
        if check.check in {"capacitor_rated_voltage_parse", "capacitor_voltage_margin"}
        else check
        for check in checks
    ]


def _resistor_checks(
    component: Component,
    value: str,
    design: Design,
    evidence: list[str],
    rating: PassiveRating | None = None,
) -> list[ComponentValidation]:
    resistance = parse_resistance_ohms(value)
    rating = rating or resolve_passive_rating(value, None, "power", component)
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
        attach_rating_sources(
            _resistor_power_check(component, resistance, rating, design, evidence), rating
        ),
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
        result=result_for_attention(
            "PASS" if rated_voltage is not None else "UNKNOWN", warning_result="UNKNOWN"
        ),
        severity=severity_for_attention("PASS" if rated_voltage is not None else "UNKNOWN"),
        evidence_kind="SOURCE_FACT",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V was parsed from '{value}'."
            if rated_voltage is not None
            else f"Capacitor rated voltage could not be parsed deterministically from '{value}'."
        ),
        evidence=evidence,
    )
