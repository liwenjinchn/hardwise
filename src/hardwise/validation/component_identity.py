"""Normalize BOM item identities for grouped profile and document coverage."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from hardwise.bom.types import BomItem, sort_refdes_key

IdentityKind = Literal[
    "mpn",
    "part_like_value",
    "passive_value",
    "library_placeholder",
    "connector_or_mechanical",
    "missing",
]
SuggestedFamily = Literal[
    "capacitor",
    "resistor",
    "inductor",
    "ferrite",
    "diode",
    "transistor",
    "ic",
    "connector",
    "test_point",
    "mechanical",
    "crystal",
    "fuse",
    "switch",
    "relay",
    "transformer",
    "battery",
    "unknown",
]


class ComponentIdentity(BaseModel):
    """Normalized BOM identity for grouping and document/profile lookup."""

    identity: str
    normalized_identity: str
    identity_kind: IdentityKind
    suggested_family: SuggestedFamily


def normalize_bom_item_identity(item: BomItem) -> ComponentIdentity:
    """Normalize a BOM item without inventing missing MPNs."""

    candidate = item.part_number or ""
    value = item.value or ""
    if _is_connector_or_mechanical(item, candidate or value):
        identity = candidate or value or "-"
        kind: IdentityKind = "connector_or_mechanical" if identity != "-" else "missing"
        return _identity(identity, kind, item)

    if _is_passive_item(item):
        identity = value or candidate or "-"
        kind = "passive_value" if identity != "-" else "missing"
        return _identity(identity, kind, item)

    if candidate:
        kind = "library_placeholder" if _is_library_placeholder(candidate) else "mpn"
        return _identity(candidate, kind, item)

    if value and _looks_like_part_number(value) and not _is_library_placeholder(value):
        return _identity(value, "part_like_value", item)

    return _identity("-", "missing", item)


def _identity(identity: str, kind: IdentityKind, item: BomItem) -> ComponentIdentity:
    return ComponentIdentity(
        identity=identity,
        normalized_identity=_normalize_identity(identity),
        identity_kind=kind,
        suggested_family=_suggest_family(item, identity),
    )


def _suggest_family(item: BomItem, identity: str) -> SuggestedFamily:
    prefix = _dominant_prefix(item.refdes_list)
    text = " ".join(
        part.upper()
        for part in [identity, item.value or "", item.part_number or "", item.description or ""]
        if part
    )

    if prefix == "TP" or "TEST_POINT" in text or "TESTPOINT" in text:
        return "test_point"
    if prefix in {"MH", "MK"} or text.startswith("HOLE") or text == "MARK":
        return "mechanical"
    if prefix in {"J", "CN", "DC"} or _has_any(text, _CONNECTOR_TOKENS):
        return "connector"
    if prefix in {"C", "CE", "PC"}:
        return "capacitor"
    if prefix in {"R", "PR", "RN", "RT", "RP", "RA"}:
        return "resistor"
    if prefix in {"L", "PL"} or _has_any(text, ("CHOKE",)):
        return "inductor"
    if prefix == "FB" or "BEAD" in text or "FERRITE" in text:
        return "ferrite"
    if prefix in {"D", "LED", "VD"} or _has_any(
        text, ("DIODE", "ZENER", "TVS", "LED", "SCHOTTKY", "RECTIFIER")
    ):
        return "diode"
    if prefix in {"Q", "PQ", "VT"} or _has_any(text, ("MOSFET", "BJT", "TRANSISTOR")):
        return "transistor"
    if prefix == "Y" or _has_any(text, ("CRYSTAL", "XTAL", "OSCILLATOR", "RESONATOR")):
        return "crystal"
    if prefix in {"F", "FU"} or _has_any(text, ("FUSE", "POLYFUSE", "PTC RESETTABLE")):
        return "fuse"
    if prefix == "SW" or _has_any(text, ("SWITCH", "PUSHBUTTON")):
        return "switch"
    if prefix in {"K", "RY"} or "RELAY" in text:
        return "relay"
    if prefix == "T" or _has_any(text, ("TRANSFORMER", "XFMR")):
        return "transformer"
    if prefix == "BT" or _has_any(text, ("BATTERY", "COIN CELL", "BUTTON CELL")):
        return "battery"
    if prefix in {"U", "PU", "IC"}:
        return "ic"
    return "unknown"


def _dominant_prefix(refdes_list: list[str]) -> str:
    if not refdes_list:
        return ""
    match = re.match(r"[A-Z_]+", sorted(refdes_list, key=sort_refdes_key)[0].upper())
    return match.group(0) if match else ""


def _is_passive_item(item: BomItem) -> bool:
    family = _suggest_family(item, item.part_number or item.value or "")
    if family in {"capacitor", "resistor", "inductor", "ferrite"}:
        return True
    return bool(item.value and _looks_like_passive_value(item.value))


def _is_connector_or_mechanical(item: BomItem, identity: str) -> bool:
    family = _suggest_family(item, identity)
    return family in {"connector", "test_point", "mechanical"}


def _is_library_placeholder(value: str) -> bool:
    text = value.strip().upper()
    return (
        text.startswith("GW_")
        or text in {"MARK", "TESTPOINT", "TEST_POINT"}
        or text.startswith("HOLE_")
    )


def _looks_like_part_number(value: str) -> bool:
    text = value.strip().upper()
    if len(text) < 4:
        return False
    if _looks_like_passive_value(text):
        return False
    return bool(re.search(r"[A-Z]", text) and re.search(r"\d", text))


def _looks_like_passive_value(value: str) -> bool:
    text = value.strip().upper().replace(" ", "").replace("\N{OHM SIGN}", "OHM")
    return bool(_PASSIVE_VALUE_RE.fullmatch(text))


def _normalize_identity(value: str) -> str:
    if value == "-":
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


_CONNECTOR_TOKENS = (
    "CONN",
    "CONNECTOR",
    "HEADER",
    "HDR",
    "SOCKET",
    "PCIE",
    "MCIO",
    "TYPEC",
    "USB",
    "KF",
)
_PASSIVE_VALUE_RE = re.compile(
    r"\d+(\.\d+)?(R|K|M|OHM|UF|NF|PF|F|UH|NH|H|V|MV|A|MA|%)(\d+)?([A-Z%]+)?"
)
