"""Production intake/managed reopen must retain multi-source premises, not just values."""

import hashlib
import json
from pathlib import Path
import re
import shutil

from fastapi.testclient import TestClient
import pytest

from hardwise.ir.voltage_review import VoltageReviewDocument
from hardwise.validation.voltage_facts import load_voltage_facts
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.decision_fingerprints import review_fingerprints
from hardwise.workbench.managed_projects import ManagedProjects
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.server import create_workbench_app
from hardwise.workbench.task_projection import build_review_tasks
from tests.ir.test_voltage_review import candidate, select
from tests.workbench.test_voltage_facts import NETLIST, BOM


class NoChat:
    datasheet_search_enabled = False


@pytest.fixture
def inputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "input.net").write_text(NETLIST)
    (source / "bom.csv").write_text(BOM)
    profiles = source / "profiles"
    profiles.mkdir()
    shutil.copyfile("data/datasheet_profiles/l78.json", profiles / "l78.json")
    review = VoltageReviewDocument(
        candidates=(
            candidate("p12", 12, net="P12"),
            candidate("p24", 24, net="P12"),
            candidate("n12", -12, net="N12"),
            candidate("gnd", 0, net="GND"),
        )
    )
    review = select(
        review,
        ("N12", "dc", "confirm", "n12"),
        ("GND", "dc", "confirm", "gnd"),
        known_nets={"P12", "N12", "GND"},
    )
    path = source / "review.json"
    path.write_text(review.model_dump_json())
    return source, path, review


def build(inputs):
    source, path, _ = inputs
    return build_workbench_context(
        netlist_path=source / "input.net",
        bom_path=source / "bom.csv",
        profiles=source / "profiles",
        voltage_facts=path,
    )


def checks(context, refdes):
    return next(r.validation for r in context.index.rows if r.refdes == refdes).component_checks


def test_conflicts_remain_unknown_and_raw_ledger_is_recorded(inputs):
    context = build(inputs)
    try:
        assert context.design.voltage_review == inputs[2]
        assert checks(context, "C1")[-1].result == "UNKNOWN"
        assert checks(context, "R1")[-1].result == "PASS"
        provenance = build_run_provenance(context)
        assert provenance.voltage_review == inputs[2]
        raw = provenance.model_dump(mode="json")
        assert raw["voltage_review"] == inputs[2].model_dump(mode="json")
        source_record = next(f for f in context.input_manifest.files if f.path == str(inputs[1]))
        assert source_record.sha256 == hashlib.sha256(inputs[1].read_bytes()).hexdigest()
    finally:
        close_workbench_context(context)


def test_resolved_projection_uses_selected_source_and_full_ledger_survives_reopen(inputs, tmp_path):
    source, path, review = inputs
    resolved = select(review, ("P12", "dc", "confirm", "p12"), known_nets={"P12", "N12", "GND"})
    path.write_text(resolved.model_dump_json())
    raw = path.read_bytes()
    context = build(inputs)
    journal = tmp_path / "journal.sqlite"
    with TestClient(
        create_workbench_app(context, NoChat(), review_db=journal, auto_datasheet_candidates=False)
    ) as client:
        state = client.get("/api/workbench/state").json()
        run = state["review_decisions"]["run_id"]
        assert checks(context, "C1")[-1].result == "FAIL"
        response = client.post("/api/workbench/projects/save", params={"expected_run_id": run})
        assert response.status_code == 200, response.text
        project = ManagedProjects(journal).list()[0]
        before = build_run_provenance(context).model_dump(mode="json")
        tasks = build_review_tasks(context)
        before_fingerprints = review_fingerprints(context, tasks)
        shutil.rmtree(source)
        opened, directory = ManagedProjects(journal).open(project["id"])
        try:
            assert opened.design.voltage_review == resolved
            assert opened.voltage_facts_path.read_bytes() == raw
            assert opened.design.voltage_facts == context.design.voltage_facts
            assert review_fingerprints(opened, build_review_tasks(opened)) == before_fingerprints
            assert build_run_provenance(opened).voltage_review == resolved
        finally:
            close_workbench_context(opened)
            shutil.rmtree(directory)
        offline = client.get(
            "/api/workbench/offline-report",
            params={
                "expected_project_id": state["review_decisions"]["project_id"],
                "expected_run_id": run,
            },
        )
        assert offline.status_code == 200, offline.text
        payload = json.loads(
            re.search(r"window\.__HARDWISE_OFFLINE_SNAPSHOT__ = (.*);\n", offline.text)[1]
        )
        assert payload["run_provenance"]["voltage_review"] == before["voltage_review"]
        assert len(payload["run_provenance"]["voltage_review"]["candidates"]) == 4


@pytest.mark.parametrize("foreign_kind", ["unselected_net", "unselected_reference", "declaration"])
def test_foreign_ledger_input_rejects_before_replacing_facts(inputs, foreign_kind):
    context = build(inputs)
    try:
        before = context.design.voltage_facts
        ledger = context.design.voltage_review
        raw = ledger.model_dump(mode="json")
        if foreign_kind == "unselected_net":
            raw["candidates"][1]["fact"]["net"] = "FOREIGN"
        elif foreign_kind == "unselected_reference":
            raw["candidates"][1]["fact"]["reference_net"] = "FOREIGN"
        else:
            raw["confirmations"][0]["net"] = "FOREIGN"
        bad = inputs[0] / "bad.json"
        bad.write_text(json.dumps(raw))
        with pytest.raises(ValueError, match="unknown nets"):
            load_voltage_facts(bad, context.design)
        assert context.design.voltage_facts is before and context.design.voltage_review is ledger
    finally:
        close_workbench_context(context)


