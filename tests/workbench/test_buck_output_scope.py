"""Real upload/rerun/export cannot promote a voltage-looking output name."""

from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app


class LocalOnlyChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize("output", ["P1V8", "GND_LABEL", "DATA_RETURN", "missing_inductor"])
def test_buck_output_role_survives_import_rerun_export(output):
    root = Path("tests/fixtures/allegro")
    netlist, bom = root / "mpq8626_sync_buck.net", root / "mpq8626_sync_buck_bom.csv"
    text = netlist.read_text()
    if output == "missing_inductor":
        text = text.replace(", PL1.1", "")
    else:
        text = text.replace("'P1V8'", repr(output))
    context = build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    result = "FAIL" if output == "missing_inductor" else "UNKNOWN"
    with TestClient(app) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("buck.net", text, "text/plain"),
                "bom": ("buck.csv", bom.read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/U13").json()
        task = next(t for t in detail["tasks"] if t["check"] == "buck_inductor")
        assert task["assessment"]["result"] == result
        assert task["assessment"]["rule_version"] == "3"
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U13").json()["checks"] == detail["checks"]
        export = client.get("/api/workbench/export?format=json").json()
        exported = next(
            t
            for t in export["review_tasks"]
            if t["refdes"] == "U13" and t["check"] == "buck_inductor"
        )
        assert exported["assessment"] == task["assessment"]
