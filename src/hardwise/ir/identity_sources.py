"""Preserve explicitly named netlist MPN declarations without interpreting library names."""

import json
from collections.abc import Iterable
from hardwise.ir.types import Component

MPN_RECORDS = "HARDWISE_NETLIST_MPN_RECORDS"
MPN_FIELDS = {"mpn", "manufacturer_part_number", "mfr_part_number"}


def is_mpn_field(name: str) -> bool:
    return name.strip().casefold().replace(" ", "_") in MPN_FIELDS


def attach_mpn_sources(component: Component, records: Iterable[dict[str, str]]) -> Component:
    records = list(records)
    properties = dict(component.properties)
    properties.pop(MPN_RECORDS, None)
    if records:
        properties[MPN_RECORDS] = json.dumps(records, ensure_ascii=False, sort_keys=True)
    return component.model_copy(update={"properties": properties})


def netlist_mpn_sources(component: Component) -> list[dict[str, str]]:
    raw = component.properties.get(MPN_RECORDS)
    return json.loads(raw) if raw else []
