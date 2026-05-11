"""R002 — Capacitor rated-voltage field completeness (Slice 2 scope).

Per `data/checklists/sch_review.yaml` R002 the full rule is "rated_voltage of
the cap must be at least 1.25 × the working_voltage of its net" (i.e. the
classic 80% derating rule). That comparison needs two facts:

  1. rated_voltage parsed from the value string (this module owns).
  2. working_voltage of the cap's net (requires a net parser).

Slice 2 ships only #1. KiCad net parsing is deferred to Slice 3 per
`docs/PLAN.md` DR-006 / Slice 2 plan. So this check produces:

  - `info` finding when rated_voltage is declared — reviewer is reminded to
    confirm the 80% rule manually against actual working voltage.
  - `medium` finding when rated_voltage is missing — the value field is
    incomplete and the rule cannot even be attempted; ask the schematic
    author to suffix `/<num>V`.

The `high` severity branch (rated_voltage parsed AND working_voltage known
AND working_voltage > rated_voltage × 0.8) is intentionally not implemented
here — it will land in Slice 3+ once `EDA.nets.power_domain` evidence is
available.

Input is the schematic-side raw `ComponentRecord` list, same convention as
R001 (DR-008): never pass the merged `BoardRegistry.components` view because
that one has been polluted by `.kicad_pcb` footprint backfill — which doesn't
affect this rule's signal, but DR-008 wants every schematic-only rule to
take the same raw source for consistency.
"""

from __future__ import annotations

import re

from hardwise.adapters.base import ComponentRecord
from hardwise.checklist.finding import Finding

# Match "/25V", "/ 25 V", "/4.7V" etc. anywhere in the value string.
# The `/` is the conventional cap-value separator in EE notation.
_RATED_VOLTAGE_RE = re.compile(r"/\s*(\d+(?:\.\d+)?)\s*V\b", re.IGNORECASE)


def parse_rated_voltage(value: str) -> float | None:
    """Return the rated voltage in volts if the value string declares one.

    >>> parse_rated_voltage("22uF/25V")
    25.0
    >>> parse_rated_voltage("100uF / 16 V")
    16.0
    >>> parse_rated_voltage("4.7nF") is None
    True
    >>> parse_rated_voltage("") is None
    True
    """
    if not value:
        return None
    match = _RATED_VOLTAGE_RE.search(value)
    if match is None:
        return None
    return float(match.group(1))


def check(schematic_records: list[ComponentRecord]) -> list[Finding]:
    findings: list[Finding] = []
    for record in schematic_records:
        if not record.refdes.startswith("C"):
            continue
        if record.refdes.startswith("#"):
            continue
        value = record.value.strip()
        if not value or value == "0":
            continue

        evidence = [f"sch:{record.source_file.name}#{record.refdes}"]
        rated_voltage = parse_rated_voltage(value)

        if rated_voltage is not None:
            findings.append(
                Finding(
                    rule_id="R002",
                    severity="info",
                    refdes=record.refdes,
                    message=(
                        f"{record.refdes} rated voltage = {rated_voltage:g} V detected from "
                        f"value '{value}'. Reviewer must confirm the 80% derating rule against "
                        f"the actual working voltage on this cap's net "
                        f"(net parser not yet available — manual check)."
                    ),
                    evidence_tokens=evidence,
                    suggested_action=(
                        f"Confirm working voltage on this cap's net does not exceed "
                        f"{rated_voltage * 0.8:g} V."
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    rule_id="R002",
                    severity="medium",
                    refdes=record.refdes,
                    message=(
                        f"{record.refdes} value field '{value}' does not declare rated voltage "
                        f"(missing '/<num>V' suffix). The 80% derating rule cannot be "
                        f"evaluated without it."
                    ),
                    evidence_tokens=evidence,
                    suggested_action=(
                        "Clarify rated voltage by suffixing the value field, e.g. '100uF/25V'."
                    ),
                )
            )
    return findings
