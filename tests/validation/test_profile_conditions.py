"""Vendor-audited relationship regression; synthetic reviewed rules are not approval."""

from pathlib import Path

import pytest

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.component import validate_component_against_profile
from hardwise.validation.profile_conditions import validate_voltage_relations


def _setup(tmp_path, en=(24, 24), vin=(12, 12), *, confirmed=True, reference="GND"):
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
    component = Component(
        refdes="U1",
        value="XL1509-12E1",
        package="SOP8",
        pins=[
            Pin(number=str(number), name="", electrical_type="passive", is_nc=False, net=net)
            for number, net in [
                (1, "VIN"),
                (2, "SW"),
                (3, "VOUT"),
                (4, "EN"),
                (5, "GND"),
                (6, "GND"),
                (7, "GND"),
                (8, "GND"),
            ]
        ],
    )
    facts = [
        VoltageFact(
            net=net,
            minimum=limits[0],
            maximum=limits[1],
            reference_net=reference,
            source="Explicit synthetic operating envelope",
            confirmed=confirmed,
            confirmed_by="fixture author",
        )
        for net, limits in [("VIN", vin), ("EN", en), ("VOUT", (12, 12))]
    ]
    design = Design(
        project_path=tmp_path,
        source_eda="allegro_netlist",
        components={"U1": component},
        voltage_facts=VoltageFactsDocument(facts=facts),
    )
    return profile, component, design


@pytest.mark.parametrize(
    "en,vin,result",
    [
        ((24, 24), (12, 12), "FAIL"),
        ((0, 0), (12, 12), "PASS"),
        ((12, 12), (12, 12), "PASS"),
        ((-1, -1), (12, 12), "FAIL"),
        ((-0.3, -0.3), (12, 12), "PASS"),
        ((10, 14), (12, 16), "UNKNOWN"),
        ((0, 1), (4.5, 40), "PASS"),
    ],
)
def test_relative_bound_uses_confirmed_envelopes(tmp_path, en, vin, result):
    profile, component, design = _setup(tmp_path, en, vin)
    check = validate_voltage_relations(component, profile, design)[0]
    assert check.result == result
    assert check.check == "pin_voltage_relation_4"
    assert "datasheet:xl1509.pdf#p4" in check.evidence
    assert any("voltage_fact:EN" in token for token in check.evidence)


@pytest.mark.parametrize(
    "change",
    [
        "unconfirmed",
        "different_ground",
        "typical_only",
        "wrong_part",
        "wrong_package",
        "missing_pin",
        "names_only",
        "other_mode",
    ],
)
def test_missing_identity_conditions_or_facts_cannot_pass(tmp_path, change):
    profile, component, design = _setup(tmp_path, en=(0, 0))
    if change == "unconfirmed":
        design.voltage_facts.facts = [
            f.model_copy(update={"confirmed": False}) for f in design.voltage_facts.facts
        ]
    if change == "different_ground":
        design.voltage_facts.facts = [
            f.model_copy(update={"reference_net": "ISOLATED_GND"})
            for f in design.voltage_facts.facts
        ]
    if change == "typical_only":
        design.voltage_facts.facts = [
            f.model_copy(update={"minimum": None, "maximum": None, "typical": 0})
            for f in design.voltage_facts.facts
        ]
    if change == "wrong_part":
        component.value = "XL1509-ADJE1"
    if change == "wrong_package":
        component.package = "OTHER"
    if change == "missing_pin":
        component.pins = [p for p in component.pins if p.number != "5"]
    if change == "names_only":
        design.voltage_facts = VoltageFactsDocument()
    if change == "other_mode":
        design.voltage_facts.active_mode = "standby"
    assert validate_voltage_relations(component, profile, design)[0].result == "UNKNOWN"


def test_quarantined_profile_cannot_certify_even_when_relation_is_evaluable(tmp_path):
    profile, component, design = _setup(tmp_path)
    assert profile.review_status == "needs_review"
    assert "on_off" not in profile.abs_max
    assert "inductor_min_uh" not in profile.recommended
    assert profile.pin_by_number("4").limits == {}
    report = validate_component_against_profile(component, profile, design)
    assert report.result == "UNKNOWN"
    assert report.needs_review
    assert all(c.result == "UNKNOWN" for c in [*report.pin_results, *report.component_checks])
    assert next(c for c in report.component_checks if c.check == "pin_voltage_relation_4").evidence


def test_reviewed_synthetic_relation_can_detect_original_counterexample(tmp_path):
    profile, component, design = _setup(tmp_path)
    # Explicit test-only approval exercises integration, never writes READY to disk.
    profile = profile.model_copy(update={"review_status": "ready"})
    report = validate_component_against_profile(component, profile, design)
    assert (
        next(c for c in report.component_checks if c.check == "pin_voltage_relation_4").result
        == "FAIL"
    )
    assert next(p for p in report.pin_results if p.pin_number == "4").result == "UNKNOWN"


def test_voltage_relation_metadata_roundtrips():
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/xl1509.json"))
    restored = DatasheetProfile.model_validate_json(profile.model_dump_json())
    assert restored == profile
    assert restored.voltage_relations[0].document_revision == "Rev 2.6"


def test_33uh_never_receives_a_global_68uh_violation(tmp_path):
    from hardwise.validation.dcdc import _validate_buck_inductor

    profile, component, design = _setup(tmp_path, en=(0, 0), vin=(15, 15))
    inductor = Component(
        refdes="L1",
        value="33uH",
        pins=[
            Pin(number="1", name="", electrical_type="passive", is_nc=False, net="SW"),
            Pin(number="2", name="", electrical_type="passive", is_nc=False, net="VOUT"),
        ],
    )
    design.components["L1"] = inductor
    check = _validate_buck_inductor(inductor, component, profile, design, "SW")
    assert check.result == "UNKNOWN"
    assert "不套用全局电感阈值" in check.summary
    assert "below" not in check.summary
    # The load-current and maximum-input conditions are intentionally not invented.
    assert "负载" in check.summary


def test_quarantine_does_not_erase_raw_topology_counterexamples(tmp_path):
    from hardwise.validation.component import _validate_component_topology

    profile, component, design = _setup(tmp_path)
    checks = _validate_component_topology(component, profile, design)
    assert next(check for check in checks if check.check == "buck_inductor").result == "FAIL"
    assert next(check for check in checks if check.check == "buck_freewheel_diode").result == "FAIL"


def test_quarantined_profile_is_visible_but_not_executable_in_primary_import():
    from hardwise.workbench.context import build_workbench_context, close_workbench_context
    from hardwise.workbench.view_model import build_workbench_state

    context = build_workbench_context(
        netlist_path=Path("tests/fixtures/allegro/mixed_controller_power_stage.net"),
        bom_path=Path("tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"),
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        row = next(row for row in context.index.rows if row.refdes == "U12")
        assert row.validation is None
        assert row.profile_path is None
        assert "隔离" in row.reason
        assert "U12" not in context.validation_targets
        candidate = next(c for c in context.candidate_report.candidates if c.refdes == "U12")
        assert candidate.candidates == [Path("data/datasheet_profiles/xl1509.json")]
        queue = next(
            row
            for row in build_workbench_state(context, datasheet_search_enabled=False).queue
            if row.refdes == "U12"
        )
        assert queue.deterministic_status_group == "manual"
        assert "隔离" in queue.title
    finally:
        close_workbench_context(context)
