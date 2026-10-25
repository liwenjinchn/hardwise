"""Synthetic declarations exercise mechanics; no record here is a human approval."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.profile_review import (
    FieldCondition,
    FieldDecision,
    FieldSource,
    ProfileReview,
    ReviewIdentity,
    ReviewedField,
    approval_problems,
    profile_values,
    transition_profile,
)


def synthetic_profile():
    profile = DatasheetProfile(
        part_number="SYNTHETIC-X",
        abs_max={"vin": 35.0},
        extracted_at="",
        extracted_model="automated synthetic fixture",
    )
    identity = ReviewIdentity(
        manufacturer="Synthetic fixture, not a manufacturer",
        part_numbers=["SYNTHETIC-X"],
        packages=["SOP8"],
    )
    source = FieldSource(
        url="https://example.invalid/synthetic.pdf",
        document_revision="synthetic-v1",
        document_sha256="1" * 64,
        page=1,
        locator="synthetic table",
        excerpt="Synthetic fixture statement, not a vendor document or real approval.",
    )
    fields = []
    for pointer, value in profile_values(profile).items():
        field = ReviewedField(
            pointer=pointer,
            value=value,
            unit="V" if pointer == "/abs_max/vin" else "text",
            subject="SYNTHETIC-X",
            role="maximum" if pointer == "/abs_max/vin" else "identity",
            nature="intrinsic",
            conditions=[FieldCondition(kind="unconditional", description="synthetic exercise")],
            source=source,
        )
        decision = FieldDecision(
            decision="approved",
            actor="human",  # simulated declaration; never actual human acceptance
            reviewer="AUTOMATED SYNTHETIC RECORD - NOT HUMAN APPROVAL",
            reviewed_at="2026-10-25T00:00:00Z",
            reason="Test mechanics only",
            content_sha256=field.content_hash(identity),
        )
        fields.append(field.model_copy(update={"decisions": [decision]}))
    return profile.model_copy(
        update={"field_review": ProfileReview(identity=identity, fields=fields)}
    )


def ready_profile():
    return transition_profile(transition_profile(synthetic_profile(), "REVIEWED"), "READY")


def test_legacy_ready_and_missing_status_are_effective_draft():
    legacy = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    assert legacy.review_status == "ready"  # preserved legacy declaration, never new approval
    assert legacy.lifecycle == "DRAFT" and not legacy.approved_for_validation
    new = DatasheetProfile(part_number="X", extracted_at="", extracted_model="")
    assert new.review_status == "needs_review" and new.lifecycle == "DRAFT"


def test_explicit_lifecycle_sequence_and_retirement():
    profile = synthetic_profile()
    with pytest.raises(ValueError):
        transition_profile(profile, "READY")
    ready = ready_profile()
    assert ready.lifecycle == "READY" and ready.approved_for_validation
    with pytest.raises(ValueError):
        transition_profile(ready, "RETIRED")
    retired = transition_profile(ready, "RETIRED", retirement_reason="Synthetic supersession")
    assert retired.lifecycle == "RETIRED" and not retired.approved_for_validation
    with pytest.raises(ValueError):
        transition_profile(retired, "READY")


@pytest.mark.parametrize(
    "change",
    [
        "value",
        "source",
        "unit",
        "identity",
        "conditions",
        "rejection",
        "partial",
        "added_field",
        "removed_field",
    ],
)
def test_changes_or_incomplete_approval_invalidate_ready_without_erasing_decisions(change):
    profile = ready_profile()
    review = profile.field_review
    if change == "value":
        profile = profile.model_copy(update={"abs_max": {"vin": 36.0}})
    elif change == "added_field":
        profile = profile.model_copy(update={"abs_max": {"vin": 35.0, "vdd": 5.0}})
    elif change == "removed_field":
        profile = profile.model_copy(update={"abs_max": {}})
    elif change == "identity":
        review = review.model_copy(
            update={"identity": review.identity.model_copy(update={"packages": ["OTHER"]})}
        )
    else:
        field = review.fields[-1]
        if change == "source":
            field = field.model_copy(
                update={"source": field.source.model_copy(update={"document_sha256": "2" * 64})}
            )
        if change == "unit":
            field = field.model_copy(update={"unit": "A"})
        if change == "conditions":
            field = field.model_copy(
                update={
                    "conditions": [
                        FieldCondition(kind="unsupported", description="unmodeled temperature")
                    ]
                }
            )
        if change == "rejection":
            field = field.model_copy(
                update={
                    "decisions": [
                        *field.decisions,
                        field.decisions[-1].model_copy(update={"decision": "rejected"}),
                    ]
                }
            )
        if change == "partial":
            field = field.model_copy(update={"decisions": []})
        review = review.model_copy(update={"fields": [*review.fields[:-1], field]})
    profile = profile.model_copy(update={"field_review": review})
    assert profile.lifecycle == "DRAFT" and not profile.approved_for_validation
    assert approval_problems(profile)
    assert ready_profile().field_review.fields[-1].decisions  # old record is never mutated


@pytest.mark.parametrize(
    "value,unit,role,nature,condition",
    [
        (True, "V", "maximum", "intrinsic", "unconditional"),
        ("35", "text", "maximum", "intrinsic", "unconditional"),
        (35.0, "A", "maximum", "intrinsic", "unconditional"),
        (35.0, "V", "typical", "intrinsic", "unconditional"),
        (35.0, "V", "maximum", "board_policy", "unconditional"),
        (35.0, "V", "maximum", "application_recommendation", "unconditional"),
        (35.0, "V", "maximum", "intrinsic", "unsupported"),
        (35.0, "V", "maximum", "intrinsic", "dc_relation"),
    ],
)
def test_approval_does_not_make_unsupported_or_wrongly_typed_premises_executable(
    value, unit, role, nature, condition
):
    profile = synthetic_profile()
    review = profile.field_review
    field = review.fields[-1]
    # model_copy deliberately models unsafe in-process mutation; the effective guard rechecks it.
    field = field.model_copy(
        update={
            "value": value,
            "unit": unit,
            "role": role,
            "nature": nature,
            "conditions": [FieldCondition(kind=condition, description="synthetic condition")],
        }
    )
    decision = field.decisions[0].model_copy(
        update={"content_sha256": field.content_hash(review.identity)}
    )
    field = field.model_copy(update={"decisions": [decision]})
    profile = profile.model_copy(
        update={
            "abs_max": {"vin": value},
            "field_review": review.model_copy(
                update={"status": "READY", "fields": [*review.fields[:-1], field]}
            ),
        }
    )
    assert not profile.approved_for_validation


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_field_values_are_rejected(value):
    field = synthetic_profile().field_review.fields[-1]
    data = field.model_dump(mode="json")
    data["value"] = value
    with pytest.raises(ValidationError):
        ReviewedField.model_validate(data)


@pytest.mark.parametrize(
    "time", ["2026-99-99T00:00:00Z", "2026-10-25T00:00:00", "2026-10-25", 1234]
)
def test_review_time_must_be_real_timezone_bearing_timestamp(time):
    data = synthetic_profile().field_review.fields[-1].decisions[-1].model_dump(mode="json")
    data["reviewed_at"] = time
    with pytest.raises(ValidationError):
        FieldDecision.model_validate(data)


def test_duplicate_review_pointers_and_blank_identity_rejected():
    review = synthetic_profile().field_review
    data = review.model_dump(mode="json")
    data["fields"].append(data["fields"][0])
    with pytest.raises(ValidationError):
        ProfileReview.model_validate(data)
    with pytest.raises(ValidationError):
        ReviewIdentity(manufacturer=" ", part_numbers=["X"], packages=[""])


def test_json_roundtrip_and_legacy_storage_integrity_guard(tmp_path):
    profile = ready_profile()
    path = tmp_path / "synthetic.json"
    profile.save(path)
    actual = DatasheetProfile.load(path)
    assert actual.model_dump(mode="json") == profile.model_dump(mode="json")
    assert actual.lifecycle == "READY"
    assert actual.model_copy(update={"storage_integrity": "legacy_incomplete"}).lifecycle == "DRAFT"


def test_python_model_dump_roundtrip_retains_review_timestamp():
    profile = ready_profile()
    restored = DatasheetProfile.model_validate(profile.model_dump())
    assert restored.lifecycle == "READY"


@pytest.mark.parametrize("name", ["reviewer", "reason"])
def test_whitespace_only_review_declaration_rejected(name):
    data = synthetic_profile().field_review.fields[-1].decisions[-1].model_dump(mode="json")
    data[name] = "   "
    with pytest.raises(ValidationError):
        FieldDecision.model_validate(data)


def test_top_level_evidence_changes_also_require_review():
    ready = ready_profile()
    changed = ready.model_copy(update={"evidence": {"abs_max.vin": "datasheet:other.pdf#p1"}})
    assert changed.lifecycle == "DRAFT"


def test_wrong_subject_cannot_be_approved_even_with_fresh_digest():
    profile = ready_profile()
    review = profile.field_review
    field = review.fields[-1]
    field = field.model_copy(update={"subject": "OTHER-DEVICE"})
    field = field.model_copy(
        update={
            "decisions": [
                field.decisions[-1].model_copy(
                    update={"content_sha256": field.content_hash(review.identity)}
                )
            ]
        }
    )
    changed = profile.model_copy(
        update={"field_review": review.model_copy(update={"fields": [*review.fields[:-1], field]})}
    )
    assert changed.lifecycle == "DRAFT"


def test_boolean_page_locator_rejected():
    data = synthetic_profile().field_review.fields[-1].source.model_dump(mode="json")
    data["page"] = True
    with pytest.raises(ValidationError):
        FieldSource.model_validate(data)


@pytest.mark.parametrize("actor", [None, "ai"])
def test_human_actor_is_explicit_never_inferred_from_missing_marker(actor):
    data = synthetic_profile().field_review.fields[-1].decisions[-1].model_dump(mode="json")
    if actor is None:
        data.pop("actor")
    else:
        data["actor"] = actor
    with pytest.raises(ValidationError):
        FieldDecision.model_validate(data)
