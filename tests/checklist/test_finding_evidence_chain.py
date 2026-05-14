"""DR-009 extension tests — EvidenceStep + Finding.evidence_chain + Finding.decision.

Pins the four invariants:
  - Existing checks (R001/R002/R003) keep working: default-empty new fields
    survive serialization without forcing them into the JSON.
  - When a rule populates evidence_chain + decision, both round-trip correctly
    and `status` stays at its default `'open'` (proving the rule/status split).
  - `EvidenceStep` enforces `source ∈ {eda, datasheet, rule}` — no free-form
    source strings leak into the report.
  - `decision` is constrained to the three rule-side judgment values; arbitrary
    strings rejected.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hardwise.checklist.finding import EvidenceStep, Finding


def test_finding_default_evidence_chain_empty_and_decision_none() -> None:
    """Backward-compat: existing checks can construct Finding as before."""
    f = Finding(rule_id="R001", severity="info", message="hello")
    assert f.evidence_chain == []
    assert f.decision is None
    assert f.status == "open"


def test_finding_default_omits_new_fields_from_dump_dict_when_unused() -> None:
    """Sleep Consolidator + report serializers see the same shape as before.

    `model_dump(exclude_defaults=True)` skips the new fields when they're at
    their defaults, so existing downstream consumers keep their original JSON.
    """
    f = Finding(rule_id="R001", severity="info", message="hello")
    dumped = f.model_dump(exclude_defaults=True)
    assert "evidence_chain" not in dumped
    assert "decision" not in dumped


def test_finding_with_evidence_chain_and_decision_serializes() -> None:
    """The R003-shape Finding: 2 EvidenceSteps + decision='likely_ok'."""
    f = Finding(
        rule_id="R003",
        severity="medium",
        refdes="U4",
        message="pin 2 marked NC; datasheet confirms NC status",
        evidence_chain=[
            EvidenceStep(
                source="eda",
                claim="U4 pin 2 marked no_connect in schematic",
                token="sch:main.kicad_sch#U4.2",
            ),
            EvidenceStep(
                source="datasheet",
                claim="datasheet page 4 lists pin 2 as 'NC / no connect'",
                token="pdf:l78.pdf#p4",
            ),
        ],
        decision="likely_ok",
    )
    assert len(f.evidence_chain) == 2
    assert f.evidence_chain[0].source == "eda"
    assert f.evidence_chain[1].source == "datasheet"
    assert f.decision == "likely_ok"
    # Rule/status split: rule writes decision, status stays default.
    assert f.status == "open"

    dumped = f.model_dump()
    assert dumped["decision"] == "likely_ok"
    assert dumped["status"] == "open"
    assert len(dumped["evidence_chain"]) == 2
    assert dumped["evidence_chain"][0]["token"] == "sch:main.kicad_sch#U4.2"


def test_evidence_step_requires_all_three_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceStep(source="eda", claim="x")  # missing token
    with pytest.raises(ValidationError):
        EvidenceStep(source="eda", token="t")  # missing claim
    with pytest.raises(ValidationError):
        EvidenceStep(claim="x", token="t")  # missing source


def test_evidence_step_rejects_invalid_source() -> None:
    """Source is Literal — no `'intuition'`, `'guess'`, or free-form strings."""
    with pytest.raises(ValidationError):
        EvidenceStep(source="intuition", claim="x", token="t")


def test_finding_rejects_invalid_decision() -> None:
    """decision is Literal — only the three rule-side judgment values."""
    with pytest.raises(ValidationError):
        Finding(
            rule_id="R003",
            severity="medium",
            message="x",
            decision="probably_fine",  # not in the Literal
        )


def test_finding_decision_and_status_are_independent() -> None:
    """A rule-side likely_ok can coexist with any human flow status."""
    f = Finding(
        rule_id="R003",
        severity="medium",
        message="x",
        decision="likely_ok",
        status="rejected",  # reviewer disagreed with the rule
    )
    assert f.decision == "likely_ok"
    assert f.status == "rejected"
