"""Tests for relational datasheet profile contract storage."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hardwise.cli import app
from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.store.profile_contracts import (
    DatasheetProfileStoreError,
    DatasheetProfileAliasRow,
    DatasheetProfilePinRow,
    DatasheetProfileRow,
    get_datasheet_profile,
    list_datasheet_profiles,
    upsert_datasheet_profile,
)
from hardwise.store.relational import create_store


def _mpq8626_profile() -> DatasheetProfile:
    return DatasheetProfile.load(Path("data/datasheet_profiles/mpq8626.json"))


def test_upsert_and_get_profile_round_trips_all_fields(tmp_path: Path) -> None:
    profile = _mpq8626_profile()
    source_path = Path("data/datasheet_profiles/mpq8626.json")
    session = create_store(tmp_path / "profiles.db")
    try:
        row = upsert_datasheet_profile(session, profile, source_path=source_path)
        stored = get_datasheet_profile(session, "MPQ8626")

        assert row.part_number == "MPQ8626"
        assert row.source_path == str(source_path)
        assert stored is not None
        assert stored.part_number == "MPQ8626"
        assert stored.part_number_aliases == ["MPQ8626GD", "MPQ8626GD-Z"]
        assert stored.review_status == "ready"
        assert stored.schema_version == "v2"
        assert stored.extracted_model == "manual-profile-v1-mpq8626"
        assert stored.recommended["topology_family"] == "buck"
        assert stored.recommended["buck_topology"] == "synchronous"
        assert stored.recommended["vin_min"] == 2.85
        assert stored.recommended["vin_max"] == 16.0
        assert stored.evidence["recommended.output_topology"] == "datasheet:mpq8626.pdf#p17"
        assert len(stored.pins) == 14

        vin = stored.pin_by_number("3")
        assert vin is not None
        assert vin.name == "VIN"
        assert vin.category == "power_input"
        assert vin.limits["recommended_voltage_min"] == 2.85
        assert vin.limits["recommended_voltage_max"] == 16.0
        assert vin.recommended_topology == [
            "Connect to the upstream input rail and local input bypass network."
        ]
        assert vin.evidence == ["datasheet:mpq8626.pdf#p1", "datasheet:mpq8626.pdf#p5"]
    finally:
        session.close()


def test_get_datasheet_profile_finds_by_part_number_and_alias(tmp_path: Path) -> None:
    session = create_store(tmp_path / "profiles.db")
    try:
        upsert_datasheet_profile(session, _mpq8626_profile())

        by_part = get_datasheet_profile(session, "MPQ8626")
        by_alias = get_datasheet_profile(session, "MPQ8626GD-Z")

        assert by_part is not None
        assert by_alias is not None
        assert by_alias.part_number == by_part.part_number
        assert by_alias.pin_by_number("10").name == "BST"
        assert get_datasheet_profile(session, "missing") is None
        assert get_datasheet_profile(session, "   ") is None
    finally:
        session.close()


def test_upsert_replaces_aliases_and_pins(tmp_path: Path) -> None:
    session = create_store(tmp_path / "profiles.db")
    try:
        original = _mpq8626_profile()
        upsert_datasheet_profile(session, original)

        replacement = original.model_copy(
            update={
                "part_number_aliases": ["MPQ8626-REVIEWED"],
                "pins": [
                    PinProfile(
                        number="A",
                        name="VIN",
                        category="power_input",
                        function="Replacement pin row.",
                        evidence=["datasheet:replacement.pdf#p1"],
                    )
                ],
            }
        )
        upsert_datasheet_profile(session, replacement)

        stored = get_datasheet_profile(session, "MPQ8626")
        assert stored is not None
        assert stored.part_number_aliases == ["MPQ8626-REVIEWED"]
        assert [(pin.number, pin.name) for pin in stored.pins] == [("A", "VIN")]
        assert get_datasheet_profile(session, "MPQ8626GD-Z") is None
        assert get_datasheet_profile(session, "MPQ8626-REVIEWED").part_number == "MPQ8626"
        assert session.query(DatasheetProfileAliasRow).count() == 1
        assert session.query(DatasheetProfilePinRow).count() == 1
    finally:
        session.close()


def test_profile_contract_store_round_trips_schematic_pin_aliases(tmp_path: Path) -> None:
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/ln2312lt1g.json"))
    session = create_store(tmp_path / "profiles.db")
    try:
        upsert_datasheet_profile(session, profile)

        stored = get_datasheet_profile(session, "LN2312LT1G")

        assert stored is not None
        assert stored.pin_by_number("1").schematic_pin_aliases == ["G"]
        assert stored.pin_by_number("2").schematic_pin_aliases == ["S"]
        assert stored.pin_by_number("3").schematic_pin_aliases == ["D"]
    finally:
        session.close()


def test_duplicate_alias_is_rejected(tmp_path: Path) -> None:
    session = create_store(tmp_path / "profiles.db")
    try:
        first = _mpq8626_profile().model_copy(
            update={"part_number": "PART_A", "part_number_aliases": ["SHARED_ALIAS"]}
        )
        second = _mpq8626_profile().model_copy(
            update={"part_number": "PART_B", "part_number_aliases": ["SHARED_ALIAS"]}
        )
        upsert_datasheet_profile(session, first)

        with pytest.raises(DatasheetProfileStoreError, match="already used as an alias"):
            upsert_datasheet_profile(session, second)

        assert list_datasheet_profiles(session)[0].part_number == "PART_A"
    finally:
        session.close()


def test_create_store_then_profile_upsert_creates_profile_tables(tmp_path: Path) -> None:
    session = create_store(tmp_path / "profiles.db")
    try:
        upsert_datasheet_profile(session, _mpq8626_profile())

        assert session.query(DatasheetProfileRow).count() == 1
        assert session.query(DatasheetProfileAliasRow).count() == 2
        assert session.query(DatasheetProfilePinRow).count() == 14
    finally:
        session.close()


def test_store_datasheet_profile_cli_writes_contract_store(tmp_path: Path) -> None:
    db_path = tmp_path / "profiles.db"

    result = CliRunner().invoke(
        app,
        [
            "store-datasheet-profile",
            "data/datasheet_profiles/mpq8626.json",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "datasheet-profile-store:" in result.output
    assert "(part=MPQ8626, aliases=2, pins=14, status=ready)" in result.output

    session = create_store(db_path)
    try:
        stored = get_datasheet_profile(session, "MPQ8626GD")
        assert stored is not None
        assert stored.part_number == "MPQ8626"
        assert stored.pin_by_number("3").name == "VIN"
    finally:
        session.close()
