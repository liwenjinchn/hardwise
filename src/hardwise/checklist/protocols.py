"""Component-check protocol and dispatcher for V2.2.

V2.2 moves the review loop from "each rule scans the whole registry" to
"the runner visits each Component and asks the rules that apply to it." The
old BoardRegistry stays in the context for now because it still owns source
file provenance used by evidence tokens.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.checklist.finding import Finding
from hardwise.ir.types import Component, Design


@dataclass(frozen=True)
class CheckContext:
    """Runtime context shared by component checks.

    ``registry`` is the compatibility bridge: V2.2 dispatches by Component,
    while evidence tokens still come from parse-level records. ``collection``
    is optional datasheet search state used by R003.
    """

    registry: BoardRegistry
    collection: Any | None = None
    top_k: int = 5

    def schematic_record_for(self, refdes: str) -> ComponentRecord | None:
        """Return the raw schematic record for a refdes, if available."""
        return next((r for r in self.registry.schematic_records if r.refdes == refdes), None)

    def nc_pins_for(self, refdes: str) -> list[NcPinRecord]:
        """Return NC pin records for one component."""
        return [pin for pin in self.registry.nc_pins if pin.refdes == refdes]


ComponentCheck = Callable[[Component, Design, CheckContext], list[Finding]]
AppliesTo = Callable[[Component], bool]


@dataclass(frozen=True)
class CheckSpec:
    """One registered component-centric schematic-review check."""

    rule_id: str
    applies_to: AppliesTo
    check: ComponentCheck


def run_component_checks(
    design: Design,
    specs: Iterable[CheckSpec],
    requested_rule_ids: set[str],
    context: CheckContext,
) -> tuple[list[Finding], list[str]]:
    """Run requested component checks and attach findings back to the IR.

    Returns ``(findings, rules_run)``. ``rules_run`` reports requested specs
    that existed, even when no component produced a finding.
    """

    findings: list[Finding] = []
    rules_run: list[str] = []
    for spec in specs:
        if spec.rule_id not in requested_rule_ids:
            continue
        rules_run.append(spec.rule_id)
        for component in design.components.values():
            if not spec.applies_to(component):
                continue
            for finding in spec.check(component, design, context):
                findings.append(finding)
                _attach_finding(component, finding)
    for component in design.components.values():
        component.decision = rollup_component_decision(component.findings)
    return findings, rules_run


def rollup_component_decision(findings: list[Finding]) -> str:
    """Return pass/warn/fail for one component's findings."""

    if not findings:
        return "pass"
    if any(f.severity in {"critical", "high"} for f in findings):
        return "fail"
    return "warn"


def _attach_finding(component: Component, finding: Finding) -> None:
    """Attach a finding to the component, and to a pin when pin_number matches."""

    component.findings.append(finding)
    if finding.pin_number is None:
        return
    pin = component.pin_by_number(finding.pin_number)
    if pin is not None:
        pin.findings.append(finding)
