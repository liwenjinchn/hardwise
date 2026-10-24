"""Malformed optional pin-table exports cannot replace the active review."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from hardwise.adapters.capture_pin_table import EXPECTED_HEADER
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app


class NoChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize(
    ("row", "diagnostic"),
    [
        ("U1,T,PKG,1,IN,INPUT(0),,P1,10,20,,\n", "nc_marker"),
        ("U1,T,PKG,1,IN,INPUT(0),,P1,10,20,2,\n", "nc_marker"),
        (",T,PKG,1,IN,INPUT(0),,P1,10,20,0,\n", "refdes"),
        ('U1,T,PKG,1,IN,INPUT(0),,P1,10,20,0,"unclosed', "CSV"),
    ],
)
def test_invalid_pin_table_upload_preserves_active_review(row: str, diagnostic: str) -> None:
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
                    "pin_table_csv": (
                        "bad-pin-table.csv",
                        (",".join(EXPECTED_HEADER) + "\n" + row).encode(),
                        "text/csv",
                    ),
                },
            )
            assert response.status_code == 400, response.text
            assert diagnostic in response.json()["detail"]
            assert ":2:" in response.json()["detail"]
            assert app.state.workbench_context["value"] is context
            after = client.get("/api/workbench/state").json()
            assert after["summary"] == before["summary"]
            assert after["review_tasks"] == before["review_tasks"]
            assert after["pin_table"] == before["pin_table"]
    finally:
        close_workbench_context(context)
