"""R008 — floating input pin (pin-table sourced).

An INPUT-type pin with no net and no NC marker is electrically floating: an
undriven CMOS input can oscillate, draw shoot-through current, or latch random
logic levels. On the validated real-board run this fired 48 times on an
81-page design — none of which the netlist path can see, because netlist/PST/
BOM exports carry no pin electrical types and no NC markers.

Standalone record-level check (same shape as R003's `check`): consumes
`PinTableRecord`s from `adapters/capture_pin_table.py` and returns standard
`Finding`s. Component-IR / workbench intake is staged in `docs/rolling_log.md`
behind the pin-table workbench slice.
"""

from __future__ import annotations

from hardwise.adapters.capture_pin_table import PinTableRecord
from hardwise.checklist.finding import EvidenceStep, Finding

RULE_ID = "R008"


def check(records: list[PinTableRecord]) -> list[Finding]:
    """One Finding per INPUT pin that has no net and no NC marker."""
    findings: list[Finding] = []
    for r in records:
        if r.pin_category != "INPUT" or r.is_connected or r.is_nc:
            continue
        location = f"{r.page}@{r.inst_x},{r.inst_y}"
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity="high",
                refdes=r.refdes,
                pin_number=r.pin_number,
                message=(
                    f"{r.refdes} pin {r.pin_number} ({r.pin_name}) is an INPUT "
                    f"pin with no net and no NC marker — floating input at "
                    f"{location}."
                ),
                evidence_tokens=[f"sch:{location}#{r.refdes}.{r.pin_number}"],
                suggested_action=(
                    "Tie the input to a defined level or its driving net, or "
                    "place an explicit NC marker if it is intentionally unused."
                ),
                evidence_chain=[
                    EvidenceStep(
                        source="eda",
                        claim=(
                            f"Pin-table row: {r.refdes}.{r.pin_number} type "
                            f"{r.pin_type_raw}, net empty, nc_marker 0 "
                            f"(page {r.page}, x={r.inst_x}, y={r.inst_y})."
                        ),
                        token=(
                            f"pintable:{r.source_file.name}"
                            f"#{r.refdes}.{r.pin_number}"
                        ),
                    )
                ],
                decision="likely_issue",
            )
        )
    return findings
