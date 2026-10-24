"""Competing assembly quantities stay unknown without changing identity/electrical truth."""

import csv
import json
from pathlib import Path
import pytest
from hardwise.bom import parse_bom, match_bom_to_design, BomParseError
from hardwise.ir.types import Component, Design
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.view_model import (
    build_workbench_state,
    build_review_prep_packet,
    render_review_prep_packet_markdown,
)
from hardwise.workbench.prep_packet import (
    build_project_review_prep_packet,
    render_project_review_prep_packet_markdown,
)
from hardwise.report import workbench_spa_snapshot
from hardwise.workbench.server_io import _task_csv_response, _annotations_response
from tests.xlsx_fixture import write_minimal_xlsx


def _write(path, quantities, rest=False, alias="Qty"):
    headers = (
        ["位号", "数量", alias, "名称", "MPN"]
        if path.suffix == ".xlsx"
        else ["Reference", "Quantity", alias, "Value", "MPN"]
    )
    rows = [headers, ["C1", *quantities, "100nF 25V", "CAP-100N"]]
    if rest:
        rows += [["U1", "1", "1", "L7805", "L7805"], ["C2", "1", "1", "100nF", "CAP-100N"]]
    if path.suffix == ".xlsx":
        write_minimal_xlsx(path, rows)
    else:
        with path.open("w", newline="") as stream:
            csv.writer(stream, delimiter="\t" if path.suffix == ".tsv" else ",").writerows(rows)


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize("values", [["1", "99"], ["99", "1"]])
def test_conflicting_quantities_have_no_selected_integer_and_keep_original_cells(
    tmp_path, suffix, values
):
    path = tmp_path / ("public" + suffix)
    _write(path, values)
    bom = parse_bom(path)
    report = match_bom_to_design(
        bom,
        Design(
            components={"C1": Component(refdes="C1")},
            project_path=tmp_path,
            source_eda="allegro_netlist",
        ),
    )
    assert bom.items[0].quantity is None
    assert report.matched_refdes == ["C1"] and not report.is_clean
    assert report.identity_conflicts == {}
    assert report.quantity_mismatches == []
    (conflict,) = report.quantity_column_conflicts
    assert conflict.source_line == 2
    assert [f.column for f in conflict.source_fields] == [2, 3]
    assert [f.value for f in conflict.source_fields] == values


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
@pytest.mark.parametrize("values", [["1", "1.0"], ["01", "1"], ["", "1"], ["1", ""]])
def test_equal_numeric_or_blank_declarations_do_not_conflict(tmp_path, suffix, values):
    path = tmp_path / ("public" + suffix)
    _write(path, values)
    bom = parse_bom(path)
    assert bom.items[0].quantity == 1
    report = match_bom_to_design(
        bom,
        Design(
            components={"C1": Component(refdes="C1")},
            project_path=tmp_path,
            source_eda="allegro_netlist",
        ),
    )
    assert report.is_clean and report.quantity_column_conflicts == []


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_invalid_unselected_alias_is_not_silently_ignored(tmp_path, suffix):
    path = tmp_path / ("public" + suffix)
    _write(path, ["1", "not-a-number"])
    with pytest.raises(BomParseError, match="invalid BOM quantity"):
        parse_bom(path)


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".xlsx"])
def test_quantity_diagnostics_survive_reports_and_leave_voltage_verdict_unchanged(
    tmp_path, monkeypatch, suffix
):
    path = tmp_path / ("public" + suffix)
    facts = json.loads(Path("tests/fixtures/allegro/l78_dc_voltage_facts.json").read_text())
    facts["facts"].append(
        dict(
            net="GND",
            reference_net="GND",
            minimum=0,
            maximum=0,
            confirmed=True,
            confirmed_by="public synthetic author",
            source="public synthetic DC premise; not measured",
        )
    )
    fact_path = tmp_path / "facts.json"
    fact_path.write_text(json.dumps(facts))

    def context():
        return build_workbench_context(
            netlist_path=Path("tests/fixtures/allegro/l78_regulator.net"),
            bom_path=path,
            profiles=Path("data/datasheet_profiles"),
            voltage_facts=fact_path,
        )

    _write(path, ["1", "1"], True)
    before = context()
    try:
        original = build_workbench_state(before, datasheet_search_enabled=False)
        original_c1 = next(row.validation for row in before.index.rows if row.refdes == "C1")
        assert original_c1.result == "PASS"
    finally:
        close_workbench_context(before)
    _write(path, ["1", "99"], True)
    after = context()
    try:
        state = build_workbench_state(after, datasheet_search_enabled=False)
        assert state.summary == original.summary
        current = next(row.validation for row in after.index.rows if row.refdes == "C1")
        assert current.model_dump() == original_c1.model_dump()
        assert len(state.evidence_package.bom_quantity_conflicts) == 1
        assert (
            next(lane for lane in state.evidence_package.lanes if lane.id == "bom").status_label
            == "quantity gaps"
        )
        assert not after.bom_report.is_clean
        project_md = render_project_review_prep_packet_markdown(
            build_project_review_prep_packet(after)
        )
        component_md = render_review_prep_packet_markdown(build_review_prep_packet(after, "C1"))
        for body in [
            project_md,
            component_md,
            bytes(_task_csv_response(after).body).decode(),
            bytes(_annotations_response(after).body).decode(),
        ]:
            assert "Qty=99" in body and "#line2" in body and "column3" in body
        monkeypatch.setattr(
            workbench_spa_snapshot, "_inline_spa_shell", lambda data, **kwargs: data
        )
        snapshot = workbench_spa_snapshot.render_spa_snapshot(after)
        assert "Qty=99" in snapshot["exports"]["csv"]
        assert (
            snapshot["state"]["evidence_package"]["bom_quantity_conflicts"][0]["source_fields"][1][
                "value"
            ]
            == "99"
        )
    finally:
        close_workbench_context(after)


