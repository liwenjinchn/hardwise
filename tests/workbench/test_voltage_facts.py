"""Voltage inputs pass through real import, rerun and offline API exports."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app

NETLIST = """$PACKAGES
 ! 'C0402' ! 1uF 16V ; C1
 ! 'R0402' ! 1K 1/4W ; R1
$NETS
 'P12' ; C1.1
 'N12' ; C1.2
 'GND' ; R1.1 R1.2
$END
"""
BOM = "Reference,Quantity,Value,Manufacturer,MPN\nC1,1,1uF 16V,Fixture,CAP\nR1,1,1K 1/4W,Fixture,RES\n"


class LocalOnlyChat:
    datasheet_search_enabled = False


def _facts():
    return {
        "schema_version": "hardwise.voltage_facts.v1",
        "active_mode": "dc",
        "facts": [
            {
                "net": net,
                "reference_net": "GND",
                "minimum": voltage,
                "maximum": voltage,
                "source": "Public synthetic bipolar DC fixture",
                "confirmed": True,
                "confirmed_by": "synthetic fixture author",
            }
            for net, voltage in [("P12", 12), ("N12", -12), ("GND", 0)]
        ],
    }


def _app(tmp_path):
    netlist, bom = tmp_path / "input.net", tmp_path / "bom.csv"
    netlist.write_text(NETLIST)
    bom.write_text(BOM)
    context = build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    return create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)


def _import(client, facts):
    return client.post(
        "/api/workbench/import",
        files={
            "netlist": ("input.net", NETLIST, "text/plain"),
            "bom": ("bom.csv", BOM, "text/csv"),
            "voltage_facts_json": ("voltage.json", json.dumps(facts), "application/json"),
        },
    )


def _capacitor(state):
    return next(row for row in state["queue"] if row["refdes"] == "C1")


def test_import_rerun_and_export_preserve_voltage_facts(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        assert (
            _capacitor(client.get("/api/workbench/state").json())["deterministic_status"]
            == "UNKNOWN"
        )
        response = _import(client, _facts())
        assert response.status_code == 200, response.text
        state = client.get("/api/workbench/state").json()
        assert _capacitor(state)["deterministic_status"] == "ERROR"
        assert "24 V" in _capacitor(state)["title"]
        facts = state["voltage_facts"]
        assert len(facts["facts"]) == 3
        rerun = client.post("/api/workbench/rerun")
        assert rerun.status_code == 200, rerun.text
        assert rerun.json()["voltage_facts"] == facts
        assert _capacitor(rerun.json())["deterministic_status"] == "ERROR"
        exported = client.get("/api/workbench/export?format=json")
        assert exported.status_code == 200
        assert exported.json()["voltage_facts"] == facts


def test_invalid_foreign_facts_do_not_replace_active_project(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        assert _import(client, _facts()).status_code == 200
        original = client.get("/api/workbench/state").json()
        invalid = _facts()
        invalid["facts"][0]["net"] = "FOREIGN"
        result = _import(client, invalid)
        assert result.status_code == 400
        assert "unknown nets" in result.text
        state = client.get("/api/workbench/state").json()
        assert state["project"] == original["project"]
        assert state["voltage_facts"] == original["voltage_facts"]
        assert _capacitor(state)["deterministic_status"] == "ERROR"


@pytest.mark.parametrize(
    "gate, expected", [((58, 58), "PASS"), ((78, 78), "ERROR"), ((67, 69), "UNKNOWN")]
)
def test_transistor_facts_import_rerun_and_export(gate, expected):
    root = Path("tests/fixtures/allegro")
    netlist, bom = root / "irf540n_highside.net", root / "irf540n_highside_bom.csv"
    context = build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    facts = json.loads((root / "irf540n_highside_dc_voltage_facts.json").read_text())
    facts["facts"][0].update(minimum=gate[0], maximum=gate[1])
    with TestClient(app) as client:
        before = client.get("/api/workbench/components/Q1").json()
        assert before["deterministic_status"] == "UNKNOWN"
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (netlist.name, netlist.read_bytes(), "text/plain"),
                "bom": (bom.name, bom.read_bytes(), "text/csv"),
                "voltage_facts_json": ("voltage.json", json.dumps(facts), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/Q1").json()
        check = next(c for c in detail["checks"] if c["summary"].startswith("Vgs "))
        assert check["status"] == expected
        assert check["assessment"]["rule_version"] == "2"
        assert len([e for e in check["evidence"] if e["token"].startswith("voltage_fact:")]) == 2
        assert client.post("/api/workbench/rerun").status_code == 200
        rerun = client.get("/api/workbench/components/Q1").json()
        assert rerun["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        assert exported["voltage_facts"]["facts"][0]["minimum"] == gate[0]
