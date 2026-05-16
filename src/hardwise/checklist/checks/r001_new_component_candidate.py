"""R001 — New-component candidate identification (footprint field empty).

Reads the schematic-side raw `ComponentRecord` list (NOT the merged
`BoardRegistry.components` — that view backfills empty schematic footprints
from the .kicad_pcb file, which would defeat this rule's signal). Per
`docs/PLAN.md` DR-008 and `data/checklists/sch_review.yaml` R001.

Filters out KiCad virtual symbols (refdes starting with `#`, e.g. `#PWR05`,
`#FLG01`) — those are power flags / no-connect markers, not real parts.

A finding here is severity `info`: it's an attention-allocation hint, not
an error. The reviewer is being told "this part has no footprint yet,
likely because layout hasn't named it — so it's probably new-build, please
re-read its datasheet."
"""

from __future__ import annotations

from hardwise.adapters.base import ComponentRecord
from hardwise.checklist.finding import Finding


def check(schematic_records: list[ComponentRecord]) -> list[Finding]:
    findings: list[Finding] = []
    for record in schematic_records:
        if record.refdes.startswith("#"):
            continue
        if record.footprint:
            continue
        findings.append(
            Finding(
                rule_id="R001",
                severity="info",
                refdes=record.refdes,
                message=(
                    f"{record.refdes} has empty Footprint field — likely a "
                    "new-build part still awaiting the layout team's footprint "
                    "assignment."
                ),
                evidence_tokens=[f"sch:{record.source_file.name}#{record.refdes}"],
                suggested_action=(
                    "Treat as new-component candidate; review the part's "
                    "datasheet symbol/footprint dimensions and pinout before "
                    "sign-off."
                ),
                decision="reviewer_to_confirm",
            )
        )
    return findings
