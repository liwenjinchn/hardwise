"""Deterministic checks for parallel-in/serial-out shift-register chains."""

from __future__ import annotations

import re

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design
from hardwise.validation.pins import is_ground_net, voltage_for_net
from hardwise.validation.types import ComponentValidation


def validate_shift_register_piso(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[ComponentValidation]:
    """Validate common PISO shift-register control and cascade topology."""

    return [
        _validate_load_fanout(component, profile, design),
        _validate_clock_fanout(component, profile, design),
        _validate_clock_enable(component, profile, design),
        _validate_serial_chain(component, profile, design),
    ]


def _validate_load_fanout(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    pin = component.pin_by_number(_profile_pin(profile, "load_pin", "1"))
    evidence = _evidence(profile, "recommended.load_pin")
    if pin is None or not pin.net:
        return _check(
            "shift_register_load_fanout",
            "ERROR",
            component,
            "Shift-register load pin is missing or not connected.",
            evidence,
        )
    peers = _peers_on_pin_net(component, profile, design, pin.number, {pin.net})
    if peers:
        return _check(
            "shift_register_load_fanout",
            "PASS",
            component,
            f"Load pin shares {pin.net} with peer shift-register(s) {', '.join(peers)}.",
            evidence,
        )
    return _check(
        "shift_register_load_fanout",
        "WARN",
        component,
        f"Load pin is connected to {pin.net}, but no peer load fanout was proven.",
        evidence,
    )


def _validate_clock_fanout(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    pin = component.pin_by_number(_profile_pin(profile, "clock_pin", "2"))
    evidence = _evidence(profile, "recommended.clock_pin")
    if pin is None or not pin.net:
        return _check(
            "shift_register_clock_fanout",
            "ERROR",
            component,
            "Shift-register clock pin is missing or not connected.",
            evidence,
        )
    reachable = _reachable_nets_through_one_resistor(component, design, pin.net)
    peers = _peers_sharing_reachable_pin(component, profile, design, pin.number, reachable)
    if peers:
        shared = _shared_reachable_net(component, profile, design, pin.number, reachable) or pin.net
        return _check(
            "shift_register_clock_fanout",
            "PASS",
            component,
            (
                f"Clock pin reaches shared clock net {shared} with peer "
                f"shift-register(s) {', '.join(peers)}."
            ),
            evidence,
        )
    return _check(
        "shift_register_clock_fanout",
        "WARN",
        component,
        f"Clock pin is connected to {pin.net}, but common clock fanout was not proven.",
        evidence,
    )


def _validate_clock_enable(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    pin = component.pin_by_number(_profile_pin(profile, "clock_enable_pin", "15"))
    evidence = _evidence(profile, "recommended.clock_enable_pin")
    if pin is None or not pin.net:
        return _check(
            "shift_register_clock_enable",
            "ERROR",
            component,
            "Clock-enable pin is missing or not connected.",
            evidence,
        )
    reachable = _reachable_nets_through_one_resistor(component, design, pin.net)
    ground = next((net for net in reachable if is_ground_net(net)), "")
    if ground:
        return _check(
            "shift_register_clock_enable",
            "PASS",
            component,
            f"Clock-enable pin reaches ground reference {ground}, enabling shift clocks.",
            evidence,
        )
    if voltage_for_net(pin.net, design) is not None:
        return _check(
            "shift_register_clock_enable",
            "PASS",
            component,
            f"Clock-enable pin is tied to deterministic net {pin.net}.",
            evidence,
        )
    return _check(
        "shift_register_clock_enable",
        "WARN",
        component,
        f"Clock-enable pin is connected to {pin.net}, but no defined level was proven.",
        evidence,
    )


def _validate_serial_chain(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> ComponentValidation:
    output_pin = component.pin_by_number(_profile_pin(profile, "serial_output_pin", "9"))
    input_pin_number = _profile_pin(profile, "serial_input_pin", "10")
    evidence = _evidence(profile, "recommended.serial_chain")
    if output_pin is None or not output_pin.net:
        return _check(
            "shift_register_serial_chain",
            "ERROR",
            component,
            "Serial output pin is missing or not connected.",
            evidence,
        )

    reachable = _reachable_nets_through_one_resistor(component, design, output_pin.net)
    next_peers = _peers_on_pin_net(component, profile, design, input_pin_number, reachable)
    if next_peers:
        return _check(
            "shift_register_serial_chain",
            "PASS",
            component,
            (
                f"Serial output {output_pin.net} cascades to DS pin on "
                f"{', '.join(next_peers)}."
            ),
            evidence,
        )

    own_index = _chain_index(output_pin.net)
    max_index = _max_chain_index(profile, design)
    if own_index is not None and max_index is not None and own_index == max_index:
        return _check(
            "shift_register_serial_chain",
            "PASS",
            component,
            f"Serial output {output_pin.net} is the terminal stage of the proven chain.",
            evidence,
        )

    status = "WARN" if own_index is None else "ERROR"
    return _check(
        "shift_register_serial_chain",
        status,
        component,
        f"Serial output {output_pin.net} does not reach another DS input in the parsed topology.",
        evidence,
    )


def _peers_on_pin_net(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    pin_number: str,
    nets: set[str],
) -> list[str]:
    peers = []
    for peer in _peer_components(component, profile, design):
        pin = peer.pin_by_number(pin_number)
        if pin is not None and pin.net in nets:
            peers.append(peer.refdes)
    return sorted(peers)


def _peers_sharing_reachable_pin(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    pin_number: str,
    reachable: set[str],
) -> list[str]:
    peers = []
    for peer in _peer_components(component, profile, design):
        pin = peer.pin_by_number(pin_number)
        if pin is None or not pin.net:
            continue
        peer_reachable = _reachable_nets_through_one_resistor(peer, design, pin.net)
        if reachable & peer_reachable:
            peers.append(peer.refdes)
    return sorted(peers)


def _shared_reachable_net(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
    pin_number: str,
    reachable: set[str],
) -> str | None:
    for peer in _peer_components(component, profile, design):
        pin = peer.pin_by_number(pin_number)
        if pin is None or not pin.net:
            continue
        shared = reachable & _reachable_nets_through_one_resistor(peer, design, pin.net)
        if shared:
            return sorted(shared)[0]
    return None


def _peer_components(
    component: Component,
    profile: DatasheetProfile,
    design: Design,
) -> list[Component]:
    identities = {_normalize(profile.part_number), *[_normalize(alias) for alias in profile.part_number_aliases]}
    return [
        peer
        for peer in design.components.values()
        if peer.refdes != component.refdes
        and (
            _normalize(peer.part_number or "") in identities
            or _normalize(peer.value or "") in identities
        )
    ]


def _reachable_nets_through_one_resistor(
    component: Component,
    design: Design,
    net_name: str,
) -> set[str]:
    reachable = {net_name}
    net = design.nets.get(net_name)
    if net is None:
        return reachable
    for refdes, _pin_number in net.nodes:
        if refdes == component.refdes or not refdes.startswith("R"):
            continue
        resistor = design.components.get(refdes)
        if resistor is None:
            continue
        for pin in resistor.pins:
            if pin.net and pin.net != net_name:
                reachable.add(pin.net)
    return reachable


def _max_chain_index(profile: DatasheetProfile, design: Design) -> int | None:
    output_pin_number = _profile_pin(profile, "serial_output_pin", "9")
    indexes = [
        _chain_index(pin.net or "")
        for component in design.components.values()
        if _normalize(component.part_number or component.value) in _profile_identities(profile)
        for pin in [component.pin_by_number(output_pin_number)]
        if pin is not None
    ]
    found = [index for index in indexes if index is not None]
    return max(found) if found else None


def _profile_identities(profile: DatasheetProfile) -> set[str]:
    return {_normalize(profile.part_number), *[_normalize(alias) for alias in profile.part_number_aliases]}


def _chain_index(net_name: str) -> int | None:
    match = re.search(r"OUT(\d+)", net_name.upper())
    if match is None:
        return None
    return int(match.group(1))


def _profile_pin(profile: DatasheetProfile, key: str, default: str) -> str:
    value = profile.recommended.get(key)
    return str(value) if value else default


def _evidence(profile: DatasheetProfile, key: str) -> list[str]:
    token = profile.evidence.get(key, "")
    return [token] if token else []


def _normalize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _check(
    name: str,
    status: str,
    component: Component,
    summary: str,
    evidence: list[str],
) -> ComponentValidation:
    return ComponentValidation(
        check=name,
        status=status,  # type: ignore[arg-type]
        refdes=component.refdes,
        summary=summary,
        evidence=evidence,
    )
