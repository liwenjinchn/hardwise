"""Voltage inputs pass through real import, rerun and offline API exports."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from tests.profile_review_fixtures import reviewed_context_for_algorithm
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
    context = reviewed_context_for_algorithm(
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
def test_transistor_facts_import_rerun_and_export(gate, expected, tmp_path):
    root = Path("tests/fixtures/allegro")
    netlist = root / "irf540n_highside.net"
    # Explicit fictional manufacturer is part of the trusted algorithm fixture and upload.
    import csv
    import io

    rows = list(csv.DictReader((root / "irf540n_highside_bom.csv").read_text().splitlines()))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[*rows[0], "Manufacturer"])
    writer.writeheader()
    writer.writerows([{**row, "Manufacturer": "SYNTHETIC-API-MANUFACTURER"} for row in rows])
    bom = tmp_path / "synthetic-reviewed-bom.csv"
    bom.write_text(buffer.getvalue())
    context = reviewed_context_for_algorithm(
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
        assert check["assessment"]["rule_version"] == "2.profile-review1"
        assert len([e for e in check["evidence"] if e["token"].startswith("voltage_fact:")]) == 2
        assert client.post("/api/workbench/rerun").status_code == 200
        rerun = client.get("/api/workbench/components/Q1").json()
        assert rerun["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        assert exported["voltage_facts"]["facts"][0]["minimum"] == gate[0]


@pytest.mark.parametrize(
    "cathode, expected", [((12, 12), "PASS"), ((48, 48), "ERROR"), ((39, 41), "UNKNOWN")]
)
def test_diode_tvs_led_import_rerun_and_export(cathode, expected):
    root = Path("tests/fixtures/allegro/diode_dc")
    context = reviewed_context_for_algorithm(
        netlist_path=root / "input.net",
        bom_path=root / "bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    facts = json.loads((root / "voltage_facts.json").read_text())
    facts["facts"][0].update(minimum=cathode[0], maximum=cathode[1])
    with TestClient(app) as client:
        assert (
            client.get("/api/workbench/components/D1").json()["deterministic_status"] == "UNKNOWN"
        )
        reply = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("input.net", (root / "input.net").read_bytes(), "text/plain"),
                "bom": ("bom.csv", (root / "bom.csv").read_bytes(), "text/csv"),
                "voltage_facts_json": ("voltage.json", json.dumps(facts), "application/json"),
            },
        )
        assert reply.status_code == 200, reply.text
        details = {
            ref: client.get(f"/api/workbench/components/{ref}").json() for ref in ("D1", "D2", "D3")
        }
        reverse = next(
            c for c in details["D1"]["checks"] if c["summary"].startswith("二极管反向电压 ")
        )
        assert reverse["status"] == expected
        assert reverse["assessment"]["rule_version"] == "2.profile-review1"
        standoff = next(
            c for c in details["D2"]["checks"] if c["summary"].startswith("TVS 两端工作电压 ")
        )
        assert standoff["status"] == "ERROR"
        led = next(c for c in details["D3"]["checks"] if "未核验串联关系" in c["summary"])
        assert led["status"] == "UNKNOWN"
        assert led["assessment"]["evidence_kind"] == "HYPOTHESIS"
        assert client.post("/api/workbench/rerun").status_code == 200
        for ref in details:
            assert (
                client.get(f"/api/workbench/components/{ref}").json()["checks"]
                == details[ref]["checks"]
            )
        exported = client.get("/api/workbench/export?format=json").json()
        assert exported["voltage_facts"]["facts"][0]["minimum"] == cathode[0]


@pytest.mark.parametrize(
    "vin, expected", [((11, 13), "PASS"), ((36, 37), "ERROR"), ((24, 26), "UNKNOWN")]
)
def test_generic_pin_bounds_import_rerun_export_without_nominal_signoff(vin, expected):
    root = Path("tests/fixtures/allegro")
    context = reviewed_context_for_algorithm(
        netlist_path=root / "l78_regulator.net",
        bom_path=root / "l78_regulator_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    app = create_workbench_app(context, LocalOnlyChat(), auto_datasheet_candidates=False)
    facts = json.loads((root / "l78_dc_voltage_facts.json").read_text())
    facts["facts"][0].update(minimum=vin[0], maximum=vin[1])
    with TestClient(app) as client:
        original = client.get("/api/workbench/components/U1").json()
        assert next(p for p in original["pins"] if p["number"] == "1")["status"] == "UNKNOWN"
        reply = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("input.net", (root / "l78_regulator.net").read_bytes(), "text/plain"),
                "bom": ("bom.csv", (root / "l78_regulator_bom.csv").read_bytes(), "text/csv"),
                "voltage_facts_json": ("voltage.json", json.dumps(facts), "application/json"),
            },
        )
        assert reply.status_code == 200, reply.text
        detail = client.get("/api/workbench/components/U1").json()
        pins = {p["number"]: p for p in detail["pins"]}
        assert pins["1"]["status"] == expected
        assert pins["1"]["assessment"]["rule_version"] == "2.profile-review1"
        assert pins["3"]["status"] == "UNKNOWN"  # a typical output value is not a tolerance
        assert "不使用固定 ±0.2 V" in pins["3"]["summary"]
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U1").json()["pins"] == detail["pins"]
        export = client.get("/api/workbench/export?format=json").json()
        assert export["voltage_facts"]["facts"][0]["minimum"] == vin[0]
