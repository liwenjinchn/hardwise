"""Actual input/re-run paths isolate uncertain edges without erasing history."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hardwise.workbench.context import build_workbench_context
from hardwise.workbench.server import create_workbench_app


class NoChat:
    datasheet_search_enabled = False


def inputs(root, signal="SIGNAL ; R1.1 R2.1"):
    net = root / "input.net"
    bom = root / "bom.csv"
    net.write_text(
        f"$PACKAGES\nR0603 ! RES ; R1 R2 R3\n$NETS\n{signal}\nGND ; R1.2 R2.2 R3.2\nOTHER ; R3.1\n$END\n"
    )
    bom.write_text(
        "Reference,Value,Footprint\nR1,10K 0.25W,R0603\nR2,10K 0.25W,R0603\nR3,10K 0.25W,R0603\n"
    )
    return net, bom


def app(root):
    context = build_workbench_context(
        netlist_path=root / "input.net",
        bom_path=root / "bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    return create_workbench_app(
        context, NoChat(), auto_datasheet_candidates=False, review_db=root / "review.sqlite"
    )


@pytest.mark.parametrize(
    "declarations",
    [
        "SIGNAL ; R1.1\nSIGNAL ; R2.1",
        "SIGNAL ; R2.1\nSIGNAL ; R1.1",
        "A ; R1.1 R2.1\nB ; R1.1",
        "SIGNAL ; R1.1 R1.1 R2.1",
    ],
)
def test_actual_upload_isolates_all_affected_endpoints_and_keeps_unrelated_branch(
    tmp_path, declarations
):
    net, bom = inputs(tmp_path)
    application = app(tmp_path)
    with TestClient(application) as client:
        inputs(tmp_path, declarations)
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (net.name, net.read_bytes(), "text/plain"),
                "bom": (bom.name, bom.read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 200, response.text
        context = application.state.workbench_context["value"]
        assert context.design.connectivity.ambiguities
        for ref in ("R1", "R2"):
            detail = client.get(f"/api/workbench/components/{ref}").json()
            pin = next(p for p in detail["pins"] if p["number"] == "1")
            assert pin["status"] == "UNKNOWN" and pin["connection_ambiguity"] and pin["net"] is None
        other = client.get("/api/workbench/components/R3").json()
        assert all(p["status"] == "PASS" for p in other["pins"])
        state = client.get("/api/workbench/state").json()
        assert "连接到 未命名网络" not in str(state["review_tasks"])
        assert any("无确定网络" in t["body"] for t in state["review_tasks"])
        ids = state["review_decisions"]
        report = client.get(
            "/api/workbench/offline-report",
            params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
        )
        assert report.status_code == 200
        assert '"ambiguous_net_names"' in report.text and '"declarations"' in report.text


def test_rerun_ambiguity_then_correction_does_not_resurrect_old_acceptance(tmp_path):
    inputs(tmp_path)
    with TestClient(app(tmp_path)) as client:
        state = client.get("/api/workbench/state").json()
        task = next(
            t
            for t in state["review_tasks"]
            if t["refdes"] == "R1" and t["kind"] == "component_check"
        )
        update = client.put(
            "/api/workbench/review-decisions",
            json={
                "stable_keys": [task["stable_key"]],
                "status": "accepted_risk",
                "reason": "Synthetic migration record only",
                "expected_run_id": state["review_decisions"]["run_id"],
            },
        )
        assert update.status_code == 200, update.text
        inputs(tmp_path, "SIGNAL ; R1.1\nSIGNAL ; R2.1")
        changed = client.post("/api/workbench/rerun")
        assert changed.status_code == 200, changed.text
        row = next(
            t for t in changed.json()["review_tasks"] if t["stable_key"] == task["stable_key"]
        )
        assert row["review_decision"]["status"] == "needs_review"
        inputs(tmp_path)
        fixed = client.post("/api/workbench/rerun").json()
        row = next(t for t in fixed["review_tasks"] if t["stable_key"] == task["stable_key"])
        assert row["review_decision"]["status"] == "needs_review"
    with sqlite3.connect(tmp_path / "review.sqlite") as db:
        assert db.execute("SELECT count(*) FROM review_events").fetchone()[0] >= 2
    with TestClient(app(tmp_path)) as client:
        state = client.get("/api/workbench/state").json()
        row = next(t for t in state["review_tasks"] if t["stable_key"] == task["stable_key"])
        assert row["review_decision"]["status"] == "needs_review"


@pytest.mark.parametrize(
    "tail",
    [
        "NET_NAME\n'VCC_3V3'\nNODE_NAME R1 99\n '@synthetic':\n '99':;\n",
        "NET_NAME\n'EXTRA'\nNODE_NAME C1 1\n '@synthetic':\n '1':;\n",
    ],
)
def test_pst_source_parser_preserves_conflicting_records_and_independent_net(tmp_path, tail):
    import shutil
    from hardwise.adapters.allegro_pst import parse_allegro_pst
    from hardwise.ir.build import build_design_from_pst

    shutil.copytree(Path("tests/fixtures/allegro/pst"), tmp_path / "pst")
    path = tmp_path / "pst/pstxnet.dat"
    original = path.read_text()
    path.write_text(original + tail)
    registry = parse_allegro_pst(path)
    design = build_design_from_pst(registry)
    assert "VCC_3V3" in design.connectivity.ambiguous_net_names
    assert "VCC_3V3" not in design.nets
    assert design.nets["CTRL"].nodes == [("U1", "1"), ("R1", "2")]
    assert len(design.connectivity.declarations) == len(registry.nets) == 4
    assert design.connectivity.declarations[-1].line == len(original.splitlines()) + 1
    assert path.read_text() == original + tail
