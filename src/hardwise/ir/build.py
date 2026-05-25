"""Aggregator from parse-level records to V2 IR Design.

KiCad path (V2.1): ``build_design(registry)`` — pulls components +
NC pin records out of the BoardRegistry the parser already populates.

Allegro netlist path (V2.5): ``build_design_from_netlist()`` lands in
a separate plan; this module will grow a second top-level function.
"""

from __future__ import annotations

from hardwise.adapters.base import NcPinRecord
from hardwise.ir.types import Pin


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
