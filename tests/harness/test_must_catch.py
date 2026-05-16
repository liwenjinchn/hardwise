"""Synthetic must-catch harness for known schematic-review safety cases.

These tests are intentionally product-level: they lock the MVP safety floor for
known review scenarios that should not regress while rules evolve. They use
minimal record objects instead of full KiCad fixtures so failures point at rule
decision boundaries, not parser details.
"""

from pathlib import Path

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.checklist.checks.r001_new_component_candidate import check as check_r001
from hardwise.checklist.checks.r002_cap_voltage_derating import check as check_r002
from hardwise.checklist.checks.r003_nc_pin_handling import check as check_r003

SOURCE = Path("/tmp/must_catch.kicad_sch")


def component(refdes: str, value: str = "MOCK", footprint: str = "") -> ComponentRecord:
    return ComponentRecord(
        refdes=refdes,
        value=value,
        footprint=footprint,
        datasheet="",
        source_file=SOURCE,
        source_kind="schematic",
    )


def nc_pin(refdes: str, pin_number: str, pin_name: str = "NC") -> NcPinRecord:
    return NcPinRecord(
        refdes=refdes,
        pin_number=pin_number,
        pin_name=pin_name,
        pin_electrical_type="passive",
        source_file=SOURCE,
    )


def registry(components: list[ComponentRecord]) -> BoardRegistry:
    return BoardRegistry(project_dir=Path("/tmp/must_catch"), components=components)


def test_must_catch_new_component_without_footprint() -> None:
    findings = check_r001([component("U10", value="STM32F103", footprint="")])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R001"
    assert finding.refdes == "U10"
    assert finding.decision == "reviewer_to_confirm"
    assert finding.evidence_tokens == ["sch:must_catch.kicad_sch#U10"]


def test_must_catch_cap_missing_rated_voltage() -> None:
    findings = check_r002([component("C10", value="100uF")])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R002"
    assert finding.refdes == "C10"
    assert finding.decision == "likely_issue"
    assert finding.severity == "medium"


def test_must_not_report_cap_with_rated_voltage_suffix() -> None:
    findings = check_r002([component("C11", value="100uF/25V")])

    assert findings == []


def test_must_catch_ic_nc_without_datasheet_as_reviewer_confirm() -> None:
    findings = check_r003(
        [nc_pin("U20", "7", "NC")],
        registry=registry([component("U20", value="PIC16F627", footprint="Package_DIP")]),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R003"
    assert finding.refdes == "U20"
    assert finding.decision == "reviewer_to_confirm"
    assert finding.severity == "medium"


def test_must_group_connector_batch_nc_as_likely_ok_with_evidence_chain() -> None:
    pins = [
        nc_pin("J10", "1", "NC"),
        nc_pin("J10", "2", "NC"),
        nc_pin("J10", "3", "NC"),
    ]
    findings = check_r003(
        pins,
        registry=registry(
            [
                component(
                    "J10",
                    value="Conn_01x03",
                    footprint="Connector_PinHeader_2.54mm:PinHeader_1x03",
                )
            ]
        ),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R003"
    assert finding.refdes == "J10"
    assert finding.decision == "likely_ok"
    assert finding.severity == "low"
    for pin_number in ("1", "2", "3"):
        assert pin_number in finding.message
    assert finding.evidence_chain
    assert finding.evidence_chain[0].source == "eda"
    assert finding.evidence_chain[0].token == "sch:must_catch.kicad_sch#J10"
