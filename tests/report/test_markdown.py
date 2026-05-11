from hardwise.checklist.finding import Finding
from hardwise.report.markdown import render


def _meta(**overrides):
    base = {
        "project_name": "demo_board",
        "project_dir": "/tmp/demo_board",
        "components_reviewed": 42,
        "rules_run": ["R001"],
        "generated_at": "2026-05-10T22:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_render_zero_findings_still_produces_valid_md() -> None:
    md = render([], _meta())

    assert "# Hardwise Schematic Review — demo_board" in md
    assert "Components reviewed | 42" in md
    assert "0 candidate findings" in md
    assert "Findings | 0" in md


def test_render_with_findings_includes_table_columns() -> None:
    findings = [
        Finding(
            rule_id="R001",
            severity="info",
            refdes="U7",
            message="empty footprint",
            evidence_tokens=["sch:main.kicad_sch#U7"],
            suggested_action="check datasheet",
        ),
    ]
    md = render(findings, _meta())

    assert "| # | Rule | Severity | Refdes" in md
    assert "U7" in md
    assert "sch:main.kicad_sch#U7" in md
    assert "check datasheet" in md
    assert "Findings | 1" in md


def test_render_escapes_pipe_chars_in_cells() -> None:
    finding = Finding(
        rule_id="R002",
        severity="high",
        refdes="C1",
        message="value | weird",  # raw pipe would break the table
        evidence_tokens=["x|y"],
        suggested_action="a|b",
    )
    md = render([finding], _meta(rules_run=["R002"]))

    # Pipes must be escaped inside cells, not bleed through as new columns.
    assert "value \\| weird" in md
    assert "x\\|y" in md
    assert "a\\|b" in md


def test_render_handles_optional_refdes_and_net() -> None:
    finding = Finding(
        rule_id="R005",
        severity="medium",
        message="dangling net",
        net="UNCONNECTED_4",
        evidence_tokens=["drc:report.txt#L42"],
    )
    md = render([finding], _meta(rules_run=["R005"]))

    # refdes is None -> rendered as em-dash; net is set -> rendered.
    assert "| — |" in md  # refdes column
    assert "UNCONNECTED_4" in md
