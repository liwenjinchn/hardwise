"""Adversarial envelopes traverse real dispatch, Runner and HTTP projection."""

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from hardwise.agent.claim_turn import CATALOG_PREFIX
from hardwise.workbench.chat import WorkbenchChatService
from hardwise.workbench.server import create_workbench_app
from tests.workbench.test_chat_output_boundary import _context, _text


class CatalogModel:
    def __init__(self, calls, mutate=None):
        self.calls = calls
        self.mutate = mutate
        self.previous = None

    def create(self, **kwargs):
        content = kwargs["messages"][-1]["content"]
        if isinstance(content, str):
            blocks = [
                SimpleNamespace(type="tool_use", id=f"call-{i}", name=name, input=args)
                for i, (name, args) in enumerate(self.calls)
            ]
            return SimpleNamespace(content=blocks)
        directory = next(b["text"] for b in content if b.get("type") == "text")
        data = json.loads(directory[len(CATALOG_PREFIX) :])
        claims = [
            {
                **{k: v for k, v in f.items() if k not in {"id", "scope_id", "call_id"}},
                "fact_id": f["id"],
            }
            for f in data["facts"][:128]
        ]
        envelope = dict(
            schema_version="hardwise.model_explanation.v1",
            scope_id=data["scope_id"],
            claims=claims,
            requests=[],
        )
        if self.mutate:
            envelope = self.mutate(envelope)
        return SimpleNamespace(
            content=[_text(envelope if isinstance(envelope, str) else json.dumps(envelope))]
        )


NEGATIVE_CALLS = [
    ("get_component", {"refdes": "U999"}),
    ("get_component_context", {"refdes": "U999"}),
    ("get_net_context", {"net_name": "missing_net"}),
    ("search_nets", {"query": "missing_net"}),
    ("list_components", {"prefix": "XYZ"}),
    ("get_nc_pins", {"refdes": "U999"}),
    ("run_component_validation", {"refdes": "U999"}),
    ("locate_component_evidence", {"refdes": "U999"}),
    ("search_datasheet", {"query": "rating"}),
    ("get_component_documents", {"refdes": "U999"}),
    ("summarize_document_coverage", {}),
    ("get_component", {"refdes": "U1"}),
    ("summarize_project_topology", {}),
    ("run_component_validation", {"refdes": "U3"}),
]


@pytest.mark.parametrize("call", NEGATIVE_CALLS)
def test_any_tool_result_cannot_authorize_free_signoff(call):
    context = _context()
    model = CatalogModel([call], lambda _: "FORGED_SIGNOFF 可以直接投板，900 V")
    service = WorkbenchChatService(context, mode="fake", client=SimpleNamespace(messages=model))
    with TestClient(create_workbench_app(context, service)) as client:
        before = client.get("/api/workbench/state").json()
        csv = client.get("/api/workbench/export?format=csv").text
        response = client.post("/api/workbench/chat", json={"question": "review"}).json()
        assert response["explanation_review"]["error"] == "invalid_envelope"
        assert response["response_kind"] == "insufficient_evidence"
        assert "FORGED_SIGNOFF" not in json.dumps(response)
        assert client.get("/api/workbench/state").json() == before
        assert client.get("/api/workbench/export?format=csv").text == csv


@pytest.mark.parametrize(
    "dimension,bad",
    [
        ("object_id", "U1"),
        ("property_key", "invented.rating"),
        ("value", "FORGED_900"),
        ("unit", "A"),
        ("conditions", {"mode": "FORGED_SLEEP"}),
        ("source_tokens", ["datasheet:forged.pdf#p1"]),
        ("rule_version", "forged-v999"),
    ],
)
def test_mixed_claims_only_render_matching_server_facts(dimension, bad):
    def mutate(envelope):
        # Retain genuine facts, then attempt to reuse a real ID with a false binding.
        forged = deepcopy(envelope["claims"][0])
        forged[dimension] = bad
        envelope["claims"] = [forged, *envelope["claims"][1:]]
        return envelope

    context = _context()
    model = CatalogModel([("get_component", {"refdes": "U3"})], mutate)
    service = WorkbenchChatService(context, mode="fake", client=SimpleNamespace(messages=model))
    with TestClient(create_workbench_app(context, service)) as client:
        payload = client.post("/api/workbench/chat", json={"question": "review"}).json()
        review = payload["explanation_review"]
        assert review["issues"][0]["code"] == "binding_mismatch"
        assert review["verified_facts"]
        assert all(f["property_key"] != "lookup.get_component" for f in review["verified_facts"])
        assert "FORGED" not in json.dumps(payload) and "forged" not in json.dumps(payload)


