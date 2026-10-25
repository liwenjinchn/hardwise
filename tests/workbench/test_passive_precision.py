"""Unrounded decimal-model decisions through real text/table intake and offline export."""

import csv
import hashlib
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app
from tests.xlsx_fixture import write_minimal_xlsx

ROOT = Path(__file__).parents[2]


class NoChat:
    datasheet_search_enabled = False


def precision_inputs(root, suffix, power):
    netlist = root / "precision.net"
    netlist.write_text(
        "$PACKAGES\n ! 'R0402' ! RES ; R1, R2, R3, R4\n"
        " ! 'C0402' ! CAP ; C1, C2\n$NETS\n"
        " 'A' ; R1.1, R2.1, R3.1, C1.1\n 'B' ; R1.2, R2.2, R3.2, C1.2\n"
        " 'X' ; R4.1, C2.1\n 'Y' ; R4.2, C2.2\n$END\n"
    )
    rows = [
        ["Reference", "Quantity", "Value", "Power Rating", "Rated Voltage"],
        ["R1", "1", "3R", power, ""],
        ["R2", "1", "10R 1W", "", ""],
        ["R3", "1", "3R 1/3W", "", ""],
        ["R4", "1", "1R 1W", "", ""],
        ["C1", "1", "1uF", "", "0.99999999999999999V"],
        ["C2", "1", "1uF 1V", "", ""],
    ]
    bom = root / ("precision" + suffix)
    if suffix == ".xlsx":
        rows[0][:3] = ["位号", "数量", "名称"]
        # Text cells preserve the declared decimal digits; no claim about Excel numeric-cell precision.
        write_minimal_xlsx(bom, rows)
    else:
        with bom.open("w", newline="") as stream:
            csv.writer(stream, delimiter="\t" if suffix == ".tsv" else ",").writerows(rows)
    facts = root / "facts.json"
    facts.write_text(
        json.dumps(
            dict(
                facts=[
                    dict(
                        net=n,
                        reference_net="B",
                        minimum=v,
                        maximum=v,
                        confirmed=True,
                        confirmed_by="synthetic author",
                        source="Public decimal-model fixture, not measured",
                    )
                    for n, v in [("A", 1), ("B", 0), ("X", 0.10000000000000003), ("Y", -0.9)]
                ]
            )
        )
    )
    return netlist, bom, facts


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize("power", ["0.3333333333333333W", "333.3333333333333mW"])
def test_precision_through_import_rerun_and_offline_export(tmp_path, suffix, power):
    netlist, bom, facts = precision_inputs(tmp_path, suffix, power)
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (netlist, bom, facts)}
    context = build_workbench_context(
        netlist_path=netlist,
        bom_path=bom,
        profiles=ROOT / "data/datasheet_profiles",
        voltage_facts=facts,
    )
    with TestClient(
        create_workbench_app(context, NoChat(), auto_datasheet_candidates=False)
    ) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (netlist.name, netlist.read_bytes(), "text/plain"),
                "bom": (bom.name, bom.read_bytes(), "application/octet-stream"),
                "voltage_facts_json": (facts.name, facts.read_bytes(), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        expected = {
            "R1": "FAIL",
            "R2": "PASS",
            "R3": "PASS",
            "R4": "FAIL",
            "C1": "FAIL",
            "C2": "FAIL",
        }
        details = {}
        for refdes, result in expected.items():
            detail = client.get("/api/workbench/components/" + refdes).json()
            details[refdes] = detail
            # Family detail order is parse / optional rating / package / final DC stress check.
            check = detail["checks"][-1]
            assert check["assessment"]["result"] == result
            assert check["assessment"]["rule_version"] == "4"
            assert all(pin["assessment"]["result"] == "PASS" for pin in detail["pins"])
            assert any(c["assessment"]["result"] == "PASS" for c in detail["checks"][:-1])
            if result == "FAIL":
                assert "精确比较" in check["summary"]
        assert client.post("/api/workbench/rerun").status_code == 200
        for refdes in details:
            assert (
                client.get("/api/workbench/components/" + refdes).json()["checks"]
                == details[refdes]["checks"]
            )
        state = client.get("/api/workbench/state").json()
        assert state["assessment_coverage"]["result_counts"]["FAIL"] == 4
        ids = state["review_decisions"]
        offline = client.get(
            "/api/workbench/offline-report",
            params={
                "expected_project_id": ids["project_id"],
                "expected_run_id": ids["run_id"],
            },
        )
        assert offline.status_code == 200
        match = re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", offline.text)
        payload = json.loads(match[1])
        assert payload["state"] == state
        for refdes, result in expected.items():
            assert payload["components"][refdes]["checks"][-1]["assessment"]["result"] == result
        assert "1/3 W" in payload["exports"]["csv"]
        assert "0.99999999999999999V" in offline.text
        assert power in offline.text
        assert "精确比较" in payload["project_prep_markdown"]
    assert before == {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (netlist, bom, facts)
    }
