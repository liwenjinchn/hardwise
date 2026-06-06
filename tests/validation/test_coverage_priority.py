"""Tests for advisory coverage-priority analytics."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.validation.coverage_priority import (
    DETERMINISTIC_VALIDATOR_FAMILIES,
    SUGGESTED_FAMILY_TO_VALIDATOR_FAMILIES,
    build_family_coverage_report,
    render_family_coverage_markdown,
    score_candidate,
    validator_family_exists,
)


def test_validator_family_mapping_tracks_dispatch_family_names() -> None:
    assert DETERMINISTIC_VALIDATOR_FAMILIES == {
        "buck",
        "half_bridge_gate_driver",
        "mcu_basic",
        "i2c_mux",
        "diode",
        "connector",
        "mosfet",
        "bjt",
        "shift_register_piso",
        "i2c_level_shift_repeater",
    }
    mapped = {
        validator
        for validators in SUGGESTED_FAMILY_TO_VALIDATOR_FAMILIES.values()
        for validator in validators
    }
    assert mapped <= DETERMINISTIC_VALIDATOR_FAMILIES
    assert validator_family_exists("ic")
    assert validator_family_exists("transistor")
    assert validator_family_exists("diode")
    assert not validator_family_exists("inductor")
    assert not validator_family_exists("unknown")


def test_score_candidate_prioritizes_active_validator_like_families() -> None:
    ic_score, ic_band = score_candidate("ic", 1)
    unknown_score, unknown_band = score_candidate("unknown", 1)
    passive_score, passive_band = score_candidate("capacitor", 60)

    assert ic_score > unknown_score
    assert passive_score < ic_score
    assert ic_band == "medium"
    assert unknown_band == "low"
    assert passive_band == "low"


def test_family_report_counts_only_unmatched_refdes_in_mixed_group(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        rows=[
            _row("D1", "matched"),
            _row("D2", "no_result"),
            _row("D3", "manual_needed"),
            _row("R1", "manual_needed"),
        ],
        groups=[
            _group(
                "diode-led-bank",
                ["D1", "D2", "D3"],
                suggested_family="diode",
                identity="LED0603",
                profile_status="mixed",
            ),
            _group(
                "passive-resistor",
                ["R1"],
                suggested_family="resistor",
                identity="10K",
                identity_kind="passive_value",
            ),
        ],
    )

    report = build_family_coverage_report(index_path)

    assert report.skipped_covered == 1
    assert len(report.recommendations) == 1
    recommendation = report.recommendations[0]
    assert recommendation.suggested_family == "diode"
    assert recommendation.uncovered_refdes_count == 2
    assert recommendation.group_count == 1
    assert recommendation.recommended_action == "try_existing_validator_profile"
    assert recommendation.candidate_validator_families == ["diode"]
    assert recommendation.identity_sample == ["LED0603"]


def test_family_report_orders_by_impact_and_marks_unmapped_families(
    tmp_path: Path,
) -> None:
    index_path = _write_index(
        tmp_path,
        rows=[
            _row("Q1", "no_result"),
            _row("Q2", "no_result"),
            _row("Q3", "no_result"),
            _row("L1", "no_result"),
            _row("L2", "no_result"),
        ],
        groups=[
            _group("transistor-bank", ["Q1", "Q2", "Q3"], "transistor", "SS8050"),
            _group("inductor-bank", ["L1", "L2"], "inductor", "6.8uH"),
        ],
    )

    report = build_family_coverage_report(index_path)

    assert [item.suggested_family for item in report.recommendations] == [
        "transistor",
        "inductor",
    ]
    assert report.recommendations[0].impact_score == 2.7
    assert report.recommendations[0].recommended_action == "try_existing_validator_profile"
    assert report.recommendations[1].impact_score == 1.0
    assert report.recommendations[1].recommended_action == "triage_for_new_validator"


def test_family_report_skips_generic_validated_passives(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        rows=[
            _row("L1", "generic_passive", validation=_validation("L1", "GENERIC_INDUCTOR")),
            _row("D1", "no_result"),
        ],
        groups=[
            _group("inductor-bank", ["L1"], "inductor", "6.8uH"),
            _group("diode-bank", ["D1"], "diode", "BAV99"),
        ],
    )

    report = build_family_coverage_report(index_path)

    assert report.skipped_covered == 1
    assert [item.suggested_family for item in report.recommendations] == ["diode"]


def test_render_family_coverage_markdown_is_advisory(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        rows=[_row("U1", "no_result")],
        groups=[_group("controller", ["U1"], "ic", "LM393")],
    )
    report = build_family_coverage_report(index_path)

    text = render_family_coverage_markdown(report)

    assert "Review priority only" in text
    assert "Validator families to check" in text
    assert "LM393" in text
    assert "try_existing_validator_profile" in text
    assert "PASS" not in text
    assert "WARN" not in text
    assert "ERROR" not in text


def _write_index(tmp_path: Path, *, rows: list[dict], groups: list[dict]) -> Path:
    path = tmp_path / "project-index.json"
    path.write_text(
        json.dumps(
            {
                "project_name": "coverage-fixture",
                "generated_at": "2026-05-31T00:00:00+08:00",
                "netlist_source": "fixture.net",
                "netlist_type": "allegro",
                "bom_source": "fixture_bom.csv",
                "profiles_dir": "data/datasheet_profiles",
                "components_in_design": len(rows),
                "bom_matched": len(rows),
                "rows": rows,
                "component_groups": groups,
            }
        ),
        encoding="utf-8",
    )
    return path


def _row(refdes: str, match_status: str, *, validation: dict | None = None) -> dict:
    row = {
        "refdes": refdes,
        "bom_value": "",
        "part_number": "",
        "manufacturer": "Fixture",
        "match_status": match_status,
        "reason": "fixture",
    }
    if validation is not None:
        row["validation"] = validation
    return row


def _validation(refdes: str, profile_part_number: str) -> dict:
    return {
        "refdes": refdes,
        "component_value": "fixture",
        "profile_part_number": profile_part_number,
        "pin_results": [
            {
                "pin_number": "1",
                "pin_name": "Terminal 1",
                "category": "generic_inductor_terminal",
                "status": "PASS",
                "summary": "fixture",
            }
        ],
        "component_checks": [],
    }


def _group(
    group_id: str,
    refdes: list[str],
    suggested_family: str,
    identity: str,
    *,
    identity_kind: str = "mpn",
    profile_status: str = "no_result",
) -> dict:
    return {
        "group_id": group_id,
        "source_line": 1,
        "refdes": refdes,
        "refdes_count": len(refdes),
        "refdes_sample": refdes[:8],
        "value": identity,
        "part_number": identity,
        "manufacturer": "Fixture",
        "identity": identity,
        "normalized_identity": identity.lower(),
        "identity_kind": identity_kind,
        "suggested_family": suggested_family,
        "profile_status": profile_status,
        "validation_status": "not_validated",
        "document_status": "no_result",
        "document_reason": "fixture",
    }
