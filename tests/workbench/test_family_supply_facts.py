"""Actual upload/rerun/export keeps pin and MCU family supply results aligned."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app


class LocalOnlyChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize(
    "bounds,result,severity",
    [
        ((2.5, 2.5), "PASS", "INFO"),
        ((4.1, 4.2), "FAIL", "ERROR"),
        ((3.5, 3.7), "UNKNOWN", "INFO"),
        ((3.7, 3.8), "FAIL", "WARNING"),
    ],
)
def test_mcu_pin_and_family_share_actual_imported_bounds(bounds, result, severity):
    root = Path("tests/fixtures/allegro")
    netlist = root / "stm32g030_mcu.net"
    bom = root / "stm32g030_mcu_bom.csv"
    context = build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    facts = {
        "schema_version": "hardwise.voltage_facts.v1",
        "active_mode": "dc",
        "facts": [
            {
                "net": "+3V3",
                "reference_net": "GND",
                "minimum": bounds[0],
                "maximum": bounds[1],
                "source": "Public synthetic API regression; not a measurement",
                "confirmed": True,
                "confirmed_by": "test author",
            }
        ],
    }
    with TestClient(app) as client:
        before = client.get("/api/workbench/components/U8").json()
        assert before["checks"][0]["assessment"]["result"] == "UNKNOWN"
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("mcu.net", netlist.read_bytes(), "text/plain"),
                "bom": ("bom.csv", bom.read_bytes(), "text/csv"),
                "voltage_facts_json": ("dc.json", json.dumps(facts), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/U8").json()
        pin = next(p for p in detail["pins"] if p["number"] == "6")
        check = next(c for c in detail["checks"] if c["summary"].startswith("引脚 VDD/VDDA"))
        assert pin["assessment"] == check["assessment"]
        assert (check["assessment"]["result"], check["assessment"]["severity"]) == (
            result,
            severity,
        )
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U8").json()["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        tasks = [
            t
            for t in exported["review_tasks"]
            if t["refdes"] == "U8" and t["check"] == "mcu_vdd_vdda_rail"
        ]
        if result == "PASS":
            assert tasks == []  # completed individual checks do not create review tasks
        else:
            assert len(tasks) == 1
            formal = tasks[0]["assessment"]
            assert (formal["result"], formal["severity"], formal["rule_version"]) == (
                result,
                severity,
                "2",
            )
        assert exported["voltage_facts"]["facts"][0]["minimum"] == bounds[0]
