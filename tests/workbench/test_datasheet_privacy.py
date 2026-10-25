"""Default-off lookup is independent from cloud AI and enforced at HTTP boundary."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.workbench.chat import WorkbenchChatService
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path("tests/fixtures/allegro")


@pytest.mark.parametrize("explicit_off", [False, True])
def test_key_present_default_and_explicit_off_never_query_any_route(monkeypatch, explicit_off):
    monkeypatch.setenv("DATASHEETS_API_KEY", "SYNTHETIC_DATASHEETS_KEY")
    monkeypatch.setenv("DATASHEETS_COM_API_KEY", "SYNTHETIC_DATASHEETS_KEY")
    lookup = Mock(side_effect=AssertionError("Disabled service must not query provider"))
    monkeypatch.setattr("hardwise.workbench.datasheet_candidates.lookup_datasheets_com", lookup)
    context = build_workbench_context(
        netlist_path=ROOT / "mixed_controller_power_stage.net",
        bom_path=ROOT / "mixed_controller_power_stage_bom.csv",
        profiles=Path("data/datasheet_profiles"),
        document_index=Path("data/document_indexes/mixed_controller_power_stage_docs.csv"),
    )
    service = WorkbenchChatService(context, mode="fake")
    try:
        with TestClient(
            create_workbench_app(
                context, service, **({"auto_datasheet_candidates": False} if explicit_off else {})
            )
        ) as client:
            before = client.get("/api/workbench/state").json()
            assert not before["capabilities"]["datasheet_candidate_lookup_enabled"]
            assert (
                client.get("/api/workbench/components/Q12").json()["document"]["candidate_search"]
                is None
            )
            for fmt in ["json", "csv", "markdown"]:
                response = client.get(
                    "/api/workbench/profile-gaps/9/datasheet-candidates", params={"format": fmt}
                )
                assert response.status_code == 403
                assert "https://www.datasheets.com/api/v1/search" in response.text
                assert "SYNTHETIC_DATASHEETS_KEY" not in response.text
            # A successful fake-AI turn does not enable independent datasheet lookup.
            assert (
                client.post(
                    "/api/workbench/chat", json={"question": "板上有没有 U999?"}
                ).status_code
                == 200
            )
            assert client.get("/api/workbench/state").json() == before
            lookup.assert_not_called()
    finally:
        close_workbench_context(context)


@pytest.mark.parametrize("enabled", [False, True])
def test_cli_default_off_and_explicit_opt_in_disclose_before_service(monkeypatch, enabled):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    args = [
        "serve-workbench",
        str(ROOT / "l78_regulator.net"),
        str(ROOT / "l78_regulator_bom.csv"),
        "--fake-ai",
        "--dry-run",
    ]
    if enabled:
        args.append("--auto-datasheet-candidates")
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert f"datasheet-candidates={'auto' if enabled else 'off'}" in result.output
    if enabled:
        assert "https://www.datasheets.com/api/v1/search" in result.output
        assert "型号/标识搜索词" in result.output
        assert result.output.index("已显式启用资料联网查询") < result.output.index(
            "serve-workbench:"
        )
