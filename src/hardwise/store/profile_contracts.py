"""Relational storage for structured datasheet profile contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Column, ForeignKey, Integer, String, Text, inspect, text
from sqlalchemy.orm import Session

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.store.relational import Base


class DatasheetProfileStoreError(ValueError):
    """Raised when a datasheet profile cannot be stored unambiguously."""


class DatasheetProfileRow(Base):
    """One materialized datasheet contract header."""

    __tablename__ = "datasheet_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String, unique=True, nullable=False, index=True)
    review_status = Column(String, nullable=False, default="needs_review")
    abs_max_json = Column(Text, nullable=False, default="{}")
    recommended_json = Column(Text, nullable=False, default="{}")
    pin_function_json = Column(Text, nullable=False, default="{}")
    evidence_json = Column(Text, nullable=False, default="{}")
    extracted_at = Column(String, nullable=False, default="")
    extracted_model = Column(String, nullable=False, default="")
    schema_version = Column(String, nullable=False, default="v1")
    source_path = Column(String, nullable=False, default="")


class DatasheetProfileAliasRow(Base):
    """One part-number alias for a datasheet contract."""

    __tablename__ = "datasheet_profile_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer,
        ForeignKey("datasheet_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias = Column(String, nullable=False, index=True)
    ordinal = Column(Integer, nullable=False, default=0)


class DatasheetProfilePinRow(Base):
    """One structured pin row for a datasheet contract."""

    __tablename__ = "datasheet_profile_pins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        Integer,
        ForeignKey("datasheet_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal = Column(Integer, nullable=False, default=0)
    number = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, default="")
    schematic_pin_aliases_json = Column(Text, nullable=False, default="[]")
    category = Column(String, nullable=False, default="")
    function = Column(Text, nullable=False, default="")
    limits_json = Column(Text, nullable=False, default="{}")
    recommended_topology_json = Column(Text, nullable=False, default="[]")
    evidence_json = Column(Text, nullable=False, default="[]")


def upsert_datasheet_profile(
    session: Session,
    profile: DatasheetProfile,
    *,
    source_path: Path | None = None,
) -> DatasheetProfileRow:
    """Insert or replace one structured datasheet profile contract."""

    _ensure_tables(session)
    existing = (
        session.query(DatasheetProfileRow)
        .filter(DatasheetProfileRow.part_number == profile.part_number)
        .one_or_none()
    )
    _validate_identity_namespace(session, profile, excluded_profile_id=existing.id if existing else None)
    if existing is None:
        row = DatasheetProfileRow(part_number=profile.part_number)
        session.add(row)
        session.flush()
    else:
        row = existing
        session.query(DatasheetProfileAliasRow).filter(
            DatasheetProfileAliasRow.profile_id == row.id
        ).delete()
        session.query(DatasheetProfilePinRow).filter(
            DatasheetProfilePinRow.profile_id == row.id
        ).delete()

    row.review_status = profile.review_status
    row.abs_max_json = _json_dump(profile.abs_max)
    row.recommended_json = _json_dump(profile.recommended)
    row.pin_function_json = _json_dump(profile.pin_function)
    row.evidence_json = _json_dump(profile.evidence)
    row.extracted_at = profile.extracted_at
    row.extracted_model = profile.extracted_model
    row.schema_version = profile.schema_version
    row.source_path = str(source_path or "")

    for idx, alias in enumerate(_profile_aliases(profile)):
        session.add(DatasheetProfileAliasRow(profile_id=row.id, alias=alias, ordinal=idx))
    for idx, pin in enumerate(profile.pins):
        session.add(
            DatasheetProfilePinRow(
                profile_id=row.id,
                ordinal=idx,
                number=pin.number,
                name=pin.name,
                schematic_pin_aliases_json=_json_dump(pin.schematic_pin_aliases),
                category=pin.category,
                function=pin.function,
                limits_json=_json_dump(pin.limits),
                recommended_topology_json=_json_dump(pin.recommended_topology),
                evidence_json=_json_dump(pin.evidence),
            )
        )

    session.commit()
    return row


def get_datasheet_profile(session: Session, part_or_alias: str) -> DatasheetProfile | None:
    """Load a structured datasheet profile by part number or alias."""

    _ensure_tables(session)
    identity = part_or_alias.strip()
    if not identity:
        return None
    row = (
        session.query(DatasheetProfileRow)
        .filter(DatasheetProfileRow.part_number == identity)
        .one_or_none()
    )
    if row is None:
        alias_row = (
            session.query(DatasheetProfileAliasRow)
            .filter(DatasheetProfileAliasRow.alias == identity)
            .one_or_none()
        )
        if alias_row is None:
            return None
        row = session.get(DatasheetProfileRow, alias_row.profile_id)
        if row is None:
            return None
    return _row_to_profile(session, row)


def list_datasheet_profiles(session: Session) -> list[DatasheetProfile]:
    """Return all stored structured datasheet profiles ordered by part number."""

    _ensure_tables(session)
    rows = session.query(DatasheetProfileRow).order_by(DatasheetProfileRow.part_number).all()
    return [_row_to_profile(session, row) for row in rows]


def _row_to_profile(session: Session, row: DatasheetProfileRow) -> DatasheetProfile:
    aliases = [
        alias.alias
        for alias in session.query(DatasheetProfileAliasRow)
        .filter(DatasheetProfileAliasRow.profile_id == row.id)
        .order_by(DatasheetProfileAliasRow.ordinal, DatasheetProfileAliasRow.alias)
        .all()
    ]
    pins = [
        PinProfile(
            number=pin.number,
            name=pin.name,
            schematic_pin_aliases=_json_load(pin.schematic_pin_aliases_json, []),
            category=pin.category,
            function=pin.function,
            limits=_json_load(pin.limits_json, {}),
            recommended_topology=_json_load(pin.recommended_topology_json, []),
            evidence=_json_load(pin.evidence_json, []),
        )
        for pin in session.query(DatasheetProfilePinRow)
        .filter(DatasheetProfilePinRow.profile_id == row.id)
        .order_by(DatasheetProfilePinRow.ordinal, DatasheetProfilePinRow.number)
        .all()
    ]
    return DatasheetProfile(
        part_number=row.part_number,
        part_number_aliases=aliases,
        review_status=row.review_status,
        abs_max=_json_load(row.abs_max_json, {}),
        recommended=_json_load(row.recommended_json, {}),
        pin_function=_json_load(row.pin_function_json, {}),
        pins=pins,
        evidence=_json_load(row.evidence_json, {}),
        extracted_at=row.extracted_at,
        extracted_model=row.extracted_model,
        schema_version=row.schema_version,
    )


def _profile_aliases(profile: DatasheetProfile) -> list[str]:
    return [alias.strip() for alias in profile.part_number_aliases if alias.strip()]


def _validate_identity_namespace(
    session: Session,
    profile: DatasheetProfile,
    *,
    excluded_profile_id: int | None,
) -> None:
    part_number = profile.part_number.strip()
    aliases = _profile_aliases(profile)
    identities = [part_number, *aliases]
    if not part_number:
        raise DatasheetProfileStoreError("datasheet profile part_number cannot be blank")
    if len(identities) != len(set(identities)):
        raise DatasheetProfileStoreError(
            f"datasheet profile identity is duplicated within {part_number}"
        )

    part_query = session.query(DatasheetProfileRow).filter(
        DatasheetProfileRow.part_number.in_(aliases)
    )
    alias_query = session.query(DatasheetProfileAliasRow).filter(
        DatasheetProfileAliasRow.alias.in_(identities)
    )
    if excluded_profile_id is not None:
        part_query = part_query.filter(DatasheetProfileRow.id != excluded_profile_id)
        alias_query = alias_query.filter(
            DatasheetProfileAliasRow.profile_id != excluded_profile_id
        )

    conflicting_part = part_query.first()
    if conflicting_part is not None:
        raise DatasheetProfileStoreError(
            f"datasheet profile alias already used as a part number: "
            f"{conflicting_part.part_number}"
        )

    conflicting_alias = alias_query.first()
    if conflicting_alias is not None:
        raise DatasheetProfileStoreError(
            f"datasheet profile identity already used as an alias: {conflicting_alias.alias}"
        )


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _ensure_tables(session: Session) -> None:
    bind = session.get_bind()
    Base.metadata.create_all(
        bind,
        tables=[
            DatasheetProfileRow.__table__,
            DatasheetProfileAliasRow.__table__,
            DatasheetProfilePinRow.__table__,
        ],
    )
    _ensure_profile_pin_alias_column(session)


def _ensure_profile_pin_alias_column(session: Session) -> None:
    """Add the pin-alias column for profile stores created before D3b."""

    bind = session.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("datasheet_profile_pins")}
    if "schematic_pin_aliases_json" in columns:
        return
    session.execute(
        text(
            "ALTER TABLE datasheet_profile_pins "
            "ADD COLUMN schematic_pin_aliases_json TEXT NOT NULL DEFAULT '[]'"
        )
    )
    session.commit()
