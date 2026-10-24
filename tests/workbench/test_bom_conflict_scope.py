"""Duplicate BOM rows cannot bind a profile or certify passive/related topology."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from hardwise.agent.tools import RunComponentValidationInput, run_component_validation
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path("tests/fixtures/allegro")


class LocalOnlyChat:
    datasheet_search_enabled = False


def _context(tmp_path, refdes="U1", reverse=False):
    lines = (ROOT / "l78_regulator_bom.csv").read_text().splitlines()
    duplicate = f"{refdes},1,DIFFERENT_VALUE,Fixture,DIFFERENT_MPN"
    lines = [lines[0], *([duplicate, *lines[1:]] if reverse else [*lines[1:], duplicate])]
    bom = tmp_path / "conflict.csv"
    bom.write_text("\n".join(lines) + "\n")
    return build_workbench_context(
        netlist_path=ROOT / "l78_regulator.net",
        bom_path=bom,
        profiles=Path("data/datasheet_profiles"),
    )


@pytest.mark.parametrize("refdes", ["U1", "C1"])
@pytest.mark.parametrize("reverse", [False, True])
def test_conflict_blocks_profile_and_generic_fallback(tmp_path, refdes, reverse):
    context = _context(tmp_path, refdes, reverse)
    try:
        assert refdes not in context.bom_report.rows_by_refdes
        assert refdes not in context.bom_report.matched_refdes
        assert refdes not in context.validation_targets
        row = next(r for r in context.index.rows if r.refdes == refdes)
        assert row.match_status == "ambiguous"
        assert row.profile_path is None
        assert row.validation.result == "UNKNOWN"
        assert row.validation.needs_review
        assert [c.check for c in row.validation.component_checks] == ["bom_identity_conflict"]
        assert row.part_number != "DIFFERENT_MPN"
        assert "DIFFERENT_MPN" in row.reason
        assert "#line" in row.reason
        result = run_component_validation(
            context.design, context.validation_targets, RunComponentValidationInput(refdes=refdes)
        )
        assert result.status == "no_profile"
        assert "BOM" in result.reason
        unaffected = next(r for r in context.index.rows if r.refdes == "C2")
        assert unaffected.validation is not None
        assert "bom_identity_conflict" not in {
            c.check for c in unaffected.validation.component_checks
        }
    finally:
        close_workbench_context(context)


def test_import_rerun_and_export_do_not_select_a_conflicting_bom_row(tmp_path):
    initial = _context(tmp_path)
    conflict_bytes = initial.bom.source_file.read_bytes()
    with TestClient(
        create_workbench_app(initial, LocalOnlyChat(), auto_datasheet_candidates=False)
    ) as client:
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": ("l78.net", (ROOT / "l78_regulator.net").read_bytes(), "text/plain"),
                "bom": ("conflict.csv", conflict_bytes, "text/csv"),
            },
        )
        assert response.status_code == 200, response.text
        detail = client.get("/api/workbench/components/U1").json()
        assert detail["bom"] is None
        assert detail["profile"]["status"] == "ambiguous"
        assert all(c["assessment"]["result"] == "UNKNOWN" for c in detail["checks"])
        assert "DIFFERENT_MPN" in detail["profile"]["reason"]
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U1").json()["checks"] == detail["checks"]
        exported = client.get("/api/workbench/export?format=json").json()
        tasks = [t for t in exported["review_tasks"] if t["refdes"] == "U1"]
        assert any(t["check"] == "bom_identity_conflict" for t in tasks)
        assert all(t["assessment"]["result"] == "UNKNOWN" for t in tasks)


def test_explicit_profile_or_passive_call_cannot_bypass_identity_block(tmp_path):
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.validation.component import validate_component_against_profile
    from hardwise.validation.generic_passive import validate_generic_passive

    context = _context(tmp_path, "C1")
    try:
        component = context.design.components["C1"]
        profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
        formal = validate_component_against_profile(component, profile, context.design)
        passive = validate_generic_passive(component, None, context.design, "capacitor")
        assert formal == passive
        assert formal.result == "UNKNOWN"
        assert formal.pin_results == []
        explicit = run_component_validation(
            context.design, {"C1": profile}, RunComponentValidationInput(refdes="C1")
        )
        assert explicit.status == "no_profile"
        assert "BOM" in explicit.reason
    finally:
        close_workbench_context(context)


def test_ambiguous_peer_blocks_topology_but_keeps_connection_observations(tmp_path):
    bom = tmp_path / "shift.csv"
    bom.write_text(
        (ROOT / "shift_register_chain_bom.csv").read_text() + "U2,1,OTHER,Fixture,OTHER\n"
    )
    context = build_workbench_context(
        netlist_path=ROOT / "shift_register_chain.net",
        bom_path=bom,
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        report = next(r.validation for r in context.index.rows if r.refdes == "U1")
        assert all(c.result == "UNKNOWN" and c.needs_review for c in report.component_checks)
        assert all("U2" in c.summary and "BOM" in c.summary for c in report.component_checks)
        assert any(p.result == "PASS" for p in report.pin_results)
        assert "U1" in context.validation_targets
        assert "U2" not in context.validation_targets
    finally:
        close_workbench_context(context)
