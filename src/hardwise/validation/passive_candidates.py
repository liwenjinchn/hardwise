"""Pre-enumerated generic-passive checks; no invented electrical function coverage."""

from hardwise.bom.types import BomRow
from hardwise.ir.types import Component, Design
from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
    UnsupportedScope,
)
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.validation.identity_scope import _identity_conflict_reason
from hardwise.validation.passive_contracts import PassiveFamily
from hardwise.validation.types import ValidationReport

FAMILY_CHECKS = {
    "capacitor": (
        ("capacitor_value_parse", "2"),
        ("capacitor_rated_voltage_parse", "3"),
        ("capacitor_package_presence", "1"),
        ("capacitor_voltage_margin", "4"),
    ),
    "resistor": (
        ("resistor_value_parse", "2"),
        ("resistor_package_presence", "1"),
        ("resistor_power_estimate", "4"),
    ),
    "inductor": (
        ("inductor_value_parse", "2"),
        ("inductor_package_presence", "1"),
        ("inductor_current_rating_token", "2"),
    ),
    "ferrite": (
        ("ferrite_impedance_parse", "2"),
        ("ferrite_package_presence", "1"),
        ("ferrite_current_rating_token", "2"),
    ),
}
PASSIVE_CATALOG = RuleCatalog(
    version="hardwise.passive_candidates.v1",
    rules=(
        RuleDefinition(
            rule_id="bom_identity_conflict",
            version="4",
            object_kind="component",
            scope="Recorded BOM/netlist identity conflicts only",
        ),
        RuleDefinition(
            rule_id="passive_terminal_inventory",
            version="1",
            object_kind="component",
            scope="Observed two-terminal inventory; not source completeness",
        ),
        RuleDefinition(
            rule_id="passive_terminal_connection",
            version="1.connection-isolation1",
            object_kind="pin",
            scope="Observed terminal connectivity only",
        ),
        *(
            RuleDefinition(
                rule_id=rule,
                version=version,
                object_kind="component",
                scope="Generic passive deterministic check; no unmodeled AC behavior",
            )
            for checks in FAMILY_CHECKS.values()
            for rule, version in checks
        ),
    ),
)
DEFINITIONS = {r.rule_id: r for r in PASSIVE_CATALOG.rules}


def _candidate(component, family, rule, *, pin=None, conflict=None):
    definition = DEFINITIONS[rule]
    instance = (("family", family),) + ((("pin", pin),) if pin is not None else ())
    return Candidate(
        catalog_version=PASSIVE_CATALOG.version,
        rule_id=rule,
        rule_version=definition.version,
        object_kind=definition.object_kind,
        object_id=component.refdes,
        instance=instance,
        applicability="unknown" if conflict else "applicable",
        reason=conflict or "Explicit generic family and observed input scope",
    )


def enumerate_passive_candidates(
    component: Component, family: PassiveFamily
) -> tuple[Candidate, ...]:
    if family not in FAMILY_CHECKS:
        raise ValueError("Unsupported generic passive family")
    if len({p.number for p in component.pins}) != len(component.pins):
        raise ValueError("Duplicate terminal identity")
    conflict = _identity_conflict_reason(component)
    return (
        _candidate(component, family, "bom_identity_conflict"),
        _candidate(component, family, "passive_terminal_inventory"),
        *(
            _candidate(component, family, rule, conflict=conflict)
            for rule, _ in FAMILY_CHECKS[family]
        ),
        *(
            _candidate(
                component, family, "passive_terminal_connection", pin=p.number, conflict=conflict
            )
            for p in component.pins
        ),
    )


def bind_passive_report(
    component: Component,
    family: PassiveFamily,
    candidates: tuple[Candidate, ...],
    report: ValidationReport,
) -> CandidateSnapshot:
    if report.refdes != component.refdes:
        raise ValueError("Report belongs to a different component")
    outcomes = []

    def add(rule, result, reason, evidence=(), pin=None):
        identity = _candidate(component, family, rule, pin=pin)
        outcomes.append(
            CandidateOutcome(
                candidate_id=identity.candidate_id,
                result=result,
                reason=reason,
                evidence=tuple(evidence),
            )
        )

    conflict = _identity_conflict_reason(component)
    # Gate checks execute directly from source facts, even if the family evaluator stops early.
    add(
        "bom_identity_conflict",
        "UNKNOWN" if conflict else "PASS",
        conflict or "No recorded identity conflict; this is not MPN authenticity verification.",
    )
    two = len(component.pins) == 2
    add(
        "passive_terminal_inventory",
        "PASS" if two else "UNKNOWN",
        "Exactly two observed terminals; source completeness is not verified."
        if two
        else "Expected generic two-terminal scope is unavailable; terminal identities are not invented.",
    )
    seen_identity = False
    for check in report.component_checks:
        if check.refdes is not None and check.refdes != component.refdes:
            raise ValueError("Check belongs to a different component")
        if check.check == "bom_identity_conflict":
            if seen_identity:
                raise ValueError("Duplicate identity-conflict output")
            seen_identity = True
            if not conflict or check.result != "UNKNOWN":
                raise ValueError("Unexpected identity-conflict output")
            continue
        if check.check not in dict(FAMILY_CHECKS[family]):
            raise ValueError("Unregistered passive result")
        if check.rule_version != DEFINITIONS[check.check].version:
            raise ValueError("Passive producer version differs from catalog")
        add(check.check, check.result, check.summary, check.evidence)
    for pin in report.pin_results:
        if pin.rule_version not in {"1", "1.connection-isolation1"}:
            raise ValueError("Unknown terminal producer version")
        add("passive_terminal_connection", pin.result, pin.summary, pin.evidence, pin.pin_number)
    unsupported = (
        UnsupportedScope(
            object_kind="component",
            object_id=component.refdes,
            scope="AC/transient/thermal functional suitability",
            reason="Generic value/rating/DC checks do not implement full component function",
        ),
    )
    return CandidateSnapshot(
        catalog=PASSIVE_CATALOG,
        candidates=candidates,
        outcomes=tuple(outcomes),
        unsupported=unsupported,
    )


def evaluate_passive_candidates(
    component: Component, bom_row: BomRow | None, design: Design, family: PassiveFamily
) -> CandidateSnapshot:
    candidates = enumerate_passive_candidates(component, family)
    report = validate_generic_passive(component, bom_row, design, family)
    return bind_passive_report(component, family, candidates, report)
