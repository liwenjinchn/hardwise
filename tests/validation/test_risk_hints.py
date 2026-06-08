"""Tests for external reviewer risk-hints contract."""

from __future__ import annotations

from pathlib import Path

from hardwise.ir.types import Component, Design
from hardwise.validation.risk_hints import (
    build_risk_hint_report,
    load_risk_hint_report,
)


def _design() -> Design:
    return Design(
        components={
            "U8": Component(
                refdes="U8",
                value="STM32G030C8T6",
                part_number="STM32G030C8T6",
                package="LQFP48",
            ),
            "U12": Component(
                refdes="U12",
                value="Gate driver",
                part_number="EG2132",
                package="SOP8",
            ),
            "C1": Component(refdes="C1", value="100nF"),
        },
        nets={},
        project_path=Path("tests/fixtures/risk-hints"),
        source_eda="allegro_netlist",
    )


def test_valid_refdes_is_accepted() -> None:
    report = build_risk_hint_report(
        {
            "hints": [
                {
                    "refdes": "U8",
                    "title": "Reset path review",
                    "body": "Check reset pullup against the public design note.",
                    "severity": "review",
                    "source": "external:note#reset",
                }
            ]
        },
        _design(),
    )

    assert report.counts == {
        "accepted": 1,
        "rejected": 0,
        "total": 1,
        "wrapped_refdes": 0,
    }
    assert report.accepted[0].refdes == "U8"
    assert report.accepted[0].title == "Reset path review"
    assert report.accepted[0].severity == "review"
    assert report.accepted[0].source == "external:note#reset"


def test_unknown_anchor_refdes_is_rejected_without_becoming_visible_hint() -> None:
    report = build_risk_hint_report(
        [
            {
                "refdes": "U88",
                "title": "Unknown part",
                "body": "Reviewer note points to a missing component.",
            }
        ],
        _design(),
    )

    assert report.accepted == []
    assert report.rejected_count == 1
    rejected = report.rejected[0]
    assert rejected.reason == "unknown_refdes"
    assert rejected.refdes == "U88"
    assert set(rejected.closest_matches) <= _design().refdes_set
    assert "U8" in rejected.closest_matches


def test_unknown_refdes_in_accepted_body_is_guard_wrapped() -> None:
    report = build_risk_hint_report(
        {
            "refdes": "U8",
            "title": "Check reset",
            "body": "Compare U8 reset with U999 before review signoff.",
        },
        _design(),
    )

    assert report.accepted_count == 1
    assert report.accepted[0].body == "Compare U8 reset with ⟨?U999⟩ before review signoff."
    assert report.wrapped_refdes_count == 1


def test_part_number_and_package_identity_tokens_are_not_wrapped() -> None:
    report = build_risk_hint_report(
        {
            "hints": [
                {
                    "refdes": "U12",
                    "title": "EG2132 package check",
                    "body": "EG2132 in SOP8 should keep bootstrap guidance near U12.",
                    "source": "external:EG2132#SOP8",
                }
            ]
        },
        _design(),
    )

    assert report.accepted_count == 1
    accepted = report.accepted[0]
    assert accepted.title == "EG2132 package check"
    assert accepted.body == "EG2132 in SOP8 should keep bootstrap guidance near U12."
    assert accepted.source == "external:EG2132#SOP8"
    assert report.wrapped_refdes_count == 0


def test_load_risk_hint_report_accepts_json_path(tmp_path: Path) -> None:
    path = tmp_path / "reviewer-hints.json"
    path.write_text(
        """
        {
          "hints": [
            {
              "refdes": "C1",
              "title": "Decoupling placement",
              "body": "Check placement against U8 power pins."
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    report = load_risk_hint_report(path, _design())

    assert report.source_path == str(path)
    assert report.accepted_count == 1
    assert report.accepted[0].refdes == "C1"
