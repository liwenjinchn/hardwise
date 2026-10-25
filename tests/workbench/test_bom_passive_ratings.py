"""Explicit BOM rating columns cannot be dropped or silently override other premises."""

import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hardwise.bom import parse_bom, apply_bom_to_design, match_bom_to_design
from hardwise.bom.source_fields import RATING_SOURCES
from hardwise.validation.generic_passive import validate_generic_passive
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.server import create_workbench_app

ROOT = Path(__file__).parents[2]


@pytest.fixture
def scene(tmp_path):
    (tmp_path / "design.net").write_text(
        "$PACKAGES\n ! 'C0805' ! CAP ; C1\n ! 'R0805' ! RES ; R1\n"
        "$NETS\n 'P20' ; C1.1, R1.1\n 'RET' ; C1.2, R1.2\n$END\n"
    )
    (tmp_path / "facts.json").write_text(
        json.dumps(
            {
                "schema_version": "hardwise.voltage_facts.v1",
                "active_mode": "dc",
                "facts": [
                    {
                        "net": n,
                        "minimum": v,
                        "maximum": v,
                        "reference_net": "RET",
                        "confirmed": True,
                        "confirmed_by": "synthetic test author",
                        "source": "public fixture",
                    }
                    for n, v in [("P20", 20), ("RET", 0)]
                ],
            }
        )
    )
    return tmp_path


def write(scene, headers, cap, resistor=None, fmt="csv"):
    path = scene / ("bom." + fmt)
    rows = [headers, cap]
    if resistor is not None:
        rows.append(resistor)
    with path.open("w", newline="") as stream:
        csv.writer(stream, delimiter="\t" if fmt == "tsv" else ",").writerows(rows)
    return path


def build(scene, path):
    return build_workbench_context(
        netlist_path=scene / "design.net",
        bom_path=path,
        profiles=ROOT / "data/datasheet_profiles",
        voltage_facts=scene / "facts.json",
    )


def check(context, refdes="C1", name="capacitor_voltage_margin"):
    row = next(row for row in context.index.validated_rows if row.refdes == refdes)
    return next(item for item in row.validation.component_checks if item.check == name)


@pytest.mark.parametrize(
    "value,header,cell,result",
    [
        ("100nF 25V", "Voltage Rating", "16V", "UNKNOWN"),
        ("100nF", "Rated Voltage", "16V", "FAIL"),
        ("100nF 25V", "Rated Voltage", "25000mV", "PASS"),
        ("100nF", "额定电压（V）", "16", "FAIL"),
        ("100nF 25V", "Voltage Rating", "16", "UNKNOWN"),
        ("100nF 25V", "Voltage Rating", "sixteen", "UNKNOWN"),
        ("100nF 25V", "Voltage Rating", "0V", "UNKNOWN"),
        ("100nF 25V", "Voltage Rating", "-16V", "UNKNOWN"),
        ("100nF 25V", "Voltage Rating", "16A", "UNKNOWN"),
        ("100nF 25V", "Voltage Rating(A)", "16", "UNKNOWN"),
        ("100nF 25V 16V", "Voltage Rating", "", "UNKNOWN"),
        ("100nF 16/25V", "Voltage Rating", "", "UNKNOWN"),
        ("100nF 25V", "Notes", "not a rating", "PASS"),
    ],
)
def test_rating_premises_have_no_source_priority(scene, value, header, cell, result):
    path = write(scene, ["Reference", "Quantity", "Value", header], ["C1", 1, value, cell])
    context = build(scene, path)
    try:
        item = check(context)
        assert item.result == result and item.rule_version == "2"
        if result == "UNKNOWN":
            assert item.needs_review
        row = next(row for row in context.index.validated_rows if row.refdes == "C1")
        assert all(pin.result == "PASS" for pin in row.validation.pin_results)
        assert (
            next(
                c for c in row.validation.component_checks if c.check == "capacitor_value_parse"
            ).result
            == "PASS"
        )
    finally:
        close_workbench_context(context)


@pytest.mark.parametrize("fmt", ["csv", "tsv"])
def test_duplicate_headers_and_original_columns_survive_import(scene, fmt):
    headers = ["位号", "数量", "名称"] if fmt == "xlsx" else ["Reference", "Quantity", "Value"]
    path = write(
        scene,
        [*headers, "Voltage Rating", "Voltage Rating", "Notes"],
        ["C1", 1, "100nF 25V", "16V", "25V", "public\nmultiline"],
        fmt=fmt,
    )
    bom = parse_bom(path)
    assert [(f.column, f.name, f.value) for f in bom.rows[0].source_fields][3:5] == [
        (4, "Voltage Rating", "16V"),
        (5, "Voltage Rating", "25V"),
    ]
    assert bom.rows[0].source_fields[-1].value == "public\nmultiline"
    context = build(scene, path)
    try:
        item = check(context)
        assert item.result == "UNKNOWN" and item.needs_review
        assert "16V" in item.summary and "25V" in item.summary
        assert any("column4" in token for token in item.evidence)
        assert any("column5" in token for token in item.evidence)
    finally:
        close_workbench_context(context)


