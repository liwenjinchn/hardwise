"""Versioned source candidates and append-only voltage confirmation declarations."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument


def content_hash(value) -> str:
    """Canonical hash binds source and scope as well as numeric content."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


class VoltageCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    fact: VoltageFact
    origin: Literal["manual", "import", "net_name", "legacy_v1"]
    locator: str = Field(min_length=1)

    @model_validator(mode="after")
    def candidate_is_not_confirmation(self):
        if not self.id.strip() or not self.locator.strip():
            raise ValueError("candidate id and locator must be nonempty")
        if self.fact.confirmed or self.fact.confirmed_by:
            raise ValueError("a candidate cannot carry a confirmation")
        return self

    def content_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class VoltageCandidateChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    before: VoltageCandidate | None = None
    after: VoltageCandidate | None = None

    @model_validator(mode="after")
    def actual_change(self):
        if self.before == self.after:
            raise ValueError("candidate change must contain different before/after values")
        if self.before and self.after and self.before.id != self.after.id:
            raise ValueError("a candidate revision must retain its id")
        return self


class VoltageReviewEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    recorded_at: datetime
    previous_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_mode: str
    active_mode: str
    changes: tuple[VoltageCandidateChange, ...] = ()
    invalidated_confirmation_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def complete_edit(self):
        if (
            not self.reviewer.strip()
            or not self.reason.strip()
            or self.recorded_at.utcoffset() is None
        ):
            raise ValueError("candidate edits require reviewer, reason and timezone-aware time")
        if not self.changes and self.previous_mode == self.active_mode:
            raise ValueError("edit must change a candidate or active mode")
        return self


class VoltageConfirmation(BaseModel):
    """A recorded user assertion, not authenticated identity or engineering approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    net: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    action: Literal["confirm", "unknown"]
    origin: Literal["human", "legacy_v1"] = "human"
    candidate_id: str | None = None
    candidate_sha256: str | None = None
    scope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    recorded_at: datetime | None = None

    @model_validator(mode="after")
    def complete_declaration(self):
        if any(
            not value.strip()
            for value in (self.id, self.net, self.mode, self.reviewer, self.reason)
        ):
            raise ValueError("confirmation identity, scope, reviewer and reason must be nonempty")
        if self.origin == "human" and (
            self.recorded_at is None or self.recorded_at.utcoffset() is None
        ):
            raise ValueError("new human declarations require a timezone-aware timestamp")
        if self.action == "confirm":
            if not self.candidate_id or not self.candidate_sha256:
                raise ValueError("confirmation requires a candidate and content hash")
            if len(self.candidate_sha256) != 64 or any(
                c not in "0123456789abcdef" for c in self.candidate_sha256
            ):
                raise ValueError("invalid candidate hash")
        elif self.candidate_id is not None or self.candidate_sha256 is not None:
            raise ValueError("unknown declarations must not select a candidate")
        return self


class VoltageReviewDocument(BaseModel):
    """Input order is audit order; latest declaration per net/mode supersedes old ones."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["hardwise.voltage_review.v1"] = "hardwise.voltage_review.v1"
    active_mode: str = Field(default="dc", min_length=1)
    candidates: tuple[VoltageCandidate, ...] = ()
    confirmations: tuple[VoltageConfirmation, ...] = ()
    edits: tuple[VoltageReviewEdit, ...] = Field(default=(), exclude_if=lambda value: not value)

    @model_validator(mode="after")
    def unique_ids(self):
        if not self.active_mode.strip():
            raise ValueError("active_mode must be nonempty")
        for items in (self.candidates, self.confirmations, self.edits):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate candidate or confirmation id")
        return self

    def scope_hash(self, net: str, mode: str) -> str:
        return content_hash(
            sorted(
                (c.id, c.content_hash())
                for c in self.candidates
                if (c.fact.net, c.fact.mode) == (net, mode)
            )
        )

    def project(self) -> VoltageFactsDocument:
        from hardwise.ir.voltage_review_projection import project_voltage_review

        return project_voltage_review(self)[0]

    @classmethod
    def from_legacy(cls, document: VoltageFactsDocument) -> VoltageReviewDocument:
        """Preserve prior explicit v1 assertions without inventing new human approval."""
        candidates = tuple(
            VoltageCandidate(
                id=f"legacy-{index}",
                fact=fact.model_copy(update={"confirmed": False, "confirmed_by": ""}),
                origin="legacy_v1",
                locator=f"facts[{index}]",
            )
            for index, fact in enumerate(document.facts)
        )
        review = cls(active_mode=document.active_mode, candidates=candidates)
        confirmations = tuple(
            VoltageConfirmation(
                id=f"legacy-confirmation-{index}",
                net=fact.net,
                mode=fact.mode,
                action="confirm",
                origin="legacy_v1",
                candidate_id=candidates[index].id,
                candidate_sha256=candidates[index].content_hash(),
                scope_sha256=review.scope_hash(fact.net, fact.mode),
                reviewer=fact.confirmed_by,
                reason="Retained explicit v1 confirmation; no new review or timestamp asserted.",
            )
            for index, fact in enumerate(document.facts)
            if fact.confirmed
        )
        return cls(
            active_mode=document.active_mode, candidates=candidates, confirmations=confirmations
        )
