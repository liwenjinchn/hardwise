"""Bounded model selections over server-owned facts; never certify arbitrary prose."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator


FactKind = Literal[
    "observation", "assessment", "approved_parameter", "source_coverage", "lookup_result"
]
ObjectKind = Literal["component", "net", "project"]
ConditionStatus = Literal["explicit", "not_required", "unknown"]


def _canonical(value) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite values are not evidence")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _finite(item)


class ClaimBinding(BaseModel):
    """Every asserted dimension is compared, including missing/unknown conditions."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    object_kind: ObjectKind
    object_id: str = Field(min_length=1, max_length=256)
    property_key: str = Field(min_length=1, max_length=256)
    kind: FactKind
    value: JsonValue
    unit: str | None
    conditions: dict[str, JsonValue]
    conditions_status: ConditionStatus
    source_tokens: tuple[str, ...]
    rule_version: str | None

    @model_validator(mode="after")
    def coherent(self):
        if not self.object_id.strip() or not self.property_key.strip():
            raise ValueError("object and property must be nonempty")
        if any(not token.strip() for token in self.source_tokens):
            raise ValueError("source tokens must be nonempty")
        if len(set(self.source_tokens)) != len(self.source_tokens):
            raise ValueError("duplicate source token")
        if self.conditions_status == "explicit" and not self.conditions:
            raise ValueError("explicit conditions must be present")
        if self.conditions_status == "not_required" and self.conditions:
            raise ValueError("not_required must not conceal conditions")
        if self.kind == "approved_parameter" and (
            not self.source_tokens or self.conditions_status == "unknown"
        ):
            raise ValueError("approved parameters require scoped sources and known applicability")
        if self.kind == "assessment" and (
            self.value not in ("PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE")
            or not self.rule_version
            or self.unit is not None
        ):
            raise ValueError("assessment must select a versioned machine result")
        _finite(self.value)
        _finite(self.conditions)
        return self


class EvidenceFact(ClaimBinding):
    """Created only from dispatched server data, never accepted as model authority.

    The digest detects accidental mutation/substitution; it is not a signature,
    independent engineering review, or authentication of a datasheet field.
    """

    id: str = Field(pattern=r"^FACT-[0-9a-f]{64}$")
    scope_id: str = Field(min_length=1, max_length=256)
    call_id: str = Field(min_length=1, max_length=256)

    def digest(self):
        return (
            "FACT-"
            + hashlib.sha256(
                _canonical(self.model_dump(mode="json", exclude={"id"})).encode()
            ).hexdigest()
        )


def make_evidence_fact(*, binding: ClaimBinding, scope_id: str, call_id: str) -> EvidenceFact:
    data = {**binding.model_dump(mode="json"), "scope_id": scope_id, "call_id": call_id}
    data["id"] = "FACT-" + hashlib.sha256(_canonical(data).encode()).hexdigest()
    # JSON revalidation copies nested containers; do not retain the caller's dict aliases.
    return EvidenceFact.model_validate_json(_canonical(data))


class ModelClaim(ClaimBinding):
    fact_id: str = Field(pattern=r"^FACT-[0-9a-f]{64}$")


class EvidenceRequest(BaseModel):
    """Unverified follow-up proposals have no free-form verdict or numeric authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    object_kind: ObjectKind
    object_id: str = Field(min_length=1, max_length=256)
    topic: Literal[
        "rating",
        "voltage_envelope",
        "operating_condition",
        "part_identity",
        "connectivity",
        "document",
    ]


class ModelExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal["hardwise.model_explanation.v1"]
    scope_id: str = Field(min_length=1, max_length=256)
    claims: tuple[ModelClaim, ...] = Field(default=(), max_length=128)
    requests: tuple[EvidenceRequest, ...] = Field(default=(), max_length=32)


class ClaimIssue(BaseModel):
    index: int
    code: Literal["unknown_fact", "binding_mismatch", "unknown_conditions", "duplicate_claim"]


class ExplanationReview(BaseModel):
    """Only server-owned matching facts escape; rejected model prose/values do not."""

    verified_facts: tuple[EvidenceFact, ...] = ()
    requests: tuple[EvidenceRequest, ...] = ()
    issues: tuple[ClaimIssue, ...] = ()
    error: Literal["invalid_envelope", "stale_scope", "invalid_catalog"] | None = None


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite JSON constant")


def verify_model_explanation(
    raw: str,
    *,
    scope_id: str,
    catalog: tuple[EvidenceFact, ...],
    known_objects: set[tuple[ObjectKind, str]],
) -> ExplanationReview:
    """Check exact typed bindings, not token occurrence or semantic trust in prose.

    Source adapters must authorize each catalog fact before this boundary. This
    pure verifier does not create a machine assessment, approve fields, store a
    decision, or provide the Runner/API/UI integration.
    """
    try:
        if len(raw) > 128_000:
            raise ValueError("envelope too large")
        data = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
        envelope = ModelExplanation.model_validate_json(_canonical(data))
    except (ValueError, TypeError, RecursionError, ValidationError):
        return ExplanationReview(error="invalid_envelope")
    if envelope.scope_id != scope_id:
        return ExplanationReview(error="stale_scope")
    facts = {}
    try:
        for fact in catalog:
            if (
                fact.scope_id != scope_id
                or fact.id != fact.digest()
                or fact.id in facts
                or (fact.object_kind, fact.object_id) not in known_objects
            ):
                return ExplanationReview(error="invalid_catalog")
            # Revalidate even nested mutable fields or bypassed model_copy updates.
            facts[fact.id] = EvidenceFact.model_validate_json(fact.model_dump_json())
    except (ValueError, TypeError, RecursionError):
        return ExplanationReview(error="invalid_catalog")
    verified, issues, seen = [], [], set()
    for index, claim in enumerate(envelope.claims):
        fact = facts.get(claim.fact_id)
        code = None
        if claim.fact_id in seen:
            code = "duplicate_claim"
        elif fact is None:
            code = "unknown_fact"
        elif _canonical(claim.model_dump(mode="json", exclude={"fact_id"})) != _canonical(
            fact.model_dump(mode="json", exclude={"id", "scope_id", "call_id"})
        ):
            code = "binding_mismatch"
        elif fact.conditions_status == "unknown":
            code = "unknown_conditions"
        seen.add(claim.fact_id)
        if code:
            issues.append(ClaimIssue(index=index, code=code))
        else:
            verified.append(fact)
    # A proposal cannot introduce a fabricated object or confer a verified verdict.
    requests = tuple(
        request
        for request in envelope.requests
        if (request.object_kind, request.object_id) in known_objects
    )
    return ExplanationReview(
        verified_facts=tuple(verified), requests=requests, issues=tuple(issues)
    )
