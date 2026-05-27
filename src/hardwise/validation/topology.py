"""Small topology helpers for deterministic component validation."""

from __future__ import annotations

import re

from hardwise.ir.types import Component, Design


def components_on_net(design: Design, net_name: str, *, exclude_refdes: str = "") -> list[Component]:
    """Return components connected to ``net_name``, excluding one refdes if requested."""

    net = design.nets.get(net_name)
    if net is None:
        return []
    seen: set[str] = set()
    components: list[Component] = []
    for refdes, _pin_number in net.nodes:
        if refdes == exclude_refdes or refdes in seen:
            continue
        component = design.components.get(refdes)
        if component is None:
            continue
        seen.add(refdes)
        components.append(component)
    return components


def first_by_prefix(components: list[Component], prefix: str) -> Component | None:
    """Return the first component whose refdes starts with ``prefix``."""

    return next((component for component in components if component.refdes.startswith(prefix)), None)


def parse_inductance_uh(value: str) -> float | None:
    """Parse a simple inductor value into microhenries."""

    compact = value.strip().replace("μ", "u").replace("µ", "u").upper()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(UH|NH|MH|H)\b", compact)
    if match is None:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "NH":
        return amount / 1000.0
    if unit == "UH":
        return amount
    if unit == "MH":
        return amount * 1000.0
    return amount * 1_000_000.0


def is_likely_schottky_diode(value: str) -> bool | None:
    """Return a conservative diode-family classification when obvious."""

    part = re.sub(r"[^A-Z0-9]", "", value.upper())
    if not part:
        return None
    if part.startswith(("SS", "SK", "MBR", "MBRA", "BAS", "BAT", "1N58")):
        return True
    if part.startswith(("1N400", "1N539", "FR", "UF")):
        return False
    return None
