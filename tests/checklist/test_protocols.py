"""Tests for V2.2 component-check protocol and dispatcher."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.checklist.checks import CHECK_SPECS
from hardwise.checklist.finding import Finding
from hardwise.checklist.protocols import CheckContext, CheckSpec, run_component_checks
from hardwise.ir.build import build_design
from hardwise.ir.types import Component, Design


SOURCE = Path("/tmp/v2_2.kicad_sch")


def _component_record(refdes: str, value: str = "MOCK", footprint: str = "") -> ComponentRecord:
    return ComponentRecord(
        refdes=refdes,
        value=value,
        footprint=footprint,
        datasheet="",
        source_file=SOURCE,
        source_kind="schematic",
    )


def _registry() -> BoardRegistry:
    components = [
        _component_record("U1", value="MCU", footprint="Package_DIP:DIP-8"),
        _component_record("C1", value="100uF", footprint="Capacitor_THT:C_Disc"),
    ]
    return BoardRegistry(
        project_dir=Path("/tmp/v2_2"),
        components=components,
        schematic_records=components,
        nc_pins=[
            NcPinRecord(
                refdes="U1",
                pin_number="7",
                pin_name="NC",
                pin_electrical_type="passive",
                source_file=SOURCE,
            )
        ],
    )


def test_check_specs_register_known_rules() -> None:
    assert [spec.rule_id for spec in CHECK_SPECS] == ["R001", "R002", "R003", "DS001"]


def test_run_component_checks_filters_by_requested_rule_and_applies_to() -> None:
    registry = _registry()
    design = build_design(registry)

    findings, rules_run = run_component_checks(
        design=design,
        specs=CHECK_SPECS,
        requested_rule_ids={"R002"},
        context=CheckContext(registry=registry),
    )

    assert rules_run == ["R002"]
    assert len(findings) == 1
    assert findings[0].rule_id == "R002"
    assert findings[0].refdes == "C1"
    assert design.components["C1"].findings == findings
    assert design.components["U1"].findings == []


def test_run_component_checks_attaches_pin_scoped_findings_to_pin() -> None:
    registry = _registry()
    design = build_design(registry)

    findings, rules_run = run_component_checks(
        design=design,
        specs=CHECK_SPECS,
        requested_rule_ids={"R003"},
        context=CheckContext(registry=registry),
    )

    assert rules_run == ["R003"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "R003"
    assert finding.refdes == "U1"
    assert finding.pin_number == "7"
    assert design.components["U1"].findings == [finding]
    assert design.components["U1"].pins[0].findings == [finding]


def test_custom_checkspec_uses_component_signature() -> None:
    calls: list[tuple[str, str]] = []

    def check(component: Component, design: Design, _context: CheckContext) -> list[Finding]:
        calls.append((component.refdes, design.source_eda))
        return [
            Finding(
                rule_id="T001",
                severity="info",
                refdes=component.refdes,
                message="custom component check ran",
                evidence_tokens=[f"sch:v2_2.kicad_sch#{component.refdes}"],
            )
        ]

    registry = _registry()
    design = build_design(registry)
    spec = CheckSpec(
        rule_id="T001",
        applies_to=lambda component: component.refdes.startswith("U"),
        check=check,
    )

    findings, rules_run = run_component_checks(
        design=design,
        specs=[spec],
        requested_rule_ids={"T001"},
        context=CheckContext(registry=registry),
    )

    assert rules_run == ["T001"]
    assert calls == [("U1", "kicad")]
    assert [finding.refdes for finding in findings] == ["U1"]
