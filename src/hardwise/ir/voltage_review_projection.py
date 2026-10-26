"""Only an applicable recorded selection enters executable voltage facts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from hardwise.ir.voltage import VoltageFactsDocument
from hardwise.ir.voltage_review import VoltageReviewDocument, content_hash


class VoltageReviewScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    net: str
    mode: str
    status: Literal["unconfirmed", "conflict", "confirmed", "unknown", "needs_review"]
    candidate_ids: tuple[str, ...]
    selected_candidate_id: str | None = None
    confirmation_id: str | None = None
    scope_sha256: str


def project_voltage_review(
    review: VoltageReviewDocument,
) -> tuple[VoltageFactsDocument, tuple[VoltageReviewScope, ...]]:
    """Candidates in other modes remain visible but cannot run in active-mode checks."""
    facts, scopes = [], []
    groups = sorted({(c.fact.net, c.fact.mode) for c in review.candidates})
    # Keep declarations visible after every candidate in their old scope was removed.
    groups = sorted(set(groups) | {(d.net, d.mode) for d in review.confirmations})
    for net, mode in groups:
        candidates = [c for c in review.candidates if (c.fact.net, c.fact.mode) == (net, mode)]
        versions = {
            content_hash(
                c.fact.model_dump(mode="json", exclude={"source", "confirmed", "confirmed_by"})
            )
            for c in candidates
        }
        status = "conflict" if len(versions) > 1 else "unconfirmed"
        declarations = [d for d in review.confirmations if (d.net, d.mode) == (net, mode)]
        latest = declarations[-1] if declarations else None
        selected = None
        scope_hash = review.scope_hash(net, mode)
        if latest:
            invalidated = any(
                latest.id in edit.invalidated_confirmation_ids for edit in review.edits
            )
            if latest.scope_sha256 != scope_hash or invalidated:
                status = "needs_review"
            elif latest.action == "unknown":
                status = "unknown"
            else:
                selected = next(
                    (
                        c
                        for c in candidates
                        if c.id == latest.candidate_id
                        and c.content_hash() == latest.candidate_sha256
                    ),
                    None,
                )
                if selected is None or (selected.origin == "net_name" and latest.origin != "human"):
                    status = "needs_review"
                    selected = None
                else:
                    status = "confirmed"
                    facts.append(
                        selected.fact.model_copy(
                            update={"confirmed": True, "confirmed_by": latest.reviewer}
                        )
                    )
        # Preserve an unconfirmed legacy singleton for exact v1 readback compatibility.
        elif len(candidates) == 1 and candidates[0].origin == "legacy_v1":
            facts.append(candidates[0].fact)
        scopes.append(
            VoltageReviewScope(
                net=net,
                mode=mode,
                status=status,
                candidate_ids=tuple(c.id for c in candidates),
                selected_candidate_id=selected.id if selected else None,
                confirmation_id=latest.id if latest else None,
                scope_sha256=scope_hash,
            )
        )
    return VoltageFactsDocument(active_mode=review.active_mode, facts=facts), tuple(scopes)
