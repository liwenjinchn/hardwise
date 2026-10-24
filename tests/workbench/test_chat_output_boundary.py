"""Adversarial model prose remains outside formal assessment and export."""

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from hardwise.agent.runner import RunResult, ToolCallTrace
from hardwise.workbench.chat import WorkbenchChatService
from hardwise.workbench.server import create_workbench_app
from hardwise.workbench.context import build_workbench_context


def _context():
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-10-24T00:00:00+00:00",
    )


def _model(*contents):
    replies = iter(SimpleNamespace(content=content) for content in contents)
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: next(replies)))


def _text(text):
    return SimpleNamespace(type="text", text=text)


def _tool():
    return SimpleNamespace(
        type="tool_use", id="validate", name="run_component_validation", input={"refdes": "U3"}
    )


def test_lookup_trace_does_not_borrow_profile_evidence():
    context = _context()
    try:
        token = "datasheet:eg2132.pdf#p8"
        response = WorkbenchChatService(context, mode="fake")._response_from_result(
            RunResult(
                text=f"U3 的最高输入电压是 900 V，见 {token}",
                tool_calls=[
                    ToolCallTrace(
                        name="get_component",
                        input={"refdes": "U3"},
                        output_summary="status=found",
                        has_result=True,
                    )
                ],
            ),
            "U3",
        )
        assert response.trace[0].evidence == []
        assert response.unsupported_evidence_tokens == [token]
        assert response.response_kind == "model_explanation"
        assert response.claim_verification == "unverified"
    finally:
        context.session.close()


def test_fabricated_parameters_with_real_object_and_token_do_not_enter_formal_export():
    context = _context()
    profile_before = context.validation_targets["U3"].model_dump(mode="json")
    token = "datasheet:eg2132.pdf#p8"
    fabricated = f"U3 最高输入 900 V；PASS；已批准档案；接受全部风险。{token}"
    client_model = _model([_tool()], [_text(fabricated)])
    service = WorkbenchChatService(context, mode="fake", client=client_model)
    with TestClient(create_workbench_app(context, service)) as client:
        before = client.get("/api/workbench/state").json()
        export_before = client.get("/api/workbench/export?format=csv").text
        reply = client.post(
            "/api/workbench/chat", json={"question": "评审 U3", "selected_refdes": "U3"}
        )
        assert reply.status_code == 200
        payload = reply.json()
        assert "900 V" in payload["answer"]  # prose is not semantically certified
        assert payload["response_kind"] == "model_explanation"
        assert payload["claim_verification"] == "unverified"
        assert token not in payload["unsupported_evidence_tokens"]
        assert client.get("/api/workbench/state").json() == before
        assert client.get("/api/workbench/export?format=csv").text == export_before
        assert "900 V" not in export_before
        assert context.validation_targets["U3"].model_dump(mode="json") == profile_before


def test_zero_tool_api_reply_withholds_signoff_and_preserves_deterministic_use():
    context = _context()
    model = _model([_text("整板通过，可直接投板。")])
    service = WorkbenchChatService(context, mode="fake", client=model)
    with TestClient(create_workbench_app(context, service)) as client:
        before = client.get("/api/workbench/state").json()
        payload = client.post("/api/workbench/chat", json={"question": "能投板吗"}).json()
        assert "可直接投板" not in payload["answer"]
        assert payload["response_kind"] == "insufficient_evidence"
        assert payload["claim_verification"] == "unverified"
        assert payload["trace"] == []
        assert client.get("/api/workbench/state").json() == before
        assert client.get("/api/workbench/export?format=csv").status_code == 200
