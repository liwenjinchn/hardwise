"""A local placeholder must never certify delivery of an offline original."""

import csv
import io
import json
from pathlib import Path

from hardwise.report import workbench_spa_snapshot as snapshot
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.evidence_package import EvidencePackageSummary
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.workbench.server_io import _task_csv_response, _annotations_response
from hardwise.workbench.view_model import build_workbench_state

ROOT = Path(__file__).parents[2].resolve()


def _context():
    return build_workbench_context(
        netlist_path=ROOT / "tests/fixtures/allegro/l78_regulator.net",
        bom_path=ROOT / "tests/fixtures/allegro/l78_regulator_bom.csv",
        profiles=ROOT / "data/datasheet_profiles",
    )


def test_existing_placeholder_is_observation_not_delivered_original(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Deliberately not a real vendor PDF; existence is the only observation.
    original = tmp_path / "data/datasheets/l78.pdf"
    original.parent.mkdir(parents=True)
    original.write_text("SYNTHETIC_PLACEHOLDER_NEVER_VENDOR_PROOF")
    context = _context()
    try:
        state = build_workbench_state(context, datasheet_search_enabled=False)
        package = state.evidence_package
        assert package.source_audit.locally_present_tokens
        assert package.source_audit.observed_at
        assert not package.source_audit.missing_tokens
        assert package.original_delivery.status == "not_attached"
        assert package.original_delivery.attached_tokens == []
        assert package.original_delivery.missing_tokens == package.original_delivery.cited_tokens
        assert package.signoff_readiness.signoff_ready is False
        before = state.summary.model_dump()
        original.unlink()
        monkeypatch.setattr(snapshot, "_inline_spa_shell", lambda data, **kwargs: data)
        payload = snapshot.render_spa_snapshot(context)
        assert payload["state"]["evidence_package"] == package.model_dump(mode="json")
        assert payload["state"]["summary"] == before
        exported = json.loads(payload["exports"]["json"])
        assert exported["evidence_package"]["original_delivery"]["status"] == "not_attached"
        assert "SYNTHETIC_PLACEHOLDER_NEVER_VENDOR_PROOF" not in json.dumps(payload)
        assert "原文随附" in payload["project_prep_markdown"]
        assert "Missing original:" in payload["project_prep_markdown"]
        for body in (payload["exports"]["csv"], bytes(_task_csv_response(context).body).decode()):
            rows = list(csv.DictReader(io.StringIO(body)))
            assert rows
            cited = [row for row in rows if row["missing_original_tokens"]]
            assert cited
            assert all(row["original_delivery_status"] == "not_attached" for row in cited)
            assert all(row["export_allowed"] == "true" for row in rows)
            assert all(row["signoff_evidence_ready"] == "false" for row in rows)
        assert (
            payload["exports"]["annotations"] == bytes(_annotations_response(context).body).decode()
        )
        assert "original_delivery_status" in payload["exports"]["annotations"]
    finally:
        close_workbench_context(context)
    # Fresh observation reflects removal; neither observation supplies the original.
    reopened = _context()
    try:
        package = build_workbench_state(reopened, datasheet_search_enabled=False).evidence_package
        assert package.source_audit.missing_tokens
        assert package.original_delivery.status == "not_attached"
        markdown = render_project_review_prep_packet_markdown(
            build_project_review_prep_packet(reopened)
        )
        assert "Missing local sources:" in markdown
        assert "Missing original:" in markdown
    finally:
        close_workbench_context(reopened)


def test_old_package_does_not_infer_originals_from_ready_flag():
    legacy = EvidencePackageSummary.model_validate(
        {
            "schema_version": "hardwise.evidence_package.v1",
            "lanes": [],
            "signoff_readiness": {"status": "ready", "signoff_ready": True, "reason": "legacy"},
        }
    )
    assert legacy.bom_quantity_conflicts is None
    assert legacy.source_audit.status == "unknown"
    assert legacy.original_delivery.status == "unknown"
    assert legacy.original_delivery.attached_tokens == []


def test_uncheckable_pdf_reference_does_not_abort_offline_delivery(tmp_path, monkeypatch):
    import shutil

    # Alter only an owned synthetic copy's citation, not its electrical facts.
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copy2(ROOT / "data/datasheet_profiles/l78.json", profiles / "l78.json")
    raw = json.loads((profiles / "l78.json").read_text())
    token = "datasheet:" + "x" * 300 + ".pdf#p4"

    def rewrite(value):
        if isinstance(value, str):
            return token if value.startswith("datasheet:") else value
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        return value

    (profiles / "l78.json").write_text(json.dumps(rewrite(raw)))
    before = _context()
    context = build_workbench_context(
        netlist_path=ROOT / "tests/fixtures/allegro/l78_regulator.net",
        bom_path=ROOT / "tests/fixtures/allegro/l78_regulator_bom.csv",
        profiles=profiles,
    )
    try:
        baseline = build_workbench_state(before, datasheet_search_enabled=False)
        state = build_workbench_state(context, datasheet_search_enabled=False)
        assert state.summary == baseline.summary
        assert [(t.stable_key, t.assessment) for t in state.review_tasks] == [
            (t.stable_key, t.assessment) for t in baseline.review_tasks
        ]
        package = state.evidence_package
        assert token in package.source_audit.unchecked_tokens
        assert token not in package.source_audit.missing_tokens
        assert token not in package.source_audit.locally_present_tokens
        assert token in package.original_delivery.missing_tokens
        assert package.original_delivery.export_allowed
        assert not package.signoff_readiness.signoff_ready
        monkeypatch.setattr(snapshot, "_inline_spa_shell", lambda data, **kwargs: data)
        payload = snapshot.render_spa_snapshot(context)
        assert token in payload["state"]["evidence_package"]["source_audit"]["unchecked_tokens"]
        assert token in payload["project_prep_markdown"]
        assert "Unchecked source:" in payload["component_prep_markdown"]["U1"]
        assert token in payload["exports"]["csv"]
        assert token in payload["exports"]["annotations"]
    finally:
        close_workbench_context(before)
        close_workbench_context(context)
