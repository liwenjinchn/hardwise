"""Pre-enumerate the connector family's declared endpoint checks only."""

from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
    UnsupportedScope,
)
from hardwise.validation.connector import validate_connector_instances
from hardwise.validation.identity_scope import (
    identity_conflict_report,
    profile_identity_conflict_report,
    scope_topology_identities,
)
from hardwise.validation.profile_approval import PROFILE_RULE_SUFFIX, approval_reason, scope_result

ENDPOINT_RULES = {
    "power_input": "connector_power_voltage",
    "ground": "connector_ground_connectivity",
    "gpio": "connector_signal_connectivity",
}
CONNECTOR_CATALOG = RuleCatalog(
    version="hardwise.connector_candidates.v1",
    rules=(
        RuleDefinition(
            rule_id="connector_endpoint_inventory",
            version="1",
            object_kind="component",
            scope="Declared supported connector endpoints only; not export completeness",
        ),
        *(
            RuleDefinition(
                rule_id=rule,
                version="1",
                object_kind="pin",
                scope="Declared connector endpoint check; not complete connector functionality",
            )
            for rule in ENDPOINT_RULES.values()
        ),
    ),
)


def _conflict(component, profile):
    return identity_conflict_report(component) or profile_identity_conflict_report(
        component, profile
    )


def _blocked(component, profile, design):
    conflict = _conflict(component, profile)
    if conflict:
        return conflict.component_checks[0].summary
    reason = approval_reason(component, profile)
    if reason:
        return reason
    blocked = sorted(c.refdes for c in design.components.values() if identity_conflict_report(c))
    return (
        "Topology paused for unresolved project identities: " + ", ".join(blocked)
        if blocked
        else None
    )


def _candidate(component, rule, instance=(), reason=None):
    return Candidate(
        catalog_version=CONNECTOR_CATALOG.version,
        rule_id=rule,
        rule_version="1",
        object_kind="component" if rule == "connector_endpoint_inventory" else "pin",
        object_id=component.refdes,
        instance=instance,
        applicability="unknown" if reason else "applicable",
        reason=reason or "Declared connector endpoint scope",
    )


def enumerate_connector_candidates(component, profile, design):
    if str(profile.recommended.get("topology_family", "")).lower() != "connector":
        raise ValueError("Connector catalog requires an explicit connector profile")
    if len({p.number for p in profile.pins}) != len(profile.pins):
        raise ValueError("Duplicate connector pin identity")
    blocked = _blocked(component, profile, design)
    candidates = (
        _candidate(component, "connector_endpoint_inventory"),
        *(
            _candidate(component, ENDPOINT_RULES[p.category], (("pin", p.number),), blocked)
            for p in profile.pins
            if p.category in ENDPOINT_RULES
        ),
    )
    CandidateSnapshot(catalog=CONNECTOR_CATALOG, candidates=candidates)
    return candidates


def bind_connector_results(component, profile, design, candidates, checks):
    expected = enumerate_connector_candidates(component, profile, design)
    if sorted(candidates, key=lambda c: c.candidate_id) != sorted(
        expected, key=lambda c: c.candidate_id
    ):
        raise ValueError("Candidates do not match current connector scope")
    endpoints = {p.number: p for p in profile.pins if p.category in ENDPOINT_RULES}
    inventory = _candidate(component, "connector_endpoint_inventory")
    outcomes = [
        CandidateOutcome(
            candidate_id=inventory.candidate_id,
            result="PASS" if endpoints else "UNKNOWN",
            reason="Profile declares supported endpoints; this does not prove export completeness."
            if endpoints
            else "No supported endpoints declared; connector function remains unknown.",
        )
    ]
    for check in checks:
        if check.refdes not in {None, component.refdes}:
            raise ValueError("Foreign connector result")
        instance = dict(check.instance)
        pin = endpoints.get(instance.get("pin"))
        if pin is None or check.instance != (("pin", pin.number),):
            raise ValueError("Unidentified connector endpoint")
        rule = ENDPOINT_RULES[pin.category]
        producer_check = (
            f"connector_signal_{pin.number}_connectivity" if pin.category == "gpio" else rule
        )
        if check.check != producer_check:
            raise ValueError("Connector result does not match endpoint role")
        bases = ("1",) if pin.category == "gpio" else ("2", "3")
        versions = {
            base + isolation + identity + PROFILE_RULE_SUFFIX
            for base in bases
            for isolation in ("", ".connection-isolation1")
            for identity in ("", ".bom-scope2")
        }
        if check.rule_version not in versions:
            raise ValueError("Unknown connector producer version")
        candidate = _candidate(component, rule, check.instance)
        outcomes.append(
            CandidateOutcome(
                candidate_id=candidate.candidate_id,
                result=check.result,
                reason=check.summary,
                evidence=tuple(check.evidence),
            )
        )
    return CandidateSnapshot(
        catalog=CONNECTOR_CATALOG,
        candidates=candidates,
        outcomes=tuple(outcomes),
        unsupported=(
            UnsupportedScope(
                object_kind="component",
                object_id=component.refdes,
                scope="Complete connector electrical/mechanical functionality",
                reason="Only declared power_input, ground and gpio endpoints are registered; other categories, current capacity, mating, transients and signal integrity are outside this catalog.",
            ),
        ),
    )


def evaluate_connector_candidates(component, profile, design):
    candidates = enumerate_connector_candidates(component, profile, design)
    checks = (
        []
        if _conflict(component, profile)
        else [
            scope_result(item, approval_reason(component, profile))
            for item in scope_topology_identities(
                validate_connector_instances(component, profile, design), design
            )
        ]
    )
    return bind_connector_results(component, profile, design, candidates, checks)
