from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile, PinProfile, extract_l78_profile


def test_datasheet_profile_json_round_trip(tmp_path: Path) -> None:
    profile = DatasheetProfile(
        part_number="TEST123",
        abs_max={"vin": 12.0},
        recommended={"vin_max": 9.0},
        pin_function={"1": "Vin"},
        pins=[
            PinProfile(
                number="1",
                name="VIN",
                category="power_input",
                function="Input supply pin.",
                limits={"abs_max_voltage": 12.0},
                recommended_topology=["Connect to input rail."],
                evidence=["datasheet:test.pdf#p2"],
            )
        ],
        evidence={"abs_max.vin": "datasheet:test.pdf#p4"},
        extracted_at="2026-05-26T00:00:00+00:00",
        extracted_model="unit-test",
    )
    path = tmp_path / "test123.json"

    profile.save(path)
    restored = DatasheetProfile.load(path)

    assert restored == profile
    assert restored.pin_by_number("1") is not None
    assert restored.pin_by_number("99") is None


def test_datasheet_profile_loads_v1_without_pin_profiles(tmp_path: Path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(
        """
{
  "part_number": "LEGACY",
  "pin_function": {"1": "VIN"},
  "evidence": {"pin_function.1": "datasheet:legacy.pdf#p1"},
  "extracted_at": "2026-05-26T00:00:00+00:00",
  "extracted_model": "legacy"
}
""".strip(),
        encoding="utf-8",
    )

    profile = DatasheetProfile.load(path)

    assert profile.schema_version == "v1"
    assert profile.pin_function["1"] == "VIN"
    assert profile.pins == []


def test_l78_profile_fixture_loads() -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))

    assert profile.part_number == "L7805"
    assert profile.abs_max["vin"] == 35.0
    assert profile.evidence["abs_max.vin"] == "datasheet:l78.pdf#p4"
    assert profile.pin_function["1"].startswith("VI")
    assert profile.schema_version == "v2"
    assert len(profile.pins) == 3
    assert profile.pin_by_number("1") is not None
    assert profile.pin_by_number("1").category == "power_input"  # type: ignore[union-attr]


def test_extract_l78_profile_is_deterministic_for_supported_pdf() -> None:
    profile = extract_l78_profile(Path("data/datasheets/l78.pdf"))

    assert profile.part_number == "L7805"
    assert profile.abs_max["vin"] == 35.0
    assert profile.recommended["vin_max"] == 25.0
    assert profile.evidence["abs_max.vin"] == "datasheet:l78.pdf#p4"
    assert profile.extracted_model == "deterministic-l78-v3.0"
    assert len(profile.pins) == 3


def test_extract_l78_profile_rejects_other_pdfs() -> None:
    with pytest.raises(ValueError):
        extract_l78_profile(Path("data/datasheets/lt1373.pdf"))
