from hardwise.checklist.finding import Finding
from hardwise.report.html import render


def _meta(**overrides):
    base = {
        "project_name": "demo_board",
        "project_dir": "/tmp/demo_board",
        "components_reviewed": 42,
        "rules_run": ["R001", "R003"],
        "generated_at": "2026-05-10T22:00:00+00:00",
        "sanitize_note": "0 unverified refdes wrapped, 0 findings dropped (no evidence)",
        "unverified_refdes_wrapped": 0,
        "findings_dropped_no_evidence": 0,
    }
    base.update(overrides)
    return base


def test_render_zero_findings_still_produces_valid_html() -> None:
    html = render([], _meta())

    assert "<!doctype html>" in html
    assert "Hardwise 原理图检视报告" in html
    assert "demo_board" in html
    assert "0 条待确认意见" in html
    assert "已扫描器件" in html


def test_render_groups_findings_by_rule_and_includes_evidence() -> None:
    findings = [
        Finding(
            rule_id="R003",
            severity="medium",
            refdes="J1",
            net="NC",
            message="J1 pin 5 (5) marked NC (type: passive). Confirm NC handling with datasheet.",
            evidence_tokens=["sch:pic_programmer.kicad_sch#J1"],
            suggested_action="Confirm the NC marker is intentional.",
        ),
        Finding(
            rule_id="R001",
            severity="info",
            refdes="U7",
            message="New component candidate",
            evidence_tokens=["sch:main.kicad_sch#U7"],
        ),
    ]

    html = render(findings, _meta())

    assert '<span class="rule-id">R001</span>' in html
    assert '<span class="rule-id">R003</span>' in html
    assert "sch:pic_programmer.kicad_sch#J1" in html
    assert "该脚允许悬空" in html
    assert "位号已由原理图注册表校验" in html
    assert "severity-medium" in html


def test_render_escapes_html_in_cells() -> None:
    finding = Finding(
        rule_id="R002",
        severity="high",
        refdes="C1",
        message="<script>alert(1)</script>",
        evidence_tokens=["sch:x#C1&bad"],
        suggested_action="Use <25V>",
    )

    html = render([finding], _meta(rules_run=["R002"]))

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "sch:x#C1&amp;bad" in html
    assert "Use &lt;25V&gt;" in html


def test_render_translates_declared_cap_voltage_without_leaking_english() -> None:
    finding = Finding(
        rule_id="R002",
        severity="info",
        refdes="C3",
        message=(
            "C3 rated voltage = 25 V detected from value '22uF/25V'. Reviewer must confirm "
            "the 80% derating rule against the actual working voltage on this cap's net "
            "(net parser not yet available — manual check)."
        ),
        evidence_tokens=["sch:pic_programmer.kicad_sch#C3"],
        suggested_action="Confirm working voltage on this cap's net does not exceed 20 V.",
    )

    html = render([finding], _meta(rules_run=["R002"]))

    assert "C3 的 value 字段为 22uF/25V" in html
    assert "Reviewer must confirm" not in html
    assert "不超过 20 V" in html
