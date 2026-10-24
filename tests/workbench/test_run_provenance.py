"""Captured sources persist with the run; old evidence never uses today's file hashes."""

import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.server import create_workbench_app

ROOT = Path(__file__).parents[2]


class LocalOnlyChat:
    datasheet_search_enabled = False


@pytest.fixture
def project(tmp_path):
    fixtures = ROOT / "tests/fixtures/allegro"
    for name in ("l78_regulator.net", "l78_regulator_bom.csv"):
        shutil.copyfile(fixtures / name, tmp_path / name)
    (tmp_path / "profiles").mkdir()
    shutil.copyfile(ROOT / "data/datasheet_profiles/l78.json", tmp_path / "profiles/l78.json")
    (tmp_path / "facts.json").write_text(
        json.dumps(
            {
                "schema_version": "hardwise.voltage_facts.v1",
                "active_mode": "dc",
                "facts": [
                    {
                        "net": n,
                        "reference_net": "GND",
                        "minimum": v,
                        "maximum": v,
                        "confirmed": True,
                        "source": "public synthetic premise",
                        "confirmed_by": "test author",
                    }
                    for n, v in [("+12V", 12), ("GND", 0)]
                ],
            }
        )
    )
    return tmp_path


def _context(root, **kwargs):
    return build_workbench_context(
        netlist_path=root / "l78_regulator.net",
        bom_path=root / "l78_regulator_bom.csv",
        profiles=root / "profiles",
        voltage_facts=root / "facts.json",
        **kwargs,
    )


def _app(root, durable=True):
    return create_workbench_app(
        _context(root),
        LocalOnlyChat(),
        auto_datasheet_candidates=False,
        review_db=root / "review.sqlite" if durable else None,
    )


def _url(run):
    return f"/api/workbench/review-runs/{run}/provenance"


def _file(payload, role):
    return next(f for f in payload["provenance"]["inputs"]["files"] if role in f["roles"])


def test_every_optional_intake_reader_records_its_actual_source(project):
    shutil.copyfile(ROOT / "tests/fixtures/allegro/document_match/docs.csv", project / "docs.csv")
    shutil.copyfile(ROOT / "tests/fixtures/capture/pin_table_demo.csv", project / "pins.csv")
    (project / "risk.json").write_text('{"hints": []}')
    (project / "notes.txt").write_text("public synthetic notes")
    (project / "review.json").write_text(
        '{"artifacts":[{"kind":"review_notes","path":"notes.txt"}]}'
    )
    context = _context(
        project,
        document_index=project / "docs.csv",
        pin_table=project / "pins.csv",
        risk_hints_json=project / "risk.json",
        review_package_manifest=project / "review.json",
    )
    try:
        provenance = build_run_provenance(context)
        roles = {r for item in provenance.inputs.files for r in item.roles}
        assert roles == {
            "netlist",
            "bom",
            "profile",
            "voltage_facts",
            "document_index",
            "pin_table",
            "risk_hints",
            "review_package",
            "review_artifact_digest",
        }
        assert provenance.raw_inputs_archived is False
        assert provenance.emitted_records == context.index.assessment_coverage.generated_checks
        assert (
            sum(rule.emitted_count for rule in provenance.rule_versions)
            == provenance.emitted_records
        )
        assert provenance.profiles[0].values == context.validation_targets["U1"].model_dump(
            mode="json"
        )
        assert provenance.profile_bindings["U1"] == provenance.profiles[0].sha256
        for item in provenance.inputs.files:
            assert item.sha256 == hashlib.sha256(Path(item.path).read_bytes()).hexdigest()
    finally:
        close_workbench_context(context)


@pytest.mark.parametrize("durable", [False, True])
def test_old_run_keeps_original_raw_hash_when_cosmetic_edit_preserves_waiver(project, durable):
    with TestClient(_app(project, durable)) as client:
        state = client.get("/api/workbench/state").json()
        run, pid = [state["review_decisions"][name] for name in ("run_id", "project_id")]
        before = client.get(_url(run), params={"expected_project_id": pid}).json()
        assert before["status"] == "recorded"
        task = next(
            t
            for t in state["review_tasks"]
            if t["refdes"] == "C1" and t["check"] == "capacitor_voltage_margin"
        )
        assert (
            client.put(
                "/api/workbench/review-decisions",
                json={
                    "stable_keys": [task["stable_key"]],
                    "status": "waived",
                    "reason": "Public synthetic historical reason",
                    "expected_run_id": run,
                },
            ).status_code
            == 200
        )
        with (project / "l78_regulator_bom.csv").open("a") as stream:
            stream.write("\n")
        state = client.post("/api/workbench/rerun").json()
        assert state["review_decisions"]["waived"] == 1
        after = client.get(_url(state["review_decisions"]["run_id"])).json()
        assert _file(before, "bom")["sha256"] != _file(after, "bom")["sha256"]
        assert client.get(_url(run)).json() == before
        assert after["provenance"]["profiles"] == before["provenance"]["profiles"]
        assert (
            client.get(_url(run), params={"expected_project_id": "old-project"}).status_code == 409
        )
        assert client.get(_url("missing-run")).status_code == 404
        assert "attachment" in client.get(_url(run)).headers["content-disposition"]
    if durable:
        with TestClient(_app(project)) as restarted:
            assert restarted.get(_url(run)).json() == before


