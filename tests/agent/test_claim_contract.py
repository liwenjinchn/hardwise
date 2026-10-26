"""A real token or object cannot authorize mismatched electrical assertions."""

import json

import pytest
from pydantic import ValidationError

from hardwise.agent.claim_contract import (
    ClaimBinding,
    make_evidence_fact,
    verify_model_explanation,
)


def fact(**updates):
    data = dict(
        object_kind="component",
        object_id="U3",
        property_key="abs_max.input_voltage",
        kind="approved_parameter",
        value=20,
        unit="V",
        conditions={"reference_net": "GND", "mode": "dc"},
        conditions_status="explicit",
        source_tokens=("datasheet:public.pdf#p8",),
        rule_version=None,
    )
    data.update(updates)
    return make_evidence_fact(
        binding=ClaimBinding(**data), scope_id="current-run:turn-1", call_id="lookup-1"
    )


def claim(item):
    return {
        **item.model_dump(mode="json", exclude={"id", "scope_id", "call_id"}),
        "fact_id": item.id,
    }


def envelope(*claims, **updates):
    return {
        "schema_version": "hardwise.model_explanation.v1",
        "scope_id": "current-run:turn-1",
        "claims": list(claims),
        "requests": [],
        **updates,
    }


def check(data, *catalog):
    return verify_model_explanation(
        json.dumps(data, ensure_ascii=False),
        scope_id="current-run:turn-1",
        catalog=tuple(catalog),
        known_objects={("component", "U3"), ("component", "U1"), ("net", "GND")},
    )


def test_matching_claim_returns_only_server_fact_and_does_not_mutate_catalog():
    item = fact()
    before = item.model_dump_json()
    result = check(envelope(claim(item)), item)
    assert result.error is None and not result.issues
    assert result.verified_facts == (item,)
    assert item.model_dump_json() == before


@pytest.mark.parametrize(
    "updates",
    [
        {"object_id": "U1"},
        {"object_kind": "net", "object_id": "GND"},
        {"property_key": "abs_max.output_current"},
        {"value": 900},
        {"value": "20"},
        {"value": True},
        {"unit": "A"},
        {"unit": None},
        {"conditions": {"reference_net": "AGND", "mode": "dc"}},
        {"conditions": {"reference_net": "GND", "mode": "sleep"}},
        {"conditions": {}, "conditions_status": "not_required"},
        {"source_tokens": ["datasheet:other.pdf#p8"]},
        {"rule_version": "invented-rule"},
        {"kind": "observation"},
    ],
)
def test_true_fact_id_and_token_cannot_authorize_mismatched_binding(updates):
    item = fact()
    altered = {**claim(item), **updates}
    result = check(envelope(altered), item)
    assert not result.verified_facts
    assert result.issues[0].code == "binding_mismatch"


def test_missing_fact_with_genuine_citation_is_not_verified():
    item = fact()
    data = claim(item)
    data["fact_id"] = "FACT-" + "0" * 64
    result = check(envelope(data), item)
    assert result.issues[0].code == "unknown_fact" and not result.verified_facts


@pytest.mark.parametrize("scope", ["previous-run:turn-1", "current-run:previous-turn"])
def test_prior_run_or_turn_cannot_borrow_current_facts(scope):
    item = fact()
    result = check(envelope(claim(item), scope_id=scope), item)
    assert result.error == "stale_scope" and not result.verified_facts


def test_unknown_applicability_is_not_upgraded_to_verified():
    item = fact(kind="observation", conditions_status="unknown", conditions={})
    result = check(envelope(claim(item)), item)
    assert result.issues[0].code == "unknown_conditions" and not result.verified_facts


def test_mixed_valid_invalid_and_duplicate_claims_do_not_borrow_authority():
    item = fact()
    wrong = {**claim(item), "fact_id": "FACT-" + "0" * 64, "value": 900}
    result = check(envelope(claim(item), wrong, claim(item)), item)
    assert result.verified_facts == (item,)
    assert [i.code for i in result.issues] == ["unknown_fact", "duplicate_claim"]
    assert "900" not in result.model_dump_json()


