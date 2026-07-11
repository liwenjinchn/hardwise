"""Resource ownership tests for Workbench context construction."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hardwise.workbench import context as context_module
from hardwise.workbench import server as server_module
from hardwise.workbench.chat import ChatResponse


def test_context_build_closes_session_when_population_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Session:
        closed = False

        def close(self) -> None:
            self.closed = True

    session = _Session()
    monkeypatch.setattr(context_module, "create_store", lambda _url: session)

    def fail_population(_session: object, _registry: object) -> None:
        raise RuntimeError("population failed")

    monkeypatch.setattr(context_module, "populate_from_registry", fail_population)

    with pytest.raises(RuntimeError, match="population failed"):
        context_module.build_workbench_context(
            netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
            bom_path=Path("tests/fixtures/allegro/l78_regulator_bom.csv"),
            profiles=Path("data/datasheet_profiles"),
        )

    assert session.closed is True


def test_import_activation_failure_closes_new_context_and_upload_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_context = context_module.build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_path=Path("tests/fixtures/allegro/l78_regulator_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
    )
    next_context = context_module.build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_path=Path("tests/fixtures/allegro/l78_regulator_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
    )

    class _ChatService:
        context = initial_context
        datasheet_search_enabled = False

        def ask(self, _request: object) -> ChatResponse:
            return ChatResponse(answer="unused", mode="fake")

    app = server_module.create_workbench_app(initial_context, _ChatService())  # type: ignore[arg-type]
    import_dir = tmp_path / "import"
    import_dir.mkdir()
    closed: list[object] = []

    monkeypatch.setattr(server_module.tempfile, "mkdtemp", lambda **_kwargs: str(import_dir))
    monkeypatch.setattr(
        server_module,
        "build_workbench_context",
        lambda **_kwargs: next_context,
    )
    original_close = server_module.close_workbench_context

    def record_close(context: object) -> None:
        closed.append(context)
        original_close(context)  # type: ignore[arg-type]

    monkeypatch.setattr(server_module, "close_workbench_context", record_close)
    monkeypatch.setattr(
        app.state.workbench_context,
        "swap",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shutting down")),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/workbench/import",
            files={"netlist": ("uploaded.net", b"fixture", "text/plain")},
        )

    assert response.status_code == 503
    assert "import activation failed" in response.json()["detail"]
    assert closed == [next_context]
    assert not import_dir.exists()
