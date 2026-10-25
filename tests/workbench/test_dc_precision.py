"""Exact terminal comparisons survive real import, rerun and offline capture."""

import csv
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from hardwise.ir.voltage import VoltageFactsDocument
from hardwise.workbench.server import create_workbench_app
from tests.profile_review_fixtures import reviewed_context_for_algorithm


class NoChat:
    datasheet_search_enabled = False


@pytest.mark.parametrize(
    "gate,source,expected",
    [
        (20, (-1e-16, -1e-16), "FAIL"),
        (-20, (1e-16, 1e-16), "FAIL"),
        (20, (-1e-16, 0), "UNKNOWN"),
        (20, (0, 0), "PASS"),
    ],
)
def test_declared_precision_through_import_rerun_and_offline(tmp_path, gate, source, expected):
    root = Path("tests/fixtures/allegro")
    netlist = root / "irf540n_highside.net"
    rows = list(csv.DictReader((root / "irf540n_highside_bom.csv").read_text().splitlines()))
    bom = tmp_path / "synthetic.csv"
    with bom.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[*rows[0], "Manufacturer"])
        writer.writeheader()
        writer.writerows([{**row, "Manufacturer": "SYNTHETIC-API-MANUFACTURER"} for row in rows])
    facts = json.loads((root / "irf540n_highside_dc_voltage_facts.json").read_text())
    facts["facts"][0].update(minimum=gate, maximum=gate)
    facts["facts"][1].update(minimum=source[0], maximum=source[1])
    context = reviewed_context_for_algorithm(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    with TestClient(
        create_workbench_app(context, NoChat(), auto_datasheet_candidates=False)
    ) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (netlist.name, netlist.read_bytes(), "text/plain"),
                "bom": (bom.name, bom.read_bytes(), "text/csv"),
                "voltage_facts_json": ("facts.json", json.dumps(facts), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/Q1").json()
        check = next(c for c in detail["checks"] if c["summary"].startswith("Vgs "))
        assert check["assessment"]["result"] == expected
        assert check["assessment"]["rule_version"] == "3.profile-review1"
        if expected == "FAIL":
            assert "20.0000000000000001" in check["summary"]
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/Q1").json()["checks"] == detail["checks"]
        state = client.get("/api/workbench/state").json()
        ids = state["review_decisions"]
        offline = client.get(
            "/api/workbench/offline-report",
            params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
        )
        assert offline.status_code == 200
        match = re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", offline.text)
        payload = json.loads(match[1])
        assert payload["state"] == state
        assert payload["components"]["Q1"]["checks"] == detail["checks"]
        assert payload["state"]["voltage_facts"] == VoltageFactsDocument.model_validate(
            facts
        ).model_dump(mode="json")
