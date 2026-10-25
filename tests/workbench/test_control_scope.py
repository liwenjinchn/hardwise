"""Confirmed DC control observations do not become functional approvals."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from tests.profile_review_fixtures import reviewed_context_for_algorithm
from hardwise.workbench.server import create_workbench_app


class LocalOnlyChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize("direct_controls", [True, False])
def test_control_unknown_survives_real_import_rerun_and_export(direct_controls):
    root = Path("tests/fixtures/allegro")
    netlist, bom = root / "stm32g030_mcu.net", root / "stm32g030_mcu_bom.csv"
    context = reviewed_context_for_algorithm(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    values = {"+3V3": 3.3, **({"NRST": 3.3, "BOOT0": 0.0} if direct_controls else {})}
    facts = {
        "schema_version": "hardwise.voltage_facts.v1",
        "active_mode": "dc",
        "facts": [
            {
                "net": n,
                "reference_net": "GND",
                "minimum": v,
                "maximum": v,
                "confirmed": True,
                "source": "synthetic API premise; not measurement",
                "confirmed_by": "test author",
            }
            for n, v in values.items()
        ],
    }
    with TestClient(app) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("mcu.net", netlist.read_bytes(), "text/plain"),
                "bom": ("bom.csv", bom.read_bytes(), "text/csv"),
                "voltage_facts_json": ("facts.json", json.dumps(facts), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/U8").json()
        state = client.get("/api/workbench/state").json()
        queue_row = next(row for row in state["queue"] if row["refdes"] == "U8")
        assert "SWDIO" in queue_row["title"]
        assert "控制脚" not in queue_row["title"]
        pins = {p["number"]: p for p in detail["pins"]}
        assert pins["10"]["assessment"]["result"] == "PASS"  # connection only
        assert pins["44"]["assessment"]["result"] == "PASS"
        controls = [c for c in detail["checks"] if "逻辑功能未评估" in c["summary"]]
        assert len(controls) == 2
        for control in controls:
            assert control["assessment"]["result"] == "UNKNOWN"
            assert control["assessment"]["rule_version"] == "2.profile-review1"
            assert ("本脚已确认直流差值" in control["summary"]) == direct_controls
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U8").json()["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        tasks = [
            t
            for t in exported["review_tasks"]
            if t["refdes"] == "U8" and t["check"] in {"mcu_nrst", "mcu_boot0"}
        ]
        assert len(tasks) == 2
        assert all(t["assessment"]["result"] == "UNKNOWN" for t in tasks)
