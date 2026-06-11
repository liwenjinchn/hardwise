"""Checks tests for the pin-table sourced rules R008 / R009 / R010."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.capture_pin_table import PinTableRecord, parse_pin_table
from hardwise.checklist.checks.r008_floating_input import check as r008_check
from hardwise.checklist.checks.r009_power_pin_unconnected import check as r009_check
from hardwise.checklist.checks.r010_nc_marker_conflict import check as r010_check

FIXTURE = Path("tests/fixtures/capture/pin_table_demo.csv")


def _record(**overrides: object) -> PinTableRecord:
    base: dict[str, object] = {
        "refdes": "U9",
        "value": "TESTPART",
        "footprint": "SOP8",
        "pin_number": "1",
        "pin_name": "VDD",
        "pin_type_raw": "POWER(7)",
        "pin_category": "POWER",
        "net": "",
        "page": "PAGE1",
        "inst_x": 10,
        "inst_y": 20,
        "is_nc": False,
        "off_page": "",
        "source_file": Path("pin_table.csv"),
    }
    base.update(overrides)
    return PinTableRecord(**base)


def test_r008_flags_exactly_the_planted_floating_input() -> None:
    findings = r008_check(parse_pin_table(FIXTURE))

    assert [(f.refdes, f.pin_number) for f in findings] == [("U2", "4")]
    finding = findings[0]
    assert finding.rule_id == "R008"
    assert finding.severity == "high"
    assert finding.decision == "likely_issue"
    assert finding.evidence_tokens == ["sch:PAGE1@500,300#U2.4"]
    assert finding.evidence_chain[0].token == "pintable:pin_table_demo.csv#U2.4"


def test_r008_skips_nc_marked_and_wired_inputs() -> None:
    findings = r008_check(parse_pin_table(FIXTURE))

    flagged = {(f.refdes, f.pin_number) for f in findings}
    assert ("U10", "7") not in flagged  # NC-marked floating input
    assert ("U10", "8") not in flagged  # wired (NC-conflict is future scope)
    assert ("U2", "3") not in flagged  # wired input


def test_r009_flags_exactly_the_planted_unconnected_power_pin() -> None:
    findings = r009_check(parse_pin_table(FIXTURE))

    assert [(f.refdes, f.pin_number) for f in findings] == [("U2", "5")]
    finding = findings[0]
    assert finding.rule_id == "R009"
    assert finding.severity == "high"
    assert finding.decision == "likely_issue"


def test_r009_nc_marked_power_pin_downgrades_to_reviewer_to_confirm() -> None:
    findings = r009_check([_record(is_nc=True)])

    assert len(findings) == 1
    assert findings[0].decision == "reviewer_to_confirm"
    assert "NC marker" in findings[0].message


def test_r010_flags_exactly_the_planted_nc_marker_conflict() -> None:
    findings = r010_check(parse_pin_table(FIXTURE))

    assert [(f.refdes, f.pin_number, f.net) for f in findings] == [
        ("U10", "8", "SENSE_A")
    ]
    finding = findings[0]
    assert finding.rule_id == "R010"
    assert finding.severity == "medium"
    assert finding.decision == "reviewer_to_confirm"
    assert finding.evidence_tokens == ["sch:PAGE2@150,220#U10.8"]
    assert finding.evidence_chain[0].token == "pintable:pin_table_demo.csv#U10.8"


def test_passive_and_unknown_categories_produce_no_findings() -> None:
    records = [
        _record(pin_type_raw="PASSIVE(4)", pin_category="PASSIVE"),
        _record(pin_type_raw="4", pin_category=""),
    ]

    assert r008_check(records) == []
    assert r009_check(records) == []
    assert r010_check(records) == []
