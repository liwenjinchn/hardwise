"""Pure all-or-nothing batch confirmation; persistence/activation owns the transaction."""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from hardwise.ir.voltage_review import VoltageConfirmation, VoltageReviewDocument, content_hash


class VoltageReviewConflict(ValueError):
    """Reload the current revision before applying any part of a stale batch."""


class VoltageSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    net: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    action: Literal["confirm", "unknown"]
    candidate_id: str | None = None
    expected_scope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def review_revision(review: VoltageReviewDocument) -> str:
    return content_hash(review.model_dump(mode="json"))


def apply_voltage_selections(
    review: VoltageReviewDocument,
    selections: tuple[VoltageSelection, ...],
    *,
    expected_revision: str,
    reviewer: str,
    reason: str,
    recorded_at: datetime,
    known_nets: set[str],
) -> VoltageReviewDocument:
    """Validate the whole batch before returning a new document, never mutate input.

    Network authentication, current project/run, journal transaction and source
    activation are separate caller obligations; this function does not provide them.
    """
    if expected_revision != review_revision(review):
        raise VoltageReviewConflict("voltage review revision changed")
    if not selections:
        raise ValueError("select at least one network and mode")
    scopes = [(s.net, s.mode) for s in selections]
    if len(scopes) != len(set(scopes)):
        raise ValueError("duplicate network and mode in batch")
    candidates = {c.id: c for c in review.candidates}
    declarations = []
    for selection in selections:
        if selection.net not in known_nets:
            raise ValueError("selection references an unknown network")
        if selection.expected_scope_sha256 != review.scope_hash(selection.net, selection.mode):
            raise VoltageReviewConflict("voltage candidate scope changed")
        candidate = candidates.get(selection.candidate_id)
        if selection.action == "confirm":
            if candidate is None or (candidate.fact.net, candidate.fact.mode) != (
                selection.net,
                selection.mode,
            ):
                raise ValueError("selected candidate does not match network and mode")
            if candidate.fact.reference_net not in known_nets:
                raise ValueError("selected candidate references an unknown reference network")
        elif selection.candidate_id is not None:
            raise ValueError("unknown action cannot select a candidate")
        declarations.append(
            VoltageConfirmation(
                id=str(uuid4()),
                net=selection.net,
                mode=selection.mode,
                action=selection.action,
                candidate_id=candidate.id if candidate and selection.action == "confirm" else None,
                candidate_sha256=candidate.content_hash()
                if candidate and selection.action == "confirm"
                else None,
                scope_sha256=selection.expected_scope_sha256,
                reviewer=reviewer,
                reason=reason,
                recorded_at=recorded_at,
            )
        )
    return VoltageReviewDocument(
        active_mode=review.active_mode,
        candidates=review.candidates,
        confirmations=(*review.confirmations, *declarations),
        edits=review.edits,
    )
