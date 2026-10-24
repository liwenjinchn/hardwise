"""Real workbench projections must not turn a competing BOM column into a selected identity."""

import csv
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app
from hardwise.report import workbench_spa_snapshot
from tests.xlsx_fixture import write_minimal_xlsx


class Chat:
    datasheet_search_enabled = False


def _bom(path, conflicting):
    prefix = (
        ["位号", "数量", "名称"] if path.suffix == ".xlsx" else ["Reference", "Quantity", "Value"]
    )
    headers = prefix + ["MPN", "MPN", "Manufacturer", "Mfr", "Package", "Footprint"]
    rows = [
        headers,
        [
            "U1",
            "1",
            "L7805",
            "WRONG_PUBLIC_FIXTURE" if conflicting else "L7805",
            "L7805",
            "VendorA" if conflicting else "ST",
            "VendorB" if conflicting else "ST",
            "TO220",
            "SOT23" if conflicting else "TO220",
        ],
        ["C1", "1", "100nF", "", "", "", "", "", ""],
        ["C2", "1", "100nF", "", "", "", "", "", ""],
    ]
    if path.suffix == ".xlsx":
        write_minimal_xlsx(path, rows)
    else:
        with path.open("w", newline="") as stream:
            csv.writer(stream, delimiter="\t" if path.suffix == ".tsv" else ",").writerows(rows)


def _context(path):
    return build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
        bom_path=path,
        profiles=Path("data/datasheet_profiles"),
    )


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_conflicts_block_only_owned_identity_and_survive_export_then_clear_on_correction(
    tmp_path, monkeypatch, suffix
):
    path = tmp_path / ("public" + suffix)
    _bom(path, True)
    context = _context(path)
    with TestClient(
        create_workbench_app(context, Chat(), auto_datasheet_candidates=False)
    ) as client:
        state = client.get("/api/workbench/state").json()
        assert "U1" in context.bom_report.identity_conflicts
        assert "U1" not in context.validation_targets
        validation = next(row.validation for row in context.index.rows if row.refdes == "U1")
        assert validation.result == "UNKNOWN"
        assert len(validation.component_checks) == 1
        assert validation.component_checks[0].check == "bom_identity_conflict"
        assert not validation.pin_results
        assert all(c.result != "PASS" for c in validation.component_checks)
        assert all(
            row.validation.component_checks[0].check != "bom_identity_conflict"
            for row in context.index.rows
            if row.refdes != "U1"
        )
        task = next(t for t in state["review_tasks"] if t["refdes"] == "U1")
        reason = context.bom_report.identity_conflicts["U1"]
        for token in (
            "column4",
            "column5",
            "WRONG_PUBLIC_FIXTURE",
            "VendorA",
            "VendorB",
            "TO220",
            "SOT23",
            "#line2",
        ):
            assert token in reason
        assert task["status"] == "UNKNOWN"
        exported = client.get("/api/workbench/export?format=json").json()
        assert reason in json.dumps(exported, ensure_ascii=False)
        assert "WRONG_PUBLIC_FIXTURE" in client.get("/api/workbench/export?format=csv").text
        assert (
            "column4" in client.get("/api/workbench/components/U1/prep-packet?format=markdown").text
        )
        monkeypatch.setattr(
            workbench_spa_snapshot, "_inline_spa_shell", lambda data, **kwargs: data
        )
        offline = workbench_spa_snapshot.render_spa_snapshot(context)
        assert reason in offline["exports"]["json"]
        assert "SOT23" in offline["component_prep_markdown"]["U1"]
    _bom(path, False)
    repaired = _context(path)
    with TestClient(
        create_workbench_app(repaired, Chat(), auto_datasheet_candidates=False)
    ) as client:
        assert repaired.bom_report.identity_conflicts == {}
        assert "U1" in repaired.validation_targets
        assert all(
            t["check"] != "bom_identity_conflict"
            for t in client.get("/api/workbench/state").json()["review_tasks"]
        )
