"""Numeric uncertainty is local through actual intake, exports and decision replay."""

import csv
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app
from tests.xlsx_fixture import write_minimal_xlsx

ROOT = Path(__file__).parents[2]


class NoChat:
    datasheet_search_enabled = False


def inputs(root, suffix):
    netlist = root / "numeric.net"
    netlist.write_text(
        "$PACKAGES\n ! 'R0402' ! RES ; R1, R2, R3\n ! 'C0402' ! CAP ; C1\n"
        "$NETS\n 'P12' ; R1.1, R2.1\n 'RET' ; R1.2, R2.2, R3.2\n"
        " 'SMALL' ; R3.1\n 'HI' ; C1.1\n 'LO' ; C1.2\n$END\n"
    )
    headers = ["位号", "数量", "名称"] if suffix == ".xlsx" else ["Reference", "Quantity", "Value"]
    rows = [
        headers,
        ["R1", 1, "9" * 400 + "R 1W"],
        ["R2", 1, "1K 1W"],
        ["R3", 1, "0." + "0" * 299 + "1R 0." + "0" * 199 + "1W"],
        ["C1", 1, "1uF 25V"],
    ]
    bom = root / ("bom" + suffix)
    if suffix == ".xlsx":
        write_minimal_xlsx(bom, [[str(v) for v in row] for row in rows])
    else:
        with bom.open("w", newline="") as f:
            csv.writer(f, delimiter="\t" if suffix == ".tsv" else ",").writerows(rows)
    facts = root / "facts.json"
    facts.write_text(
        json.dumps(
            dict(
                facts=[
                    dict(
                        net=n,
                        reference_net="RET",
                        minimum=v,
                        maximum=v,
                        confirmed=True,
                        confirmed_by="synthetic fixture author",
                        source="public numeric fixture",
                    )
                    for n, v in [
                        ("P12", 12),
                        ("RET", 0),
                        ("SMALL", 1e-200),
                        ("HI", 1e308),
                        ("LO", -1e308),
                    ]
                ]
            )
        )
    )
    return netlist, bom, facts


def context(root, suffix=".csv"):
    paths = inputs(root, suffix)
    return build_workbench_context(
        netlist_path=paths[0],
        bom_path=paths[1],
        profiles=ROOT / "data/datasheet_profiles",
        voltage_facts=paths[2],
    )


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_import_unusable_numbers_keeps_other_checks_and_exports(tmp_path, suffix):
    c = context(tmp_path, suffix)
    try:
        with TestClient(
            create_workbench_app(
                c, NoChat(), auto_datasheet_candidates=False, review_db=tmp_path / "journal.sqlite"
            )
        ) as client:
            # Exercise uploaded intake, not only a hand-constructed model.
            files = {
                key: (path.name, path.read_bytes())
                for key, path in zip(
                    ["netlist", "bom", "voltage_facts_json"],
                    [
                        tmp_path / "numeric.net",
                        tmp_path / ("bom" + suffix),
                        tmp_path / "facts.json",
                    ],
                )
            }
            imported = client.post("/api/workbench/import", files=files)
            assert imported.status_code == 200, imported.text
            state = client.get("/api/workbench/state").json()
            selected = {(t["refdes"], t["check"]): t for t in state["review_tasks"]}
            for key in [
                ("R1", "resistor_value_parse"),
                ("R1", "resistor_power_estimate"),
                ("C1", "capacitor_voltage_margin"),
            ]:
                assert selected[key]["assessment"]["result"] == "UNKNOWN"
            small = selected["R3", "resistor_power_estimate"]
            assert small["assessment"]["result"] == "FAIL" and "1e-100 W" in small["body"]
            assert any(
                row["refdes"] == "R2" and row["deterministic_status"] == "PASS"
                for row in state["queue"]
            )
            assert "9" * 400 in client.get("/api/workbench/components/R1").text
            ids = state["review_decisions"]
            response = client.get(
                "/api/workbench/offline-report",
                params=dict(expected_project_id=ids["project_id"], expected_run_id=ids["run_id"]),
            )
            assert response.status_code == 200, response.text
            snap = json.loads(
                re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", response.text)[1]
            )
            assert snap["state"] == state
            assert "电阻值缺失或超出可计算数值范围" in snap["project_prep_markdown"]
            assert "电阻值缺失或超出可计算数值范围" in snap["exports"]["csv"]
            assert "1e-100 W" in snap["exports"]["annotations"]
            assert not snap["state"]["evidence_package"]["signoff_readiness"]["signoff_ready"]
    finally:
        close_workbench_context(c)


def test_rating_rule_version_change_reopens_once_preserving_original_reason(tmp_path):
    # Simulate the old producer version on identical numerical results. A separate
    # archived-source process probe verifies the real old/new implementation.
    from hardwise.workbench.decision_fingerprints import review_fingerprints, review_project_key
    from hardwise.workbench.task_projection import build_review_tasks
    from hardwise.workbench.review_decisions import ReviewDecisionStore, ReviewDecisionRequest

    c = context(tmp_path)
    try:
        tasks = build_review_tasks(c)
        current = next(
            t for t in tasks if t.refdes == "R1" and t.check == "resistor_power_estimate"
        )
        assert current.assessment.rule_version == "3"
        old = current.model_copy(
            update={"assessment": current.assessment.model_copy(update={"rule_version": "2"})}
        )
        store = ReviewDecisionStore(tmp_path / "replay.sqlite")
        key = review_project_key(c)
        old_fp = review_fingerprints(c, [old])
        store.begin_run(key, old_fp)
        rid = store.summary([old.stable_key], project=key).run_id
        store.update(
            request=ReviewDecisionRequest(
                stable_keys=[old.stable_key],
                status="accepted_risk",
                reason="合成规则升级测试，保留原理由，不是人工批准",
                expected_run_id=rid,
            ),
            known_keys=[old.stable_key],
            fingerprints=old_fp,
        )
        current_fp = review_fingerprints(c, [current])
        assert current_fp != old_fp
        store.begin_run(key, current_fp)
        item = store.apply([current], fingerprints=current_fp)[0].review_decision
        assert item.status == "needs_review" and item.previous_status == "accepted_risk"
        assert item.reason == "合成规则升级测试，保留原理由，不是人工批准"
        count = len(store.history())
        store.begin_run(key, current_fp)
        assert len(store.history()) == count == 2
    finally:
        close_workbench_context(c)
