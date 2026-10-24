"""Bootstrap branch observations and an independent limited VB-VS DC bound."""

from math import isfinite

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.gate_driver_helpers import (
    components_between_nets,
    pin_by_profile_name,
    profile_evidence,
)
from hardwise.validation.terminal_voltage import terminal_voltage_check
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def floating_supply_voltage(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    value = profile.abs_max.get("vb_vs")
    limit = None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            number = float(value)
            if isfinite(number):
                limit = number
        except (ValueError, OverflowError):
            pass
    return terminal_voltage_check(
        component,
        design,
        positive=pin_by_profile_name(component, profile, "VB"),
        negative=pin_by_profile_name(component, profile, "VS"),
        limit=limit,
        check="gate_driver_vb_vs_voltage",
        label="VB−VS",
        evidence=profile_evidence(profile, "abs_max.vb_vs"),
        symmetric=False,
        require_nonnegative=True,
    )


def bootstrap_observation(
    component: Component, profile: DatasheetProfile, design: Design
) -> ComponentValidation:
    evidence = profile_evidence(profile, "recommended.bootstrap_diode")
    vb, vs, vcc = (pin_by_profile_name(component, profile, n) for n in ("VB", "VS", "VCC"))
    result, severity, kind, refdes = "UNKNOWN", "INFO", "DERIVED", component.refdes
    if vb is None or not vb.net or vs is None or not vs.net:
        result, severity = "FAIL", "ERROR"
        reason = "Gate-driver bootstrap pins VB/VS are missing or not connected."
    else:
        caps = components_between_nets(design, vb.net, vs.net, "C")
        if not caps and profile.recommended.get("bootstrap_required") is True and evidence:
            result, severity = "FAIL", "ERROR"
            reason = f"Gate-driver bootstrap path lacks a capacitor between {vb.net} and {vs.net}. Only the declared direct bootstrap topology is checked."
        else:
            diodes = [
                d
                for d in components_on_net(design, vb.net, exclude_refdes=component.refdes)
                if d.refdes.startswith("D") and any(p.net == vb.net for p in d.pins)
            ]
            direct = [
                d
                for d in diodes
                if vcc
                and vcc.net
                and len(d.pins) == 2
                and {p.net for p in d.pins} == {vb.net, vcc.net}
            ]
            refdes = ", ".join(sorted(d.refdes for d in diodes)) or component.refdes
            kind = "HYPOTHESIS"
            cap_text = ", ".join(sorted(c.refdes for c in caps)) or "未找到"
            diode_text = (
                ", ".join(f"{d.refdes} ({d.part_number or d.value})" for d in diodes) or "未找到"
            )
            direct_text = ", ".join(sorted(d.refdes for d in direct)) or "未确认"
            reason = (
                f"VB−VS 电容支路候选：{cap_text}；VB 邻接二极管候选：{diode_text}；"
                f"VCC−VB 直接两端支路候选：{direct_text}。"
                "未核验二极管身份/极性、耐压、动态应力和自举充电条件；不从型号猜额定值或从高侧网名传播所需耐压。"
                "二极管端点耐压由该器件自身检查单列；本项自举功能未评估。"
            )
    return ComponentValidation(
        check="gate_driver_bootstrap",
        refdes=refdes,
        result=result,
        severity=severity,
        evidence_kind=kind,
        rule_version="2",
        summary=reason,
        evidence=evidence,
    )
