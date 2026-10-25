"""Multi-source model tests; no simulated declaration is actual engineering approval."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.ir.voltage_review import VoltageCandidate, VoltageReviewDocument
from hardwise.ir.voltage_review_actions import (
    VoltageReviewConflict,
    VoltageSelection,
    apply_voltage_selections,
    review_revision,
)
from hardwise.ir.voltage_review_projection import project_voltage_review


def candidate(
    id, voltage=12, *, net="P", reference="GND", mode="dc", origin="manual", typical=False
):
    return VoltageCandidate(
        id=id,
        fact=VoltageFact(
            net=net,
            reference_net=reference,
            mode=mode,
            source=f"Public synthetic source {id}",
            **({"typical": voltage} if typical else {"minimum": voltage, "maximum": voltage}),
        ),
        origin=origin,
        locator=f"Synthetic table {id}",
    )


def select(review, *choices, **updates):
    args = dict(
        expected_revision=review_revision(review),
        reviewer="SYNTHETIC TEST AUTHOR",
        reason="Algorithm fixture, not engineering approval",
        recorded_at=datetime.now(timezone.utc),
        known_nets={"P", "GND", "OTHER", "Q"},
    )
    args.update(updates)
    return apply_voltage_selections(
        review,
        tuple(
            VoltageSelection(
                net=net,
                mode=mode,
                action=action,
                candidate_id=id,
                expected_scope_sha256=review.scope_hash(net, mode),
            )
            for net, mode, action, id in choices
        ),
        **args,
    )


def scope(review, net="P", mode="dc"):
    return next(s for s in project_voltage_review(review)[1] if (s.net, s.mode) == (net, mode))


@pytest.mark.parametrize("change", ["value", "reference", "range", "mode"])
def test_unresolved_sources_never_project_a_confirmed_fact(change):
    a = candidate("a")
    kwargs = (
        {"voltage": 24}
        if change == "value"
        else {"reference": "OTHER"}
        if change == "reference"
        else {"typical": True}
        if change == "range"
        else {"mode": "sleep"}
    )
    b = candidate("b", **kwargs)
    review = VoltageReviewDocument(candidates=(a, b))
    assert review.project().facts == []
    assert scope(review).status == ("unconfirmed" if change == "mode" else "conflict")


def test_equal_sources_still_require_human_selection():
    review = VoltageReviewDocument(candidates=(candidate("a"), candidate("b")))
    assert scope(review).status == "unconfirmed" and not review.project().facts
    confirmed = select(review, ("P", "dc", "confirm", "b"))
    assert scope(confirmed).status == "confirmed"
    assert confirmed.project().facts[0].source == "Public synthetic source b"
    assert confirmed.candidates == review.candidates


@pytest.mark.parametrize("mutation", ["value", "source", "locator", "added", "removed", "renamed"])
def test_changed_candidate_or_candidate_set_invalidates_confirmation(mutation):
    review = select(
        VoltageReviewDocument(candidates=(candidate("a"), candidate("b", 24))),
        ("P", "dc", "confirm", "a"),
    )
    old = review.model_dump(mode="json")
    values = list(review.candidates)
    if mutation == "value":
        values[0] = candidate("a", 13)
    elif mutation == "source":
        values[0] = values[0].model_copy(
            update={"fact": values[0].fact.model_copy(update={"source": "Changed source"})}
        )
    elif mutation == "locator":
        values[0] = values[0].model_copy(update={"locator": "Changed page"})
    elif mutation == "added":
        values.append(candidate("c", 12))
    elif mutation == "removed":
        values = []
    else:
        values[0] = candidate("renamed")
    updated = VoltageReviewDocument(candidates=tuple(values), confirmations=review.confirmations)
    assert scope(updated).status == "needs_review" and not updated.project().facts
    assert review.model_dump(mode="json") == old
    assert updated.confirmations == review.confirmations


def test_candidate_order_does_not_invalidate_a_bound_set():
    review = select(
        VoltageReviewDocument(candidates=(candidate("a"), candidate("b", 24))),
        ("P", "dc", "confirm", "a"),
    )
    reordered = review.model_copy(update={"candidates": tuple(reversed(review.candidates))})
    assert scope(reordered).status == "confirmed"


def test_unknown_revokes_only_selected_scope_and_preserves_audit():
    review = VoltageReviewDocument(candidates=(candidate("a"), candidate("q", 5, net="Q")))
    both = select(review, ("P", "dc", "confirm", "a"), ("Q", "dc", "confirm", "q"))
    revoked = select(both, ("P", "dc", "unknown", None))
    assert scope(revoked).status == "unknown" and scope(revoked, "Q").status == "confirmed"
    assert [f.net for f in revoked.project().facts] == ["Q"]
    assert revoked.confirmations[:2] == both.confirmations and len(revoked.confirmations) == 3


def test_modes_keep_independent_selections():
    review = VoltageReviewDocument(candidates=(candidate("a"), candidate("sleep", 0, mode="sleep")))
    review = select(review, ("P", "dc", "confirm", "a"))
    assert scope(review, "P", "sleep").status == "unconfirmed"
    assert review.model_copy(update={"active_mode": "sleep"}).project().active_mode == "sleep"
    assert all(f.mode == "dc" for f in review.project().facts)


def test_typical_only_confirmation_never_invents_an_envelope():
    review = select(
        VoltageReviewDocument(candidates=(candidate("a", typical=True),)),
        ("P", "dc", "confirm", "a"),
    )
    fact = review.project().facts[0]
    assert fact.confirmed and fact.minimum is None and fact.maximum is None and fact.typical == 12


@pytest.mark.parametrize(
    "changes",
    [
        {"reviewer": " "},
        {"reason": " "},
        {"recorded_at": datetime(2026, 1, 1)},
        {"known_nets": {"P"}},
    ],
)
def test_bad_batch_leaves_input_and_history_unchanged(changes):
    review = VoltageReviewDocument(candidates=(candidate("a"),))
    before = review.model_dump_json()
    with pytest.raises(ValueError):
        select(review, ("P", "dc", "confirm", "a"), **changes)
    assert review.model_dump_json() == before


@pytest.mark.parametrize(
    "choices",
    [
        (("P", "dc", "confirm", "a"), ("Q", "dc", "confirm", "missing")),
        (("P", "dc", "confirm", "a"), ("P", "dc", "confirm", "a")),
        (("P", "dc", "unknown", "a"),),
        (),
    ],
)
def test_batch_rejects_all_items_if_any_selection_invalid(choices):
    review = VoltageReviewDocument(candidates=(candidate("a"),))
    with pytest.raises(ValueError):
        select(review, *choices)
    assert review.confirmations == ()


def test_stale_revision_rejects_before_any_confirmation():
    review = VoltageReviewDocument(candidates=(candidate("a"),))
    with pytest.raises(VoltageReviewConflict):
        select(review, ("P", "dc", "confirm", "a"), expected_revision="0" * 64)
    assert not review.confirmations


def test_legacy_roundtrip_preserves_values_and_assertions_without_new_approval():
    legacy = VoltageFactsDocument(
        facts=[
            candidate("a").fact.model_copy(
                update={"confirmed": True, "confirmed_by": "Original v1 author"}
            ),
            candidate("q", 5, net="Q", typical=True).fact,
        ]
    )
    review = VoltageReviewDocument.from_legacy(legacy)
    restored = VoltageReviewDocument.model_validate_json(review.model_dump_json())
    assert restored.project() == legacy
    assert restored.confirmations[0].origin == "legacy_v1"
    assert restored.confirmations[0].recorded_at is None
    assert scope(restored, "Q").status == "unconfirmed"


def test_candidate_cannot_smuggle_an_existing_confirmation():
    fact = candidate("a").fact.model_copy(update={"confirmed": True, "confirmed_by": "someone"})
    with pytest.raises(ValidationError):
        VoltageCandidate(id="a", fact=fact, origin="manual", locator="p1")


def test_duplicate_candidate_and_event_ids_rejected():
    with pytest.raises(ValidationError):
        VoltageReviewDocument(candidates=(candidate("a"), candidate("a", 24)))
    review = select(
        VoltageReviewDocument(candidates=(candidate("a"),)), ("P", "dc", "confirm", "a")
    )
    with pytest.raises(ValidationError):
        VoltageReviewDocument(candidates=review.candidates, confirmations=review.confirmations * 2)


def test_projection_drives_existing_stress_validator_without_trusting_conflicts():
    from tests.validation.test_transistor_voltage_facts import _case, _check

    design, profile = _case()
    review = VoltageReviewDocument(
        candidates=(
            candidate("gate-a", 10, net="GATE", reference="REF"),
            candidate("gate-b", 30, net="GATE", reference="REF"),
            candidate("source", 0, net="SOURCE", reference="REF"),
            candidate("drain", 10, net="DRAIN", reference="REF"),
        )
    )
    nets = {"GATE", "SOURCE", "DRAIN", "REF"}
    review = select(
        review,
        ("SOURCE", "dc", "confirm", "source"),
        ("DRAIN", "dc", "confirm", "drain"),
        known_nets=nets,
    )
    design.voltage_facts = review.project()
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"
    assert _check(design, profile, "mosfet_vds_rating").result == "PASS"
    resolved = select(review, ("GATE", "dc", "confirm", "gate-b"), known_nets=nets)
    design.voltage_facts = resolved.project()
    assert _check(design, profile, "mosfet_vgs_rating").result == "FAIL"
    assert _check(design, profile, "mosfet_vgs_rating", reviewed=False).result == "UNKNOWN"
    revoked = select(resolved, ("GATE", "dc", "unknown", None), known_nets=nets)
    design.voltage_facts = revoked.project()
    assert _check(design, profile, "mosfet_vgs_rating").result == "UNKNOWN"
    assert _check(design, profile, "mosfet_vds_rating").result == "PASS"


def test_net_name_candidate_is_not_automatically_confirmed():
    review = VoltageReviewDocument(candidates=(candidate("name", origin="net_name"),))
    assert review.project().facts == []
    confirmed = select(review, ("P", "dc", "confirm", "name"))
    assert confirmed.project().facts[0].confirmed
    assert confirmed.confirmations[0].origin == "human"


def test_stale_scope_rejects_entire_batch_even_with_current_document_revision():
    review = VoltageReviewDocument(candidates=(candidate("a"),))
    selection = VoltageSelection(
        net="P", mode="dc", action="confirm", candidate_id="a", expected_scope_sha256="0" * 64
    )
    with pytest.raises(VoltageReviewConflict):
        apply_voltage_selections(
            review,
            (selection,),
            expected_revision=review_revision(review),
            reviewer="Synthetic author",
            reason="Synthetic stale scope",
            recorded_at=datetime.now(timezone.utc),
            known_nets={"P", "GND"},
        )
    assert not review.confirmations
