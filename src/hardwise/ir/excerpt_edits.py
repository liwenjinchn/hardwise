"""Human source entry cannot confer electrical approval or change parameter values."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hardwise.ir.excerpt_sharing import ExcerptSharingDeclaration, source_content_hash
from hardwise.ir.profile_review import (
    FieldCondition,
    FieldSource,
    ProfileReview,
    ReviewIdentity,
    ReviewedField,
    expected_subject,
    profile_values,
)


class ManualSource(FieldSource):
    @model_validator(mode="after")
    def no_supplied_declaration(self):
        if self.sharing is not None:
            raise ValueError("Sharing declaration is recorded by the server")
        return self


class ExcerptEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pointer: str = Field(pattern=r"^/", max_length=2000)
    source: ManualSource
    unit: str = Field(min_length=1, max_length=128)
    role: Literal["identity", "minimum", "typical", "maximum", "definition", "relationship"]
    nature: Literal["intrinsic", "application_recommendation", "board_policy"]
    conditions: list[FieldCondition] = Field(min_length=1, max_length=100)
    identity: ReviewIdentity | None = None
    sharing: Literal["allow", "withhold"]
    declared_by: str = Field(min_length=1, max_length=256)
    reason: str = Field(min_length=1, max_length=2000)


def apply_excerpt_edit(profile, edit: ExcerptEdit, *, recorded_at: datetime):
    values = profile_values(profile)
    if edit.pointer not in values or values[edit.pointer] is None:
        raise ValueError("Select an existing non-null parameter")
    review = profile.field_review
    if review is not None and review.status == "RETIRED":
        raise ValueError("Retired profiles cannot be edited")
    if review is None:
        if edit.identity is None or profile.part_number not in edit.identity.part_numbers:
            raise ValueError("First source entry requires explicit matching device identity")
        review = ProfileReview(identity=edit.identity)
    elif edit.identity is not None and edit.identity != review.identity:
        raise ValueError("Source editing cannot replace device identity")
    source = FieldSource.model_validate(edit.source.model_dump(mode="json"))
    declaration = ExcerptSharingDeclaration(
        decision=edit.sharing,
        source_sha256=source_content_hash(source),
        declared_by=edit.declared_by,
        declared_at=recorded_at,
        reason=edit.reason,
        actor="human",
    )
    source = source.model_copy(update={"sharing": declaration})
    previous = next((f for f in review.fields if f.pointer == edit.pointer), None)
    field = ReviewedField(
        pointer=edit.pointer,
        value=values[edit.pointer],
        unit=edit.unit,
        subject=expected_subject(profile, edit.pointer),
        role=edit.role,
        nature=edit.nature,
        conditions=edit.conditions,
        source=source,
        decisions=previous.decisions if previous else [],
    )
    fields = [field if f.pointer == edit.pointer else f for f in review.fields]
    if previous is None:
        fields.append(field)
    changed = previous is None or previous.content_hash(review.identity) != field.content_hash(
        review.identity
    )
    updated = review.model_copy(
        update={"fields": fields, "status": "DRAFT" if changed else review.status}
    )
    return profile.model_copy(update={"field_review": updated})
