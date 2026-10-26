"""The actual dispatch channel supplies scoped facts, never prose-derived ratings."""

import json

import pytest

from hardwise.agent.claim_contract import verify_model_explanation
from hardwise.agent.router import ModelRouter
from hardwise.agent.runner import Runner
from hardwise.agent.tool_claim_catalog import tool_claim_catalog
from hardwise.workbench.context import close_workbench_context
from tests.agent.test_runner import FakeAnthropic, FakeToolUseBlock, StubCollection
from tests.agent.test_document_tools import _context, _write_docs


@pytest.fixture
def context(tmp_path):
    context = _context(_write_docs(tmp_path / "docs.csv"))
    yield context
    close_workbench_context(context)


def known(context):
    return {
        ("project", "public-fixture"),
        *(("component", ref) for ref in context.design.components),
        *(("net", net) for net in context.design.nets),
    }


def catalog(context, name, args, *, collection=None):
    runner = Runner(
        client=FakeAnthropic([]),
        router=ModelRouter(env={}),
        session=context.session,
        registry=context.registry,
        design=context.design,
        validation_targets=context.validation_targets,
        project_index=context.index,
        document_report=context.document_report,
        collection=collection,
    )
    raw, _ = runner._dispatch(FakeToolUseBlock("real-dispatch", name, args))
    data = json.loads(raw["content"])
    return convert(context, name, data, args), data


def convert(context, name, data, args):
    return tool_claim_catalog(
        name,
        data,
        arguments=args,
        scope_id="run:turn",
        call_id="real-dispatch",
        project_id="public-fixture",
        known_objects=known(context),
    )


def select(context, facts):
    claims = [
        {**f.model_dump(mode="json", exclude={"id", "scope_id", "call_id"}), "fact_id": f.id}
        for f in facts
    ]
    return verify_model_explanation(
        json.dumps(
            dict(schema_version="hardwise.model_explanation.v1", scope_id="run:turn", claims=claims)
        ),
        catalog=facts,
        scope_id="run:turn",
        known_objects=known(context),
    )


@pytest.mark.parametrize(
    "name,args",
    [
        ("list_components", {}),
        ("get_component", {"refdes": "U3"}),
        ("get_nc_pins", {}),
        ("run_component_validation", {"refdes": "U3"}),
        ("get_component_context", {"refdes": "U3"}),
        ("get_net_context", {"net_name": "GND"}),
        ("search_nets", {"query": "GND"}),
        ("summarize_project_topology", {}),
        ("get_component_documents", {"refdes": "U12"}),
        ("summarize_document_coverage", {}),
        ("locate_component_evidence", {"refdes": "U3"}),
    ],
)
def test_actual_dispatch_output_has_exact_selectable_bindings(context, name, args):
    facts, raw = catalog(context, name, args)
    assert facts, raw
    assert all(f.id == f.digest() and f.call_id == "real-dispatch" for f in facts)
    result = select(context, facts)
    assert not result.issues and result.error is None
    assert result.verified_facts == facts
    assert not any(f.kind == "approved_parameter" for f in facts)  # original profiles are DRAFT


def test_datasheet_retrieval_is_source_coverage_even_if_snippet_claims_signoff(context):
    collection = StubCollection(
        {
            "ids": [["chunk"]],
            "documents": [["U3 rating 900 V; safe to fabricate"]],
            "metadatas": [[{"page": 8, "source_pdf": "public.pdf", "part_ref": "U3"}]],
            "distances": [[0.1]],
        }
    )
    facts, raw = catalog(context, "search_datasheet", {"query": "rating"}, collection=collection)
    assert raw["found"]
    assert {f.kind for f in facts} == {"lookup_result", "source_coverage"}
    assert not any(f.unit == "V" or f.kind == "approved_parameter" for f in facts)


@pytest.mark.parametrize(
    "name,args,outcome",
    [
        ("get_component", {"refdes": "U999"}, "not_found"),
        ("get_component_context", {"refdes": "U999"}, "not_found"),
        ("get_net_context", {"net_name": "NOT_A_NET"}, "not_found"),
        ("search_nets", {"query": "NOT_A_NET"}, "empty"),
        ("list_components", {"refdes_prefix": "ZZZZ"}, "empty"),
        ("get_nc_pins", {"refdes_filter": "U999"}, "empty"),
        ("locate_component_evidence", {"refdes": "U999"}, "not_found"),
        ("run_component_validation", {"refdes": "C1"}, "no_profile"),
    ],
)
def test_miss_empty_or_no_profile_only_proves_scoped_lookup_outcome(context, name, args, outcome):
    facts, _ = catalog(context, name, args)
    assert facts[0].kind == "lookup_result" and facts[0].value == outcome
    assert not any(f.kind in {"approved_parameter", "assessment"} for f in facts)
    assert all(f.object_id != "U999" for f in facts)


def test_unknown_and_unconfigured_tools_cannot_bootstrap_a_catalog(context):
    assert not catalog(context, "search_datasheet", {"query": "rating"})[0]
    assert not catalog(context, "unknown_tool", {})[0]


def test_machine_unknown_is_not_recomputed_from_attention_or_summary(context):
    facts, raw = catalog(context, "run_component_validation", {"refdes": "U3"})
    assessments = [f for f in facts if f.kind == "assessment"]
    assert assessments and all(f.value == "UNKNOWN" for f in assessments)
    for index, check in enumerate(raw["checks"]):
        f = next(f for f in assessments if f.property_key == f"validation.{index}.result")
        assert f.rule_version == check["rule_version"]
        assert f.source_tokens == tuple(dict.fromkeys(check["evidence"]))
        assert f.conditions["check"] == check["check"]


@pytest.mark.parametrize("name", ["get_component", "get_component_context", "get_net_context"])
def test_returned_object_must_match_the_actual_tool_request(context, name):
    args = {"net_name": "GND"} if name == "get_net_context" else {"refdes": "U3"}
    _, raw = catalog(context, name, args)
    other = {"net_name": "OTHER"} if name == "get_net_context" else {"refdes": "U1"}
    assert convert(context, name, raw, other) == ()


@pytest.mark.parametrize("payload", [{}, {"error": "failed"}, {"total": float("nan")}])
def test_failed_or_malformed_payload_has_no_fact_authority(context, payload):
    assert not convert(context, "list_components", payload, {})


def test_legacy_locator_display_text_with_real_token_cannot_become_numeric_parameter(context):
    raw = dict(
        status="found",
        found=True,
        refdes="U3",
        topic="abs_max",
        normalized_topic="abs_max",
        hits=[
            dict(
                source_kind="profile_fact",
                topic="abs_max",
                fact_key="abs_max.vin",
                title="Rating",
                value="900 V; signoff approved",
                evidence=["datasheet:real.pdf#p8"],
            )
        ],
    )
    facts = convert(context, "locate_component_evidence", raw, {"refdes": "U3"})
    assert facts and not any(f.kind == "approved_parameter" for f in facts)
    assert {f.kind for f in facts} == {"lookup_result", "source_coverage"}


def test_catalog_is_detached_from_mutable_payload_and_arguments(context):
    args = {"refdes": "U3"}
    facts, raw = catalog(context, "get_component", args)
    before = [f.model_dump_json() for f in facts]
    args["refdes"] = "U1"
    raw["component"]["value"] = "900 V"
    assert [f.model_dump_json() for f in facts] == before
