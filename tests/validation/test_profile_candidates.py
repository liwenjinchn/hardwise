"""Tests for BOM-to-profile candidate generation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom import parse_bom
from hardwise.documents import match_documents_to_bom, parse_document_index
from hardwise.ir.build import build_design_from_netlist
from hardwise.validation.profile_candidates import (
    ProfileCandidateError,
    render_profile_candidate_manifest,
    suggest_profile_candidates,
)


def test_suggest_profile_candidates_matches_mixed_regulators() -> None:
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))

    report = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))

    assert report.counts_by_status == {
        "matched": 2,
        "no_result": 8,
        "ambiguous": 0,
        "manual_needed": 0,
    }
    matches = {candidate.refdes: candidate for candidate in report.candidates}
    assert matches["U1"].profile == Path("data/datasheet_profiles/l78.json")
    assert matches["U12"].profile == Path("data/datasheet_profiles/xl1509.json")
    assert matches["D5"].match_status == "no_result"


def test_suggest_profile_candidates_matches_profile_aliases(tmp_path: Path) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U13,1,MPQ8626GD,MPS,MPQ8626GD\n"
        "U23,1,MPQ8626GD-Z,MPS,MPQ8626GD-Z\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), Path("data/datasheet_profiles"))

    matches = {candidate.refdes: candidate for candidate in report.candidates}
    assert matches["U13"].profile == Path("data/datasheet_profiles/mpq8626.json")
    assert matches["U23"].profile == Path("data/datasheet_profiles/mpq8626.json")


def test_suggest_profile_candidates_extracts_public_mpn_from_value_after_internal_pn(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U13,1,IC MPQ8626GD-Z QFN-14 power converter MPS,MPS,1273963\n"
        "D26,1,TVS 1.5SMC15A SMC Littelfuse,Littelfuse,1276307\n"
        "D27,1,Schottky SM340AF SMA-FL LRC,LRC,1260597\n"
        "D36,1,Schottky SD103AWS-7-F SOD323 Diodes,Diodes,1179226\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), Path("data/datasheet_profiles"))

    matches = {candidate.refdes: candidate for candidate in report.candidates}
    assert matches["U13"].match_status == "matched"
    assert matches["U13"].identity == "MPQ8626GD-Z"
    assert matches["U13"].identity_kind == "value_mpn"
    assert matches["U13"].profile == Path("data/datasheet_profiles/mpq8626.json")
    assert matches["D26"].profile == Path("data/datasheet_profiles/1_5smc15a.json")
    assert matches["D27"].profile == Path("data/datasheet_profiles/sm340af.json")
    assert matches["D36"].profile == Path("data/datasheet_profiles/sd103aws_7_f.json")


def test_suggest_profile_candidates_rejects_value_mpn_when_pin_ids_do_not_fit(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U13,1,IC MPQ8626GD-Z QFN-14 power converter MPS,MPS,1273963\n",
        encoding="utf-8",
    )
    netlist_path = tmp_path / "mpq_bad_pin_fit.net"
    netlist_path.write_text(
        """$PACKAGES
  ! 'QFN14' ! MPQ8626_LOCAL ; U13
$NETS
  'P12V' ; U13.A
  'GND' ; U13.B
$END
""",
        encoding="utf-8",
    )
    design = build_design_from_netlist(parse_allegro_netlist(netlist_path))

    report = suggest_profile_candidates(
        parse_bom(bom_path),
        Path("data/datasheet_profiles"),
        design=design,
    )

    candidate = report.candidates[0]
    assert candidate.refdes == "U13"
    assert candidate.match_status == "no_result"
    assert candidate.identity == "MPQ8626GD-Z"
    assert candidate.identity_kind == "value_mpn"
    assert candidate.profile is None
    assert "pin IDs do not match" in candidate.reason


def test_suggest_profile_candidates_matches_l2n7002klt1g_mpn(tmp_path: Path) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "PQ10,1,Mainboard local transistor label,LRC,L2N7002KLT1G\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), Path("data/datasheet_profiles"))

    candidate = report.candidates[0]
    assert candidate.refdes == "PQ10"
    assert candidate.match_status == "matched"
    assert candidate.identity == "L2N7002KLT1G"
    assert candidate.identity_kind == "mpn"
    assert candidate.profile == Path("data/datasheet_profiles/l2n7002klt1g.json")


def test_suggest_profile_candidates_uses_matched_document_mpn_with_pin_fit(
    tmp_path: Path,
) -> None:
    value_alias = "N-MOS管 L2N7002KLT1G SOT23 1.5 LRC"
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        f"PQ10,1,{value_alias},LRC,\n",
        encoding="utf-8",
    )
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Manufacturer,Title,URL,Value\n"
        f"L2N7002KLT1G,LRC,L2 public datasheet,https://example.test/l2.pdf,{value_alias}\n",
        encoding="utf-8",
    )
    netlist_path = tmp_path / "l2.net"
    netlist_path.write_text(
        """$PACKAGES
  ! 'SOT23' ! LOCAL_VALUE ; PQ10
