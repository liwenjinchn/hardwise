"""Real-mode deterministic review works without credentials or a model connection."""

import copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from hardwise.cli import app as cli_app
from hardwise.workbench.chat import ChatRequest, WorkbenchChatService
from hardwise.workbench.chat_fake_client import FakeWorkbenchAnthropic
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path(__file__).parents[2]


@pytest.fixture(autouse=True)
def no_user_credentials(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda **kwargs: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("DATASHEETS_API_KEY", raising=False)


def context():
    return build_workbench_context(
        netlist_path=ROOT / "tests/fixtures/allegro/l78_regulator.net",
        bom_path=ROOT / "tests/fixtures/allegro/l78_regulator_bom.csv",
        profiles=ROOT / "data/datasheet_profiles",
    )


def create(path, client=None):
    ctx = context()
    service = WorkbenchChatService(ctx, mode="real", client=client)
    return create_workbench_app(ctx, service, review_db=path, auto_datasheet_candidates=False)


def test_real_cli_dry_run_never_constructs_model_client(monkeypatch):
    constructor = Mock(side_effect=AssertionError("Model client must be deferred"))
    monkeypatch.setattr(anthropic, "Anthropic", constructor)
    result = CliRunner().invoke(
        cli_app,
        [
            "serve-workbench",
            str(ROOT / "tests/fixtures/allegro/l78_regulator.net"),
            str(ROOT / "tests/fixtures/allegro/l78_regulator_bom.csv"),
            "--profiles",
            str(ROOT / "data/datasheet_profiles"),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "mode=real" in result.output
    constructor.assert_not_called()


@pytest.mark.parametrize("key", ["", "replace_me"])
def test_missing_key_keeps_real_review_import_rerun_export_and_restart_working(
    tmp_path, monkeypatch, key
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)
    constructor = Mock(side_effect=AssertionError("No real provider connection permitted"))
    monkeypatch.setattr(anthropic, "Anthropic", constructor)
    path = tmp_path / "review.sqlite"
    with TestClient(create(path)) as client:
        before = client.get("/api/workbench/state").json()
        failed = client.post("/api/workbench/chat", json={"question": "Explain U1"})
        assert failed.status_code == 503
        assert "ANTHROPIC_API_KEY" in failed.json()["detail"]
        assert client.get("/api/workbench/state").json() == before
        decision = client.put(
            "/api/workbench/review-decisions",
            json={
                "stable_keys": [before["review_tasks"][0]["stable_key"]],
                "status": "waived",
                "reason": "public no-key review reason",
                "expected_run_id": before["review_decisions"]["run_id"],
            },
        )
        assert decision.status_code == 200
        assert client.post("/api/workbench/rerun").json()["review_decisions"]["waived"] == 1
        for export_format in ("json", "csv", "annotations"):
            assert (
                client.get("/api/workbench/export", params={"format": export_format}).status_code
                == 200
            )
    with TestClient(create(path)) as client:
        restored = client.get("/api/workbench/state").json()
        assert restored["review_decisions"]["waived"] == 1
        assert (
            client.get("/api/workbench/review-decisions/history").json()["events"][0]["decision"][
                "reason"
            ]
            == "public no-key review reason"
        )
        imported = client.post(
            "/api/workbench/import",
            files={
                "netlist": (
                    "board.net",
                    (ROOT / "tests/fixtures/allegro/l78_regulator.net").read_bytes(),
                ),
                "bom": (
                    "bom.csv",
                    (ROOT / "tests/fixtures/allegro/l78_regulator_bom.csv").read_bytes(),
                ),
            },
        )
        assert imported.status_code == 200
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/export?format=json").status_code == 200
    constructor.assert_not_called()


def test_real_request_snapshots_share_one_lazily_initialized_client(monkeypatch):
    factory = Mock(return_value=FakeWorkbenchAnthropic())
    monkeypatch.setattr(WorkbenchChatService, "_default_client", staticmethod(factory))
    ctx = context()
    try:
        service = WorkbenchChatService(ctx, mode="real")
        factory.assert_not_called()
        first, second = copy.copy(service), copy.copy(service)
        first.ask(ChatRequest(question="板上有没有 U999?"))
        second.ask(ChatRequest(question="板上有没有 U999?"))
        factory.assert_called_once_with("real")
        assert first.client is second.client is service.client
    finally:
        close_workbench_context(ctx)


def test_real_mode_retains_dotenv_model_slot_before_deferred_client_creation(monkeypatch):
    def load(**kwargs):
        monkeypatch.setenv("HARDWISE_MODEL_NORMAL", "synthetic-configured-model")
        return True

    monkeypatch.setattr("dotenv.load_dotenv", load)
    constructor = Mock(side_effect=AssertionError("Not an AI request"))
    monkeypatch.setattr(anthropic, "Anthropic", constructor)
    ctx = context()
    try:
        service = WorkbenchChatService(ctx, mode="real")
        assert service.router.select("normal") == "synthetic-configured-model"
        constructor.assert_not_called()
    finally:
        close_workbench_context(ctx)


def test_failed_initialization_can_retry_after_explicit_configuration(tmp_path, monkeypatch):
    constructor = Mock(return_value=FakeWorkbenchAnthropic())
    monkeypatch.setattr(anthropic, "Anthropic", constructor)
    with TestClient(create(tmp_path / "review.sqlite")) as client:
        assert (
            client.post("/api/workbench/chat", json={"question": "板上有没有 U999?"}).status_code
            == 503
        )
        constructor.assert_not_called()
        monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-value")
        response = client.post("/api/workbench/chat", json={"question": "板上有没有 U999?"})
        assert response.status_code == 200 and response.json()["mode"] == "real"
        assert response.json()["trace"]
        constructor.assert_called_once()


@pytest.mark.parametrize("failure", ["connection", "timeout", "authentication"])
def test_provider_failure_does_not_publish_answer_or_change_review_state(tmp_path, failure):
    request = httpx.Request("POST", "https://example.invalid/messages")
    if failure == "connection":
        error = anthropic.APIConnectionError(request=request, message="synthetic-private-detail")
    elif failure == "timeout":
        error = anthropic.APITimeoutError(request=request)
    else:
        error = anthropic.AuthenticationError(
            "synthetic-private-detail",
            response=httpx.Response(401, request=request),
            body={"secret": "synthetic-private-detail"},
        )
    messages = SimpleNamespace(create=Mock(side_effect=error))
    with TestClient(
        create(tmp_path / "review.sqlite", SimpleNamespace(messages=messages))
    ) as client:
        before = client.get("/api/workbench/state").json()
        response = client.post("/api/workbench/chat", json={"question": "Explain U1"})
        assert response.status_code == 503
        assert "AI 服务暂不可用" in response.json()["detail"]
        assert "synthetic-private-detail" not in response.text
        assert "answer" not in response.json()
        assert client.get("/api/workbench/state").json() == before
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/export?format=json").status_code == 200
