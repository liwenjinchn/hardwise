"""Deterministic diode topology checks."""

from __future__ import annotations

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import voltage_for_net
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def validate_diode(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate a two-terminal diode against its structured pin profile."""

    checks = [
        _validate_pin_connected(component, profile, "Cathode", "diode_cathode_connectivity"),
        _validate_pin_connected(component, profile, "Anode", "diode_anode_connectivity"),
        _validate_reverse_voltage(component, profile, design),
    ]
    if _is_led_indicator(profile):
        checks.extend(
            [
                _validate_led_indicator_polarity(component, profile, design),
                _validate_led_current_limit(component, profile, design),
            ]
        )
    return checks


def _validate_pin_connected(
    component: Component,
    profile: DatasheetProfile,
    pin_name: str,
    check: str,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, f"pin_function.{_pin_number(profile, pin_name)}")
    pin = _pin_by_profile_name(component, profile, pin_name)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=check,
            status="ERROR",
            summary=f"Diode {pin_name.lower()} pin is not connected.",
            evidence=evidence,
        )
    return ComponentValidation(
        check=check,
        status="PASS",
        refdes=component.refdes,
        summary=f"Diode {pin_name.lower()} is connected to {pin.net}.",
        evidence=evidence,
    )


def _validate_reverse_voltage(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "abs_max.reverse_voltage")
    cathode = _pin_by_profile_name(component, profile, "Cathode")
    anode = _pin_by_profile_name(component, profile, "Anode")
    if cathode is None or not cathode.net:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="ERROR",
            summary="Diode cathode pin is not connected; cannot check reverse voltage.",
            evidence=evidence,
        )
    if anode is None or not anode.net:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="ERROR",
            summary="Diode anode pin is not connected; cannot check reverse voltage.",
            evidence=evidence,
        )

    cathode_voltage = voltage_for_net(cathode.net, design)
    anode_voltage = voltage_for_net(anode.net, design)
    if cathode_voltage is None or anode_voltage is None:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="WARN",
            refdes=component.refdes,
            summary="Diode reverse voltage cannot be inferred from cathode/anode net names.",
            evidence=evidence,
        )

    reverse_voltage = cathode_voltage - anode_voltage
    reverse_limit = _float_abs_max(profile, "reverse_voltage")
    if reverse_limit is not None and reverse_voltage > reverse_limit:
        return ComponentValidation(
            check="diode_reverse_voltage",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"Diode reverse voltage is {reverse_voltage:g} V, "
                f"above profile maximum {reverse_limit:g} V."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="diode_reverse_voltage",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"Diode reverse voltage is {reverse_voltage:g} V"
            + (f", within profile maximum {reverse_limit:g} V." if reverse_limit else ".")
        ),
        evidence=evidence,
    )


def _validate_led_indicator_polarity(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.diode_role")
    anode = _pin_by_profile_name(component, profile, "Anode")
    cathode = _pin_by_profile_name(component, profile, "Cathode")
    if anode is None or not anode.net:
        return ComponentValidation(
            check="led_indicator_polarity",
            status="ERROR",
            summary="LED anode pin is not connected; cannot check indicator polarity.",
            evidence=evidence,
        )
    if cathode is None or not cathode.net:
        return ComponentValidation(
            check="led_indicator_polarity",
            status="ERROR",
            summary="LED cathode pin is not connected; cannot check indicator polarity.",
            evidence=evidence,
        )

    anode_voltage = voltage_for_net(anode.net, design)
    cathode_voltage = voltage_for_net(cathode.net, design)
    if anode_voltage is None or cathode_voltage is None:
        return ComponentValidation(
            check="led_indicator_polarity",
            status="WARN",
            refdes=component.refdes,
            summary="LED indicator polarity cannot be inferred from anode/cathode net names.",
            evidence=evidence,
        )
    if anode_voltage <= cathode_voltage:
        return ComponentValidation(
            check="led_indicator_polarity",
            status="ERROR",
            refdes=component.refdes,
            summary=(
                f"LED anode is at {anode_voltage:g} V and cathode is at "
                f"{cathode_voltage:g} V; expected anode above cathode."
            ),
            evidence=evidence,
        )
    return ComponentValidation(
        check="led_indicator_polarity",
        status="PASS",
        refdes=component.refdes,
        summary=(
            f"LED anode is at {anode_voltage:g} V and cathode is at "
            f"{cathode_voltage:g} V."
        ),
        evidence=evidence,
    )


def _validate_led_current_limit(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    evidence = _profile_evidence(profile, "recommended.requires_current_limit")
    if not _bool_recommended(profile, "requires_current_limit"):
        return ComponentValidation(
            check="led_current_limit",
            status="PASS",
            refdes=component.refdes,
            summary="LED indicator profile does not require a deterministic current-limit check.",
            evidence=evidence,
        )

    anode = _pin_by_profile_name(component, profile, "Anode")
    cathode = _pin_by_profile_name(component, profile, "Cathode")
    if anode is None or not anode.net:
        return ComponentValidation(
            check="led_current_limit",
            status="ERROR",
            summary="LED anode pin is not connected; cannot check current limiting.",
            evidence=evidence,
        )
    if cathode is None or not cathode.net:
        return ComponentValidation(
            check="led_current_limit",
            status="ERROR",
            summary="LED cathode pin is not connected; cannot check current limiting.",
            evidence=evidence,
        )

    limiting_net = _current_limit_net(component, design, (anode.net, cathode.net))
    if limiting_net is None:
        return ComponentValidation(
            check="led_current_limit",
            status="ERROR",
            refdes=component.refdes,
            summary="LED indicator has no resistor neighbor on its anode or cathode net.",
            evidence=evidence,
        )
    return ComponentValidation(
        check="led_current_limit",
        status="PASS",
        refdes=component.refdes,
        summary=f"LED indicator has a resistor neighbor on {limiting_net}.",
        evidence=evidence,
    )


def _pin_by_profile_name(component: Component, profile: DatasheetProfile, name: str):
    number = _pin_number(profile, name)
    if number is None:
        return None
    return component.pin_by_number(number)


def _pin_number(profile: DatasheetProfile, name: str) -> str | None:
    normalized = _normalize(name)
    for pin in profile.pins:
        if _normalize(pin.name) == normalized:
            return pin.number
    return None


def _float_abs_max(profile: DatasheetProfile, key: str) -> float | None:
    value = profile.abs_max.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _is_led_indicator(profile: DatasheetProfile) -> bool:
    return str(profile.recommended.get("diode_role", "")).lower() == "led_indicator"


def _bool_recommended(profile: DatasheetProfile, key: str) -> bool:
    return profile.recommended.get(key) is True


def _current_limit_net(
    component: Component,
    design: Design,
    net_names: tuple[str, str],
) -> str | None:
    for net_name in net_names:
        if any(
            neighbor.refdes.startswith("R")
            for neighbor in components_on_net(design, net_name, exclude_refdes=component.refdes)
        ):
            return net_name
    return None


def _profile_evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key)
    return [token] if token else []


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())
