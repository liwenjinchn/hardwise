"""Observe control connectivity without promoting it to unmodeled logic function."""

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.dc_envelope import confirmed_dc_difference
from hardwise.validation.pin_resolver import schematic_pin_for_profile_pin
from hardwise.validation.pin_voltage import profile_reference_pin
from hardwise.validation.topology import components_on_net
from hardwise.validation.types import ComponentValidation


def observe_control_scope(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    pin_profile: PinProfile | None,
    check: str,
    scope: str,
) -> ComponentValidation:
    """Retain direct facts and branch candidates; never propagate through R/C."""
    if pin_profile is None:
        return ComponentValidation(
            check=check,
            refdes=component.refdes,
            result="UNKNOWN",
            severity="INFO",
            evidence_kind="HYPOTHESIS",
            needs_review=True,
            rule_version="2",
            summary="缺少控制脚档案，无法核验逻辑功能或引脚映射。",
        )
    pin = schematic_pin_for_profile_pin(component, pin_profile)
    evidence = list(pin_profile.evidence)
    if pin is None or not pin.net:
        return ComponentValidation(
            check=check,
            refdes=component.refdes,
            result="FAIL",
            severity="ERROR",
            rule_version="2",
            evidence=evidence,
            summary=f"控制脚 {pin_profile.name} 缺失或没有连接网络；仅报告连接错误。",
        )
    evidence.append(f"rule:parsed_pin_connection#{component.refdes}.{pin.number};net={pin.net}")
    neighbors = [
        n
        for n in components_on_net(design, pin.net, exclude_refdes=component.refdes)
        if any(p.net == pin.net for p in n.pins)
    ]
    observations = [f"控制脚 {pin_profile.name} 已连接到已解析网络 {pin.net}"]
    observations.append(
        "邻接器件：" + ", ".join(sorted(n.refdes for n in neighbors))
        if neighbors
        else "未发现外部邻接器件，不能据此断定悬空或排除内部驱动"
    )
    candidates = []
    for neighbor in neighbors:
        other = sorted({p.net for p in neighbor.pins if p.net and p.net != pin.net})
        if neighbor.refdes.startswith(("R", "C")) and len(neighbor.pins) == 2 and len(other) == 1:
            candidates.append(f"{neighbor.refdes} → {other[0]}")
    if candidates:
        observations.append(
            "相邻两端支路候选："
            + ", ".join(sorted(candidates))
            + "；不将支路另一端电压传播成本脚电压"
        )
    delta = confirmed_dc_difference(design, pin, profile_reference_pin(component, profile))
    evidence.extend(delta.evidence)
    if delta.minimum is not None and delta.maximum is not None:
        observations.append(
            f"本脚已确认直流差值 [{delta.minimum:g}, {delta.maximum:g}] V（相对档案地引脚）"
        )
    else:
        observations.append("本脚直流范围未确认或参考关系不满足")
    observations.append(
        f"{scope}所需逻辑门限、工作条件或时序未建模；逻辑功能未评估。连接和邻接器件不证明默认电平或正常工作"
    )
    return ComponentValidation(
        check=check,
        refdes=component.refdes,
        result="UNKNOWN",
        severity="INFO",
        evidence_kind="HYPOTHESIS" if candidates else "DERIVED",
        rule_version="2",
        summary="。".join(observations) + "。",
        evidence=list(dict.fromkeys(evidence)),
    )
