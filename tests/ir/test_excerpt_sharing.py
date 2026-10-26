"""Sharing permissions never stand in for engineering approval or source truth."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from hardwise.ir.excerpt_sharing import (
    ExcerptSharingDeclaration,
    sharing_status,
    source_content_hash,
)
from hardwise.ir.profile_review import FieldSource, digest, effective_lifecycle
from tests.ir.test_profile_review import ready_profile


def source():
    return ready_profile().field_review.fields[0].source


def declare(original, decision="allow"):
    return original.model_copy(
        update={
            "sharing": ExcerptSharingDeclaration(
                decision=decision,
                source_sha256=source_content_hash(original),
                declared_by="Synthetic reviewer; no real approval",
                declared_at="2026-10-26T08:00:00+00:00",
                reason="Synthetic excerpt for software validation only",
                actor="human",
            )
        }
    )


def test_legacy_source_is_undeclared_and_serializes_without_new_null_field():
    original = source()
    raw = original.model_dump(mode="json")
    assert "sharing" not in raw
    assert sharing_status(original) == "undeclared"
    assert FieldSource.model_validate(raw).model_dump(mode="json") == raw


def test_valid_sharing_and_withholding_bind_the_same_original_source():
    original = source()
    shared, withheld = declare(original), declare(original, "withhold")
    assert sharing_status(shared) == "allowed"
    assert sharing_status(withheld) == "withheld"
    assert (
        source_content_hash(original)
        == source_content_hash(shared)
        == source_content_hash(withheld)
    )
    assert sharing_status(FieldSource.model_validate_json(shared.model_dump_json())) == "allowed"
    assert original.sharing is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.com/other.pdf"),
        ("document_revision", "different"),
        ("document_sha256", "b" * 64),
        ("page", 999),
        ("locator", "different table"),
        ("excerpt", "Different synthetic excerpt"),
    ],
)
def test_any_source_change_invalidates_sharing(field, value):
    shared = declare(source())
    assert getattr(shared, field) != value
    changed = shared.model_copy(update={field: value})
    assert sharing_status(changed) == "stale"
    assert sharing_status(shared) == "allowed"


@pytest.mark.parametrize("decision", ["allow", "withhold"])
def test_sharing_metadata_does_not_invalidate_original_electrical_approval(decision):
    profile = ready_profile()
    review = profile.field_review
    field = review.fields[0]
    legacy_hash = digest(
        {
            "identity": review.identity.model_dump(mode="json"),
            "field": field.model_dump(mode="json", exclude={"decisions"}),
        }
    )
    assert field.content_hash(review.identity) == legacy_hash
    changed = field.model_copy(update={"source": declare(field.source, decision)})
    assert changed.content_hash(review.identity) == legacy_hash
    assert changed.approved(review.identity)
    updated = profile.model_copy(
        update={"field_review": review.model_copy(update={"fields": [changed, *review.fields[1:]]})}
    )
    assert effective_lifecycle(updated) == effective_lifecycle(profile) == "READY"


def test_sharing_does_not_approve_draft_or_changed_electrical_source():
    profile = ready_profile()
    field = profile.field_review.fields[0]
    draft = field.model_copy(update={"decisions": [], "source": declare(field.source)})
    assert sharing_status(draft.source) == "allowed"
    assert not draft.approved(profile.field_review.identity)
    changed = field.model_copy(
        update={
            "source": declare(field.source).model_copy(
                update={"excerpt": "Changed source assertion"}
            )
        }
    )
    assert sharing_status(changed.source) == "stale"
    assert not changed.approved(profile.field_review.identity)


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor", "model"),
        ("declared_by", "   "),
        ("reason", ""),
        ("declared_at", 1234),
        ("declared_at", "2026-10-26"),
        ("declared_at", "2026-10-26T08:00:00"),
        ("source_sha256", "0"),
        ("decision", "approved"),
        ("extra", "safe to fabricate"),
    ],
)
def test_bad_declarations_fail_closed(field, value):
    data = declare(source()).sharing.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        ExcerptSharingDeclaration.model_validate(data)


def test_bypassed_declaration_validation_is_stale():
    shared = declare(source())
    invalid = shared.sharing.model_copy(update={"actor": "model"})
    assert sharing_status(shared.model_copy(update={"sharing": invalid})) == "stale"


def test_electrical_hash_excludes_only_sharing_not_original_source_content():
    profile = ready_profile()
    field = profile.field_review.fields[0]
    changed = deepcopy(field)
    changed = changed.model_copy(
        update={
            "source": declare(field.source).model_copy(
                update={"document_revision": "different revision"}
            )
        }
    )
    assert changed.content_hash(profile.field_review.identity) != field.content_hash(
        profile.field_review.identity
    )


def test_sharing_projection_withholds_original_and_reason_without_mutating_local_record():
    import json
    from hardwise.ir.shared_excerpts import share_excerpt_projection, has_withheld_excerpt

    original = source().model_copy(update={"excerpt": "SYNTHETIC_PRIVATE_EXCERPT"})
    shared = declare(original, "withhold")
    shared = shared.model_copy(
        update={
            "sharing": shared.sharing.model_copy(update={"reason": "SYNTHETIC_PRIVATE_EXCERPT"})
        }
    )
    raw = shared.model_dump(mode="json")
    before = deepcopy(raw)
    projected = share_excerpt_projection({"nested": [raw]})
    assert "SYNTHETIC_PRIVATE_EXCERPT" not in json.dumps(projected)
    assert projected["nested"][0]["excerpt_delivery"]["reason"] == "withheld"
    assert projected["nested"][0]["document_sha256"] == original.document_sha256
    assert raw == before
    assert has_withheld_excerpt(raw)
    allowed = declare(original).model_dump(mode="json")
    assert share_excerpt_projection(allowed) == allowed
    assert not has_withheld_excerpt(allowed)


@pytest.mark.parametrize("state", ["legacy", "stale", "invalid"])
def test_sharing_projection_fails_closed_for_unapproved_source_shapes(state):
    from hardwise.ir.shared_excerpts import share_excerpt_projection

    original = source().model_copy(update={"excerpt": "WITHHELD_SENTINEL"})
    data = original.model_dump(mode="json")
    if state == "stale":
        data = declare(original).model_dump(mode="json")
        data["page"] += 1
    elif state == "invalid":
        data = {"excerpt": "WITHHELD_SENTINEL", "sharing": {"decision": "allow"}}
    projected = share_excerpt_projection(data)
    assert "excerpt" not in projected
    assert projected["excerpt_delivery"]["status"] == "omitted"
    assert (
        projected["excerpt_delivery"]["reason"]
        == {"legacy": "undeclared", "stale": "stale", "invalid": "invalid_source"}[state]
    )


def test_redacted_receipt_preserves_local_hash_and_labels_shared_payload_hash():
    import hashlib
    import json
    from hardwise.ir.shared_excerpts import share_excerpt_projection

    values = {"field_review": {"fields": [{"source": source().model_dump(mode="json")}]}}
    local_hash = digest(values)
    receipt = dict(sha256=local_hash, part_number="SYNTHETIC", review_status="ready", values=values)
    before = deepcopy(receipt)
    result = share_excerpt_projection(receipt)
    assert receipt == before
    assert result["sha256"] == local_hash
    assert result["share_projection"]["original_local_sha256"] == local_hash
    actual_hash = hashlib.sha256(
        json.dumps(
            result["values"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    assert result["share_projection"]["shared_values_sha256"] == actual_hash != local_hash


def test_noncanonical_source_cannot_reuse_permission_for_different_raw_excerpt():
    from hardwise.ir.shared_excerpts import share_excerpt_projection

    original = declare(source()).model_dump(mode="json")
    original["excerpt"] = " " + original["excerpt"] + " "
    projected = share_excerpt_projection(original)
    assert "excerpt" not in projected
    assert projected["excerpt_delivery"]["reason"] == "invalid_source"
