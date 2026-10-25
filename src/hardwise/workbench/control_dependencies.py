"""Audited control observation v2: component plus immediate control-net neighborhood."""

from hardwise.validation.control_scope import CONTROL_CHECKS, control_pin_profile
from hardwise.validation.pin_resolver import schematic_pin_for_profile_pin
from hardwise.validation.topology import components_on_net


def local_voltage_facts(design, component, extra_components=()):
    """Retain existing component-local voltage/reference scope, in canonical order."""
    nets = {pin.net for item in [component, *extra_components] for pin in item.pins if pin.net}
    facts = [
        fact
        for fact in design.voltage_facts.facts
        if fact.net in nets and fact.mode == design.voltage_facts.active_mode
    ]
    nets.update(fact.reference_net for fact in facts)
    return [
        fact.model_dump(mode="json")
        for fact in sorted(design.voltage_facts.facts, key=lambda fact: (fact.mode, fact.net))
        if fact.net in nets and fact.mode == design.voltage_facts.active_mode
    ]


def control_dependency_payload(context, task, component_snapshot, profile_snapshot):
    """Unknown producers/versions never inherit this scope by name resemblance."""
    if (
        task.kind != "component_check"
        or task.check not in CONTROL_CHECKS
        or task.assessment is None
        or task.assessment.rule_version not in {"2", "2.profile-review1", "3", "3.profile-review1"}
    ):
        return None
    component = context.design.components.get(task.refdes)
    profile = context.validation_targets.get(task.refdes)
    if component is None or profile is None:
        return None
    pin_profile = control_pin_profile(profile, task.check)
    pin = schematic_pin_for_profile_pin(component, pin_profile) if pin_profile else None
    net_name = pin.net if pin else None
    net = context.design.nets.get(net_name) if net_name else None
    neighbors = (
        [
            item
            for item in components_on_net(context.design, net_name, exclude_refdes=task.refdes)
            if any(p.net == net_name for p in item.pins)
        ]
        if net_name
        else []
    )
    payload = {
        "scope": "control_neighborhood.v1",
        "component": component_snapshot(component),
        "profile": profile_snapshot,
        "control_pin_number": pin.number if pin else None,
        "control_net": net_name,
        "control_net_nodes": sorted(net.nodes) if net else [],
        "neighbors": {
            item.refdes: component_snapshot(item)
            for item in sorted(neighbors, key=lambda item: item.refdes)
        },
        "active_mode": context.design.voltage_facts.active_mode,
        "facts": local_voltage_facts(context.design, component, neighbors),
    }
    review = local_voltage_review(context.design, component, neighbors)
    if review is not None:
        payload["voltage_review"] = review
    return payload


def local_voltage_review(design, component, extra_components=()):
    """Bind unresolved candidate/decision premises only in the observed scope."""
    review = design.voltage_review
    if review is None:
        return None
    nets = {pin.net for item in [component, *extra_components] for pin in item.pins if pin.net}
    candidates = [
        c for c in review.candidates if c.fact.net in nets and c.fact.mode == review.active_mode
    ]
    nets.update(c.fact.reference_net for c in candidates)
    return {
        "active_mode": review.active_mode,
        "candidates": [
            c.model_dump(mode="json")
            for c in sorted(review.candidates, key=lambda c: c.id)
            if c.fact.net in nets and c.fact.mode == review.active_mode
        ],
        "confirmations": [
            d.model_dump(mode="json")
            for d in review.confirmations
            if d.net in nets and d.mode == review.active_mode
        ],
    }
