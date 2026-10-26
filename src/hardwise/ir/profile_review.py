"""Typed, content-bound human review records; these are declarations, not authentication."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
    field_validator,
)

from hardwise.ir.profile_units import declaration_problem
from hardwise.ir.excerpt_sharing import ExcerptSharingDeclaration

Lifecycle = Literal["DRAFT", "REVIEWED", "READY", "RETIRED"]
SHA256 = r"^[a-f0-9]{64}$"


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class ReviewIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    manufacturer: str = Field(min_length=1)
    part_numbers: list[str] = Field(min_length=1)
    packages: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def exact_identity(self):
        if not self.manufacturer.strip() or any(
            not x.strip() for x in [*self.part_numbers, *self.packages]
        ):
            raise ValueError("identity scope must contain nonblank exact values")
        return self


class FieldSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    url: str = Field(pattern=r"^https?://[^\s]+$")
    document_revision: str = Field(min_length=1)
    document_sha256: str = Field(pattern=SHA256)
    page: int = Field(ge=1, strict=True)
    locator: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)
    # Keep old source serialization and historical field hashes byte-compatible.
    sharing: ExcerptSharingDeclaration | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class FieldCondition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    kind: Literal["unconditional", "dc_relation", "unsupported"]
    description: str = Field(min_length=1)


class FieldDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    decision: Literal["approved", "rejected", "needs_information"]
    reviewer: str = Field(min_length=1)
    reviewed_at: AwareDatetime
    reason: str = Field(min_length=1)
    content_sha256: str = Field(pattern=SHA256)
    actor: Literal["human"]

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def timestamp_is_explicit(cls, value):
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("reviewed_at must be an explicit timezone-bearing ISO timestamp")
        return value


class ReviewedField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    pointer: str = Field(pattern=r"^/")
    value: StrictBool | StrictInt | StrictFloat | StrictStr
    unit: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    role: Literal["identity", "minimum", "typical", "maximum", "definition", "relationship"]
    nature: Literal["intrinsic", "application_recommendation", "board_policy"]
    conditions: list[FieldCondition] = Field(min_length=1)
    source: FieldSource
    decisions: list[FieldDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def finite_and_typed(self):
        # bool is intentionally distinct from numeric and cannot carry voltage/current units.
        import math

        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("profile field numbers must be finite")
        if isinstance(self.value, bool) and self.unit != "boolean":
            raise ValueError("boolean fields require the boolean unit")
        return self

    def content_hash(self, identity: ReviewIdentity) -> str:
        return digest(
            {
                "identity": identity.model_dump(mode="json"),
                "field": self.model_dump(
                    mode="json", exclude={"decisions": True, "source": {"sharing"}}
                ),
            }
        )

    def approved(self, identity: ReviewIdentity) -> bool:
        return bool(
            self.decisions
            and self.decisions[-1].decision == "approved"
            and self.decisions[-1].content_sha256 == self.content_hash(identity)
        )


class ProfileReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["hardwise.profile_review.v1"] = "hardwise.profile_review.v1"
    identity: ReviewIdentity
    status: Lifecycle = "DRAFT"
    fields: list[ReviewedField] = Field(default_factory=list)
    retirement_reason: str | None = None

    @model_validator(mode="after")
    def unique_pointers(self):
        if self.status == "RETIRED" and not (self.retirement_reason or "").strip():
            raise ValueError("retired profiles require a reason")
        pointers = [field.pointer for field in self.fields]
        if len(pointers) != len(set(pointers)):
            raise ValueError("duplicate profile review field pointer")
        return self


def profile_values(profile) -> dict[str, object]:
    """Every declared fact leaf, including identities/conditions; no guessed metadata."""
    raw = profile.model_dump(
        mode="json",
        include={
            "part_number",
            "part_number_aliases",
            "abs_max",
            "recommended",
            "pin_function",
            "pins",
            "voltage_relations",
            "evidence",
        },
    )
    values = {}

    def visit(value, pointer):
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, pointer + "/" + str(index))
        else:
            values[pointer] = value

    visit(raw, "")
    return values


def same_value(first, second):
    try:
        return digest(first) == digest(second)
    except (ValueError, TypeError):
        return False


def expected_subject(profile, pointer):
    parts = pointer.split("/")
    if len(parts) > 2 and parts[1] == "pins":
        return f"pin:{profile.pins[int(parts[2])].number}"
    if len(parts) > 2 and parts[1] == "pin_function":
        return f"pin:{parts[2]}"
    if len(parts) > 2 and parts[1] == "voltage_relations":
        relation = profile.voltage_relations[int(parts[2])]
        return f"pin:{relation.target_pin}->pin:{relation.supply_pin}@pin:{relation.ground_pin}"
    return profile.part_number


def approval_problems(profile) -> list[str]:
    review = profile.field_review
    if review is None:
        return ["缺少逐字段来源与人工批准；旧标签不构成批准。"]
    if profile.part_number not in review.identity.part_numbers:
        return ["档案型号与批准身份作用域不一致。"]
    values = profile_values(profile)
    fields = {field.pointer: field for field in review.fields}
    problems = []
    for pointer, value in values.items():
        field = fields.get(pointer)
        if field is None or not same_value(field.value, value):
            problems.append(f"{pointer}: 缺少匹配当前值的字段声明。")
        elif not field.approved(review.identity):
            problems.append(f"{pointer}: 缺少匹配当前内容与来源的人工批准。")
        elif field.subject != expected_subject(profile, pointer):
            problems.append(f"{pointer}: 批准主体与档案/引脚关系不一致。")
        elif problem := declaration_problem(field):
            problems.append(f"{pointer}: {problem}")
    for pointer in fields.keys() - values.keys():
        problems.append(f"{pointer}: 字段已不存在，批准不可沿用。")
    return problems


def effective_lifecycle(profile) -> Lifecycle:
    review = profile.field_review
    if review is None or profile.storage_integrity != "complete":
        return "DRAFT"
    if review.status == "RETIRED":
        return "RETIRED"
    if review.status == "READY" and approval_problems(profile):
        return "DRAFT"
    if review.status == "REVIEWED":
        values = profile_values(profile)
        fields = {field.pointer: field for field in review.fields}
        if set(values) != set(fields) or any(
            not same_value(fields[p].value, value)
            or not fields[p].decisions
            or fields[p].decisions[-1].content_sha256 != fields[p].content_hash(review.identity)
            for p, value in values.items()
        ):
            return "DRAFT"
    return review.status


def transition_profile(profile, target: Lifecycle, *, retirement_reason=None):
    """Local explicit review operation; never called by extraction/chat pipelines."""
    current = effective_lifecycle(profile)
    allowed = {
        "DRAFT": {"REVIEWED", "RETIRED"},
        "REVIEWED": {"DRAFT", "READY", "RETIRED"},
        "READY": {"DRAFT", "RETIRED"},
        "RETIRED": set(),
    }
    if target not in allowed[current] or profile.field_review is None:
        raise ValueError(f"profile transition {current} -> {target} is not allowed")
    raw = profile.field_review.model_dump(mode="json")
    raw.update(status=target)
    if target == "RETIRED":
        raw["retirement_reason"] = retirement_reason
    updated = profile.model_copy(update={"field_review": ProfileReview.model_validate(raw)})
    if effective_lifecycle(updated) != target:
        raise ValueError("profile transition prerequisites are incomplete or stale")
    return updated
