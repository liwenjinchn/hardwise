"""Catalog of profile approval, declared pins and explicit DC relationships.

Topology families remain a separate catalog; this is never full project coverage.
"""

from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
    UnsupportedScope,
)
from hardwise.validation.component import validate_component_against_profile
from hardwise.validation.identity_scope import (
    identity_conflict_report,
    profile_identity_conflict_report,
)
from hardwise.validation.profile_approval import PROFILE_RULE_SUFFIX, approval_reason
from hardwise.validation.profile_conditions import relation_instance

PROFILE_CATALOG = RuleCatalog(
    version="hardwise.profile_candidates.v1",
    rules=tuple(
        RuleDefinition(rule_id=rule, version="1", object_kind=kind, scope=scope)
        for rule, kind, scope in [
            ("profile_identity", "component", "Recorded identity agreement only"),
            (
                "profile_approval",
                "component",
                "Effective field approval and component applicability",
            ),
            ("profile_pin_inventory", "component", "Declared profile pin inventory only"),
            ("profile_pin", "pin", "Profiled pin check; not complete pin function"),
            ("profile_voltage_relation", "relation", "Explicit conditional DC relationship only"),
        ]
    ),
)
RULES = {r.rule_id: r for r in PROFILE_CATALOG.rules}


def _conflict(component, profile):
    report = identity_conflict_report(component) or profile_identity_conflict_report(
        component, profile
    )
    return report.component_checks[0].summary if report else None


def _candidate(component, rule, instance=(), reason=None):
    return Candidate(
        catalog_version=PROFILE_CATALOG.version,
        rule_id=rule,
        rule_version="1",
        object_kind=RULES[rule].object_kind,
        object_id=component.refdes,
        instance=instance,
        applicability="unknown" if reason else "applicable",
        reason=reason or "Declared profile scope",
    )


def enumerate_profile_candidates(component, profile):
    conflict = _conflict(component, profile)
    blocked = conflict or approval_reason(component, profile)
    candidates = [
        _candidate(component, r)
        for r in ("profile_identity", "profile_approval", "profile_pin_inventory")
    ]
    candidates.extend(
        _candidate(component, "profile_pin", (("pin", p.number),), blocked) for p in profile.pins
    )
    candidates.extend(
        _candidate(component, "profile_voltage_relation", relation_instance(r), blocked)
        for r in profile.voltage_relations
    )
    # Validate repeated pin/relationship identities before execution, not after collapse.
    CandidateSnapshot(catalog=PROFILE_CATALOG, candidates=tuple(candidates))
    return tuple(candidates)


def bind_profile_report(component, profile, candidates, report):
    if report.refdes != component.refdes:
        raise ValueError("Foreign profile report")
    expected = enumerate_profile_candidates(component, profile)
    if sorted(candidates, key=lambda c: c.candidate_id) != sorted(
        expected, key=lambda c: c.candidate_id
    ):
        raise ValueError("Candidates do not match the current profile scope")
    conflict_report = identity_conflict_report(component) or profile_identity_conflict_report(
        component, profile
    )
    if report.profile_part_number != ("" if conflict_report else profile.part_number):
        raise ValueError("Foreign profile identity in report")
    outcomes = []

    def add(rule, result, reason, instance=(), evidence=()):
        identity = _candidate(component, rule, instance)
        outcomes.append(
            CandidateOutcome(
                candidate_id=identity.candidate_id,
                result=result,
                reason=reason,
                evidence=tuple(evidence),
            )
        )

    conflict = _conflict(component, profile)
    blocked = conflict or approval_reason(component, profile)
    add(
        "profile_identity",
        "UNKNOWN" if conflict else "PASS",
        conflict or "No recorded profile identity conflict.",
    )
    add(
        "profile_approval",
        "UNKNOWN" if blocked else "PASS",
        blocked or "Effective field approval applies to this component.",
    )
    add(
        "profile_pin_inventory",
        "PASS" if profile.pins else "UNKNOWN",
        "Profile declares pins; export completeness and full function are not verified."
        if profile.pins
        else "Profile declares no pins; pin checks cannot be enumerated.",
    )
    seen = set()
    for check in report.component_checks:
        if check.refdes not in {None, component.refdes}:
            raise ValueError("Foreign profile check")
        if check.check in {
            "bom_identity_conflict",
            "profile_identity_conflict",
            "profile_review_status",
        }:
            expected_gate = conflict_report.component_checks[0] if conflict_report else None
            valid_gate = (
                check.check == expected_gate.check
                and check.rule_version == expected_gate.rule_version
                if expected_gate is not None
                else check.check == "profile_review_status"
                and check.rule_version == "2" + PROFILE_RULE_SUFFIX
                and blocked is not None
            )
            if check.check in seen or check.result != "UNKNOWN" or not valid_gate:
                raise ValueError("Unexpected or duplicate profile gate")
            seen.add(check.check)
            continue
        if not check.check.startswith("pin_voltage_relation_") or not check.instance:
            raise ValueError("Unregistered or unidentified base-profile result")
        if check.rule_version != "1" + PROFILE_RULE_SUFFIX:
            raise ValueError("Unknown relation producer version")
        add("profile_voltage_relation", check.result, check.summary, check.instance, check.evidence)
    for pin in report.pin_results:
        if pin.rule_version not in {
            version + PROFILE_RULE_SUFFIX for version in ("1", "2", "3", "1.connection-isolation1")
        }:
            raise ValueError("Unknown pin producer version or missing profile approval scope")
        add("profile_pin", pin.result, pin.summary, (("pin", pin.pin_number),), pin.evidence)
    unsupported = (
        UnsupportedScope(
            object_kind="component",
            object_id=component.refdes,
            scope="Complete pin function and topology outside base profile catalog",
            reason="Pin/DC relationship coverage alone does not establish complete functionality",
        ),
    )
    return CandidateSnapshot(
        catalog=PROFILE_CATALOG,
        candidates=candidates,
        outcomes=tuple(outcomes),
        unsupported=unsupported,
    )


def evaluate_profile_candidates(component, profile, design):
    candidates = enumerate_profile_candidates(component, profile)
    report = validate_component_against_profile(
        component, profile, design, include_topology=False, include_candidate_instances=True
    )
    return bind_profile_report(component, profile, candidates, report)