def test_candidate_change_with_same_unknown_result_invalidates_only_local_decision(inputs):
    bom = inputs[0] / "bom.csv"
    bom.write_text(bom.read_text().replace("1K 1/4W", "1K"))
    context = build(inputs)
    try:
        before = review_fingerprints(context, build_review_tasks(context))
        tasks = {
            t.refdes: t
            for t in build_review_tasks(context)
            if t.check in {"capacitor_voltage_margin", "resistor_power_estimate"}
        }
    finally:
        close_workbench_context(context)
    source, path, review = inputs
    candidates = list(review.candidates)
    candidates[1] = candidate("p24", 36, net="P12")
    path.write_text(
        VoltageReviewDocument(
            candidates=tuple(candidates), confirmations=review.confirmations
        ).model_dump_json()
    )
    context = build(inputs)
    try:
        after = review_fingerprints(context, build_review_tasks(context))
        assert before[tasks["C1"].stable_key] != after[tasks["C1"].stable_key]
        assert before[tasks["R1"].stable_key] == after[tasks["R1"].stable_key]
        assert checks(context, "C1")[-1].result == "UNKNOWN"
    finally:
        close_workbench_context(context)


def test_loading_legacy_v1_clears_old_ledger_without_backfilling_provenance(inputs):
    context = build(inputs)
    try:
        legacy = inputs[0] / "legacy.json"
        legacy.write_text('{"facts": []}')
        load_voltage_facts(legacy, context.design)
        assert context.design.voltage_review is None
        assert "voltage_review" not in build_run_provenance(context).model_dump(mode="json")
    finally:
        close_workbench_context(context)


def test_real_import_rerun_backup_restore_retains_full_ledger(inputs, tmp_path):
    source, path, review = inputs
    context = build(inputs)
    with TestClient(
        create_workbench_app(
            context, NoChat(), review_db=tmp_path / "api.sqlite", auto_datasheet_candidates=False
        )
    ) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("input.net", NETLIST, "text/plain"),
                "bom": ("bom.csv", BOM, "text/csv"),
                "voltage_facts_json": ("ledger.json", path.read_bytes(), "application/json"),
            },
        )
        assert response.status_code == 200, response.text
        state = client.get("/api/workbench/state").json()
        assert client.post("/api/workbench/rerun").status_code == 200
        state = client.get("/api/workbench/state").json()
        run = state["review_decisions"]["run_id"]
        query = {"expected_run_id": run}
        assert client.post("/api/workbench/projects/save", params=query).status_code == 200
        backup = client.post("/api/workbench/projects/backup", params=query)
        assert backup.status_code == 200, backup.text
        restored = client.post(
            "/api/workbench/projects/restore",
            params=query,
            files={"archive": ("backup.zip", backup.content, "application/zip")},
        )
        assert restored.status_code == 200, restored.text
        receipt = restored.json()
        catalog = ManagedProjects(Path(receipt["journal"]))
        shutil.rmtree(source)
        opened, directory = catalog.open(receipt["saved_project_ids"][0])
        try:
            assert opened.design.voltage_review == review
            assert checks(opened, "C1")[-1].result == "UNKNOWN"
            assert checks(opened, "R1")[-1].result == "PASS"
            assert len(opened.design.voltage_review.candidates) == 4
            assert len(opened.design.voltage_review.confirmations) == 2
        finally:
            close_workbench_context(opened)
            shutil.rmtree(directory)


def test_old_download_keeps_original_ledger_after_source_changes_and_rerun(inputs, tmp_path):
    context = build(inputs)
    with TestClient(
        create_workbench_app(
            context,
            NoChat(),
            review_db=tmp_path / "history.sqlite",
            auto_datasheet_candidates=False,
        )
    ) as client:
        before = client.get("/api/workbench/state").json()
        project = before["review_decisions"]["project_id"]
        old_run = before["review_decisions"]["run_id"]
        old = client.get(
            f"/api/workbench/review-runs/{old_run}/provenance",
            params={"expected_project_id": project},
        )
        assert old.status_code == 200, old.text
        ledger = old.json()["provenance"]["voltage_review"]
        assert ledger == inputs[2].model_dump(mode="json")
        resolved = select(
            inputs[2], ("P12", "dc", "confirm", "p12"), known_nets={"P12", "N12", "GND"}
        )
        inputs[1].write_text(resolved.model_dump_json())
        response = client.post("/api/workbench/rerun")
        assert response.status_code == 200, response.text
        new_run = response.json()["review_decisions"]["run_id"]
        assert new_run != old_run
        current = client.get(
            f"/api/workbench/review-runs/{new_run}/provenance",
            params={"expected_project_id": project},
        )
        assert current.status_code == 200, current.text
        assert current.json()["provenance"]["voltage_review"] == resolved.model_dump(mode="json")
        assert (
            client.get(
                f"/api/workbench/review-runs/{old_run}/provenance",
                params={"expected_project_id": project},
            ).json()
            == old.json()
        )


def test_exported_contract_allows_historical_runs_without_ledger():
    schema = json.loads(
        Path("frontend/workbench/src/generated/workbench-contracts.schema.json").read_text()
    )
    definition = schema["$defs"]["RunProvenance"]
    assert "voltage_review" in definition["properties"]
    assert "voltage_review" not in definition["required"]
    assert "emitted_records" in definition["required"]
