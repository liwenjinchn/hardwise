"""Explicit synthetic approvals exercise binding mechanics, not real field acceptance."""

import json

import pytest

from hardwise.agent.profile_claim_bindings import profile_claim_bindings
from hardwise.agent.evidence_locator import (
    locate_component_evidence,
    LocateComponentEvidenceInput,
    evidence_locator_tokens,
)
from hardwise.agent.tool_claim_catalog import tool_claim_catalog
from hardwise.ir.types import Component
from hardwise.workbench.context import close_workbench_context
from hardwise.validation.profile_approval import approved_tokens
from hardwise.guards.evidence_class import classify_evidence_token
from tests.ir.test_profile_review import ready_profile
from tests.agent.test_evidence_locator import _context


def component(profile):
    return Component(
        refdes="U1",
        part_number=profile.part_number,
        package="SOP8",
        manufacturer=profile.field_review.identity.manufacturer,
    )


def test_approved_value_unit_role_conditions_document_and_decision_are_bound_exactly():
    profile = ready_profile()
    (binding,) = profile_claim_bindings(profile, component(profile), pointer="/abs_max/vin")
    field = next(f for f in profile.field_review.fields if f.pointer == "/abs_max/vin")
    assert binding.value == field.value == 35.0
    assert binding.unit == field.unit == "V"
    assert binding.kind == "approved_parameter"
    assert binding.property_key == "profile/abs_max/vin"
    assert binding.source_tokens == (f"datasheet:{field.source.url}#p{field.source.page}",)
    assert (
        classify_evidence_token(
            binding.source_tokens[0], reviewed_profile_tokens=approved_tokens(profile)
        ).source_class
        == "reviewed_profile"
    )
    assert binding.conditions["source"] == field.source.model_dump(mode="json")
    assert binding.conditions["approval"] == field.decisions[-1].model_dump(mode="json")
    assert binding.conditions["applicability"] == [
        c.model_dump(mode="json") for c in field.conditions
    ]
    assert binding.conditions["role"] == "maximum"
    assert binding.conditions["identity"] == profile.field_review.identity.model_dump(mode="json")


@pytest.mark.parametrize(
    "field,value",
    [
        ("manufacturer", "Different manufacturer"),
        ("package", "OTHER_PACKAGE"),
        ("part_number", "SYNTHETIC-X-OTHER-SUFFIX"),
    ],
)
def test_approval_scope_cannot_be_borrowed_for_another_component_identity(field, value):
    profile = ready_profile()
    other = component(profile).model_copy(update={field: value})
    assert not profile_claim_bindings(profile, other, pointer="/abs_max/vin")


@pytest.mark.parametrize("change", ["legacy", "value", "unit", "source", "conditions"])
def test_missing_or_changed_approval_cannot_emit_parameter_binding(change):
    profile = ready_profile()
    original_component = component(profile)
    if change == "legacy":
        profile = profile.model_copy(update={"field_review": None})
    else:
        review = profile.field_review
        fields = list(review.fields)
        index = next(i for i, f in enumerate(fields) if f.pointer == "/abs_max/vin")
        field = fields[index]
        if change == "value":
            profile = profile.model_copy(update={"abs_max": {"vin": 900.0}})
        elif change == "unit":
            fields[index] = field.model_copy(update={"unit": "A"})
        elif change == "source":
            fields[index] = field.model_copy(
                update={"source": field.source.model_copy(update={"document_revision": "changed"})}
            )
        else:
            fields[index] = field.model_copy(
                update={
                    "conditions": [
                        field.conditions[0].model_copy(update={"description": "different"})
                    ]
                }
            )
        profile = profile.model_copy(
            update={"field_review": review.model_copy(update={"fields": fields})}
        )
    assert not profile_claim_bindings(profile, original_component, pointer="/abs_max/vin")


def test_missing_pointer_does_not_fall_back_to_a_nearby_field():
    profile = ready_profile()
    assert not profile_claim_bindings(profile, component(profile), pointer="/abs_max/vout")


@pytest.mark.parametrize("topic", ["abs_max", "boot"])
def test_actual_approved_locator_payload_preserves_bound_parameters_through_catalog(topic):
    context = _context()
    try:
        args = {"refdes": "U8", "topic": topic, "limit": 50}
        result = locate_component_evidence(
            context.design,
            context.validation_targets,
            context.index,
            context.document_report,
            LocateComponentEvidenceInput(**args),
        )
        bindings = [b for hit in result.hits for b in hit.claim_bindings]
        assert bindings and all(b.object_id == "U8" for b in bindings)
        returned_tokens = evidence_locator_tokens(result)
        assert all(token in returned_tokens for b in bindings for token in b.source_tokens)
        facts = tool_claim_catalog(
            "locate_component_evidence",
            result.model_dump(mode="json"),
            arguments=args,
            scope_id="run:turn",
            call_id="locator",
            project_id="public-fixture",
            known_objects={("project", "public-fixture"), ("component", "U8")},
        )
        parameters = [f for f in facts if f.kind == "approved_parameter"]
        assert parameters
        for binding in bindings:
            actual = next(f for f in parameters if f.property_key == binding.property_key)
            assert actual.model_dump(exclude={"id", "scope_id", "call_id"}) == binding.model_dump()
        if topic == "boot":
            assert any(f.property_key.startswith("profile/pins/") for f in parameters)
        # Binding metadata is serialized with the dispatched tool payload;
        # the adapter receives no access to the context/index/profile objects.
        assert "claim_bindings" in json.dumps(result.model_dump(mode="json"))
    finally:
        close_workbench_context(context)