def test_legacy_punctuated_quantity_header_is_not_dropped(tmp_path):
    path = tmp_path / "public.csv"
    _write(path, ["1", "99"], alias="Qty.")
    bom = parse_bom(path)
    assert bom.items[0].quantity is None
    report = match_bom_to_design(
        bom,
        Design(
            components={"C1": Component(refdes="C1")},
            project_path=tmp_path,
            source_eda="allegro_netlist",
        ),
    )
    assert report.quantity_column_conflicts[0].source_fields[1].name == "Qty."


def test_auto_selection_prefers_a_clean_candidate_over_quantity_ambiguity(tmp_path):
    from hardwise.project_inputs import resolve_bom_input

    _write(tmp_path / "a-ambiguous.csv", ["1", "99"], True)
    _write(tmp_path / "z-clean.csv", ["1", "1"], True)
    design = Design(
        components={ref: Component(refdes=ref) for ref in ["C1", "C2", "U1"]},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    resolved = resolve_bom_input(netlist_path=tmp_path, bom_path=None, design=design)
    assert resolved.bom.source_file.name == "z-clean.csv"
    assert (
        next(c for c in resolved.candidates if c.path.name == "a-ambiguous.csv").mismatch_count == 1
    )


def test_quantity_sources_are_visible_in_cli_and_intake_markdown(tmp_path):
    from typer.testing import CliRunner
    from hardwise.cli import app
    from hardwise.report.allegro_bom_markdown import render

    path = tmp_path / "public.csv"
    _write(path, ["1", "99"], True)
    result = CliRunner().invoke(
        app, ["inspect-bom-match", "tests/fixtures/allegro/l78_regulator.net", str(path)]
    )
    assert result.exit_code == 0
    assert "quantity column conflicts: 1" in result.output
    assert "Quantity=1" in result.output and "Qty=99" in result.output
    bom = parse_bom(path)
    design = Design(
        components={ref: Component(refdes=ref) for ref in ["C1", "C2", "U1"]},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    report = match_bom_to_design(bom, design)
    text = render(design, bom, report, {})
    assert "quantity-column-conflict" in text
    assert "Quantity Column Conflicts" in text and "Qty=99" in text
    assert "Qty=99" in render(design, bom, report, {}, mismatch_only=True)


def test_reapplying_an_unknown_quantity_removes_stale_confirmed_metadata(tmp_path):
    from hardwise.bom import apply_bom_to_design

    path = tmp_path / "public.csv"
    design = Design(
        components={"C1": Component(refdes="C1")},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    _write(path, ["1", "1"])
    previous = apply_bom_to_design(design, match_bom_to_design(parse_bom(path), design))
    assert previous.components["C1"].properties["BOM_ITEM_QUANTITY"] == "1"
    _write(path, ["1", "99"])
    report = match_bom_to_design(parse_bom(path), design)
    current = apply_bom_to_design(previous, report)
    assert "BOM_ITEM_QUANTITY" not in current.components["C1"].properties


def test_explicit_zero_is_not_rendered_as_an_unknown_quantity(tmp_path):
    from hardwise.report.allegro_bom_markdown import render

    path = tmp_path / "public.csv"
    _write(path, ["0", "0.0"])
    bom = parse_bom(path)
    design = Design(
        components={"C1": Component(refdes="C1")},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    report = match_bom_to_design(bom, design)
    assert bom.items[0].quantity == 0 and not report.quantity_column_conflicts
    assert "| 1 | 0 | 1 | quantity-mismatch |" in render(design, bom, report, {})


def test_identical_quantity_headers_preserve_both_cells_instead_of_dictreader_last_value(tmp_path):
    path = tmp_path / "public.csv"
    _write(path, ["1", "99"], alias="Quantity")
    bom = parse_bom(path)
    assert bom.items[0].quantity is None
    design = Design(
        components={"C1": Component(refdes="C1")},
        project_path=tmp_path,
        source_eda="allegro_netlist",
    )
    (conflict,) = match_bom_to_design(bom, design).quantity_column_conflicts
    assert [(field.column, field.name, field.value) for field in conflict.source_fields] == [
        (2, "Quantity", "1"),
        (3, "Quantity", "99"),
    ]
