"""R010 — NC marker on a connected pin (pin-table sourced).

Capture's pin-table export is the first public input channel that carries both
the net name and the explicit NC marker for the same pin. When both are present,
the schematic has contradictory intent: either the NC marker is stale, or the
pin should not be wired. The check stays at reviewer-to-confirm because the CSV
alone cannot know which side is wrong.
"""

from __future__ import annotations

from hardwise.adapters.capture_pin_table import PinTableRecord
from hardwise.checklist.finding import EvidenceStep, Finding

RULE_ID = "R010"


def check(records: list[PinTableRecord]) -> list[Finding]:
    """One Finding per pin that is both wired and marked NC."""
    findings: list[Finding] = []
    for r in records:
        if not r.is_nc or not r.is_connected:
            continue
        location = f"{r.page}@{r.inst_x},{r.inst_y}"
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity="medium",
                refdes=r.refdes,
                pin_number=r.pin_number,
                net=r.net,
                message=(
                    f"{r.refdes} pin {r.pin_number} ({r.pin_name}) is marked NC "
                    f"but is connected to net {r.net} at {location}."
                ),
                evidence_tokens=[f"sch:{location}#{r.refdes}.{r.pin_number}"],
                suggested_action=(
                    "Remove the NC marker if the connection is intentional, or "
                    "disconnect the pin if it should truly remain no-connect."
                ),
                evidence_chain=[
                    EvidenceStep(
                        source="eda",
                        claim=(
                            f"Pin-table row: {r.refdes}.{r.pin_number} has net "
                            f"{r.net!r} and nc_marker 1 (page {r.page}, "
                            f"x={r.inst_x}, y={r.inst_y})."
                        ),
                        token=(
                            f"pintable:{r.source_file.name}"
                            f"#{r.refdes}.{r.pin_number}"
                        ),
                    )
                ],
                decision="reviewer_to_confirm",
            )
        )
    return findings
