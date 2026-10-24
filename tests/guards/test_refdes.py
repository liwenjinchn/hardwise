from pathlib import Path

import pytest

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


def test_sanitize_text_passes_verified_part_number_and_package() -> None:
    """Refdes-shaped part numbers / packages from the registry pass; near-misses don't.

    `EG2132` (value) and `SOP8` (footprint) are real board identifiers that match
    the refdes regex — wrapping them is a false positive. A near-miss like
    `EG2133` and an unknown designator like `Q999` are absent from the board and
    must still be wrapped, so anti-hallucination is preserved.
    """
    reg = BoardRegistry(
        project_dir=Path("/tmp/x"),
        components=[
            ComponentRecord(
                refdes="U3",
                value="EG2132",
                footprint="SOP8",
                datasheet="",
                source_file=Path("/tmp/x.kicad_sch"),
                source_kind="schematic",
            )
        ],
    )

    out, wrapped = sanitize_text("U3 (EG2132, SOP8) but EG2133 and Q999 are invented", reg)

    assert "EG2132" in out and "⟨?EG2132⟩" not in out
    assert "SOP8" in out and "⟨?SOP8⟩" not in out
    assert "⟨?EG2133⟩" in out
    assert "⟨?Q999⟩" in out
    assert wrapped == 2


def test_sanitize_text_wraps_missing_refdes_even_when_equal_to_component_value() -> None:
    """A common-refdes-prefix value such as `R47` is not a verified board object."""
    reg = BoardRegistry(
        project_dir=Path("/tmp/x"),
        components=[
            ComponentRecord(
                refdes="U1",
                value="R47",
                footprint="SOT-23",
                datasheet="",
                source_file=Path("/tmp/x.kicad_sch"),
                source_kind="schematic",
            )
        ],
    )

    out, wrapped = sanitize_text("U1 mentions R47, but R47 is not a board refdes", reg)

    assert "U1" in out
    assert "⟨?R47⟩" in out
    assert wrapped == 2


def test_sanitize_text_is_idempotent_for_already_wrapped_tokens() -> None:
    reg = _registry([])

    out, wrapped = sanitize_text("already marked ⟨?U999⟩ plus U999", reg)

    assert out == "already marked ⟨?U999⟩ plus ⟨?U999⟩"
    assert wrapped == 1


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


def test_sanitize_text_does_not_let_pin_parentheses_hide_common_refdes() -> None:
    reg = _registry(["U1"])

    out, wrapped = sanitize_text("U1 pin 5 (Q47) needs checking", reg)

    assert "⟨?Q47⟩" in out
    assert wrapped == 1


def test_sanitize_text_leaves_multi_function_pin_names_untouched() -> None:
    reg = _registry(["U5", "U6"])
    out, wrapped = sanitize_text("U5 pin 12 (ICSPC/RB6) and U6 pin 3 (GP4/OSC2)", reg)

    assert "RB6" in out
    assert "GP4" in out
    assert "OSC2" in out
    assert "⟨?" not in out
    assert wrapped == 0


def test_sanitize_text_leaves_connector_nc_pin_list_untouched() -> None:
    reg = _registry(["J1"])
    out, wrapped = sanitize_text("J1 has 1 NC pins (A4) on a connector-like part", reg)

    assert "A4" in out
    assert "⟨?" not in out
    assert wrapped == 0


def test_sanitize_text_leaves_alphanumeric_pin_numbers_untouched() -> None:
    reg = _registry(["XA1"])
    out, wrapped = sanitize_text("XA1 pin A4 (A4) and XA1 pin GND3 (GND) marked NC", reg)

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


@pytest.mark.parametrize("text", ["检查U999是否接地", "请复查U10000。", "U123456 的供电"])
def test_guard_covers_chinese_adjacency_and_long_numbers(text: str) -> None:
    out, wrapped = sanitize_text(text, _registry([]))
    assert wrapped == 1
    assert "⟨?U" in out
    assert sanitize_text(out, _registry([])) == (out, 0)


def test_guard_preserves_verified_long_refdes_in_chinese() -> None:
    text = "检查U10000与R12345之间的连接"
    assert sanitize_text(text, _registry(["U10000", "R12345"])) == (text, 0)


@pytest.mark.parametrize("text", ["DDR4 内存接口", "检查DDR4接口", "DDR5 与 DDR3"])
def test_guard_distinguishes_memory_generation_words(text: str) -> None:
    assert sanitize_text(text, _registry([])) == (text, 0)


@pytest.mark.parametrize("text", ["位号DDR4", "refdes DDR4", "component DDR4"])
def test_explicit_component_context_does_not_exempt_memory_words(text: str) -> None:
    out, wrapped = sanitize_text(text, _registry([]))
    assert "⟨?DDR4⟩" in out
    assert wrapped == 1


def test_ascii_identifiers_are_not_partially_rewritten() -> None:
    text = "USB3P0_D_P PCIE_TX3P3V abcU999 U999_A U999B"
    assert sanitize_text(text, _registry([])) == (text, 0)


def test_common_refdes_cannot_hide_as_direct_pin_name() -> None:
    out, wrapped = sanitize_text("U1 pin U999", _registry(["U1"]))
    assert out == "U1 pin ⟨?U999⟩"
    assert wrapped == 1


def test_finding_object_identity_stays_strict_for_technical_words() -> None:
    finding = Finding(
        rule_id="R001",
        severity="info",
        refdes="DDR4",
        message="DDR4 内存",
        suggested_action="人工复核",
        evidence_tokens=[],
    )
    out, wrapped = sanitize_finding(finding, _registry([]))
    assert out.refdes == "⟨?DDR4⟩"
    assert out.message == "DDR4 内存"
    assert wrapped == 1


@pytest.mark.parametrize("identity", ["DDR4", "SOP8", "U10000"])
def test_explicit_tool_object_does_not_use_prose_exemptions(identity: str) -> None:
    args = {"refdes": identity, "query": "DDR4 内存"}
    out, wrapped = sanitize_args(args, _registry([]))
    assert out == {"refdes": f"⟨?{identity}⟩", "query": "DDR4 内存"}
    assert wrapped == 1
    assert args["refdes"] == identity  # the actual tool input remains untouched
    assert sanitize_args(out, _registry([])) == (out, 0)
