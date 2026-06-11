"""R009 — power pin without a net (pin-table sourced).

A POWER-type pin with no net means a supply or ground pin is unconnected —
either a real wiring miss or a deliberate omission that deserves an explicit
NC marker. Pin electrical types exist only in the Capture pin-table export;
the netlist path cannot run this check. The enum mapping behind
`pin_category == "POWER"` was cross-validated on a real 81-page design:
99.9% of POWER(7) pins landed on power/ground-pattern nets.

Standalone record-level check; see R008 for the staging note on workbench
intake.
"""

from __future__ import annotations

from hardwise.adapters.capture_pin_table import PinTableRecord
from hardwise.checklist.finding import EvidenceStep, Finding

RULE_ID = "R009"


def check(records: list[PinTableRecord]) -> list[Finding]:
    """One Finding per POWER pin that has no net.

    An NC marker on a power pin downgrades the machine judgment to
    `reviewer_to_confirm` — unusual but sometimes legitimate (e.g. an unused
    supply section) — while an unmarked one is `likely_issue`.
    """
    findings: list[Finding] = []
    for r in records:
        if r.pin_category != "POWER" or r.is_connected:
            continue
        location = f"{r.page}@{r.inst_x},{r.inst_y}"
        nc_note = " (carries an NC marker)" if r.is_nc else ""
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity="high",
                refdes=r.refdes,
                pin_number=r.pin_number,
                message=(
                    f"{r.refdes} pin {r.pin_number} ({r.pin_name}) is a POWER "
                    f"pin with no net{nc_note} at {location}."
                ),
                evidence_tokens=[f"sch:{location}#{r.refdes}.{r.pin_number}"],
                suggested_action=(
                    "Connect the pin to its supply/ground net, or document the "
                    "omission with an explicit NC marker and a design note."
                ),
                evidence_chain=[
                    EvidenceStep(
                        source="eda",
                        claim=(
                            f"Pin-table row: {r.refdes}.{r.pin_number} type "
                            f"{r.pin_type_raw}, net empty, nc_marker "
                            f"{int(r.is_nc)} (page {r.page}, x={r.inst_x}, "
                            f"y={r.inst_y})."
                        ),
                        token=(
                            f"pintable:{r.source_file.name}"
                            f"#{r.refdes}.{r.pin_number}"
                        ),
                    )
                ],
                decision="reviewer_to_confirm" if r.is_nc else "likely_issue",
            )
        )
    return findings
