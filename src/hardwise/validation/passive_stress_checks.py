"""Passive DC stress comparisons retain exact model quantities before display rounding."""

from hardwise.ir.types import Component, Design
from hardwise.validation.assessment import result_for_attention, severity_for_attention
from hardwise.validation.passive_numeric import (
    finite_quantity,
    resistor_dc_power_fraction,
    exact_quantity_text,
)
from hardwise.validation.passive_ratings import PassiveRating, RATING_RULE_VERSIONS
from hardwise.validation.value_parsing import ParsedResistance
from hardwise.validation.voltage_facts import terminal_dc_stress
from hardwise.validation.types import ComponentValidation


def _output(*, check: str, **fields) -> ComponentValidation:
    return ComponentValidation(check=check, rule_version=RATING_RULE_VERSIONS[check], **fields)


def _capacitor_voltage_margin(
    component: Component,
    rating: PassiveRating,
    design: Design,
    evidence: list[str],
) -> ComponentValidation:
    rated_voltage = rating.value
    exact_rating = rating.exact_value
    if rated_voltage is None or exact_rating is None:
        return _output(
            check="capacitor_voltage_margin",
            result="UNKNOWN",
            severity="INFO",
            refdes=component.refdes,
            summary="Capacitor voltage margin cannot be checked because rated voltage is missing.",
            evidence=evidence,
        )

    stress = terminal_dc_stress(component, design)
    evidence = [*evidence, *stress.evidence]
    if stress.maximum_delta is None or stress.exact_delta is None:
        return _output(
            check="capacitor_voltage_margin",
            result="UNKNOWN",
            severity="INFO",
            refdes=component.refdes,
            summary=(f"Capacitor voltage margin cannot be checked: {stress.reason}."),
            evidence=evidence,
        )

    dc_stress = stress.maximum_delta
    if exact_rating < stress.exact_delta:
        return _output(
            check="capacitor_voltage_margin",
            result="FAIL",
            severity="ERROR",
            refdes=component.refdes,
            summary=(
                f"按已确认数值的规范十进制表示精确比较：额定耐压 {exact_quantity_text(exact_rating)} V "
                f"低于端间直流应力 {exact_quantity_text(stress.exact_delta)} V；显示值已舍入。{stress.reason}."
                if rated_voltage == dc_stress
                else f"Capacitor rated voltage {rated_voltage:g} V is below confirmed "
                f"terminal-to-terminal DC voltage {dc_stress:g} V "
                f"({stress.reason})."
            ),
            evidence=evidence,
        )
    return _output(
        check="capacitor_voltage_margin",
        result="PASS",
        severity="INFO",
        refdes=component.refdes,
        summary=(
            f"Capacitor rated voltage {rated_voltage:g} V is not below confirmed "
            f"terminal-to-terminal DC voltage {dc_stress:g} V "
            f"({stress.reason})."
        ),
        evidence=evidence,
    )


def _resistor_power_check(
    component: Component,
    resistance: ParsedResistance | None,
    rating: PassiveRating,
    design: Design,
    evidence: list[str],
) -> ComponentValidation:
    power_rating = rating.value
    exact_rating = rating.exact_value
    if resistance is None:
        return _output(
            check="resistor_power_estimate",
            result="UNKNOWN",
            severity="INFO",
            refdes=component.refdes,
            summary="Resistor power cannot be estimated because resistance is missing or numerically unavailable.",
            evidence=evidence,
        )

    stress = terminal_dc_stress(component, design)
    evidence = [*evidence, *stress.evidence]
    if stress.maximum_delta is None or stress.exact_delta is None:
        return _output(
            check="resistor_power_estimate",
            result="UNKNOWN",
            severity="INFO",
            refdes=component.refdes,
            summary=(f"Resistor power cannot be estimated: {stress.reason}."),
            evidence=evidence,
        )

    delta = stress.maximum_delta
    if resistance.ohms == 0:
        return _output(
            check="resistor_power_estimate",
            result=result_for_attention("WARN" if delta else "UNKNOWN", warning_result="UNKNOWN"),
            severity=severity_for_attention("WARN" if delta else "UNKNOWN"),
            refdes=component.refdes,
            summary=(
                f"Zero-ohm link may bridge a confirmed DC difference up to {delta:g} V; "
                "confirm current and intended stuffing option."
                if delta
                else "Zero-ohm link has zero confirmed DC difference; current and power margin remain unknown."
            ),
            evidence=evidence,
        )

    exact_power = resistor_dc_power_fraction(stress.exact_delta, resistance.ohms)
    power = finite_quantity(exact_power) if exact_power is not None else None
    if power is None:
        return _output(
            check="resistor_power_estimate",
            result="UNKNOWN",
            severity="INFO",
            refdes=component.refdes,
            summary="Resistor DC power is numerically unavailable; no power margin was evaluated.",
            evidence=evidence,
        )
    if exact_rating is not None and exact_power > exact_rating:
        return _output(
            check="resistor_power_estimate",
            result="FAIL",
            severity="ERROR",
            refdes=component.refdes,
            summary=(
                f"按已确认电压及已解析阻值的规范十进制表示精确比较：功耗 {exact_quantity_text(exact_power)} W "
                f"高于额定 {exact_quantity_text(exact_rating)} W；显示值已舍入。{stress.reason}."
                if power == power_rating
                else f"Estimated resistor power {power:g} W from {delta:g} V across "
                f"{resistance.token} exceeds parsed rating {power_rating:g} W; {stress.reason}."
            ),
            evidence=evidence,
        )

    rating_text = (
        f"parsed rating {power_rating:g} W"
        if power_rating is not None
        else "power margin not evaluated: no explicit power rating in the BOM value"
    )
    return _output(
        check="resistor_power_estimate",
        result=result_for_attention(
            "PASS" if power_rating is not None else "UNKNOWN", warning_result="UNKNOWN"
        ),
        severity=severity_for_attention("PASS" if power_rating is not None else "UNKNOWN"),
        refdes=component.refdes,
        summary=(
            f"Estimated resistor power {power:g} W from {delta:g} V across "
            f"{resistance.token}; {rating_text}; {stress.reason}."
        ),
        evidence=evidence,
    )
