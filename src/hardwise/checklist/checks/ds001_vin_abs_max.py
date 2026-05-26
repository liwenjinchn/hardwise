"""DS001 — datasheet-driven Vin absolute-maximum check."""

from __future__ import annotations

import re

from hardwise.checklist.finding import EvidenceStep, Finding
from hardwise.checklist.protocols import CheckContext, CheckSpec
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design


def applies_to(component: Component) -> bool:
    """DS001 applies only when a structured datasheet profile is attached."""

    return component.datasheet_profile is not None


def check_component(
    component: Component,
    design: Design,
    _context: CheckContext,
) -> list[Finding]:
    """Check one component's Vin against datasheet abs-max."""

    profile = component.datasheet_profile
    if profile is None:
        return []
    vin_max_raw = profile.abs_max.get("vin")
    if not isinstance(vin_max_raw, (int, float)):
        return []
    vin_max = float(vin_max_raw)
    applied = _estimate_vin(component, design)
    if applied is None:
        return [
            _finding(
                component=component,
                profile=profile,
                severity="medium",
                decision="reviewer_to_confirm",
                message=(
                    f"{component.refdes} has datasheet abs_max.vin = {vin_max:.1f} V, "
                    "but Hardwise cannot infer the applied Vin rail from schematic nets yet."
                ),
            )
        ]
    if applied > vin_max:
        return [
            _finding(
                component=component,
                profile=profile,
                severity="high",
                decision="likely_issue",
                message=(
                    f"{component.refdes} Vin={applied:.1f} V exceeds datasheet "
                    f"abs_max.vin={vin_max:.1f} V."
                ),
            )
        ]
    if applied > 0.8 * vin_max:
        return [
            _finding(
                component=component,
                profile=profile,
                severity="medium",
                decision="reviewer_to_confirm",
                message=(
                    f"{component.refdes} Vin={applied:.1f} V is above 80% of "
                    f"datasheet abs_max.vin={vin_max:.1f} V."
                ),
            )
        ]
    return [
        _finding(
            component=component,
            profile=profile,
            severity="low",
            decision="likely_ok",
            message=(
                f"{component.refdes} Vin={applied:.1f} V is below 80% of "
                f"datasheet abs_max.vin={vin_max:.1f} V."
            ),
        )
    ]


def _finding(
    *,
    component: Component,
    profile: DatasheetProfile,
    severity: str,
    decision: str,
    message: str,
) -> Finding:
    token = profile.evidence.get("abs_max.vin", f"datasheet:{profile.part_number}#abs_max.vin")
    return Finding(
        rule_id="DS001",
        severity=severity,  # type: ignore[arg-type]
        refdes=component.refdes,
        pin_number="1" if profile.pin_function.get("1") else None,
        message=message,
        evidence_tokens=[token],
        evidence_chain=[
            EvidenceStep(
                source="datasheet",
                claim=f"{profile.part_number} abs_max.vin = {profile.abs_max['vin']} V.",
                token=token,
            ),
            EvidenceStep(
                source="rule",
                claim="DS001 compares inferred Vin rail against datasheet abs max.",
                token="rule:DS001#vin_abs_max",
            ),
        ],
        suggested_action=(
            "Confirm the regulator input rail voltage in the schematic and ensure it stays "
            "below the datasheet absolute maximum with appropriate margin."
        ),
        decision=decision,  # type: ignore[arg-type]
    )


def _estimate_vin(component: Component, design: Design) -> float | None:
    """Infer Vin from pin/net metadata when available."""

    pin = component.pin_by_name("Vin") or component.pin_by_name("VI") or component.pin_by_number("1")
    if pin is None or not pin.net:
        return None
    net = design.nets.get(pin.net)
    if net is not None and net.voltage_hint is not None:
        return net.voltage_hint
    return _voltage_from_net_name(pin.net)


def _voltage_from_net_name(net_name: str) -> float | None:
    upper = net_name.upper()
    if "VBUS" in upper:
        return 5.0
    match = re.search(r"([+-]?)(\d+)(?:V|P)(\d+)?", upper)
    if match is None:
        return None
    whole = float(match.group(2))
    frac = match.group(3)
    volts = whole if frac is None else float(f"{int(whole)}.{frac}")
    return -volts if match.group(1) == "-" else volts


DS001_SPEC = CheckSpec(rule_id="DS001", applies_to=applies_to, check=check_component)
