"""Actual conflicting-reference intake blocks all candidates and permits correction."""

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


def write_bom(path, conflicting):
    prefix = (
        ["位号", "Refdes", "数量", "名称"]
        if path.suffix == ".xlsx"
        else ["Reference", "Refdes", "Quantity", "Value"]
    )
    rows = [
        prefix,
        ["U1", "C1" if conflicting else "U1", "1", "L7805"],
        ["C1", "C1", "1", "100nF 25V"],
        ["C2", "C2", "1", "100nF 25V"],
    ]
    if path.suffix == ".xlsx":
        write_minimal_xlsx(path, rows)
    else:
        with path.open("w", newline="") as f:
            csv.writer(f, delimiter="\t" if path.suffix == ".tsv" else ",").writerows(rows)


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_reference_quarantine_survives_import_rerun_exports_and_correction(tmp_path, suffix):
    root = Path("tests/fixtures/allegro")
    net = root / "l78_regulator.net"
    bom = tmp_path / ("refs" + suffix)
    write_bom(bom, True)
    facts = tmp_path / "facts.json"
    facts.write_text(
        json.dumps(
            dict(
                facts=[
                    dict(
                        net=n,
                        reference_net="GND",
                        minimum=v,
                        maximum=v,
                        confirmed=True,
                        confirmed_by="synthetic fixture author",
                        source="public reference conflict fixture",
                    )
                    for n, v in [("+12V", 12), ("+5V", 5), ("GND", 0)]
                ]
            )
        )
    )
    c = build_workbench_context(
        netlist_path=net,
        bom_path=root / "l78_regulator_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        with TestClient(
            create_workbench_app(c, NoChat(), auto_datasheet_candidates=False)
        ) as client:

            def upload():
                return client.post(
                    "/api/workbench/import",
                    files={
                        "netlist": (net.name, net.read_bytes()),
                        "bom": (bom.name, bom.read_bytes()),
                        "voltage_facts_json": (facts.name, facts.read_bytes()),
                    },
                )

            r = upload()
            assert r.status_code == 200, r.text
            state = client.get("/api/workbench/state").json()
            for ref in ["U1", "C1"]:
                tasks = [t for t in state["review_tasks"] if t["refdes"] == ref]
                assert len(tasks) == 1 and tasks[0]["check"] == "bom_identity_conflict"
                assert tasks[0]["assessment"]["result"] == "UNKNOWN"
                assert tasks[0]["assessment"]["rule_version"] == "4"
                assert "column1" in tasks[0]["body"] and "column2" in tasks[0]["body"]
                detail = client.get("/api/workbench/components/" + ref).json()
                assert detail["profile_part_number"] in ["", None]
                # Registry pins stay visible; no electrical assessment is authorized.
                assert detail["pins"] and all(p["assessment"] is None for p in detail["pins"])
            assert (
                next(r for r in state["queue"] if r["refdes"] == "C2")["deterministic_status"]
                == "PASS"
            )
            assert client.post("/api/workbench/rerun").status_code == 200
            repeated = client.get("/api/workbench/state").json()
            assert repeated["review_tasks"] == state["review_tasks"]
            ids = repeated["review_decisions"]
            r = client.get(
                "/api/workbench/offline-report",
                params=dict(expected_project_id=ids["project_id"], expected_run_id=ids["run_id"]),
            )
            assert r.status_code == 200
            snapshot = json.loads(
                re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", r.text)[1]
            )
            assert snapshot["state"] == repeated
            assert (
                "column1" in snapshot["project_prep_markdown"]
                and "column2" in snapshot["project_prep_markdown"]
            )
            assert "column2" in client.get("/api/workbench/export?format=csv").text
            write_bom(bom, False)
            r = upload()
            assert r.status_code == 200, r.text
            fixed = client.get("/api/workbench/state").json()
            assert not any(t["check"] == "bom_identity_conflict" for t in fixed["review_tasks"])
            assert (
                next(r for r in fixed["queue"] if r["refdes"] == "C2")["deterministic_status"]
                == "PASS"
            )
    finally:
        close_workbench_context(c)
