from pydantic import ValidationError

import pytest

from hardwise.checklist.finding import Finding


def test_finding_minimum_construction() -> None:
    f = Finding(rule_id="R001", severity="info", message="hello")
    assert f.rule_id == "R001"
    assert f.severity == "info"
    assert f.refdes is None
    assert f.net is None
    assert f.evidence_tokens == []
    assert f.suggested_action == ""
    assert f.status == "open"


def test_finding_full_construction() -> None:
    f = Finding(
        rule_id="R002",
        severity="high",
        refdes="C7",
        net="+3V3",
        message="cap rated voltage too low",
        evidence_tokens=["sch:main.kicad_sch#C7", "datasheet:cap.pdf#p3"],
        suggested_action="raise rated voltage",
        status="accepted",
    )
    assert f.refdes == "C7"
    assert len(f.evidence_tokens) == 2
    assert f.status == "accepted"


def test_finding_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        Finding(rule_id="R001", severity="catastrophic", message="x")


def test_finding_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        Finding(rule_id="R001", severity="info", message="x", status="parked")
