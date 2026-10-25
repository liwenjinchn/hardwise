"""Actual BOM intake must survive unusable inductance without certifying its value."""

import csv
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app
from tests.xlsx_fixture import write_minimal_xlsx


class NoChat:
    datasheet_search_enabled = False


def scene(root, suffix):
    netlist = root / "inductor.net"
    netlist.write_text(
        "$PACKAGES\n ! 'IND' ! COIL ; L1, L2\n ! 'R0402' ! RES ; R1\n"
        "$NETS\n 'A' ; L1.1, L2.1, R1.1\n 'B' ; L1.2, L2.2, R1.2\n$END\n"
    )
    bom = root / ("bom" + suffix)
    rows = [
        ["位号", "数量", "名称"] if suffix == ".xlsx" else ["Reference", "Quantity", "Value"],
        ["L1", "1", "9" * 400 + "uH"],
        ["L2", "1", "1" * 5000 + "R1"],
        ["R1", "1", "1K 1W"],
    ]
    if suffix == ".xlsx":
        write_minimal_xlsx(bom, rows)
    else:
        with bom.open("w", newline="") as f:
            csv.writer(f, delimiter="\t" if suffix == ".tsv" else ",").writerows(rows)
    return netlist, bom


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_unusable_inductance_import_rerun_and_offline(tmp_path, suffix):
    root = Path("tests/fixtures/allegro")
    c = build_workbench_context(
        netlist_path=root / "l78_regulator.net",
        bom_path=root / "l78_regulator_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    netlist, bom = scene(tmp_path, suffix)
    try:
        with TestClient(
            create_workbench_app(c, NoChat(), auto_datasheet_candidates=False)
        ) as client:
            r = client.post(
                "/api/workbench/import",
                files={
                    "netlist": (netlist.name, netlist.read_bytes()),
                    "bom": (bom.name, bom.read_bytes()),
                },
            )
            assert r.status_code == 200, r.text
            state = client.get("/api/workbench/state").json()
            for refdes in ["L1", "L2"]:
                tasks = [t for t in state["review_tasks"] if t["refdes"] == refdes]
                check = next(t for t in tasks if t["check"] == "inductor_value_parse")
                assert check["assessment"]["result"] == "UNKNOWN"
                assert check["assessment"]["rule_version"] == "2"
                detail = client.get(f"/api/workbench/components/{refdes}").json()
                assert any(
                    c["assessment"]["result"] == "PASS" and "封装" in c["summary"]
                    for c in detail["checks"]
                )
                assert all(p["assessment"]["result"] == "PASS" for p in detail["pins"])
            assert client.post("/api/workbench/rerun").status_code == 200
            repeated = client.get("/api/workbench/state").json()
            for key in ["summary", "assessment_coverage", "review_tasks"]:
                assert repeated[key] == state[key]
            state = repeated
            assert "1" * 5000 in client.get("/api/workbench/components/L2").text
            ids = state["review_decisions"]
            r = client.get(
                "/api/workbench/offline-report",
                params=dict(expected_project_id=ids["project_id"], expected_run_id=ids["run_id"]),
            )
            assert r.status_code == 200, r.text
            snapshot = json.loads(
                re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", r.text)[1]
            )
            assert snapshot["state"] == state
            assert "数值不可用" in snapshot["project_prep_markdown"]
            assert "数值不可用" in client.get("/api/workbench/export?format=csv").text
            resistor = client.get("/api/workbench/components/R1").json()
            assert any(c["assessment"]["result"] == "PASS" for c in resistor["checks"])

    finally:
        close_workbench_context(c)
