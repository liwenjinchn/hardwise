from pathlib import Path

from hardwise.adapters.base import ComponentRecord
from hardwise.adapters.kicad import parse_project
from hardwise.checklist.checks.r001_new_component_candidate import check


def _record(refdes: str, footprint: str = "") -> ComponentRecord:
    return ComponentRecord(
        refdes=refdes,
        value="MOCK",
        footprint=footprint,
        datasheet="",
        source_file=Path("/tmp/mock.kicad_sch"),
        source_kind="schematic",
    )


def test_real_component_with_empty_footprint_is_flagged() -> None:
    findings = check([_record("U7", footprint="")])

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R001"
    assert f.severity == "info"
    assert f.refdes == "U7"
    assert f.evidence_tokens, "evidence_tokens must not be empty"
    assert "sch:" in f.evidence_tokens[0]


def test_real_component_with_filled_footprint_is_not_flagged() -> None:
    findings = check([_record("U7", footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")])

    assert findings == []


def test_virtual_kicad_marker_with_empty_footprint_is_not_flagged() -> None:
    """`#PWR05` and `#FLG01` are power flags / no-connect markers, not real parts.
    They almost always have empty Footprint by design — must not be reported."""
    findings = check(
        [
            _record("#PWR05", footprint=""),
            _record("#FLG01", footprint=""),
        ]
    )

    assert findings == []


def test_mixed_set_only_flags_real_empty_footprint_components() -> None:
    findings = check(
        [
            _record("U1", footprint=""),  # flagged
            _record("U2", footprint="LQFP-64"),  # not flagged
            _record("#PWR03", footprint=""),  # not flagged (virtual)
            _record("R5", footprint=""),  # flagged
        ]
    )

    flagged_refdes = {f.refdes for f in findings}
    assert flagged_refdes == {"U1", "R5"}


def test_pic_programmer_runs_without_error_and_skips_virtual_markers() -> None:
    """End-to-end against the real public sample. pic_programmer is a fully
    completed KiCad demo, so all real components have footprints. R001
    should report 0 findings (the 58 empty-footprint records are all #PWR*
    virtual markers, which the rule correctly skips)."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    findings = check(registry.schematic_records)

    assert all(not f.refdes.startswith("#") for f in findings if f.refdes)
    assert len(findings) == 0
