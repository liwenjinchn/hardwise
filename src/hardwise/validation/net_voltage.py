"""Parse voltage hints from schematic net names.

These hints are naming-rule evidence only. They do not prove the rail's
electrical source or measured voltage; they only let validation rules compare
clear net names such as P3V3_STBY against datasheet limits.
"""

from __future__ import annotations

import re

from pydantic import BaseModel


class VoltageHint(BaseModel):
    """Structured voltage-name parse result."""

    found: bool
    net_name: str
    voltage: float | None = None
    rule_token: str | None = None
    reason: str | None = None


def parse_voltage_hint(net_name: str) -> VoltageHint:
    """Parse a voltage hint from a known rail naming convention."""

    normalized = net_name.strip().upper()
    match = _P_RAIL_RE.search(normalized) or _VCC_VDD_RE.search(normalized)
    if match is None:
        return VoltageHint(
            found=False,
            net_name=net_name,
            reason="No voltage hint found in net name.",
        )

    whole = float(match.group("whole"))
    frac_text = match.group("frac") or ""
    voltage = whole if not frac_text else whole + int(frac_text) / (10 ** len(frac_text))
    return VoltageHint(
        found=True,
        net_name=net_name,
        voltage=voltage,
        rule_token=f"rule:net_voltage_name#{net_name}",
    )


_P_RAIL_RE = re.compile(r"(?:^|_)(?:P)(?P<whole>\d+)V(?P<frac>\d+)?(?:_|$)")
_VCC_VDD_RE = re.compile(r"(?:^|_)(?:VCC|VDD)_(?P<whole>\d+)V(?P<frac>\d+)?(?:_|$)")
