"""Real upload/rerun/export preserves floating gate-supply voltage scope."""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app


class LocalOnlyChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize(
    "vb,result", [((36, 36), "PASS"), ((60, 60), "FAIL"), ((48, 50), "UNKNOWN")]
)
def test_actual_floating_supply_import(vb, result):
    root = Path("tests/fixtures/allegro")
    netlist, bom = root / "eg2132_gate_driver.net", root / "eg2132_gate_driver_bom.csv"
    context = build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    facts = {
        "schema_version": "hardwise.voltage_facts.v1",
        "active_mode": "dc",
        "facts": [
            {
                "net": n,
                "reference_net": "GND",
                "minimum": lo,
                "maximum": hi,
                "confirmed": True,
                "source": "synthetic floating-supply API premise; not measurement",
                "confirmed_by": "test author",
            }
            for n, lo, hi in [("VB_U", *vb), ("PHASE_U", 24, 24), ("+12V", 12, 12)]
        ],
    }
    with TestClient(app) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("gate.net", netlist.read_bytes(), "text/plain"),
                "bom": ("bom.csv", bom.read_bytes(), "text/csv"),
                "voltage_facts_json": ("facts.json", json.dumps(facts), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/U3").json()
        floating = next(
            c for c in detail["checks"] if c["summary"].startswith("VB−VS 已确认直流范围")
        )
        assert floating["assessment"]["result"] == result
        assert floating["assessment"]["rule_version"] == "2"
        bootstrap = next(c for c in detail["checks"] if "本项自举功能未评估" in c["summary"])
        assert bootstrap["assessment"]["result"] == "UNKNOWN"
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U3").json()["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        tasks = [
            t
            for t in exported["review_tasks"]
            if t["refdes"] == "U3" and t["check"] == "gate_driver_vb_vs_voltage"
        ]
        if result == "PASS":
            assert tasks == []
        else:
            assert tasks[0]["assessment"]["result"] == result
        assert exported["voltage_facts"]["facts"][0]["minimum"] == vb[0]
