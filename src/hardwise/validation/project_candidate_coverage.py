"""Compose registered scopes; enumerate the entire project before executing any scope."""

from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
    UnsupportedScope,
)
from hardwise.validation.connector_candidates import (
    CONNECTOR_CATALOG,
    enumerate_connector_candidates,
    evaluate_connector_candidates,
)
from hardwise.validation.identity_scope import identity_conflict_report
from hardwise.validation.net_candidates import (
    NET_CATALOG,
    enumerate_net_candidates,
    evaluate_net_candidates,
)
from hardwise.validation.passive_candidates import (
    PASSIVE_CATALOG,
    enumerate_passive_candidates,
    evaluate_passive_candidates,
)
from hardwise.validation.profile_candidates_coverage import (
    PROFILE_CATALOG,
    enumerate_profile_candidates,
    evaluate_profile_candidates,
)
from hardwise.validation.topology_candidate_catalog import TOPOLOGY_CATALOG, FAMILIES
from hardwise.validation.topology_candidates import (
    enumerate_topology_candidates,
    evaluate_topology_candidates,
)

UNMODELED_CATALOG = RuleCatalog(
    version="hardwise.unmodeled_candidates.v1",
    rules=(
        RuleDefinition(
            rule_id="unmodeled_component_identity",
            version="1",
            object_kind="component",
            scope="Recorded identity conflicts only; no device-function check is invented",
        ),
    ),
)
CATALOGS = {
    c.version: c
    for c in (
        NET_CATALOG,
        PASSIVE_CATALOG,
        PROFILE_CATALOG,
        CONNECTOR_CATALOG,
        TOPOLOGY_CATALOG,
        UNMODELED_CATALOG,
    )
}
PROJECT_CATALOG = RuleCatalog(
    version="hardwise.project_candidates.v1",
    rules=tuple(rule for c in CATALOGS.values() for rule in c.rules),
)


def merge_candidate_snapshots(snapshots):
    candidates, outcomes, unsupported = [], [], []
    for snapshot in snapshots:
        if CATALOGS.get(snapshot.catalog.version) != snapshot.catalog:
            raise ValueError("Unregistered project subcatalog")
        identities = {}
        for c in snapshot.candidates:
            if any(key == "source_catalog" for key, _ in c.instance):
                raise ValueError("Reserved source catalog role")
            rewritten = c.model_copy(
                update={
                    "catalog_version": PROJECT_CATALOG.version,
                    "instance": (*c.instance, ("source_catalog", c.catalog_version)),
                }
            )
            identities[c.candidate_id] = rewritten.candidate_id
            candidates.append(rewritten)
        outcomes.extend(
            o.model_copy(update={"candidate_id": identities[o.candidate_id]})
            for o in snapshot.outcomes
        )
        unsupported.extend(snapshot.unsupported)
    return CandidateSnapshot(
        catalog=PROJECT_CATALOG,
        candidates=tuple(candidates),
        outcomes=tuple(outcomes),
        unsupported=tuple(unsupported),
    )


def _unmodeled(component, *, executed):
    conflict = identity_conflict_report(component)
    candidate = Candidate(
        catalog_version=UNMODELED_CATALOG.version,
        rule_id="unmodeled_component_identity",
        rule_version="1",
        object_kind="component",
        object_id=component.refdes,
        applicability="applicable",
        reason="Inspect recorded identity conflicts only, without inferring device function",
    )
    outcomes = (
        (
            CandidateOutcome(
                candidate_id=candidate.candidate_id,
                result="UNKNOWN" if conflict else "PASS",
                reason=conflict.component_checks[0].summary
                if conflict
                else "No recorded identity conflict; device function remains unsupported.",
            ),
        )
        if executed
        else ()
    )
    return CandidateSnapshot(
        catalog=UNMODELED_CATALOG,
        candidates=(candidate,),
        outcomes=outcomes,
        unsupported=(
            UnsupportedScope(
                object_kind="component",
                object_id=component.refdes,
                scope="Unmodeled component electrical function",
                reason="No matched profile or recognized passive family; no electrical checks invented.",
            ),
        ),
    )


def _unsupported_topology(component, profile):
    return UnsupportedScope(
        object_kind="component",
        object_id=component.refdes,
        scope="Unregistered profile topology family",
        reason="No registered topology family: "
        + str(profile.recommended.get("topology_family", "(absent)")),
    )


def enumerate_project_candidates(design, profiles, passive_families, *, naming_policy=None):
    if set(profiles) - set(design.components) or set(passive_families) - set(design.components):
        raise ValueError("Candidate scope contains a foreign component")
    snapshots = [
        CandidateSnapshot(
            catalog=NET_CATALOG, candidates=enumerate_net_candidates(design, naming_policy)
        )
    ]
    for ref, c in sorted(design.components.items()):
        profile = profiles.get(ref)
        if profile is not None:
            snapshots.append(
                CandidateSnapshot(
                    catalog=PROFILE_CATALOG, candidates=enumerate_profile_candidates(c, profile)
                )
            )
            family = str(profile.recommended.get("topology_family", "")).lower()
            if family == "connector":
                snapshots.append(
                    CandidateSnapshot(
                        catalog=CONNECTOR_CATALOG,
                        candidates=enumerate_connector_candidates(c, profile, design),
                    )
                )
            elif family in FAMILIES:
                snapshots.append(
                    CandidateSnapshot(
                        catalog=TOPOLOGY_CATALOG,
                        candidates=enumerate_topology_candidates(c, profile, design),
                    )
                )
            else:
                snapshots.append(
                    CandidateSnapshot(
                        catalog=PROFILE_CATALOG,
                        candidates=(),
                        unsupported=(_unsupported_topology(c, profile),),
                    )
                )
        elif ref in passive_families:
            snapshots.append(
                CandidateSnapshot(
                    catalog=PASSIVE_CATALOG,
                    candidates=enumerate_passive_candidates(c, passive_families[ref]),
                )
            )
        else:
            snapshots.append(_unmodeled(c, executed=False))
    return merge_candidate_snapshots(snapshots)


def evaluate_project_candidates(
    design, profiles, passive_families, bom_rows, *, naming_policy=None, source_label=None
):
    # This call completes before any validator executes. Missing results stay in this plan.
    plan = enumerate_project_candidates(
        design, profiles, passive_families, naming_policy=naming_policy
    )
    snapshots = [evaluate_net_candidates(design, policy=naming_policy, source_label=source_label)]
    for ref, c in sorted(design.components.items()):
        profile = profiles.get(ref)
        if profile is not None:
            snapshots.append(evaluate_profile_candidates(c, profile, design))
            family = str(profile.recommended.get("topology_family", "")).lower()
            if family == "connector":
                snapshots.append(evaluate_connector_candidates(c, profile, design))
            elif family in FAMILIES:
                snapshots.append(evaluate_topology_candidates(c, profile, design))
            else:
                snapshots.append(
                    CandidateSnapshot(
                        catalog=PROFILE_CATALOG,
                        candidates=(),
                        unsupported=(_unsupported_topology(c, profile),),
                    )
                )
        elif ref in passive_families:
            snapshots.append(
                evaluate_passive_candidates(c, bom_rows.get(ref), design, passive_families[ref])
            )
        else:
            snapshots.append(_unmodeled(c, executed=True))
    result = merge_candidate_snapshots(snapshots)
    if {c.candidate_id: c for c in plan.candidates} != {
        c.candidate_id: c for c in result.candidates
    }:
        raise ValueError("Project candidate scope changed during execution")
    return result
