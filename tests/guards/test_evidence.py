from hardwise.checklist.finding import Finding
from hardwise.guards.evidence import strip_unsupported


def test_strips_findings_with_empty_evidence_tokens() -> None:
    findings = [
        Finding(
            rule_id="R001",
            severity="info",
            message="ok",
            evidence_tokens=["sch:x#U1"],
        ),
        Finding(
            rule_id="R001",
            severity="info",
            message="no evidence",
            evidence_tokens=[],
        ),
        Finding(
            rule_id="R002",
            severity="high",
            message="also ok",
            evidence_tokens=["bom:y#row3"],
        ),
    ]

    kept, dropped = strip_unsupported(findings)

    assert dropped == 1
    assert len(kept) == 2
    assert all(f.evidence_tokens for f in kept)


def test_strip_no_op_when_all_have_evidence() -> None:
    findings = [
        Finding(
            rule_id="R001",
            severity="info",
            message="m",
            evidence_tokens=["sch:a#U1"],
        ),
    ]
    kept, dropped = strip_unsupported(findings)
    assert dropped == 0
    assert kept == findings


def test_strip_handles_empty_input() -> None:
    kept, dropped = strip_unsupported([])
    assert kept == []
    assert dropped == 0