$NETS
  'P3V3' ; PQ10.1
  'GND' ; PQ10.2
  'P12V' ; PQ10.3
$END
""",
        encoding="utf-8",
    )
    bom = parse_bom(bom_path)
    document_report = match_documents_to_bom(bom, parse_document_index(docs_path))
    design = build_design_from_netlist(parse_allegro_netlist(netlist_path))

    report = suggest_profile_candidates(
        bom,
        Path("data/datasheet_profiles"),
        document_report=document_report,
        design=design,
    )

    candidate = report.candidates[0]
    assert candidate.refdes == "PQ10"
    assert candidate.match_status == "matched"
    assert candidate.identity == "L2N7002KLT1G"
    assert candidate.identity_kind == "document_mpn"
    assert candidate.profile == Path("data/datasheet_profiles/l2n7002klt1g.json")
    assert "doc:docs.csv#line2" in candidate.reason


def test_suggest_profile_candidates_rejects_document_mpn_when_pin_ids_do_not_fit(
    tmp_path: Path,
) -> None:
    value_alias = "N-MOS管 LN2312LT1G 5A SOT-23 LRC"
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        f"PQ9,1,{value_alias},LRC,\n",
        encoding="utf-8",
    )
    docs_path = tmp_path / "docs.csv"
    docs_path.write_text(
        "MPN,Manufacturer,Title,URL,Value\n"
        f"LN2312LT1G,LRC,LN public datasheet,https://example.test/ln.pdf,{value_alias}\n",
        encoding="utf-8",
    )
    netlist_path = tmp_path / "ln.net"
    netlist_path.write_text(
        """$PACKAGES
  ! 'SOT23' ! LOCAL_VALUE ; PQ9
$NETS
  'P3V3' ; PQ9.G
  'GND' ; PQ9.S
  'P12V' ; PQ9.D
$END
""",
        encoding="utf-8",
    )
    bom = parse_bom(bom_path)
    document_report = match_documents_to_bom(bom, parse_document_index(docs_path))
    design = build_design_from_netlist(parse_allegro_netlist(netlist_path))

    report = suggest_profile_candidates(
        bom,
        Path("data/datasheet_profiles"),
        document_report=document_report,
        design=design,
    )

    candidate = report.candidates[0]
    assert candidate.refdes == "PQ9"
    assert candidate.match_status == "no_result"
    assert candidate.identity == "LN2312LT1G"
    assert candidate.identity_kind == "document_mpn"
    assert candidate.profile is None
    assert "pin IDs do not match" in candidate.reason


def test_suggest_profile_candidates_skips_needs_review_drafts(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    draft = profiles / "draft.json"
    draft.write_text(
        '{"part_number":"DRAFT123","review_status":"needs_review",'
        '"extracted_at":"2026-05-29T00:00:00+00:00","extracted_model":"test"}',
        encoding="utf-8",
    )
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\nU1,1,DRAFT123,Fixture,DRAFT123\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), profiles)

    assert report.candidates[0].match_status == "no_result"
    assert report.candidates[0].profile is None


def test_suggest_profile_candidates_reports_manual_needed_for_missing_identity(
    tmp_path: Path,
) -> None:
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\nR1,1,10K,Yageo,\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), Path("data/datasheet_profiles"))

    candidate = report.candidates[0]
    assert candidate.refdes == "R1"
    assert candidate.match_status == "manual_needed"
    assert candidate.identity_kind == "missing"


def test_suggest_profile_candidates_reports_ambiguous_duplicate_profile(
    tmp_path: Path,
) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78-a.json")
    shutil.copyfile(Path("data/datasheet_profiles/l78.json"), profiles / "l78-b.json")
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\nU1,1,L7805,ST,L7805\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), profiles)

    candidate = report.candidates[0]
    assert candidate.match_status == "ambiguous"
    assert candidate.candidates == [profiles / "l78-a.json", profiles / "l78-b.json"]


def test_render_profile_candidate_manifest_can_emit_v35_manifest_shape() -> None:
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))
    report = suggest_profile_candidates(bom, Path("data/datasheet_profiles"))

    text = render_profile_candidate_manifest(report, matched_only=True)

    assert "status:" not in text
    assert "unmatched:" not in text
    assert "refdes: U1" in text
    assert "profile: data/datasheet_profiles/l78.json" in text
    assert "refdes: U12" in text
    assert "profile: data/datasheet_profiles/xl1509.json" in text


def test_suggest_profile_candidates_rejects_missing_profile_dir() -> None:
    bom = parse_bom(Path("tests/fixtures/allegro/mixed_regulators_bom.csv"))

    with pytest.raises(ProfileCandidateError, match="profile directory not found"):
        suggest_profile_candidates(bom, Path("does/not/exist"))