@pytest.mark.parametrize(
    "value,cell,result",
    [
        ("1K 1W", "250mW", "UNKNOWN"),
        ("1K", "250mW", "FAIL"),
        ("10K 1/4W", "250mW", "PASS"),
        ("1K 1W 1/4W", "", "UNKNOWN"),
    ],
)
def test_resistor_keeps_independent_estimate_when_rating_unresolved(scene, value, cell, result):
    path = write(
        scene,
        ["Reference", "Quantity", "Value", "Power Rating"],
        ["C1", 1, "100nF", ""],
        ["R1", 1, value, cell],
    )
    context = build(scene, path)
    try:
        item = check(context, "R1", "resistor_power_estimate")
        assert item.result == result and item.rule_version == "2"
        assert "Estimated resistor power" in item.summary
        if result == "UNKNOWN":
            assert item.needs_review and "0.4 W" in item.summary
    finally:
        close_workbench_context(context)


def test_preserved_sources_cannot_be_bypassed_by_omitting_row_and_clear_on_reapply(scene):
    path = write(
        scene, ["Reference", "Quantity", "Value", "Voltage Rating"], ["C1", 1, "100nF 25V", "16V"]
    )
    context = build(scene, path)
    try:
        component = context.design.components["C1"]
        report = validate_generic_passive(component, None, context.design, "capacitor")
        assert (
            next(c for c in report.component_checks if c.check == "capacitor_voltage_margin").result
            == "UNKNOWN"
        )
        # Removing the extra rating column is an explicit new source snapshot.
        write(scene, ["Reference", "Quantity", "Value"], ["C1", 1, "100nF 25V"])
        report = match_bom_to_design(parse_bom(path), context.design)
        updated = apply_bom_to_design(context.design, report)
        assert RATING_SOURCES not in updated.components["C1"].properties
        result = validate_generic_passive(updated.components["C1"], None, updated, "capacitor")
        assert (
            next(c for c in result.component_checks if c.check == "capacitor_voltage_margin").result
            == "PASS"
        )
    finally:
        close_workbench_context(context)


def test_changed_rating_invalidates_but_unrelated_bom_note_keeps_waiver(scene):
    headers = ["Reference", "Quantity", "Value", "Voltage Rating", "Notes"]
    path = write(scene, headers, ["C1", 1, "100nF 25V", "16V", "first"])

    class LocalOnlyChat:
        datasheet_search_enabled = False

    app = create_workbench_app(
        build(scene, path),
        LocalOnlyChat(),
        profiles=ROOT / "data/datasheet_profiles",
        review_db=scene / "review.sqlite",
        auto_datasheet_candidates=False,
    )
    with TestClient(app) as client:
        state = client.get("/api/workbench/state").json()
        task = next(
            t
            for t in state["review_tasks"]
            if t["refdes"] == "C1" and t["check"] == "capacitor_voltage_margin"
        )
        assert task["assessment"]["result"] == "UNKNOWN"
        assert (
            client.put(
                "/api/workbench/review-decisions",
                json={
                    "stable_keys": [task["stable_key"]],
                    "status": "accepted_risk",
                    "reason": "public rating source review reason",
                    "expected_run_id": state["review_decisions"]["run_id"],
                },
            ).status_code
            == 200
        )
        write(scene, headers, ["C1", 1, "100nF 25V", "16V", "unrelated note changed"])
        assert client.post("/api/workbench/rerun").json()["review_decisions"]["accepted_risk"] == 1
        write(scene, headers, ["C1", 1, "100nF 25V", "18V", "unrelated note changed"])
        state = client.post("/api/workbench/rerun").json()
        assert state["review_decisions"]["needs_review"] == 1
        assert (
            client.get("/api/workbench/review-decisions/history").json()["events"][0]["decision"][
                "reason"
            ]
            == "public rating source review reason"
        )
        exported = client.get("/api/workbench/export?format=json").json()
        assert any(
            t["check"] == "capacitor_voltage_margin" and t["assessment"]["result"] == "UNKNOWN"
            for t in exported["review_tasks"]
        )


def test_duplicate_value_columns_cannot_hide_an_alternative_rating(scene):
    path = write(
        scene, ["Reference", "Quantity", "Value", "Value"], ["C1", 1, "100nF 16V", "100nF 25V"]
    )
    context = build(scene, path)
    try:
        assert check(context).result == "UNKNOWN" and check(context).needs_review
        report = validate_generic_passive(
            context.design.components["C1"], None, context.design, "capacitor"
        )
        assert (
            next(c for c in report.component_checks if c.check == "capacitor_voltage_margin").result
            == "UNKNOWN"
        )
    finally:
        close_workbench_context(context)


def test_supplied_row_cannot_override_preserved_source_premises(scene):
    path = write(
        scene, ["Reference", "Quantity", "Value", "Voltage Rating"], ["C1", 1, "100nF 25V", "16V"]
    )
    context = build(scene, path)
    try:
        row = context.bom_report.rows_by_refdes["C1"].model_copy(
            update={"value": "100nF 16V", "source_fields": []}
        )
        report = validate_generic_passive(
            context.design.components["C1"], row, context.design, "capacitor"
        )
        assert (
            next(c for c in report.component_checks if c.check == "capacitor_voltage_margin").result
            == "UNKNOWN"
        )
    finally:
        close_workbench_context(context)
