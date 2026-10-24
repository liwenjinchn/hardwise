"""Input filename collisions must not silently replace source bytes."""

import io
import json
from pathlib import Path

from fastapi import UploadFile
from fastapi.testclient import TestClient
import pytest

from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app
from hardwise.workbench.server_io import _save_upload


class NoChat:
    datasheet_search_enabled = False


def test_upload_collision_preserves_the_first_source(tmp_path: Path) -> None:
    first = UploadFile(filename="source.json", file=io.BytesIO(b"first source"))
    second = UploadFile(filename="source.json", file=io.BytesIO(b"second source"))
    path = _save_upload(first, tmp_path, fallback_name="first.json")
    with pytest.raises(ValueError, match="duplicate upload filename"):
        _save_upload(second, tmp_path, fallback_name="second.json")
    assert path.read_bytes() == b"first source"


@pytest.mark.parametrize("same_name", [True, False])
def test_optional_uploads_preserve_sources_or_reject_collision(same_name: bool) -> None:
    netlist = Path("tests/fixtures/allegro/l78_regulator.net")
    bom = Path("tests/fixtures/allegro/l78_regulator_bom.csv")
    context = build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    app = create_workbench_app(context, NoChat())  # type: ignore[arg-type]
    try:
        with TestClient(app) as client:
            before = client.get("/api/workbench/state").json()
            response = client.post(
                "/api/workbench/import",
                files={
                    "netlist": (netlist.name, netlist.read_bytes(), "text/plain"),
                    "bom": (bom.name, bom.read_bytes(), "text/csv"),
                    "risk_hints_json": (
                        "config.json",
                        json.dumps(
                            {"hints": [{"refdes": "U1", "title": "Review", "body": "Verify U1"}]}
                        ),
                        "application/json",
                    ),
                    "voltage_facts_json": (
                        "config.json" if same_name else "facts.json",
                        '{"facts": []}',
                        "application/json",
                    ),
                },
            )
            after = client.get("/api/workbench/state").json()
            if same_name:
                assert response.status_code == 400, response.text
                assert "duplicate upload filename" in response.json()["detail"]
                assert "config.json" in response.json()["detail"]
                assert app.state.workbench_context["value"] is context
                assert after["risk_hints"] == before["risk_hints"]
                assert after["review_tasks"] == before["review_tasks"]
            else:
                assert response.status_code == 200, response.text
                active = app.state.workbench_context["value"]
                assert active.risk_hints.accepted_count == 1
                assert active.input_manifest is not None
                files = active.input_manifest.files
                hints = next(item for item in files if "risk_hints" in item.roles)
                facts = next(item for item in files if "voltage_facts" in item.roles)
                assert hints.path != facts.path
                assert hints.sha256 != facts.sha256
    finally:
        close_workbench_context(context)
