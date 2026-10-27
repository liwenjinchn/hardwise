"""Pre-enumerate nine bounded family catalogs, then reconcile scoped execution."""

from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    UnsupportedScope,
)
from hardwise.validation.component import _validate_component_topology
from hardwise.validation.dcdc import validate_buck_topology_complete
from hardwise.validation.identity_scope import (
    identity_conflict_report,
    profile_identity_conflict_report,
    scope_topology_identities,
)
from hardwise.validation.profile_approval import PROFILE_RULE_SUFFIX, approval_reason, scope_result
from hardwise.validation.topology_candidate_catalog import TOPOLOGY_CATALOG, selected_rules
from hardwise.validation.types import ValidationReport


def _conflict(component, profile):
    return identity_conflict_report(component) or profile_identity_conflict_report(
        component, profile
    )


def _blocked(component, profile, design):
    conflict = _conflict(component, profile)
    if conflict:
        return conflict.component_checks[0].summary
    approval = approval_reason(component, profile)
    if approval:
        return approval
    identities = sorted(c.refdes for c in design.components.values() if identity_conflict_report(c))
    return (
        "Unresolved project identities pause topology: " + ", ".join(identities)
        if identities
        else None
    )


def _candidate(component, family, check, applicability="applicable", reason=None):
    return Candidate(
        catalog_version=TOPOLOGY_CATALOG.version,
        rule_id="topology." + check,
        rule_version="1",
        object_kind="component",
        object_id=component.refdes,
        instance=(("family", family),),
        applicability=applicability,
        reason=reason or "Declared bounded family rule scope",
    )


def enumerate_topology_candidates(component, profile, design):
    family, rules = selected_rules(profile)
    blocked = _blocked(component, profile, design)
    candidates = []
    for check in rules:
        state, reason = ("unknown", blocked) if blocked else ("applicable", None)
        if not blocked and check == "led_current_limit":
            if profile.recommended.get("requires_current_limit") is False and profile.evidence.get(
                "recommended.requires_current_limit"
            ):
                # This declared exemption returns before any neighbor traversal.
                ambiguous = (
                    set(design.connectivity.ambiguous_net_names) if design.connectivity else set()
                )
                if any(p.connection_ambiguity or p.net in ambiguous for p in component.pins):
                    state, reason = (
                        "unknown",
                        "Ambiguous diode endpoints pause the family including the exemption.",
                    )
                else:
                    state, reason = (
                        "not_applicable",
                        "Approved profile explicitly exempts current limiting.",
                    )
            else:
                state, reason = (
                    "unknown",
                    "LED current/driver/series-path applicability is not modeled.",
                )
        if (
            not blocked
            and family == "bjt"
            and check.endswith("_rating")
            and profile.recommended.get("polarity") != "npn"
        ):
            state, reason = (
                "unknown",
                "Terminal model requires an explicitly declared NPN polarity.",
            )
        candidates.append(_candidate(component, family, check, state, reason))
    CandidateSnapshot(catalog=TOPOLOGY_CATALOG, candidates=tuple(candidates))
    return tuple(candidates)


def execute_topology_report(component, profile, design):
    family, _ = selected_rules(profile)
    checks = []
    if not _conflict(component, profile):
        checks = (
            validate_buck_topology_complete(component, profile, design)
            if family == "buck"
            else _validate_component_topology(component, profile, design)
        )
        checks = [
            scope_result(item, approval_reason(component, profile))
            for item in scope_topology_identities(checks, design)
        ]
    return ValidationReport(
        refdes=component.refdes,
        component_value=component.value,
        part_number=component.part_number,
        profile_part_number=profile.part_number,
        component_checks=checks,
    )


def bind_topology_report(component, profile, design, candidates, report):
    family, rules = selected_rules(profile)
    if (
        report.refdes != component.refdes
        or report.profile_part_number != profile.part_number
        or report.pin_results
    ):
        raise ValueError("Foreign topology report or unexpected pin results")
    if sorted(candidates, key=lambda c: c.candidate_id) != sorted(
        enumerate_topology_candidates(component, profile, design), key=lambda c: c.candidate_id
    ):
        raise ValueError("Candidates do not match current topology scope")
    outcomes = []
    for check in report.component_checks:
        if check.check not in rules:
            raise ValueError("Unregistered topology result")
        # Some rules report a registry-verified neighbor (or comma-joined neighbors).
        if check.refdes is not None and any(
            ref not in design.components for ref in check.refdes.split(", ")
        ):
            raise ValueError("Unregistered topology evidence refdes")
        versions = {
            v + isolation + identity + PROFILE_RULE_SUFFIX
            for v in rules[check.check]
            for isolation in ("", ".connection-isolation1")
            for identity in ("", ".bom-scope2")
        }
        if check.rule_version not in versions:
            raise ValueError("Unknown topology producer version")
        candidate = _candidate(component, family, check.check)
        outcomes.append(
            CandidateOutcome(
                candidate_id=candidate.candidate_id,
                result=check.result,
                reason=check.summary,
                evidence=tuple(check.evidence),
            )
        )
    return CandidateSnapshot(
        catalog=TOPOLOGY_CATALOG,
        candidates=candidates,
        outcomes=tuple(outcomes),
        unsupported=(
            UnsupportedScope(
                object_kind="component",
                object_id=component.refdes,
                scope="Complete device and circuit function outside registered family checks",
                reason="These atomic/group assessments do not cover all pins, dynamic behavior, SI/PI, thermal or full electrical suitability.",
            ),
        ),
    )


def evaluate_topology_candidates(component, profile, design):
    candidates = enumerate_topology_candidates(component, profile, design)
    return bind_topology_report(
        component, profile, design, candidates, execute_topology_report(component, profile, design)
    )
