from pathlib import Path

import pytest

from hardwise.ir.profile import (
    DatasheetProfile,
    extract_l78_profile,
    extract_pca9548a_profile,
)


def test_datasheet_profile_json_round_trip(tmp_path: Path) -> None:
    profile = DatasheetProfile(
        part_number="TEST123",
        abs_max={"vin": 12.0},
        recommended={"vin_max": 9.0},
        pin_function={"1": "Vin"},
        evidence={"abs_max.vin": "datasheet:test.pdf#p4"},
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )
    path = tmp_path / "test123.json"

    profile.save(path)
    restored = DatasheetProfile.load(path)

    assert restored == profile


def test_l78_profile_fixture_loads() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))

    assert profile.part_number == "L7805"
    assert profile.abs_max["vin"] == 35.0
    assert profile.recommended["vout_nominal"] == 5.0
    assert profile.evidence["abs_max.vin"] == "datasheet:l78.pdf#p4"
    assert profile.evidence["recommended.vout_nominal"] == "datasheet:l78.pdf#p6"
    assert profile.pin_function["1"].startswith("VI")


def test_pca9548a_profile_fixture_loads() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/pca9548a.json"))

    assert profile.part_number == "PCA9548A"
    assert profile.recommended["vdd_min"] == 2.3
    assert profile.recommended["vdd_max"] == 5.5
    assert len(profile.pin_function) == 24
    assert profile.pin_function["3"] == "RESET (active-low reset input)"
    assert profile.pin_function["22"] == "SCL (upstream serial clock input)"
    assert profile.evidence["pin_function.24"] == "datasheet:pca9548a.pdf#p4"


def test_extract_l78_profile_is_deterministic_for_supported_pdf() -> None:
    profile = extract_l78_profile(Path("data/datasheets/l78.pdf"))

    assert profile.part_number == "L7805"
    assert profile.abs_max["vin"] == 35.0
    assert profile.recommended["vin_max"] == 25.0
    assert profile.recommended["vout_nominal"] == 5.0
    assert profile.evidence["abs_max.vin"] == "datasheet:l78.pdf#p4"
    assert profile.extracted_model == "deterministic-l78-v2.4"


def test_extract_pca9548a_profile_is_deterministic_for_supported_pdf() -> None:
    profile = extract_pca9548a_profile(Path("data/datasheets/pca9548a.pdf"))

    assert profile.part_number == "PCA9548A"
    assert profile.recommended["vdd_max"] == 5.5
    assert profile.pin_function["12"] == "VSS (ground)"
    assert profile.pin_function["24"] == "VDD (supply voltage)"
    assert profile.evidence["recommended.vdd_min"] == "datasheet:pca9548a.pdf#p15"
    assert profile.extracted_model == "deterministic-pca9548a-v3.0"


def test_extract_l78_profile_rejects_other_pdfs() -> None:
    with pytest.raises(ValueError):
        extract_l78_profile(Path("data/datasheets/lt1373.pdf"))


def test_extract_pca9548a_profile_rejects_other_pdfs() -> None:
    with pytest.raises(ValueError):
        extract_pca9548a_profile(Path("data/datasheets/l78.pdf"))