@pytest.mark.parametrize(
    "data",
    [
        "整板通过，可以直接投板。",
        {"answer": "Safe to fabricate"},
        envelope(answer="All checks passed"),
        envelope(schema_version="hardwise.model_explanation.v999"),
        envelope(requests=[{"object_kind": "component", "object_id": "U3", "topic": "signoff"}]),
        envelope(claims=[{"fact_id": "made-up"}]),
    ],
)
def test_unstructured_prose_verdicts_and_invalid_fields_are_not_echoed(data):
    result = check(data)
    assert result.error == "invalid_envelope" and not result.verified_facts
    assert "fabricate" not in result.model_dump_json()
    assert "投板" not in result.model_dump_json()


@pytest.mark.parametrize(
    "raw",
    [
        '{"scope_id":"old","scope_id":"new"}',
        '{"x":{"value":1,"value":2}}',
        '{"value":NaN}',
        '{"value":Infinity}',
        '"' + "x" * 128_001 + '"',
        "[" * 1100 + "]" * 1100,
    ],
)
def test_malformed_ambiguous_nonfinite_or_oversized_json_fails_closed(raw):
    result = verify_model_explanation(
        raw, scope_id="current-run:turn-1", catalog=(), known_objects=set()
    )
    assert result.error == "invalid_envelope"


@pytest.mark.parametrize("kind", ["mutated", "duplicate", "foreign_scope", "unknown_object"])
def test_catalog_cannot_be_substituted_or_mutated_after_registration(kind):
    item = fact()
    catalog = [item]
    if kind == "mutated":
        item.conditions["mode"] = "sleep"
    elif kind == "duplicate":
        catalog.append(item)
    elif kind == "foreign_scope":
        item = item.model_copy(update={"scope_id": "previous"})
        catalog = [item]
    else:
        catalog = [fact(object_id="U999")]
    result = check(envelope(claim(item)), *catalog)
    assert result.error == "invalid_catalog" and not result.verified_facts


def test_evidence_fact_copies_nested_source_containers():
    binding = ClaimBinding(**fact().model_dump(exclude={"id", "scope_id", "call_id"}))
    item = make_evidence_fact(binding=binding, scope_id="turn", call_id="lookup")
    before = item.model_dump_json()
    binding.conditions["mode"] = "sleep"
    assert item.model_dump_json() == before


def test_only_known_objects_can_receive_unverified_follow_up_requests():
    data = envelope(
        requests=[
            {"object_kind": "component", "object_id": "U3", "topic": "operating_condition"},
            {"object_kind": "component", "object_id": "U999", "topic": "rating"},
        ]
    )
    result = check(data)
    assert not result.verified_facts and result.error is None
    assert [r.object_id for r in result.requests] == ["U3"]


@pytest.mark.parametrize(
    "updates",
    [
        {"conditions_status": "unknown"},
        {"source_tokens": ()},
        {"value": float("inf")},
        {"conditions": {"temperature": float("nan")}},
        {"conditions": {}, "conditions_status": "explicit"},
    ],
)
def test_catalog_parameter_requires_sources_applicability_and_finite_data(updates):
    with pytest.raises(ValidationError):
        fact(**updates)


def test_machine_unknown_is_preserved_and_cannot_be_promoted_to_pass():
    item = fact(
        kind="assessment",
        property_key="input_voltage.result",
        value="UNKNOWN",
        unit=None,
        rule_version="3.profile-review1",
    )
    assert check(envelope(claim(item)), item).verified_facts[0].value == "UNKNOWN"
    result = check(envelope({**claim(item), "value": "PASS"}), item)
    assert not result.verified_facts and result.issues[0].code == "binding_mismatch"


def test_scope_and_tool_call_are_both_part_of_fact_identity():
    binding = ClaimBinding(**fact().model_dump(exclude={"id", "scope_id", "call_id"}))
    ids = {
        make_evidence_fact(binding=binding, scope_id=scope, call_id=call).id
        for scope, call in [("turn-1", "call-1"), ("turn-2", "call-1"), ("turn-1", "call-2")]
    }
    assert len(ids) == 3
