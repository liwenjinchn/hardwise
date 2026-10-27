"""Candidate denominators survive missing results and reject false completion."""

import pytest
from pydantic import ValidationError

from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
    UnsupportedScope,
)


def candidate(**changes):
    return Candidate(
        **(
            dict(
                catalog_version="catalog1",
                rule_id="voltage",
                rule_version="1",
                object_kind="pin",
                object_id="U1",
                instance=(("pin", "1"),),
                applicability="applicable",
                reason="Profile declares supply pin",
            )
            | changes
        )
    )


def snapshot(candidates, outcomes=(), unsupported=()):
    return CandidateSnapshot(
        catalog=RuleCatalog(
            version="catalog1",
            rules=(
                RuleDefinition(rule_id="voltage", version="1", object_kind="pin", scope="DC only"),
            ),
        ),
        candidates=tuple(candidates),
        outcomes=tuple(outcomes),
        unsupported=tuple(unsupported),
    )


def outcome(c, result):
    return CandidateOutcome(candidate_id=c.candidate_id, result=result, reason="Synthetic evidence")


def test_missing_outcome_remains_in_denominator_and_unknown():
    c = candidate()
    for results, completed, unexecuted in [
        ((), 0, 1),
        ((outcome(c, "UNKNOWN"),), 0, 0),
        ((outcome(c, "PASS"),), 1, 0),
        ((outcome(c, "FAIL"),), 1, 0),
    ]:
        counts = snapshot([c], results).counts()
        assert counts["candidate_count"] == 1
        assert counts["completed_count"] == completed
        assert counts["unknown_count"] == 1 - completed
        assert counts["unexecuted_count"] == unexecuted


def test_applicability_unknown_and_explicit_exclusion_are_distinct():
    unknown = candidate(applicability="unknown", reason="Missing device variant")
    excluded = candidate(
        object_id="U2", applicability="not_applicable", reason="Pin is documented NC"
    )
    counts = snapshot([unknown, excluded]).counts()
    assert counts["unknown_count"] == counts["not_applicable_count"] == 1
    assert counts["applicability_unknown_count"] == counts["unexecuted_count"] == 1
    assert counts["completed_count"] == 0


@pytest.mark.parametrize(
    "applicability,result",
    [
        ("unknown", "PASS"),
        ("unknown", "FAIL"),
        ("unknown", "NOT_APPLICABLE"),
        ("not_applicable", "PASS"),
        ("not_applicable", "UNKNOWN"),
        ("applicable", "NOT_APPLICABLE"),
    ],
)
def test_conflicting_outcome_cannot_inflate_completion(applicability, result):
    c = candidate(applicability=applicability)
    with pytest.raises(ValidationError, match="contradicts"):
        snapshot([c], [outcome(c, result)])


def test_duplicate_or_orphan_outcomes_cannot_inflate_counts():
    c = candidate()
    for candidates, results, error in [
        ([c, c], [], "Duplicate candidate"),
        ([c], [outcome(c, "PASS")] * 2, "Duplicate outcome"),
        ([], [outcome(c, "PASS")], "Orphan outcome"),
    ]:
        with pytest.raises(ValidationError, match=error):
            snapshot(candidates, results)


def test_identity_uses_named_instance_not_display_reason_or_result():
    c = candidate(instance=(("target", "1"), ("supply", "2")))
    reordered = candidate(instance=(("supply", "2"), ("target", "1")), reason="Another description")
    assert c.candidate_id == reordered.candidate_id
    assert c.candidate_id != candidate(instance=(("target", "1"), ("supply", "3"))).candidate_id
    assert candidate(object_id="A/U1").candidate_id != candidate(object_id="B/U1").candidate_id


@pytest.mark.parametrize(
    "changes",
    [
        {"catalog_version": "other"},
        {"rule_version": "2"},
        {"rule_id": "foreign"},
        {"object_kind": "net"},
    ],
)
def test_catalog_mismatch_is_not_silently_counted(changes):
    with pytest.raises(ValidationError, match="catalog definition"):
        snapshot([candidate(**changes)])


def test_empty_and_unsupported_do_not_fabricate_candidates():
    unsupported = UnsupportedScope(
        object_kind="component", object_id="U9", scope="function", reason="No supported topology"
    )
    counts = snapshot([], unsupported=[unsupported]).counts()
    assert counts["candidate_count"] == counts["completed_count"] == 0
    assert counts["unsupported_scope_count"] == 1
    with pytest.raises(ValidationError, match="Duplicate unsupported"):
        snapshot([], unsupported=[unsupported, unsupported])


def test_snapshot_roundtrip_preserves_identity_and_counts():
    c = candidate()
    original = snapshot([c], [outcome(c, "UNKNOWN")])
    # Computed IDs are derived, not accepted as caller-controlled input.
    restored = CandidateSnapshot.model_validate_json(original.model_dump_json())
    assert restored == original and restored.counts() == original.counts()


def test_blank_reason_and_duplicate_roles_rejected():
    for changes in [{"reason": " "}, {"instance": (("pin", "1"), ("pin", "2"))}]:
        with pytest.raises(ValidationError):
            candidate(**changes)
