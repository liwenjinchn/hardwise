"""Single-row manufacturer declarations cannot silently overwrite netlist identity."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path("tests/fixtures/allegro")


class LocalOnlyChat:
    datasheet_search_enabled = False


def _inputs(tmp_path, declarations, bom_mpn="L7812", bom_value="L7805"):
    netlist = tmp_path / "identity.net"
    text = (ROOT / "l78_regulator.net").read_text()
    records = "\n".join(f"  '{field}' '{value}' ; U1" for field, value in declarations)
    netlist.write_text(text.replace("$NETS", f"$A_PROPERTIES\n{records}\n$NETS"))
    bom = tmp_path / "identity.csv"
    bom.write_text(
        f'Reference,Quantity,Value,Manufacturer,MPN\nU1,1,{bom_value},ST,{bom_mpn}\n"C1 C2",2,100nF,Fixture,CAP-100N\n'
    )
    return netlist, bom


def _context(paths):
    netlist, bom = paths
    return build_workbench_context(
        netlist_path=netlist, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )


@pytest.mark.parametrize("field", ["MPN", "Manufacturer Part Number", "MFR_PART_NUMBER"])
def test_explicit_mpn_disagreement_has_two_sources_and_no_selected_row(tmp_path, field):
    context = _context(_inputs(tmp_path, [(field, "L7805")]))
    try:
        assert not context.bom_report.is_clean
        assert "U1" not in context.bom_report.rows_by_refdes
        assert "U1" not in context.bom_report.matched_refdes
        assert "U1" not in context.validation_targets
        assert len(context.bom_report.conflicting_rows["U1"]) == 1
        reason = context.bom_report.identity_conflicts["U1"]
        assert "L7805" in reason and "L7812" in reason
        assert "identity.net#A_PROPERTIES[1]" in reason
        assert "identity.csv#line2" in reason
        row = next(r for r in context.index.rows if r.refdes == "U1")
        assert row.match_status == "ambiguous" and row.profile_path is None
        assert row.validation.result == "UNKNOWN" and row.validation.needs_review
        assert context.design.components["U1"].part_number != "L7812"
    finally:
        close_workbench_context(context)
    corrected = _context(_inputs(tmp_path, [(field, "L7805")], bom_mpn="L7805"))
    try:
        assert corrected.bom_report.identity_conflicts == {}
        assert "U1" in corrected.validation_targets
        assert "BOM_IDENTITY_CONFLICT" not in corrected.design.components["U1"].properties
    finally:
        close_workbench_context(corrected)


@pytest.mark.parametrize(
    "field,value,bom_mpn",
    [
        ("MPN", " l7805 ", "L7805"),
        ("PART_NAME", "LIBRARY_SYMBOL", "L7812"),
        ("ROOM", "L7805", "L7812"),
    ],
)
def test_case_whitespace_and_library_labels_do_not_create_mpn_conflicts(
    tmp_path, field, value, bom_mpn
):
    context = _context(_inputs(tmp_path, [(field, value)], bom_mpn=bom_mpn))
    try:
        assert context.bom_report.identity_conflicts == {}
        assert "U1" in context.bom_report.rows_by_refdes
    finally:
        close_workbench_context(context)


def test_two_netlist_declarations_cannot_select_the_one_that_matches_bom(tmp_path):
    context = _context(
        _inputs(tmp_path, [("MPN", "L7805"), ("MFR_PART_NUMBER", "L7812")], bom_mpn="L7805")
    )
    try:
        reason = context.bom_report.identity_conflicts["U1"]
        assert "A_PROPERTIES[1]" in reason and "A_PROPERTIES[2]" in reason
        assert "U1" not in context.validation_targets
    finally:
        close_workbench_context(context)


def test_declared_netlist_mpn_blocks_a_different_profile_even_without_bom_mpn(tmp_path):
    context = _context(_inputs(tmp_path, [("MPN", "L7805")], bom_mpn="", bom_value="STM32G030C8T6"))
    try:
        assert context.bom_report.identity_conflicts == {}  # absence is not a contradictory MPN
        candidate = next(c for c in context.candidate_report.candidates if c.refdes == "U1")
        assert candidate.match_status == "ambiguous"
        assert candidate.profile is None
        assert "网表明确 MPN" in candidate.reason
        assert "U1" not in context.validation_targets
        assert "BOM_IDENTITY_CONFLICT" in context.design.components["U1"].properties
    finally:
        close_workbench_context(context)


def test_api_import_rerun_and_export_keep_single_row_identity_unknown(tmp_path):
    paths = _inputs(tmp_path, [("MPN", "L7805")])
    with TestClient(
        create_workbench_app(_context(paths), LocalOnlyChat(), auto_datasheet_candidates=False)
    ) as client:
        netlist, bom = paths
        response = client.post(
            "/api/workbench/import",
            files={
                "netlist": (netlist.name, netlist.read_bytes(), "text/plain"),
                "bom": (bom.name, bom.read_bytes(), "text/csv"),
            },
        )
        assert response.status_code == 200, response.text
        state = client.get("/api/workbench/state").json()
        bom_lane = next(lane for lane in state["evidence_package"]["lanes"] if lane["id"] == "bom")
        assert any(
            m["key"] == "identity_conflicts" and m["value"] == 1 for m in bom_lane["metrics"]
        )
        detail = client.get("/api/workbench/components/U1").json()
        assert detail["bom"] is None and detail["profile"]["status"] == "ambiguous"
        assert all(c["assessment"]["result"] == "UNKNOWN" for c in detail["checks"])
        assert client.post("/api/workbench/rerun").status_code == 200
        assert client.get("/api/workbench/components/U1").json()["checks"] == detail["checks"]
        tasks = client.get("/api/workbench/export?format=json").json()["review_tasks"]
        assert any(t["refdes"] == "U1" and t["check"] == "bom_identity_conflict" for t in tasks)


def test_pst_explicit_mpn_keeps_primitive_property_source(tmp_path):
    import csv
    import shutil
    from hardwise.adapters.allegro_pst import parse_allegro_pst

    pst = tmp_path / "pst"
    shutil.copytree(ROOT / "pst", pst)
    registry = parse_allegro_pst(pst)
    selected = registry.parts[0]
    chip = pst / "pstchip.dat"
    text = chip.read_text()
    old = f"PART_NAME='{selected.properties['PART_NAME']}';"
    chip.write_text(text.replace(old, old + "\n    MPN='NETLIST_DECLARED_PART';", 1))
    bom = tmp_path / "pst.csv"
    with bom.open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Reference", "Quantity", "Value", "MPN"])
        for part in registry.parts:
            writer.writerow(
                [
                    part.refdes,
                    1,
                    part.properties.get("VALUE", ""),
                    "BOM_DECLARED_PART"
                    if part.refdes == selected.refdes
                    else part.properties.get("PART_NAME", ""),
                ]
            )
    context = build_workbench_context(
        netlist_path=pst, bom_path=bom, profiles=Path("data/datasheet_profiles")
    )
    try:
        reason = context.bom_report.identity_conflicts[selected.refdes]
        assert "pstchip.dat#primitive=" in reason and "field=MPN" in reason
        assert "NETLIST_DECLARED_PART" in reason and "BOM_DECLARED_PART" in reason
        row = next(r for r in context.index.rows if r.refdes == selected.refdes)
        assert row.validation.result == "UNKNOWN" and row.validation.needs_review
    finally:
        close_workbench_context(context)


def test_explicit_profile_assignment_cannot_override_netlist_declared_mpn(tmp_path):
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.validation.component import validate_component_against_profile

    context = _context(_inputs(tmp_path, [("MPN", "L7805")], bom_mpn="L7805"))
    try:
        profile = DatasheetProfile.load(Path("data/datasheet_profiles/stm32g030c8t6.json"))
        report = validate_component_against_profile(
            context.design.components["U1"], profile, context.design
        )
        assert report.result == "UNKNOWN" and report.needs_review
        assert report.pin_results == []
        assert report.component_checks[0].check == "profile_identity_conflict"
    finally:
        close_workbench_context(context)


def test_mpn_source_coordinates_and_typographic_whitespace_are_not_electrical_facts(tmp_path):
    from hardwise.workbench.decision_fingerprints import review_fingerprints
    from hardwise.workbench.task_projection import build_review_tasks

    first = _context(_inputs(tmp_path, [("MPN", "L7805")], bom_mpn="L7805"))
    try:
        task = next(
            t for t in build_review_tasks(first) if t.refdes == "U1" and t.kind == "pin_check"
        )
        before = review_fingerprints(first, [task])[task.stable_key]
    finally:
        close_workbench_context(first)
    second = _context(
        _inputs(tmp_path, [("ROOM", "ignored location"), ("MPN", " l7805 ")], bom_mpn="L7805")
    )
    try:
        task = next(t for t in build_review_tasks(second) if t.stable_key == task.stable_key)
        assert review_fingerprints(second, [task])[task.stable_key] == before
    finally:
        close_workbench_context(second)


def test_unbound_profile_peer_also_blocks_related_topology(tmp_path):
    net = tmp_path / "shift.net"
    net.write_text(
        (ROOT / "shift_register_chain.net")
        .read_text()
        .replace("$NETS", "$A_PROPERTIES\n 'MPN' 'L7805' ; U2\n$NETS")
    )
    bom = tmp_path / "shift.csv"
    bom.write_text(
        (ROOT / "shift_register_chain_bom.csv").read_text().replace('"U1 U2 U3",3,', '"U1 U3",2,')
        + "U2,1,74LV165PW,Nexperia,\n"
    )
    context = _context((net, bom))
    try:
        assert "U2" not in context.bom_report.identity_conflicts
        assert "U2" not in context.validation_targets
        assert "BOM_IDENTITY_CONFLICT" in context.design.components["U2"].properties
        u1 = next(row.validation for row in context.index.rows if row.refdes == "U1")
        assert all(
            check.result == "UNKNOWN" and check.needs_review for check in u1.component_checks
        )
        assert all("U2" in check.summary for check in u1.component_checks)
    finally:
        close_workbench_context(context)


def test_explicit_mpn_target_must_belong_to_the_parsed_registry(tmp_path):
    net, bom = _inputs(tmp_path, [("MPN", "L7805")])
    net.write_text(net.read_text().replace("'L7805' ; U1", "'L7805' ; U999"))
    with pytest.raises(ValueError, match="explicit MPN target U999.*absent"):
        _context((net, bom))


def test_conflicting_netlist_mpn_without_a_bom_row_still_blocks_related_checks(tmp_path):
    net = tmp_path / "shift.net"
    net.write_text(
        (ROOT / "shift_register_chain.net")
        .read_text()
        .replace(
            "$NETS", "$A_PROPERTIES\n 'MPN' 'L7805' ; U2\n 'MFR_PART_NUMBER' 'L7812' ; U2\n$NETS"
        )
    )
    bom = tmp_path / "shift.csv"
    bom.write_text(
        (ROOT / "shift_register_chain_bom.csv").read_text().replace('"U1 U2 U3",3,', '"U1 U3",2,')
    )
    context = _context((net, bom))
    try:
        u2 = next(row.validation for row in context.index.rows if row.refdes == "U2")
        assert u2.result == "UNKNOWN" and u2.needs_review
        assert u2.component_checks[0].rule_version == "3"
        assert (
            "L7805" in u2.component_checks[0].summary and "L7812" in u2.component_checks[0].summary
        )
        u1 = next(row.validation for row in context.index.rows if row.refdes == "U1")
        assert all(
            check.result == "UNKNOWN" and "U2" in check.summary for check in u1.component_checks
        )
    finally:
        close_workbench_context(context)
