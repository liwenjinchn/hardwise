"""R003 — NC pin handling (EDA-only stage).

Slice 3 implementation: lists all NC-marked pins as medium findings.
Datasheet semantic comparison deferred to Slice 4.
"""

from __future__ import annotations

from hardwise.adapters.base import NcPinRecord
from hardwise.checklist.finding import Finding


def check(nc_pins: list[NcPinRecord]) -> list[Finding]:
    """Produce a medium finding for every pin with a no_connect marker."""
    findings: list[Finding] = []
    for pin in nc_pins:
        findings.append(
            Finding(
                rule_id="R003",
                severity="medium",
                refdes=pin.refdes,
                message=(
                    f"{pin.refdes} pin {pin.pin_number} ({pin.pin_name}) "
                    f"marked NC (type: {pin.pin_electrical_type}). "
                    f"Confirm NC handling with datasheet."
                ),
                evidence_tokens=[f"sch:{pin.source_file.name}#{pin.refdes}"],
                suggested_action=(
                    "Review datasheet NC pin section. Confirm whether "
                    "pin should float, tie to GND, or tie to VCC."
                ),
            )
        )
    return findings
