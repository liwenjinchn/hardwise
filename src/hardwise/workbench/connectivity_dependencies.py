"""Electrical ambiguity premises, excluding movable provenance locations."""

from hardwise.ir.connectivity_queries import ambiguous_net_names


def connectivity_premises(design, component=None):
    blocked = ambiguous_net_names(design)
    if not blocked:
        return None
    if component is not None:
        names = {pin.net for pin in component.pins if pin.net}
        names.update(n for pin in component.pins for n in pin.connection_ambiguity)
        names.update(
            f.reference_net
            for f in design.voltage_facts.facts
            if f.net in names and f.mode == design.voltage_facts.active_mode
        )
        blocked &= names
    if not blocked:
        return None
    records = [
        (d.net_name, sorted(d.nodes))
        for d in design.connectivity.declarations
        if d.net_name in blocked
    ]
    return {
        "contract": "hardwise.connectivity.v1",
        "ambiguous_net_names": sorted(blocked),
        "declarations": sorted(records),
    }
