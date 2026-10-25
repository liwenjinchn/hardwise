"""Real HTTP/Runner boundary using an injected SDK constructor, never a provider."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from hardwise.workbench.chat import WorkbenchChatService, FakeWorkbenchAnthropic
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(
        "socket.socket.connect",
        lambda *args: (_ for _ in ()).throw(AssertionError("No provider sockets allowed")),
    )
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SYNTHETIC_KEY_SENTINEL")
    monkeypatch.setenv(
        "ANTHROPIC_BASE_URL",
        "https://URL_USER:URL_SECRET@relay.invalid/private/PATH_SECRET?key=QUERY_SECRET#FRAGMENT_SECRET",
    )
    monkeypatch.setenv("HARDWISE_MODEL_NORMAL", "synthetic-model")
    calls = []

    class Recorder:
        def __init__(self):
            self.fake = FakeWorkbenchAnthropic()
            self.messages = self

        def create(self, **kwargs):
            calls.append(kwargs)
            return self.fake.messages.create(**kwargs)

    constructor = Mock(side_effect=lambda **kwargs: Recorder())
    monkeypatch.setattr("anthropic.Anthropic", constructor)
    root = Path("tests/fixtures/allegro")
    context = build_workbench_context(
        netlist_path=root / "l78_regulator.net",
        bom_path=root / "l78_regulator_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    service = WorkbenchChatService(context, mode="real")
    try:
        with TestClient(
            create_workbench_app(context, service, auto_datasheet_candidates=False)
        ) as client:
            yield client, constructor, calls, service
    finally:
        close_workbench_context(context)


def test_disclosure_and_missing_stale_requests_never_construct_sdk(configured):
    client, constructor, calls, _ = configured
    before = client.get("/api/workbench/state").json()
    description = client.get("/api/workbench/ai-disclosure")
    data = description.json()
    assert data["available"] and data["mode"] == "real"
    assert data["destination"] == "https://relay.invalid" and data["model"] == "synthetic-model"
    assert len(data["data_categories"]) == 4
    for secret in [
        "SYNTHETIC_KEY_SENTINEL",
        "URL_USER",
        "URL_SECRET",
        "PATH_SECRET",
        "QUERY_SECRET",
        "FRAGMENT_SECRET",
    ]:
        assert secret not in description.text
    assert client.post("/api/workbench/chat", json={"question": "Explain U1"}).status_code == 428
    assert (
        client.post(
            "/api/workbench/chat", json={"question": "Explain U1", "disclosure_id": "stale"}
        ).status_code
        == 409
    )
    constructor.assert_not_called()
    assert calls == []
    assert client.get("/api/workbench/state").json() == before


def test_confirmed_actual_runner_sends_history_and_tool_result_without_changing_machine(configured):
    client, constructor, calls, _ = configured
    before = client.get("/api/workbench/state").json()
    receipt = client.get("/api/workbench/ai-disclosure").json()["disclosure_id"]
    response = client.post(
        "/api/workbench/chat",
        json={
            "question": "查看 U1 的证据链",
            "selected_refdes": "U1",
            "history": [{"role": "user", "content": "synthetic short prior context"}],
            "disclosure_id": receipt,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["trace"] and len(calls) >= 2
    sent = json.dumps(calls, ensure_ascii=False, default=str)
    assert "synthetic short prior context" in sent and "tool_result" in sent
    assert client.get("/api/workbench/state").json() == before
    constructor.assert_called_once()
    settings = constructor.call_args.kwargs
    assert settings["api_key"] == "SYNTHETIC_KEY_SENTINEL"
    assert settings["auth_token"] == ""
    assert (
        settings["base_url"]
        == "https://URL_USER:URL_SECRET@relay.invalid/private/PATH_SECRET?key=QUERY_SECRET#FRAGMENT_SECRET"
    )
    again = client.post(
        "/api/workbench/chat", json={"question": "板上有没有 U999?", "disclosure_id": receipt}
    )
    assert again.status_code == 200
    constructor.assert_called_once()


def test_destination_model_key_changes_invalidate_before_initialization(configured, monkeypatch):
    client, constructor, _, _ = configured
    old = client.get("/api/workbench/ai-disclosure").json()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://second.invalid/v1")
    monkeypatch.setenv("HARDWISE_MODEL_NORMAL", "second-synthetic-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SECOND_SYNTHETIC_KEY")
    r = client.post(
        "/api/workbench/chat", json={"question": "U1", "disclosure_id": old["disclosure_id"]}
    )
    assert r.status_code == 409
    constructor.assert_not_called()
    current = client.get("/api/workbench/ai-disclosure").json()
    assert (
        current["destination"] == "https://second.invalid"
        and current["model"] == "second-synthetic-model"
    )
    assert current["disclosure_id"] != old["disclosure_id"]
    assert (
        client.post(
            "/api/workbench/chat",
            json={"question": "板上有没有 U999?", "disclosure_id": current["disclosure_id"]},
        ).status_code
        == 200
    )
    assert constructor.call_args.kwargs["base_url"] == "https://second.invalid/v1"
    assert constructor.call_args.kwargs["api_key"] == "SECOND_SYNTHETIC_KEY"
    monkeypatch.setenv(
        "ANTHROPIC_BASE_URL",
        "https://URL_USER:URL_SECRET@relay.invalid/private/PATH_SECRET?key=QUERY_SECRET#FRAGMENT_SECRET",
    )
    assert (
        client.post(
            "/api/workbench/chat", json={"question": "U1", "disclosure_id": old["disclosure_id"]}
        ).status_code
        == 409
    )


def test_import_changes_receipt_and_rejects_old_confirmation(configured):
    client, constructor, _, _ = configured
    old = client.get("/api/workbench/ai-disclosure").json()
    root = Path("tests/fixtures/allegro")
    r = client.post(
        "/api/workbench/import",
        files={
            "netlist": ("new.net", (root / "l78_regulator.net").read_bytes()),
            "bom": ("new.csv", (root / "l78_regulator_bom.csv").read_bytes()),
        },
    )
    assert r.status_code == 200
    new = client.get("/api/workbench/ai-disclosure").json()
    assert new["context_id"] != old["context_id"]
    assert (
        client.post(
            "/api/workbench/chat", json={"question": "U1", "disclosure_id": old["disclosure_id"]}
        ).status_code
        == 409
    )
    constructor.assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "file:///SYNTHETIC_SECRET",
        "https://",
        "https://example.invalid:99999/private-secret",
        "https://example.invalid/\nSECRET",
    ],
)
def test_invalid_destination_is_unavailable_and_never_echoed(configured, monkeypatch, url):
    client, constructor, _, _ = configured
    monkeypatch.setenv("ANTHROPIC_BASE_URL", url)
    r = client.get("/api/workbench/ai-disclosure")
    assert not r.json()["available"]
    assert "SECRET" not in r.text and "private-secret" not in r.text
    assert client.post("/api/workbench/chat", json={"question": "U1"}).status_code == 503
    constructor.assert_not_called()


def test_offline_capture_does_not_freeze_live_receipt_or_credentials(configured):
    client, constructor, _, _ = configured
    descriptor = client.get("/api/workbench/ai-disclosure").json()
    state = client.get("/api/workbench/state").json()
    ids = state["review_decisions"]
    response = client.get(
        "/api/workbench/offline-report",
        params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
    )
    assert response.status_code == 200
    for secret in [
        descriptor["disclosure_id"],
        "SYNTHETIC_KEY_SENTINEL",
        "QUERY_SECRET",
        "URL_SECRET",
    ]:
        assert secret not in response.text
    constructor.assert_not_called()


@pytest.mark.parametrize("name", ["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS"])
def test_auxiliary_credentials_change_invalidates_receipt(configured, monkeypatch, name):
    client, constructor, _, _ = configured
    old = client.get("/api/workbench/ai-disclosure").json()
    monkeypatch.setenv(
        name, "X-Test: SYNTHETIC_HEADER" if name.endswith("HEADERS") else "SYNTHETIC_AUTH"
    )
    new = client.get("/api/workbench/ai-disclosure").json()
    assert new["disclosure_id"] != old["disclosure_id"]
    assert "SYNTHETIC_AUTH" not in json.dumps(new)
    assert "SYNTHETIC_HEADER" not in json.dumps(new)
    assert (
        client.post(
            "/api/workbench/chat", json={"question": "U1", "disclosure_id": old["disclosure_id"]}
        ).status_code
        == 409
    )
    constructor.assert_not_called()


def test_sensitive_model_identifier_disables_sending(configured, monkeypatch):
    client, constructor, _, _ = configured
    monkeypatch.setenv("HARDWISE_MODEL_NORMAL", "SYNTHETIC_KEY_SENTINEL")
    response = client.get("/api/workbench/ai-disclosure")
    assert not response.json()["available"]
    assert "SYNTHETIC_KEY_SENTINEL" not in response.text
    assert client.post("/api/workbench/chat", json={"question": "U1"}).status_code == 503
    constructor.assert_not_called()


def test_disclosure_version_invalidates_receipt(configured, monkeypatch):
    client, constructor, _, _ = configured
    old = client.get("/api/workbench/ai-disclosure").json()
    monkeypatch.setattr("hardwise.workbench.ai_disclosure.DISCLOSURE_VERSION", "synthetic.v2")
    assert (
        client.post(
            "/api/workbench/chat", json={"question": "U1", "disclosure_id": old["disclosure_id"]}
        ).status_code
        == 409
    )
    constructor.assert_not_called()


def test_injected_client_without_declared_destination_is_unavailable(configured):
    _, _, _, service = configured
    other = WorkbenchChatService(service.context, mode="real", client=FakeWorkbenchAnthropic())
    assert not other.disclosure().available
    assert other.disclosure().destination is None


def test_observed_configuration_round_trip_does_not_resurrect_old_receipt(configured, monkeypatch):
    client, constructor, _, _ = configured
    old = client.get("/api/workbench/ai-disclosure").json()
    from hardwise.workbench.ai_config import ProviderConfig

    original = ProviderConfig.current().base_url
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://temporary.invalid")
    middle = client.get("/api/workbench/ai-disclosure").json()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", original)
    restored = client.get("/api/workbench/ai-disclosure").json()
    assert old["destination"] == restored["destination"]
    assert len({old["disclosure_id"], middle["disclosure_id"], restored["disclosure_id"]}) == 3
    assert (
        client.post(
            "/api/workbench/chat", json={"question": "U1", "disclosure_id": old["disclosure_id"]}
        ).status_code
        == 409
    )
    constructor.assert_not_called()
