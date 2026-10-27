"""Reconcile pre-enumerated rule instances; never infer a denominator from results.

This contract is not yet wired to the project index. Each candidate is atomic:
producers with multiple checks must enumerate distinct, structured instances.
"""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hardwise.validation.assessment import CheckResult

ObjectKind = Literal["project", "component", "pin", "net", "relation"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuleDefinition(Contract):
    rule_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    object_kind: ObjectKind
    scope: str = Field(min_length=1)


class RuleCatalog(Contract):
    version: str = Field(min_length=1)
    rules: tuple[RuleDefinition, ...]

    @model_validator(mode="after")
    def unique_rules(self):
        if len({r.rule_id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate rule definition")
        return self


class Candidate(Contract):
    catalog_version: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    object_kind: ObjectKind
    object_id: str = Field(min_length=1)
    # Named roles distinguish endpoints/relations without relying on list position.
    instance: tuple[tuple[str, str], ...] = ()
    applicability: Literal["applicable", "unknown", "not_applicable"]
    reason: str = Field(min_length=1)
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def named_roles(self):
        if any(not k.strip() or not v.strip() for k, v in self.instance):
            raise ValueError("Instance roles and values must be nonempty")
        if len({k for k, _ in self.instance}) != len(self.instance):
            raise ValueError("Duplicate instance role")
        if not self.reason.strip():
            raise ValueError("Applicability requires an explicit reason")
        return self

    @property
    def candidate_id(self) -> str:
        identity = (
            self.catalog_version,
            self.rule_id,
            self.rule_version,
            self.object_kind,
            self.object_id,
            sorted(self.instance),
        )
        payload = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
        return "candidate-" + hashlib.sha256(payload.encode()).hexdigest()


class CandidateOutcome(Contract):
    candidate_id: str = Field(min_length=1)
    result: CheckResult
    reason: str = Field(min_length=1)
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def meaningful_reason(self):
        if not self.reason.strip():
            raise ValueError("Outcome requires an explicit reason")
        return self


class UnsupportedScope(Contract):
    object_kind: ObjectKind
    object_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CandidateSnapshot(Contract):
    schema_version: Literal["hardwise.candidate_coverage.v1"] = "hardwise.candidate_coverage.v1"
    catalog: RuleCatalog
    candidates: tuple[Candidate, ...]
    outcomes: tuple[CandidateOutcome, ...] = ()
    unsupported: tuple[UnsupportedScope, ...] = ()

    @model_validator(mode="after")
    def reconcile(self):
        definitions = {r.rule_id: r for r in self.catalog.rules}
        candidates = {}
        for c in self.candidates:
            definition = definitions.get(c.rule_id)
            if (
                c.catalog_version != self.catalog.version
                or definition is None
                or c.rule_version != definition.version
                or c.object_kind != definition.object_kind
            ):
                raise ValueError("Candidate does not match its catalog definition")
            if c.candidate_id in candidates:
                raise ValueError("Duplicate candidate identity")
            candidates[c.candidate_id] = c
        seen = set()
        for outcome in self.outcomes:
            candidate = candidates.get(outcome.candidate_id)
            if candidate is None:
                raise ValueError("Orphan outcome has no enumerated candidate")
            if outcome.candidate_id in seen:
                raise ValueError("Duplicate outcome for atomic candidate")
            seen.add(outcome.candidate_id)
            allowed = {
                "applicable": {"PASS", "FAIL", "UNKNOWN"},
                "unknown": {"UNKNOWN"},
                "not_applicable": {"NOT_APPLICABLE"},
            }[candidate.applicability]
            if outcome.result not in allowed:
                raise ValueError("Outcome contradicts candidate applicability")
        unsupported_keys = [(s.object_kind, s.object_id, s.scope) for s in self.unsupported]
        if len(set(unsupported_keys)) != len(unsupported_keys):
            raise ValueError("Duplicate unsupported scope")
        return self

    def counts(self) -> dict[str, int]:
        """Completed + unknown + not_applicable partitions candidates.

        unexecuted is an overlapping diagnostic subset of unknown, not an extra
        denominator. Unsupported scopes are separate, never invented candidates.
        """
        outcomes = {o.candidate_id: o.result for o in self.outcomes}
        complete = sum(o.result in {"PASS", "FAIL"} for o in self.outcomes)
        na = sum(c.applicability == "not_applicable" for c in self.candidates)
        return {
            "candidate_count": len(self.candidates),
            "applicable_count": sum(c.applicability == "applicable" for c in self.candidates),
            "applicability_unknown_count": sum(
                c.applicability == "unknown" for c in self.candidates
            ),
            "completed_count": complete,
            "unknown_count": len(self.candidates) - complete - na,
            "not_applicable_count": na,
            "unexecuted_count": sum(
                c.applicability != "not_applicable" and c.candidate_id not in outcomes
                for c in self.candidates
            ),
            "unsupported_scope_count": len(self.unsupported),
        }
