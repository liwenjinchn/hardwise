"""Full-contract persistence, legacy completeness markers and corrupt data refusal."""

import sqlite3
from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.store.profile_contracts import (
    DatasheetProfileRow,
    DatasheetProfileStoreError,
    get_datasheet_profile,
    upsert_datasheet_profile,
)
from hardwise.store.relational import create_store
from tests.ir.test_profile_review import ready_profile


def test_all_declared_profiles_roundtrip_entire_model(tmp_path):
    for path in sorted(Path("data/datasheet_profiles").glob("*.json")):
        profile = DatasheetProfile.load(path)
        session = create_store(tmp_path / (path.stem + ".sqlite"))
        try:
            upsert_datasheet_profile(session, profile)
            actual = get_datasheet_profile(session, profile.part_number)
            assert actual.model_dump(mode="json") == profile.model_dump(mode="json"), path
        finally:
            session.close()


def test_relationship_updates_and_intentional_empty_list_survive_restart(tmp_path):
    path = tmp_path / "profile.sqlite"
    source = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
    for relations in [source.voltage_relations, source.voltage_relations[:1], []]:
        profile = source.model_copy(update={"voltage_relations": relations})
        session = create_store(path)
        upsert_datasheet_profile(session, profile)
        session.close()
        reopened = create_store(path)
        try:
            stored = get_datasheet_profile(reopened, source.part_number)
            assert stored.voltage_relations == relations
            assert stored.storage_integrity == "complete"
        finally:
            reopened.close()


def test_review_decisions_sources_and_effective_state_survive_storage(tmp_path):
    profile = ready_profile()
    session = create_store(tmp_path / "synthetic.sqlite")
    try:
        upsert_datasheet_profile(session, profile)
        stored = get_datasheet_profile(session, profile.part_number)
        assert stored.model_dump(mode="json") == profile.model_dump(mode="json")
        assert stored.lifecycle == "READY"
        changed = stored.model_copy(update={"abs_max": {"vin": 36.0}})
        upsert_datasheet_profile(session, changed)
        stored = get_datasheet_profile(session, profile.part_number)
        assert stored.lifecycle == "DRAFT"
        assert stored.field_review.fields[-1].decisions == profile.field_review.fields[-1].decisions
    finally:
        session.close()


def test_legacy_schema_addition_keeps_old_row_and_marks_missing_contract(tmp_path):
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as old:
        old.execute("""CREATE TABLE datasheet_profiles (
          id INTEGER PRIMARY KEY, part_number TEXT NOT NULL UNIQUE, review_status TEXT NOT NULL,
          abs_max_json TEXT NOT NULL, recommended_json TEXT NOT NULL, pin_function_json TEXT NOT NULL,
          evidence_json TEXT NOT NULL, extracted_at TEXT NOT NULL, extracted_model TEXT NOT NULL,
          schema_version TEXT NOT NULL, source_path TEXT NOT NULL)""")
        row = (
            1,
            "SYNTHETIC-X",
            "ready",
            '{"vin":35}',
            "{}",
            "{}",
            "{}",
            "old-time",
            "legacy",
            "v2",
            "missing.json",
        )
        old.execute("INSERT INTO datasheet_profiles VALUES (?,?,?,?,?,?,?,?,?,?,?)", row)
    session = create_store(path)
    try:
        stored = get_datasheet_profile(session, "SYNTHETIC-X")
        assert stored.review_status == "ready" and stored.abs_max == {"vin": 35.0}
        assert stored.storage_integrity == "legacy_incomplete" and stored.lifecycle == "DRAFT"
    finally:
        session.close()
    with sqlite3.connect(path) as migrated:
        actual = migrated.execute(
            "SELECT id,part_number,review_status,abs_max_json,recommended_json,pin_function_json,evidence_json,extracted_at,extracted_model,schema_version,source_path FROM datasheet_profiles"
        ).fetchone()
        assert actual == row
        assert migrated.execute("SELECT profile_json FROM datasheet_profiles").fetchone() == (None,)


@pytest.mark.parametrize("corruption", ["not json", "{}", '{"part_number":"WRONG"}'])
def test_corrupt_authoritative_contract_never_silently_falls_back(tmp_path, corruption):
    session = create_store(tmp_path / "broken.sqlite")
    try:
        profile = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
        upsert_datasheet_profile(session, profile)
        row = session.query(DatasheetProfileRow).one()
        row.profile_json = corruption
        session.commit()
        with pytest.raises(DatasheetProfileStoreError, match="no empty fallback"):
            get_datasheet_profile(session, profile.part_number)
    finally:
        session.close()


def test_full_contract_identity_must_match_lookup_index(tmp_path):
    session = create_store(tmp_path / "identity.sqlite")
    try:
        source = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
        upsert_datasheet_profile(session, source)
        row = session.query(DatasheetProfileRow).one()
        row.profile_json = source.model_copy(
            update={"part_number": "SYNTHETIC-WRONG"}
        ).model_dump_json()
        session.commit()
        with pytest.raises(DatasheetProfileStoreError):
            get_datasheet_profile(session, source.part_number)
    finally:
        session.close()


@pytest.mark.parametrize("broken", ["{", "[]", '"not a mapping"'])
def test_legacy_corruption_does_not_turn_into_an_empty_limit_mapping(tmp_path, broken):
    session = create_store(tmp_path / "legacy-broken.sqlite")
    try:
        source = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
        upsert_datasheet_profile(session, source)
        row = session.query(DatasheetProfileRow).one()
        row.profile_json = None
        row.abs_max_json = broken
        session.commit()
        with pytest.raises(DatasheetProfileStoreError):
            get_datasheet_profile(session, source.part_number)
    finally:
        session.close()
