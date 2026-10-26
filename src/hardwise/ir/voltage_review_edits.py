"""Revision and removal retain original candidate content and invalidate old approvals."""

from datetime import datetime
from uuid import uuid4

from hardwise.ir.voltage_review import (
    VoltageCandidate,
    VoltageCandidateChange,
    VoltageReviewDocument,
    VoltageReviewEdit,
)
from hardwise.ir.voltage_review_actions import review_revision, VoltageReviewConflict


def edit_voltage_candidates(
    review: VoltageReviewDocument,
    *,
    upserts: tuple[VoltageCandidate, ...],
    remove_ids: tuple[str, ...],
    active_mode: str | None,
    expected_revision: str,
    reviewer: str,
    reason: str,
    recorded_at: datetime,
    known_nets: set[str],
) -> VoltageReviewDocument:
    if expected_revision != review_revision(review):
        raise VoltageReviewConflict("voltage review revision changed")
    ids = [c.id for c in upserts]
    if (
        len(ids) != len(set(ids))
        or len(remove_ids) != len(set(remove_ids))
        or set(ids) & set(remove_ids)
    ):
        raise ValueError("candidate ids must be unique across upserts and removals")
    existing = {c.id: c for c in review.candidates}
    if any(id not in existing for id in remove_ids):
        raise ValueError("cannot remove an unknown candidate")
    mode = review.active_mode if active_mode is None else active_mode.strip()
    if not mode:
        raise ValueError("active mode must be nonempty")
    changes = []
    for candidate in upserts:
        if candidate.origin != "manual":
            raise ValueError("editor candidates must declare manual origin")
        if candidate.fact.net not in known_nets or candidate.fact.reference_net not in known_nets:
            raise ValueError("candidate references an unknown network")
        previous = existing.get(candidate.id)
        if previous != candidate:
            changes.append(VoltageCandidateChange(before=previous, after=candidate))
            existing[candidate.id] = candidate
    for id in remove_ids:
        changes.append(VoltageCandidateChange(before=existing.pop(id)))
    scopes = {
        (candidate.fact.net, candidate.fact.mode)
        for change in changes
        for candidate in (change.before, change.after)
        if candidate is not None
    }
    edit = VoltageReviewEdit(
        id=str(uuid4()),
        reviewer=reviewer,
        reason=reason,
        recorded_at=recorded_at,
        previous_revision=expected_revision,
        previous_mode=review.active_mode,
        active_mode=mode,
        changes=tuple(changes),
        invalidated_confirmation_ids=tuple(
            d.id for d in review.confirmations if (d.net, d.mode) in scopes
        ),
    )
    return VoltageReviewDocument(
        active_mode=mode,
        candidates=tuple(existing.values()),
        confirmations=review.confirmations,
        edits=(*review.edits, edit),
    )
