from pathlib import Path

from hardwise.checklist.finding import Finding
from hardwise.ir.types import Component, Design, Pin
from hardwise.report.component_markdown import render


def _meta(**overrides):
    base = {
        "project_name": "demo_board",
        "project_dir": "/tmp/demo_board",
        "components_reviewed": 2,
        "rules_run": ["R002", "R003"],
        "generated_at": "2026-05-26T10:00:00+00:00",
        "sanitize_note": "0 unverified refdes wrapped, 0 findings dropped (no evidence)",
    }
    base.update(overrides)
    return base


def _design() -> Design:
    return Design(
        components={
            "C1": Component(refdes="C1", value="100uF", package="C_0805", decision="warn"),
            "U1": Component(
                refdes="U1",
                value="MCU",
                package="Package_DIP:DIP-8",
                pins=[
                    Pin(
                        number="7",
                        name="NC",
                        electrical_type="passive",
                        is_nc=True,
                    )
                ],
                decision="warn",
            ),
        },
        nets={},
        project_path=Path("/tmp/demo_board"),
        source_eda="kicad",
    )


def test_component_report_includes_summary_and_component_sections() -> None:
    findings = [
        Finding(
            rule_id="R002",
            severity="medium",
            refdes="C1",
            message="C1 missing voltage",
            evidence_tokens=["sch:main.kicad_sch#C1"],
            suggested_action="Add /25V",
            decision="likely_issue",
        ),
        Finding(
            rule_id="R003",
            severity="medium",
            refdes="U1",
            pin_number="7",
            message="U1 pin 7 marked NC",
            evidence_tokens=["sch:main.kicad_sch#U1"],
            suggested_action="Check datasheet",
            decision="reviewer_to_confirm",
        ),
    ]

    md = render(findings, _meta(), _design())

    assert "# Hardwise Component Review - demo_board" in md
    assert "## Component Summary" in md
    assert "| C1 | warn | 100uF | C_0805 | 1 |" in md
    assert "| U1 | warn | MCU | Package_DIP:DIP-8 | 1 |" in md
    assert "### C1 - 100uF" in md
    assert "### U1 - MCU" in md
    assert "| R003 | medium | 7 |" in md
    assert "sch:main.kicad_sch#U1" in md


def test_component_report_lists_zero_finding_components_as_pass() -> None:
    design = _design()
    design.components["U1"].decision = "pass"

    md = render([], _meta(rules_run=["R001"]), design)

    assert "| U1 | pass | MCU | Package_DIP:DIP-8 | 0 |" in md
    assert "0 candidate findings" in md


def test_component_report_escapes_pipe_chars() -> None:
    design = _design()
    finding = Finding(
        rule_id="R002",
        severity="medium",
        refdes="C1",
        message="value | weird",
        evidence_tokens=["sch:x#C1|bad"],
        suggested_action="a|b",
    )

    md = render([finding], _meta(), design)

    assert "value \\| weird" in md
    assert "sch:x#C1\\|bad" in md
    assert "a\\|b" in md
