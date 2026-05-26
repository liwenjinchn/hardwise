"""Aggregator from parse-level records to V2 IR Design.

KiCad path (V2.1): ``build_design(registry)`` — pulls components +
NC pin records out of the BoardRegistry the parser already populates.

Allegro netlist paths (V2.5): ``build_design_from_netlist()`` handles
Telesis-style single-file netlists, and ``build_design_from_pst()``
handles Capture/Allegro PST handoff directories.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from hardwise.adapters.allegro_netlist import AllegroNetlistRegistry
from hardwise.adapters.allegro_pst import AllegroPstRegistry
from hardwise.adapters.base import BoardRegistry, NcPinRecord
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin


def _build_pin_from_nc(nc: NcPinRecord) -> Pin:
    """Convert one ``NcPinRecord`` (parse-level) into a Pin (IR-level).

    ``is_nc`` is always True because an NcPinRecord only exists when the
    schematic placed an explicit ``no_connect`` marker. ``net`` is left
    as None — NC pins are not connected to any net.
    """
    return Pin(
        number=nc.pin_number,
        name=nc.pin_name,
        electrical_type=nc.pin_electrical_type,
        is_nc=True,
        net=None,
    )


def build_design(registry: BoardRegistry, profile_dir: Path | None = None) -> Design:
    """Aggregate a KiCad-parsed BoardRegistry into a V2 Design.

    Each ComponentRecord becomes one Component. NcPinRecord rows are
    grouped by refdes and attached as ``Pin`` objects on the matching
    Component. V2.1 leaves ``Design.nets`` empty — schematic-side net
    parsing is V2.5+. Components whose refdes has no NcPinRecord get
    an empty pin list (no shared mutable default).
    """
    nc_by_refdes: dict[str, list[NcPinRecord]] = {}
    for nc in registry.nc_pins:
        nc_by_refdes.setdefault(nc.refdes, []).append(nc)

    components: dict[str, Component] = {}
    for record in registry.components:
        pins = [_build_pin_from_nc(nc) for nc in nc_by_refdes.get(record.refdes, [])]
        components[record.refdes] = Component(
            refdes=record.refdes,
            value=record.value,
            package=record.footprint or None,
            datasheet_path=record.datasheet or None,
            datasheet_profile=_try_load_profile(record.datasheet, profile_dir),
            pins=pins,
        )

    return Design(
        components=components,
        nets={},
        project_path=registry.project_dir,
        source_eda="kicad",
    )


def build_design_from_netlist(registry: AllegroNetlistRegistry) -> Design:
    """Aggregate an Allegro/Telesis netlist registry into a V2 Design.

    Telesis netlists provide connectivity, not datasheet identity. Each
    package refdes becomes a Component, and every net endpoint becomes a
    non-NC Pin with its ``net`` populated. Datasheet fields stay empty so
    datasheet-driven checks skip rather than guessing.
    """
    components: dict[str, Component] = {}
    for package in registry.packages:
        for refdes in package.refdes_list:
            components[refdes] = Component(
                refdes=refdes,
                value=package.device_name,
                package=package.package_name,
            )

    nets: dict[str, Net] = {}
    seen_pin_nets: dict[tuple[str, str], str] = {}
    pins_by_refdes: dict[str, list[Pin]] = {refdes: [] for refdes in components}

    for net in registry.nets:
        nodes: list[tuple[str, str]] = []
        for refdes, pin_number in net.nodes:
            key = (refdes, pin_number)
            previous_net = seen_pin_nets.get(key)
            if previous_net is not None:
                raise ValueError(
                    f"{refdes}.{pin_number} appears on multiple nets: {previous_net}, {net.name}"
                )
            seen_pin_nets[key] = net.name
            nodes.append(key)
            pins_by_refdes[refdes].append(
                Pin(
                    number=pin_number,
                    name="",
                    electrical_type="",
                    is_nc=False,
                    net=net.name,
                )
            )
        nets[net.name] = Net(name=net.name, nodes=nodes)

    for refdes, pins in pins_by_refdes.items():
        components[refdes] = components[refdes].model_copy(update={"pins": pins})

    return Design(
        components=components,
        nets=nets,
        project_path=registry.source_file.parent,
        source_eda="allegro_netlist",
    )


def build_design_from_pst(registry: AllegroPstRegistry) -> Design:
    """Aggregate a Capture/Allegro PST registry into a V2 Design.

    PST exports split schematic facts across part, net, and primitive
    files. Parts become Components, ``NODE_NAME`` rows become connected
    Pins, and primitive body fields are preserved as component properties
    without inventing datasheet links.
    """
    components: dict[str, Component] = {}
    for part in registry.parts:
        value = part.properties.get("VALUE", part.primitive_name)
        package = part.properties.get("JEDEC_TYPE")
        components[part.refdes] = Component(
            refdes=part.refdes,
            value=value,
            package=package,
            part_number=part.properties.get("PART_NAME"),
            properties=part.properties,
        )

    nets: dict[str, Net] = {}
    seen_pin_nets: dict[tuple[str, str], str] = {}
    pins_by_refdes: dict[str, list[Pin]] = {refdes: [] for refdes in components}

    for net in registry.nets:
        nodes: list[tuple[str, str]] = []
        for node in net.nodes:
            key = (node.refdes, node.pin_number)
            previous_net = seen_pin_nets.get(key)
            if previous_net is not None:
                raise ValueError(
                    f"{node.refdes}.{node.pin_number} appears on multiple nets: "
                    f"{previous_net}, {net.name}"
                )
            seen_pin_nets[key] = net.name
            nodes.append(key)
            pins_by_refdes[node.refdes].append(
                Pin(
                    number=node.pin_number,
                    name=node.pin_name,
                    electrical_type="",
                    is_nc=False,
                    net=net.name,
                )
            )
        nets[net.name] = Net(name=net.name, nodes=nodes)

    for refdes, pins in pins_by_refdes.items():
        components[refdes] = components[refdes].model_copy(update={"pins": pins})

    return Design(
        components=components,
        nets=nets,
        project_path=registry.source_dir,
        source_eda="allegro_netlist",
    )


def _try_load_profile(
    datasheet_path: str,
    profile_dir: Path | None = None,
) -> DatasheetProfile | None:
    """Load a datasheet profile by datasheet basename, if present."""

    if not datasheet_path:
        return None
    basename = _datasheet_stem(datasheet_path)
    if not basename:
        return None
    root = profile_dir or Path("data/datasheet_profiles")
    path = root / f"{basename}.json"
    if not path.exists():
        return None
    return DatasheetProfile.load(path)


def _datasheet_stem(datasheet_path: str) -> str:
    parsed = urlparse(datasheet_path)
    path = parsed.path if parsed.scheme else datasheet_path
    return Path(path).stem
