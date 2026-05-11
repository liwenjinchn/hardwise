from pathlib import Path

import pytest

from hardwise.checklist.loader import load_rules


def test_load_real_checklist_yaml_returns_only_active_rules() -> None:
    rules = load_rules(Path("data/checklists/sch_review.yaml"))

    assert len(rules) >= 1, "at least R001 must be active"
    ids = [r.id for r in rules]
    assert "R001" in ids
    assert all(r.status == "active" for r in rules)


def test_load_rules_r001_fields_intact() -> None:
    rules = load_rules(Path("data/checklists/sch_review.yaml"))
    r001 = next(r for r in rules if r.id == "R001")

    assert r001.severity == "info"
    assert r001.slice == 1
    assert "r001_new_component_candidate" in r001.check_function
    assert r001.required_evidence  # at least one evidence source listed


def test_load_rules_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_rules(Path("data/checklists/does_not_exist.yaml"))


def test_load_rules_rejects_non_list_root(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("just a string, not a list", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rules(bad)
