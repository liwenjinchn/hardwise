"""Separate observed source identifiers from executable connectivity."""

from hardwise.ir.types import Design


def observed_net_names(design: Design) -> set[str]:
    names = set(design.nets)
    if design.connectivity:
        names.update(d.net_name for d in design.connectivity.declarations)
    return names


def ambiguous_net_names(design: Design) -> set[str]:
    return set(design.connectivity.ambiguous_net_names) if design.connectivity else set()


def declaration_token(declaration, index: int) -> str:
    location = (
        f"line{declaration.line}" if declaration.line is not None else f"declaration{index + 1}"
    )
    return f"netlist:{declaration.source}#{location};net={declaration.net_name}"
