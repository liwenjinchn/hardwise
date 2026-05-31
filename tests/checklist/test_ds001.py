from pathlib import Path

from hardwise.checklist.checks.ds001_vin_abs_max import check_component
from hardwise.checklist.protocols import CheckContext
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin


def _profile() -> DatasheetProfile:
    return DatasheetProfile(
        part_number="L7805",
        abs_max={"vin": 35.0},
        recommended={"vin_max": 25.0},
        pin_function={"1": "VI (input)"},
        evidence={"abs_max.vin": "datasheet:l78.pdf#p4"},
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )


def _component(net: str | None = None, profile: DatasheetProfile | None = None) -> Component:
    return Component(
        refdes="U3",
        value="7805",
        datasheet_profile=profile,
        pins=[
            Pin(
                number="1",
                name="VI",
                electrical_type="power_in",
                is_nc=False,
                net=net,
            )
        ],
    )


def _design(component: Component, voltage_hint: float | None = None) -> Design:
    nets = {}
    if component.pins[0].net and voltage_hint is not None:
        nets[component.pins[0].net] = Net(
            name=component.pins[0].net,
            nodes=[(component.refdes, "1")],
            voltage_hint=voltage_hint,
        )
    return Design(
        components={component.refdes: component},
        nets=nets,
        project_path=Path("/tmp/ds001"),
        source_eda="kicad",
    )


def test_ds001_profile_missing_skips_component() -> None:
    component = _component(net="+12V", profile=None)

    assert check_component(component, _design(component), _context()) == []


def test_ds001_no_inferred_vin_yields_reviewer_confirm() -> None:
    component = _component(profile=_profile())
    findings = check_component(component, _design(component), _context())

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "DS001"
    assert finding.severity == "medium"
    assert finding.decision == "reviewer_to_confirm"
    assert finding.refdes == "U3"
    assert finding.pin_number == "1"
    assert finding.evidence_tokens == ["datasheet:l78.pdf#p4"]
    assert finding.evidence_chain[0].source == "datasheet"
    assert finding.evidence_chain[0].token == "datasheet:l78.pdf#p4"


def test_ds001_vin_over_abs_max_is_likely_issue() -> None:
    component = _component(net="+40V", profile=_profile())
    findings = check_component(component, _design(component), _context())

    assert findings[0].severity == "high"
    assert findings[0].decision == "likely_issue"
    assert "exceeds" in findings[0].message


def test_ds001_vin_above_80_percent_is_reviewer_confirm() -> None:
    component = _component(net="VIN", profile=_profile())
    findings = check_component(component, _design(component, voltage_hint=30.0), _context())

    assert findings[0].severity == "medium"
    assert findings[0].decision == "reviewer_to_confirm"
    assert "above 80%" in findings[0].message


def test_ds001_vin_below_80_percent_is_likely_ok() -> None:
    component = _component(net="+12V", profile=_profile())
    findings = check_component(component, _design(component), _context())

    assert findings[0].severity == "low"
    assert findings[0].decision == "likely_ok"
    assert "below 80%" in findings[0].message


def _context() -> CheckContext:
    from hardwise.adapters.base import BoardRegistry

    return CheckContext(registry=BoardRegistry(project_dir=Path("/tmp/ds001")))