def test_legacy_run_explicitly_lacks_provenance_without_reading_current_files(project):
    import sqlite3

    with TestClient(_app(project)) as client:
        run = client.get("/api/workbench/state").json()["review_decisions"]["run_id"]
    with sqlite3.connect(project / "review.sqlite") as db:
        data = json.loads(
            db.execute("SELECT data FROM review_runs WHERE run_id=?", (run,)).fetchone()[0]
        )
        data.pop("provenance")
        db.execute("UPDATE review_runs SET data=? WHERE run_id=?", (json.dumps(data), run))
    with TestClient(_app(project)) as client:
        response = client.get(_url(run)).json()
        assert response["status"] == "not_recorded"
        assert response["provenance"] is None
        assert "no hashes were reconstructed" in response["reason"]


def test_changed_import_closes_candidate_and_keeps_active_project(project, monkeypatch):
    from hardwise.workbench import context as context_module

    app = _app(project)
    with TestClient(app) as client:
        before = client.get("/api/workbench/state").json()
        original_create, original_populate = (
            context_module.create_store,
            context_module.populate_from_registry,
        )
        created = []

        def create(*args, **kwargs):
            session = original_create(*args, **kwargs)
            session.close = Mock(wraps=session.close)
            created.append(session)
            return session

        def populate(session, registry):
            original_populate(session, registry)
            with (registry.project_dir / "bom.csv").open("a") as stream:
                stream.write("\n")

        monkeypatch.setattr(context_module, "create_store", create)
        monkeypatch.setattr(context_module, "populate_from_registry", populate)
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (
                    "board.net",
                    (project / "l78_regulator.net").read_bytes(),
                    "text/plain",
                ),
                "bom": ("bom.csv", (project / "l78_regulator_bom.csv").read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 400 and "input changed" in response.text
        assert client.get("/api/workbench/state").json() == before
        assert len(created) == 1
        created[0].close.assert_called_once()


def test_pst_group_records_all_three_consumed_sources(project):
    import csv
    from hardwise.adapters.allegro_pst import parse_allegro_pst

    directory = project / "pst"
    shutil.copytree(ROOT / "tests/fixtures/allegro/pst", directory)
    registry = parse_allegro_pst(directory)
    with (project / "pst.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Reference", "Quantity", "Value"])
        for part in registry.parts:
            writer.writerow([part.refdes, 1, part.primitive_name])
    context = build_workbench_context(
        netlist_path=directory, bom_path=project / "pst.csv", profiles=project / "profiles"
    )
    try:
        files = [item for item in context.input_manifest.files if "pst" in item.roles]
        assert {Path(item.path).name for item in files} == {
            "pstxprt.dat",
            "pstxnet.dat",
            "pstchip.dat",
        }
        for item in files:
            assert item.sha256 == hashlib.sha256(Path(item.path).read_bytes()).hexdigest()
    finally:
        close_workbench_context(context)


def test_real_project_import_cannot_read_previous_projects_run(project):
    with TestClient(_app(project)) as client:
        original = client.get("/api/workbench/state").json()["review_decisions"]
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("board.net", (project / "l78_regulator.net").read_bytes()),
                "bom": ("bom.csv", (project / "l78_regulator_bom.csv").read_bytes()),
            },
        )
        assert response.status_code == 200
        assert client.get(_url(original["run_id"])).status_code == 404
        assert (
            client.get(
                _url(original["run_id"]),
                params={"expected_project_id": original["project_id"]},
            ).status_code
            == 409
        )


def test_offline_export_preserves_captured_inputs_without_inventing_journal_run(
    project, monkeypatch
):
    from hardwise.report import workbench_spa_snapshot as snapshot

    context = _context(project)
    try:
        original = context.input_manifest.model_dump(mode="json")
        with (project / "l78_regulator_bom.csv").open("a") as stream:
            stream.write("\n")
        monkeypatch.setattr(snapshot, "_inline_spa_shell", lambda data, **kwargs: data)
        payload = snapshot.render_spa_snapshot(context)
        assert payload["run_provenance"]["inputs"] == original
        assert payload["run_provenance"]["raw_inputs_archived"] is False
        assert (
            payload["run_provenance"]["emitted_records"]
            == context.index.assessment_coverage.generated_checks
        )
        assert "run_id" not in payload["run_provenance"]
    finally:
        close_workbench_context(context)
