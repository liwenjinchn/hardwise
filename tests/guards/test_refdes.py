from pathlib import Path

from hardwise.adapters.base import BoardRegistry, ComponentRecord
from hardwise.checklist.finding import Finding
from hardwise.guards.refdes import sanitize_args, sanitize_finding, sanitize_text


def _registry(refdes_list: list[str]) -> BoardRegistry:
    components = [
        ComponentRecord(
            refdes=r,
            value="",
            footprint="",
            datasheet="",
            source_file=Path("/tmp/x.kicad_sch"),
            source_kind="schematic",
        )
        for r in refdes_list
    ]
    return BoardRegistry(project_dir=Path("/tmp/x"), components=components)


def test_sanitize_text_wraps_only_unverified_refdes() -> None:
    reg = _registry(["U23", "C1"])
    text = "U23 should be near C1, but U999 is hallucinated and J7 too"

    out, wrapped = sanitize_text(text, reg)

    assert "U23" in out
    assert "C1" in out
    assert "⟨?U999⟩" in out
    assert "⟨?J7⟩" in out
    assert wrapped == 2


def test_sanitize_text_handles_no_refdes_in_text() -> None:
    reg = _registry(["U1"])
    out, wrapped = sanitize_text("plain prose with no designators here", reg)

    assert wrapped == 0
    assert out == "plain prose with no designators here"


def test_sanitize_text_leaves_pin_name_parentheses_untouched() -> None:
    reg = _registry(["U1"])
    out, wrapped = sanitize_text("U1 pin 17 (RA0) and U1 pin 18 (RB1)", reg)

    assert "RA0" in out
    assert "RB1" in out
    assert "⟨?" not in out
    assert wrapped == 0


def test_sanitize_text_leaves_multi_function_pin_names_untouched() -> None:
    reg = _registry(["U5", "U6"])
    out, wrapped = sanitize_text(
        "U5 pin 12 (ICSPC/RB6) and U6 pin 3 (GP4/OSC2)", reg
    )

    assert "RB6" in out
    assert "GP4" in out
    assert "OSC2" in out
    assert "⟨?" not in out
    assert wrapped == 0


def test_sanitize_text_leaves_connector_nc_pin_list_untouched() -> None:
    reg = _registry(["J1"])
    out, wrapped = sanitize_text(
        "J1 has 1 NC pins (A4) on a connector-like part", reg
    )

    assert "A4" in out
    assert "⟨?" not in out
    assert wrapped == 0


def test_sanitize_text_leaves_alphanumeric_pin_numbers_untouched() -> None:
    reg = _registry(["XA1"])
    out, wrapped = sanitize_text(
        "XA1 pin A4 (A4) and XA1 pin GND3 (GND) marked NC", reg
    )

    assert "A4" in out
    assert "GND3" in out
    assert "⟨?" not in out
    assert wrapped == 0


def test_sanitize_finding_wraps_message_action_and_refdes_field() -> None:
    reg = _registry(["U23"])
    f = Finding(
        rule_id="R001",
        severity="info",
        refdes="U999",
        message="U999 has problems with U23",
        suggested_action="check J7 carefully",
        evidence_tokens=["sch:foo.kicad_sch#U999"],
    )

    sanitized, wrapped = sanitize_finding(f, reg)

    assert sanitized.refdes == "⟨?U999⟩"
    assert "⟨?U999⟩" in sanitized.message
    assert "U23" in sanitized.message  # verified, kept as-is
    assert "⟨?J7⟩" in sanitized.suggested_action
    assert wrapped >= 3  # refdes field + U999 in message + J7 in action


def test_sanitize_finding_passthrough_when_all_verified() -> None:
    reg = _registry(["U7", "C5"])
    f = Finding(
        rule_id="R001",
        severity="info",
        refdes="U7",
        message="U7 needs C5 nearby",
        suggested_action="place C5 within 2mm of U7",
        evidence_tokens=["sch:x.kicad_sch#U7"],
    )

    sanitized, wrapped = sanitize_finding(f, reg)

    assert wrapped == 0
    assert sanitized.refdes == "U7"
    assert "⟨" not in sanitized.message


def test_sanitize_args_wraps_string_values_only() -> None:
    reg = _registry(["U3"])
    args = {"refdes": "U999", "top_k": 5, "query": "U3 pin function", "filter": None}

    sanitized, wrapped = sanitize_args(args, reg)

    assert sanitized["refdes"] == "⟨?U999⟩"
    assert sanitized["query"] == "U3 pin function"  # U3 verified, untouched
    assert sanitized["top_k"] == 5  # non-string passthrough
    assert sanitized["filter"] is None
    assert wrapped == 1


def test_sanitize_args_empty_dict() -> None:
    reg = _registry(["U1"])
    sanitized, wrapped = sanitize_args({}, reg)
    assert sanitized == {}
    assert wrapped == 0
