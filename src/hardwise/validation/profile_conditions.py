"""Evaluate pin-to-supply bounds from explicitly confirmed DC envelopes."""

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.profile_conditions import PinVoltageRelation
from hardwise.ir.types import Component, Design
from hardwise.validation.types import ComponentValidation


def validate_voltage_relations(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    *,
    include_instances: bool = False,
) -> list[ComponentValidation]:
    results = []
    for relation in profile.voltage_relations:
        result = _relation(component, profile, design, relation)
        if include_instances:
            result = result.model_copy(update={"instance": relation_instance(relation)})
        results.append(result)
    return results


def relation_instance(relation):
    import hashlib
    import json

    payload = json.dumps(relation.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return (
        ("relation_sha256", hashlib.sha256(payload.encode()).hexdigest()),
        ("target", relation.target_pin),
        ("supply", relation.supply_pin),
        ("ground", relation.ground_pin),
    )


def _relation(
    component: Component, profile: DatasheetProfile, design: Design, relation: PinVoltageRelation
) -> ComponentValidation:
    evidence = [
        relation.evidence,
        f"profile_source:{relation.document_sha256}#p{relation.page};revision={relation.document_revision}",
    ]
    result, reason = "UNKNOWN", "缺少已确认的引脚电压范围、共同参考地或适用型号/封装。"
    pins = [
        component.pin_by_number(number)
        for number in (relation.target_pin, relation.supply_pin, relation.ground_pin)
    ]
    if any(pin and pin.connection_ambiguity for pin in pins):
        return _output(
            component,
            relation,
            "UNKNOWN",
            "关系式端点连接声明有歧义，不能绑定电压/参考域。",
            evidence,
        )
    identity = component.part_number or component.value
    identity_matches = identity == profile.part_number or identity in profile.part_number_aliases
    if (
        component.package != relation.required_package
        or not identity_matches
        or not all(pin and pin.net for pin in pins)
    ):
        return _output(component, relation, result, reason, evidence)
    target_pin, supply_pin, ground_pin = pins
    facts = {
        fact.net: fact
        for fact in design.voltage_facts.facts
        if fact.mode == design.voltage_facts.active_mode
    }
    target, supply = facts.get(target_pin.net), facts.get(supply_pin.net)
    blocked = set(design.connectivity.ambiguous_net_names) if design.connectivity else set()
    if any(f and (f.net in blocked or f.reference_net in blocked) for f in (target, supply)):
        return _output(component, relation, "UNKNOWN", "关系式事实引用有歧义的连接域。", evidence)
    if (
        not target
        or not supply
        or not all(
            f.confirmed and f.minimum is not None and f.maximum is not None
            for f in (target, supply)
        )
    ):
        return _output(component, relation, result, reason, evidence)
    if target.reference_net != ground_pin.net or supply.reference_net != ground_pin.net:
        return _output(component, relation, result, reason, evidence)
    evidence.extend(
        f"voltage_fact:{f.net}#mode={f.mode};reference={f.reference_net};range={f.minimum},{f.maximum}V;source={f.source};confirmed_by={f.confirmed_by}"
        for f in (target, supply)
    )
    bound = f"引脚 {relation.target_pin} ≥ {relation.minimum_voltage:g} V 且 ≤ 引脚 {relation.supply_pin}"
    same_net = target.net == supply.net
    if target.maximum < relation.minimum_voltage or (
        not same_net and target.minimum > supply.maximum
    ):
        result, reason = "FAIL", f"已确认直流范围违反关系约束：{bound}。"
    elif target.minimum >= relation.minimum_voltage and (
        same_net or target.maximum <= supply.minimum
    ):
        result, reason = "PASS", f"已确认直流范围满足关系约束：{bound}；未评估瞬态。"
    else:
        reason = f"直流范围跨越关系边界：{bound}；缺少相关性/运行状态，不能证明通过或确定违规。"
    return _output(component, relation, result, reason, evidence)


def _output(component, relation, result, reason, evidence):
    return ComponentValidation(
        check=f"pin_voltage_relation_{relation.target_pin}",
        refdes=component.refdes,
        result=result,
        severity="ERROR" if result == "FAIL" else "INFO",
        summary=reason,
        evidence=evidence,
        rule_version="1",
    )
