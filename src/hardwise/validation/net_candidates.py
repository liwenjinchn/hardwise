"""Network-only catalog with enumeration independent of validator outputs.

Not the full project denominator: component/pin/topology catalogs are pending.
"""

import hashlib
import json
import re

from hardwise.ir.connectivity_queries import observed_net_names
from hardwise.ir.types import Design
from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
)
from hardwise.validation.net_naming import (
    CHECK_DIFF_PAIR,
    CHECK_NAME_CHARSET,
    CHECK_NAME_LENGTH,
    DEFAULT_NAMING_POLICY,
    NamingPolicy,
    validate_net_naming,
)
from hardwise.validation.nets import (
    CHECK_MISSING_GROUND,
    CHECK_SINGLE_ENDPOINT,
    NetValidation,
    validate_design_nets,
)

NET_CATALOG = RuleCatalog(
    version="hardwise.net_candidates.v1",
    rules=tuple(
        RuleDefinition(rule_id=rule, version="1", object_kind=kind, scope=scope)
        for rule, kind, scope in [
            ("net_connection_ambiguity", "net", "Imported declaration consistency only"),
            (CHECK_SINGLE_ENDPOINT, "net", "Imported endpoint cardinality only"),
            (CHECK_MISSING_GROUND, "project", "Recognized ground name presence only"),
            (CHECK_NAME_CHARSET, "net", "Configured name character policy"),
            (CHECK_NAME_LENGTH, "net", "Configured name length policy"),
            (CHECK_DIFF_PAIR, "net", "Configured differential name mate only"),
        ]
    ),
)
NAMING_RULES = {CHECK_NAME_CHARSET, CHECK_NAME_LENGTH, CHECK_DIFF_PAIR}


def _policy_key(policy):
    payload = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return (("policy_sha256", hashlib.sha256(payload.encode()).hexdigest()),)


def _candidate(rule, name, *, applicability="applicable", reason, instance=()):
    return Candidate(
        catalog_version=NET_CATALOG.version,
        rule_id=rule,
        rule_version="1",
        object_kind="project" if rule == CHECK_MISSING_GROUND else "net",
        object_id=name,
        instance=instance,
        applicability=applicability,
        reason=reason,
    )


def enumerate_net_candidates(
    design: Design, policy: NamingPolicy | None = None
) -> tuple[Candidate, ...]:
    """Read input facts/policy only; never execute or inspect check results."""
    policy = policy or DEFAULT_NAMING_POLICY
    if len(set(policy.diff_pair_suffixes)) != len(policy.diff_pair_suffixes):
        raise ValueError("Duplicate differential suffix policy")
    names = observed_net_names(design)
    candidates = [
        _candidate(
            CHECK_MISSING_GROUND,
            "loaded-project",
            reason="Inspect observed names for ground naming",
        )
    ]
    policy_key = _policy_key(policy)
    for name in sorted(names):
        for rule in (
            "net_connection_ambiguity",
            CHECK_SINGLE_ENDPOINT,
            CHECK_NAME_CHARSET,
            CHECK_NAME_LENGTH,
        ):
            candidates.append(
                _candidate(
                    rule,
                    name,
                    reason="Observed input net is in this rule's scope",
                    instance=policy_key if rule in NAMING_RULES else (),
                )
            )
        for positive, negative in policy.diff_pair_suffixes:
            pattern = rf"^.+_(?:{re.escape(positive)}|{re.escape(negative)})\d*$"
            matches = re.match(pattern, name) is not None
            candidates.append(
                _candidate(
                    CHECK_DIFF_PAIR,
                    name,
                    instance=(
                        *policy_key,
                        ("positive_suffix", positive),
                        ("negative_suffix", negative),
                    ),
                    applicability="applicable" if matches else "not_applicable",
                    reason=(
                        "Name matches configured suffix pair"
                        if matches
                        else "Name does not match this configured suffix pair"
                    ),
                )
            )
    return tuple(candidates)


def bind_net_outcomes(
    candidates: tuple[Candidate, ...],
    results: list[NetValidation],
    policy: NamingPolicy | None = None,
) -> CandidateSnapshot:
    """Strictly bind atomic results, leaving absent results unexecuted."""
    policy = policy or DEFAULT_NAMING_POLICY
    key = _policy_key(policy)
    outcomes = []
    for result in results:
        instance = (*key, *result.instance) if result.check in NAMING_RULES else result.instance
        identity = _candidate(
            result.check,
            "loaded-project" if result.check == CHECK_MISSING_GROUND else result.net_name,
            instance=instance,
            reason="Binding only",
        )
        outcomes.append(
            CandidateOutcome(
                candidate_id=identity.candidate_id,
                result=result.result,
                reason=result.summary,
                evidence=tuple(result.evidence),
            )
        )
    return CandidateSnapshot(catalog=NET_CATALOG, candidates=candidates, outcomes=tuple(outcomes))


def evaluate_net_candidates(
    design: Design, *, policy: NamingPolicy | None = None, source_label: str | None = None
) -> CandidateSnapshot:
    candidates = enumerate_net_candidates(design, policy)
    results = [
        *validate_design_nets(design, source_label=source_label, include_complete=True),
        *validate_net_naming(
            design, policy=policy, source_label=source_label, include_complete=True
        ),
    ]
    return bind_net_outcomes(candidates, results, policy)
