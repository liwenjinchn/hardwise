from pathlib import Path

from fastapi.testclient import TestClient

from hardwise.workbench.api_contracts import ImportResponse
from hardwise.workbench.chat import ChatResponse
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app
from hardwise.workbench.view_model import ComponentDetail, WorkbenchState


class _ChatService:
    datasheet_search_enabled = False

    def __init__(self) -> None:
        self.context = None

    def ask(self, request) -> ChatResponse:
        return ChatResponse(answer=request.question, mode="fake")


def _client() -> TestClient:
    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_path=Path("tests/fixtures/allegro/l78_regulator_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
        generated_at="2026-05-30T00:00:00+00:00",
    )
    return TestClient(create_workbench_app(context, _ChatService()))  # type: ignore[arg-type]


def test_core_json_endpoints_reference_named_openapi_schemas() -> None:
    client = _client()
    schema = client.get("/openapi.json").json()

    expected = {
        ("/api/workbench/state", "get"): "WorkbenchState",
        ("/api/workbench/components/{refdes}", "get"): "ComponentDetail",
        ("/api/workbench/import", "post"): "ImportResponse",
        ("/api/workbench/chat", "post"): "ChatResponse",
    }
    for (path, method), model_name in expected.items():
        response_schema = schema["paths"][path][method]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert response_schema["$ref"] == f"#/components/schemas/{model_name}"


def test_state_component_and_import_payloads_validate_against_contracts() -> None:
    client = _client()

    state_payload = client.get("/api/workbench/state").json()
    state = WorkbenchState.model_validate(state_payload)
    refdes = state.selected_refdes or state.queue[0].refdes
    ComponentDetail.model_validate(client.get(f"/api/workbench/components/{refdes}").json())

    with (
        Path("tests/fixtures/allegro/l78_regulator.net").open("rb") as netlist,
        Path("tests/fixtures/allegro/l78_regulator_bom.csv").open("rb") as bom,
    ):
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("l78_regulator.net", netlist, "text/plain"),
                "bom": ("l78_regulator_bom.csv", bom, "text/csv"),
            },
        )

    assert response.status_code == 200, response.text
    imported = ImportResponse.model_validate(response.json())
    assert imported.ok is True
    assert imported.project.name

    chat_response = client.post("/api/workbench/chat", json={"question": "contract smoke"})
    assert chat_response.status_code == 200
    chat = ChatResponse.model_validate(chat_response.json())
    assert chat.answer == "contract smoke"
