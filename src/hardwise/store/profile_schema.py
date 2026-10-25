"""Additive profile-store columns; NULL means an old incomplete full contract."""

from sqlalchemy import inspect, text


def ensure_profile_columns(session):
    bind = session.get_bind()
    additions = [
        (
            "datasheet_profile_pins",
            "schematic_pin_aliases_json",
            "ALTER TABLE datasheet_profile_pins ADD COLUMN schematic_pin_aliases_json TEXT NOT NULL DEFAULT '[]'",
        ),
        (
            "datasheet_profiles",
            "profile_json",
            "ALTER TABLE datasheet_profiles ADD COLUMN profile_json TEXT",
        ),
    ]
    for table, column, statement in additions:
        names = {item["name"] for item in inspect(bind).get_columns(table)}
        if column not in names:
            session.execute(text(statement))
            session.commit()
