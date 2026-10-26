"""Candidate editing never silently restores an older human selection."""

from datetime import datetime, timezone

import pytest

from hardwise.ir.voltage_review import VoltageReviewDocument
from hardwise.ir.voltage_review_actions import review_revision
from hardwise.ir.voltage_review_edits import edit_voltage_candidates
from tests.ir.test_voltage_review import candidate, select, scope


def edit(review, *, upserts=(), remove_ids=(), active_mode=None, **updates):
    args = dict(
        upserts=upserts,
        remove_ids=remove_ids,
        active_mode=active_mode,
        expected_revision=review_revision(review),
        reviewer="SYNTHETIC EDIT AUTHOR",
        reason="Public algorithm test",
        recorded_at=datetime.now(timezone.utc),
        known_nets={"P", "Q", "GND", "OTHER"},
    )
    args.update(updates)
    return edit_voltage_candidates(review, **args)


def test_reverting_a_candidate_does_not_resurrect_a_prior_confirmation():
    original = candidate("a")
    review = select(VoltageReviewDocument(candidates=(original,)), ("P", "dc", "confirm", "a"))
    changed = edit(review, upserts=(candidate("a", 24),))
    reverted = edit(changed, upserts=(original,))
    assert scope(reverted).status == "needs_review" and not reverted.project().facts
    assert reverted.confirmations == review.confirmations
    assert reverted.edits[0].changes[0].before == original
    assert reverted.edits[1].changes[0].after == original
    reconfirmed = select(reverted, ("P", "dc", "confirm", "a"))
    assert scope(reconfirmed).status == "confirmed"
    assert reconfirmed.edits == reverted.edits
    assert VoltageReviewDocument.model_validate_json(reconfirmed.model_dump_json()) == reconfirmed


def test_remove_and_readd_cannot_restore_old_confirmation():
    review = select(
        VoltageReviewDocument(candidates=(candidate("a"),)), ("P", "dc", "confirm", "a")
    )
    removed = edit(review, remove_ids=("a",))
    assert removed.candidates == ()
    restored = edit(removed, upserts=(candidate("a"),))
    assert scope(restored).status == "needs_review"
    assert removed.edits[0].changes[0].before == review.candidates[0]


def test_mode_switch_retains_other_mode_confirmations_without_fabricating_values():
    review = select(
        VoltageReviewDocument(candidates=(candidate("a"), candidate("sleep", 0, mode="sleep"))),
        ("P", "dc", "confirm", "a"),
    )
    changed = edit(review, active_mode="sleep")
    assert scope(changed).status == "confirmed"
    assert scope(changed, "P", "sleep").status == "unconfirmed"
    assert changed.project().active_mode == "sleep"
    assert changed.edits[0].changes == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"upserts": (candidate("a"),), "remove_ids": ("a",)},
        {"remove_ids": ("missing",)},
        {"upserts": (candidate("a"), candidate("a", 24))},
        {"upserts": (candidate("foreign", net="FOREIGN"),)},
        {"upserts": (candidate("pretend", origin="legacy_v1"),)},
        {"active_mode": " "},
        {"active_mode": "sleep", "reason": " "},
        {},
    ],
)
def test_invalid_candidate_batch_does_not_mutate_input(kwargs):
    review = VoltageReviewDocument(candidates=(candidate("a"),))
    before = review.model_dump_json()
    with pytest.raises(ValueError):
        edit(review, **kwargs)
    assert review.model_dump_json() == before
