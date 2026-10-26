"""Construct an explicit share projection without mutating local source records."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from pydantic import ValidationError

from hardwise.ir.excerpt_sharing import sharing_status, source_content_hash
from hardwise.ir.profile_review import FieldSource


BOUNDARY = "Share projection; original local content hashes do not describe redacted payloads."


def _source_status(data, withheld_hashes=frozenset(), allowed_hashes=None):
    try:
        source = FieldSource.model_validate(data)
        if source.model_dump(mode="json") != data:
            return None, "invalid_source"
        status = sharing_status(source)
        if source_content_hash(source) in withheld_hashes:
            status = "withheld"
        elif (
            status == "allowed"
            and allowed_hashes is not None
            and source_content_hash(source) not in allowed_hashes
        ):
            status = "not_currently_allowed"
        return source, status
    except (ValueError, TypeError, ValidationError):
        return None, "invalid_source"


def has_withheld_excerpt(value, withheld_hashes=frozenset(), allowed_hashes=None) -> bool:
    """Chat claims must be retained whole or withheld; never change verified fact IDs."""
    if isinstance(value, dict):
        if (
            "excerpt" in value
            and _source_status(value, withheld_hashes, allowed_hashes)[1] != "allowed"
        ):
            return True
        return any(
            has_withheld_excerpt(item, withheld_hashes, allowed_hashes) for item in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(has_withheld_excerpt(item, withheld_hashes, allowed_hashes) for item in value)
    return False


def share_excerpt_projection(value, withheld_hashes=frozenset(), allowed_hashes=None):
    """Redact undeclared/stale/withheld excerpts, preserving their exact source hash.

    Only typed FieldSource objects with an effective allow declaration retain
    excerpts. Unknown excerpt-shaped dictionaries fail closed. This function
    operates on structured data, not arbitrary strings or rendered HTML; callers
    must rebuild derived text after projection and cover all export surfaces.
    """
    if isinstance(value, list):
        return [share_excerpt_projection(item, withheld_hashes, allowed_hashes) for item in value]
    if not isinstance(value, dict):
        return deepcopy(value)
    result = {
        key: share_excerpt_projection(item, withheld_hashes, allowed_hashes)
        for key, item in value.items()
    }
    if "excerpt" in value:
        source, status = _source_status(value, withheld_hashes, allowed_hashes)
        if status != "allowed":
            result.pop("excerpt", None)
            # The declaration's free-form reason is not a substitute export
            # channel for the withheld original. Preserve only its status.
            result.pop("sharing", None)
            excerpt = value["excerpt"]
            result["excerpt_delivery"] = {
                "status": "omitted",
                "reason": status,
                "source_sha256": source_content_hash(source) if source else None,
                "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest()
                if isinstance(excerpt, str)
                else None,
                "boundary": "Excerpt omitted; no redistribution permission or engineering approval inferred.",
            }
    # A receipt keeps its original local identifier; never claim that it hashes
    # the now-redacted values. The share payload has its own hash and clear scope.
    if {"sha256", "values", "part_number", "review_status"}.issubset(value) and result[
        "values"
    ] != value["values"]:
        result["share_projection"] = {
            "original_local_sha256": value["sha256"],
            "shared_values_sha256": hashlib.sha256(
                json.dumps(
                    result["values"],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode()
            ).hexdigest(),
            "boundary": BOUNDARY,
        }
    return result
