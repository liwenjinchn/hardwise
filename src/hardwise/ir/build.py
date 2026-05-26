"""Aggregator from parse-level records to V2 IR Design.

KiCad path (V2.1): ``build_design(registry)`` — pulls components +
NC pin records out of the BoardRegistry the parser already populates.

Allegro netlist path (V2.5): ``build_design_from_netlist()`` lands in
a separate plan; this module will grow a second top-level function.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from hardwise.adapters.base import BoardRegistry, NcPinRecord
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin


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
