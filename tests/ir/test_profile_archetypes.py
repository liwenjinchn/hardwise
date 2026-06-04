from pathlib import Path

from typer.testing import CliRunner

from hardwise.bom import parse_bom
from hardwise.cli import app
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.profile_draft import ProfileDraftError, draft_profile_from_project_index
from hardwise.validation.component_groups import ProjectComponentGroup
from hardwise.validation.profile_candidates import suggest_profile_candidates
from hardwise.validation.project_index import ProjectValidationIndex


def test_74x165_archetype_generates_needs_review_profile(tmp_path: Path) -> None:
    index_path = _write_shift_register_index(tmp_path)

    profile = draft_profile_from_project_index(
        index_path,
        identity="74LV165PW",
        archetype_id="74x165_piso_16pin",
    )

    assert profile.part_number == "74LV165PW"
    assert profile.review_status == "needs_review"
    assert "74LV165" in profile.part_number_aliases
    assert profile.recommended["topology_family"] == "shift_register_piso"
    assert profile.recommended["load_pin"] == "1"
    assert profile.recommended["clock_pin"] == "2"
    assert profile.recommended["serial_output_pin"] == "9"
    assert profile.recommended["serial_input_pin"] == "10"
    assert profile.recommended["clock_enable_pin"] == "15"
    assert len(profile.pins) == 16
    q7 = profile.pin_by_number("9")
    vcc = profile.pin_by_number("16")
    first_pin = profile.pin_by_number("1")
    assert q7 is not None
    assert vcc is not None
    assert first_pin is not None
    assert q7.name == "Q7"
    assert vcc.category == "power_input"
    assert "Reviewer must confirm" in profile.pin_function["1"]
    assert profile.evidence["recommended.serial_chain"].startswith("reviewer_to_confirm:")
    assert first_pin.evidence[0].startswith("reviewer_to_confirm:")


def test_draft_datasheet_profile_cli_accepts_archetype(tmp_path: Path) -> None:
    index_path = _write_shift_register_index(tmp_path)
    output = tmp_path / "74lv165pw-draft.json"

    result = CliRunner().invoke(
        app,
        [
            "draft-datasheet-profile",
            str(index_path),
            "--identity",
            "74LV165PW",
            "--archetype",
            "74x165_piso_16pin",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "archetype=74x165_piso_16pin" in result.output
    profile = DatasheetProfile.load(output)
    assert profile.review_status == "needs_review"
    assert profile.recommended["topology_family"] == "shift_register_piso"


def test_draft_profile_attaches_datasheet_chunk_evidence(tmp_path: Path) -> None:
    index_path = _write_shift_register_index(tmp_path)
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text(
        "\n".join(
            [
                '{"text":"pin table","source_pdf":"74lv165.html","page":3,'
                '"chunk_index":0,"evidence_token":"datasheet:74lv165.html#p3"}',
                '{"text":"application","source_pdf":"74lv165.html","page":8,'
                '"chunk_index":0}',
            ]
        ),
        encoding="utf-8",
    )

    profile = draft_profile_from_project_index(
        index_path,
        identity="74LV165PW",
        evidence_chunks_path=chunks,
    )

    assert profile.review_status == "needs_review"
    assert profile.evidence["document.source"] == "doc:74lv165"
    assert profile.evidence["evidence.chunks.count"] == "2"
    assert profile.evidence["evidence.chunks.sources"] == "74lv165.html"
    assert profile.evidence["evidence.chunks.tokens"] == (
        "datasheet:74lv165.html#p3, datasheet:74lv165.html#p8"
    )


def test_draft_datasheet_profile_cli_accepts_evidence_chunks(tmp_path: Path) -> None:
    index_path = _write_shift_register_index(tmp_path)
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text(
        '{"text":"pin table","source_pdf":"74lv165.html","page":3,"chunk_index":0}\n',
        encoding="utf-8",
    )
    output = tmp_path / "74lv165pw-draft.json"

    result = CliRunner().invoke(
        app,
        [
            "draft-datasheet-profile",
            str(index_path),
            "--identity",
            "74LV165PW",
            "--evidence-chunks",
            str(chunks),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "evidence_chunks=on" in result.output
    profile = DatasheetProfile.load(output)
    assert profile.review_status == "needs_review"
    assert profile.evidence["evidence.chunks.tokens"] == "datasheet:74lv165.html#p3"


def test_generated_archetype_profile_is_ignored_by_profile_matching(tmp_path: Path) -> None:
    index_path = _write_shift_register_index(tmp_path)
    profile = draft_profile_from_project_index(
        index_path,
        identity="74LV165PW",
        archetype_id="74x165_piso_16pin",
    )
    profiles = tmp_path / "profiles"
    profile.save(profiles / "74lv165pw-draft.json")
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "Reference,Quantity,Value,Manufacturer,MPN\n"
        "U1,1,74LV165PW,Nexperia,74LV165PW\n",
        encoding="utf-8",
    )

    report = suggest_profile_candidates(parse_bom(bom_path), profiles)

    assert report.candidates[0].match_status == "no_result"
    assert report.candidates[0].profile is None


def test_unknown_archetype_reports_available_choices(tmp_path: Path) -> None:
    index_path = _write_shift_register_index(tmp_path)

    try:
        draft_profile_from_project_index(
            index_path,
            identity="74LV165PW",
            archetype_id="missing",
        )
    except ProfileDraftError as exc:
        assert "unknown profile archetype 'missing'" in str(exc)
        assert "74x165_piso_16pin" in str(exc)
    else:
        raise AssertionError("unknown archetype should fail")


def _write_shift_register_index(tmp_path: Path) -> Path:
    index = ProjectValidationIndex(
        project_name="shift-archetype",
        generated_at="2026-06-02T00:00:00+00:00",
        netlist_source="tests/fixtures/allegro/shift.net",
        netlist_type="allegro_netlist",
        bom_source=str(tmp_path / "bom.csv"),
        profiles_dir="data/datasheet_profiles",
        components_in_design=1,
        bom_matched=1,
        component_groups=[
            ProjectComponentGroup(
                group_id="item:1",
                item_number="1",
                source_line=2,
                refdes=["U1"],
                refdes_count=1,
                refdes_sample=["U1"],
                value="74LV165PW",
                part_number="74LV165PW",
                manufacturer="Nexperia",
                identity="74LV165PW",
                normalized_identity="74lv165pw",
                identity_kind="mpn",
                suggested_family="ic",
                profile_status="no_result",
                validation_status="not_validated",
                document_status="matched",
                document_title="74LV165 public datasheet",
                document_url="https://example.test/74lv165.pdf",
                document_source="doc:74lv165",
            )
        ],
    )
    path = tmp_path / "project-index.json"
    path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
    return path
