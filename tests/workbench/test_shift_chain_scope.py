"""The API preserves observed chain connectivity without net-name authority."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from tests.profile_review_fixtures import reviewed_context_for_algorithm
from hardwise.workbench.server import create_workbench_app


class LocalOnlyChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize(
    "change,refdes,result",
    [
        ("nominal", "U3", "UNKNOWN"),
        ("rename", "U3", "UNKNOWN"),
        ("disconnected", "U1", "UNKNOWN"),
        ("missing_output", "U3", "FAIL"),
    ],
)
def test_import_rerun_export_preserves_chain_scope(tmp_path, change, refdes, result):
    fixtures = Path("tests/fixtures/allegro")
    text = (fixtures / "shift_register_chain.net").read_text()
    if change == "rename":
        text = text.replace("'OUT2'", "'DATA_RETURN'")
    elif change == "disconnected":
        text = text.replace(
            "'OUT0_R' ; RCHAIN1.2, U2.10", "'OUT0_R' ; RCHAIN1.2\n 'BROKEN_DS' ; U2.10"
        )
    elif change == "missing_output":
        text = text.replace("  'OUT2' ; U3.9\n", "")
    netlist, bom = tmp_path / "shift.net", tmp_path / "shift_bom.csv"
    netlist.write_text(text)
    bom.write_bytes((fixtures / "shift_register_chain_bom.csv").read_bytes())
    profiles = Path("data/datasheet_profiles")
    context = reviewed_context_for_algorithm(netlist_path=netlist, bom_path=bom, profiles=profiles)
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("shift.net", netlist.read_bytes(), "text/plain"),
                "bom": ("shift.csv", bom.read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get(f"/api/workbench/components/{refdes}").json()
        chain = next(c for c in detail["checks"] if c["summary"].startswith("Serial output"))
        assert chain["assessment"]["result"] == result
        assert chain["assessment"]["rule_version"] == "2.profile-review1"
        assert chain["assessment"]["needs_review"] == (result == "UNKNOWN")
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get(f"/api/workbench/components/{refdes}").json()["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        task = next(
            t
            for t in exported["review_tasks"]
            if t["refdes"] == refdes and t["check"] == "shift_register_serial_chain"
        )
        assert task["assessment"] == chain["assessment"]
