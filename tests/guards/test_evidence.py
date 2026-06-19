from hardwise.checklist.finding import EvidenceStep, Finding
from hardwise.guards.evidence import (
    cited_evidence_tokens,
    strip_unsupported,
    unsupported_evidence_tokens,
)


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


def test_strip_keeps_structured_evidence_chain_tokens() -> None:
    finding = Finding(
        rule_id="R009",
        severity="high",
        message="power pin unconnected",
        evidence_chain=[
            EvidenceStep(
                source="eda",
                claim="U1 pin 3 is unconnected",
                token="sch:main.kicad_sch#U1",
            )
        ],
    )

    kept, dropped = strip_unsupported([finding])

    assert dropped == 0
    assert kept == [finding]


def test_strip_handles_empty_input() -> None:
    kept, dropped = strip_unsupported([])
    assert kept == []
    assert dropped == 0


def test_cited_evidence_tokens_extracts_datasheet_and_doc_tokens() -> None:
    text = "见 datasheet:l78.pdf#p4 和 doc:mixed_controller#row3，详见上文。"
    assert cited_evidence_tokens(text) == [
        "datasheet:l78.pdf#p4",
        "doc:mixed_controller#row3",
    ]


def test_cited_evidence_tokens_dedupes_preserving_order() -> None:
    text = "datasheet:a.pdf#p1, datasheet:b.pdf#p2; datasheet:a.pdf#p1"
    assert cited_evidence_tokens(text) == ["datasheet:a.pdf#p1", "datasheet:b.pdf#p2"]


def test_cited_evidence_tokens_matches_token_glued_to_cjk() -> None:
    # Model prose often glues a token directly to Chinese text with no space;
    # the guard must still detect it (Python `\b` would not — see pattern note).
    assert cited_evidence_tokens("电感不足datasheet:xl1509.pdf#p8") == [
        "datasheet:xl1509.pdf#p8"
    ]


def test_cited_evidence_tokens_ignores_embedded_prefix() -> None:
    # A prefix glued to a longer ASCII word is not a source token.
    assert cited_evidence_tokens("xdatasheet:nope.pdf#p1") == []


def test_unsupported_evidence_tokens_flags_unbacked_prose_token() -> None:
    text = "L1 不足 datasheet:xl1509.pdf#p8 另见 datasheet:ghost.pdf#p9。"
    verified = ["datasheet:xl1509.pdf#p8"]
    assert unsupported_evidence_tokens(text, verified) == ["datasheet:ghost.pdf#p9"]


def test_unsupported_evidence_tokens_empty_when_all_backed() -> None:
    text = "见 datasheet:l78.pdf#p4。"
    assert unsupported_evidence_tokens(text, ["datasheet:l78.pdf#p4"]) == []