def test_previous_turn_envelope_is_rejected_and_negative_query_is_diagnostic():
    context = _context()
    saved = []

    def replay(envelope):
        if not saved:
            saved.append(deepcopy(envelope))
        return saved[0]

    model = CatalogModel([("get_component", {"refdes": "U999"})], replay)
    service = WorkbenchChatService(context, mode="fake", client=SimpleNamespace(messages=model))
    with TestClient(create_workbench_app(context, service)) as client:
        first = client.post("/api/workbench/chat", json={"question": "missing?"}).json()
        assert first["response_kind"] == "structured_explanation"
        assert "没有找到该对象" in first["answer"]
        assert "⟨?U999⟩" in first["answer"]
        second = client.post("/api/workbench/chat", json={"question": "repeat"}).json()
        assert second["explanation_review"]["error"] == "stale_scope"
        assert second["response_kind"] == "insufficient_evidence"


@pytest.mark.parametrize(
    "dimension,bad",
    [
        (None, None),
        ("value", 900.0),
        ("unit", "A"),
        ("object_id", "U3"),
        ("conditions", {"mode": "sleep"}),
        ("source_tokens", ["datasheet:other.pdf#p1"]),
    ],
)
def test_actual_approved_parameter_survives_only_with_original_binding(dimension, bad):
    from tests.agent.test_evidence_locator import _context as approved_context

    def mutate(envelope):
        parameter = next(c for c in envelope["claims"] if c["kind"] == "approved_parameter")
        envelope["claims"] = [parameter]
        if dimension:
            parameter[dimension] = bad
        return envelope

    context = approved_context()  # Explicit synthetic approval, never production approval.
    profile_before = context.validation_targets["U8"].model_dump(mode="json")
    model = CatalogModel(
        [("locate_component_evidence", {"refdes": "U8", "topic": "abs_max"})], mutate
    )
    service = WorkbenchChatService(context, mode="fake", client=SimpleNamespace(messages=model))
    with TestClient(create_workbench_app(context, service)) as client:
        before = client.get("/api/workbench/state").json()
        payload = client.post("/api/workbench/chat", json={"question": "rating"}).json()
        review = payload["explanation_review"]
        if dimension:
            assert not review["verified_facts"]
            assert review["issues"][0]["code"] == "binding_mismatch"
            assert payload["response_kind"] == "insufficient_evidence"
        else:
            (fact,) = review["verified_facts"]
            assert fact["unit"] == "V"
            assert fact["conditions"]["source"] and fact["conditions"]["approval"]
            assert "适用条件" in payload["answer"]
            assert payload["response_kind"] == "structured_explanation"
        assert client.get("/api/workbench/state").json() == before
        assert context.validation_targets["U8"].model_dump(mode="json") == profile_before


@pytest.mark.parametrize("attack", ["duplicate", "unknown", "extra", "duplicate_key", "requests"])
def test_bounded_envelope_failures_and_followups(attack):
    def mutate(envelope):
        if attack == "duplicate":
            envelope["claims"] = [envelope["claims"][0]] * 2
        elif attack == "unknown":
            envelope["claims"] = [envelope["claims"][0]]
            envelope["claims"][0]["fact_id"] = "FACT-" + "0" * 64
        elif attack == "extra":
            envelope["signoff"] = "FORGED_SIGNOFF"
        elif attack == "duplicate_key":
            return json.dumps(envelope)[:-1] + ',"claims":[]}'
        else:
            envelope["claims"] = []
            envelope["requests"] = [
                dict(object_kind="component", object_id="U3", topic="rating"),
                dict(object_kind="component", object_id="U999", topic="rating"),
            ]
        return envelope

    context = _context()
    model = CatalogModel([("get_component", {"refdes": "U3"})], mutate)
    service = WorkbenchChatService(context, mode="fake", client=SimpleNamespace(messages=model))
    with TestClient(create_workbench_app(context, service)) as client:
        payload = client.post("/api/workbench/chat", json={"question": "review"}).json()
        review = payload["explanation_review"]
        if attack == "duplicate":
            assert len(review["verified_facts"]) == 1
            assert review["issues"][0]["code"] == "duplicate_claim"
        elif attack == "unknown":
            assert not review["verified_facts"]
            assert review["issues"][0]["code"] == "unknown_fact"
        elif attack == "requests":
            assert not review["verified_facts"]
            assert review["requests"] == [
                dict(object_kind="component", object_id="U3", topic="rating")
            ]
            assert "待核补资料建议" in payload["answer"]
        else:
            assert review["error"] == "invalid_envelope"
            assert "FORGED_SIGNOFF" not in json.dumps(payload)
