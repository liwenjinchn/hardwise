"""Build an isolated graph for explicit consumers, without changing legacy intake."""

from hardwise.ir.connectivity import ConnectionDeclaration, project_connectivity
from hardwise.ir.types import Design, Net, Pin


def with_connectivity(design: Design, declarations: list[ConnectionDeclaration]) -> Design:
    """Return an independent graph; no ambiguous edge is an executable fact.

    Call only when all downstream consumers understand connection_ambiguity.
    Original declarations, including repeated endpoint occurrences, remain intact.
    Existing pin metadata is retained; no ambiguity is converted to NC.
    """
    projection = project_connectivity(declarations)
    result = design.model_copy(deep=True)
    result.connectivity = projection
    result.nets = {
        name: (design.nets.get(name) or Net(name=name)).model_copy(
            deep=True, update={"nodes": list(nodes)}
        )
        for name, nodes in projection.resolved_nets.items()
    }
    names_by_endpoint: dict[tuple[str, str], set[str]] = {}
    for declaration in projection.declarations:
        for refdes, number in declaration.nodes:
            if refdes not in result.components:
                raise ValueError(f"Unknown endpoint component {refdes!r}")
            names_by_endpoint.setdefault((refdes, number), set()).add(declaration.net_name)
    blocked = set(projection.ambiguous_endpoints)
    for refdes, component in result.components.items():
        # A supplied pin catalog may contain unconnected pins; do not discard it.
        pins = {pin.number: pin for pin in component.pins}
        if len(pins) != len(component.pins):
            raise ValueError(f"Duplicate pin metadata for {refdes}")
        for (owner, number), names in names_by_endpoint.items():
            if owner != refdes:
                continue
            pin = pins.get(number) or Pin(number=number, name="", electrical_type="", is_nc=False)
            if pin.is_nc:
                raise ValueError(
                    f"Connected declaration contradicts NC metadata for {refdes}.{number}"
                )
            pin.net = None if (refdes, number) in blocked else next(iter(names))
            pin.connection_ambiguity = sorted(names) if (refdes, number) in blocked else []
            pins[number] = pin
        # Clear old connection values absent from the authoritative declarations.
        for number, pin in pins.items():
            if (refdes, number) not in names_by_endpoint:
                pin.net = None
                pin.connection_ambiguity = []
        component.pins = list(pins.values())
    return result
