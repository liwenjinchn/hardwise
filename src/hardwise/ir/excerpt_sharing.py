"""Human sharing declarations bind exact source content, not electrical approval."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class ExcerptSharingDeclaration(BaseModel):
    """A recorded human assertion, not authentication or proof of redistribution rights."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    decision: Literal["allow", "withhold"]
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    declared_by: str = Field(min_length=1, max_length=256)
    declared_at: AwareDatetime
    reason: str = Field(min_length=1, max_length=2000)
    actor: Literal["human"]

    @field_validator("declared_at", mode="before")
    @classmethod
    def explicit_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("sharing declaration requires an explicit timezone-bearing timestamp")
        return value


def source_content_hash(source: Any) -> str:
    """Hash the original source fields only; no sharing decision can authorize itself."""
    data = source.model_dump(mode="json", exclude={"sharing"})
    return hashlib.sha256(
        json.dumps(
            data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def sharing_status(source: Any) -> Literal["allowed", "withheld", "undeclared", "stale"]:
    from hardwise.ir.profile_review import FieldSource

    try:
        source = FieldSource.model_validate_json(source.model_dump_json())
    except (ValueError, TypeError, AttributeError):
        return "stale"
    declaration = source.sharing
    if declaration is None:
        return "undeclared"
    # Frozen models still permit model_copy bypasses; validate the declaration
    # at the trust boundary, and bind all original source dimensions exactly.
    try:
        declaration = ExcerptSharingDeclaration.model_validate_json(declaration.model_dump_json())
        if declaration.source_sha256 != source_content_hash(source):
            return "stale"
    except (ValueError, TypeError, AttributeError):
        return "stale"
    return "allowed" if declaration.decision == "allow" else "withheld"
