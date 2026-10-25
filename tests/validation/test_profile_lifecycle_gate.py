"""Formal consumers require effective, applicable approval; legacy tags never grant it."""

from pathlib import Path

import pytest

from hardwise.guards.evidence_class import classify_evidence_tokens
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Pin
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument
from hardwise.validation.component import validate_component_against_profile
from hardwise.validation.profile_approval import approved_tokens
from tests.profile_review_fixtures import approve_for_algorithm


def circuit():
    profile = DatasheetProfile.load(Path("data/datasheet_profiles/l78.json"))
    component = Component(
        refdes="U1",
        value="L7805",
        part_number="L7805",
        manufacturer="SYNTHETIC",
        package="TEST-TO220",
        pins=[
            Pin(number=str(i), name="", electrical_type="", is_nc=False, net=n)
            for i, n in [(1, "VIN"), (2, "RET"), (3, "VOUT")]
        ],
    )
    facts = [
        VoltageFact(
            net=n,
            minimum=v,
            maximum=v,
            reference_net="RET",
            source="explicit synthetic test envelope",
            confirmed=True,
            confirmed_by="test author",
        )
        for n, v in [("VIN", 12), ("RET", 0), ("VOUT", 5)]
    ]
    design = Design(
        project_path=Path("/synthetic"),
        source_eda="allegro_netlist",
        components={"U1": component},
        voltage_facts=VoltageFactsDocument(facts=facts),
    )
    return component, profile, design


@pytest.mark.parametrize("legacy", ["ready", "needs_review"])
def test_old_tags_cannot_certify_new_formal_checks(legacy):
    component, profile, design = circuit()
    profile = profile.model_copy(update={"review_status": legacy})
    report = validate_component_against_profile(component, profile, design)
    assert report.profile_lifecycle == "DRAFT" and report.legacy_profile_status == legacy
    assert report.result == "UNKNOWN" and report.reviewed_profile_tokens == []
    assert all(
        c.result == "UNKNOWN" and c.needs_review and c.evidence_kind == "HYPOTHESIS"
        for c in [*report.pin_results, *report.component_checks]
    )
    assert any(c.check == "profile_review_status" for c in report.component_checks)
    assert all(
        c.rule_version.endswith(".profile-review1")
        for c in [*report.pin_results, *report.component_checks]
    )


def test_fictional_complete_applicable_review_drives_the_actual_algorithm():
    component, profile, design = circuit()
    profile = approve_for_algorithm(
        profile, manufacturer=component.manufacturer, packages=[component.package]
    )
    report = validate_component_against_profile(component, profile, design)
    assert report.profile_lifecycle == "READY"
    assert [p.result for p in report.pin_results] == ["PASS", "PASS", "UNKNOWN"]
    # Reviewed nominal output metadata still cannot certify an unmodelled output bound.
    assert report.reviewed_profile_tokens == sorted(approved_tokens(profile))
    classification = classify_evidence_tokens(
        report.reviewed_profile_tokens, reviewed_profile_tokens=report.reviewed_profile_tokens
    )
    assert any(item.source_class == "reviewed_profile" for item in classification)


@pytest.mark.parametrize(
    "changes",
    [{"manufacturer": None}, {"manufacturer": "OTHER"}, {"package": None}, {"package": "OTHER"}],
)
def test_reviewed_content_does_not_apply_to_missing_or_wrong_identity_scope(changes):
    component, profile, design = circuit()
    profile = approve_for_algorithm(
        profile, manufacturer=component.manufacturer, packages=[component.package]
    )
    component = component.model_copy(update=changes)
    report = validate_component_against_profile(component, profile, design)
    assert report.result == "UNKNOWN" and not report.reviewed_profile_tokens
    assert all(c.result == "UNKNOWN" for c in [*report.pin_results, *report.component_checks])


def test_mutating_an_approved_value_cannot_reuse_the_old_record():
    component, profile, design = circuit()
    profile = approve_for_algorithm(
        profile, manufacturer=component.manufacturer, packages=[component.package]
    )
    old = profile.field_review.model_dump(mode="json")
    profile = profile.model_copy(update={"abs_max": {**profile.abs_max, "vin": 11.0}})
    report = validate_component_against_profile(component, profile, design)
    assert report.profile_lifecycle == "DRAFT" and report.result == "UNKNOWN"
    assert profile.field_review.model_dump(mode="json") == old


def test_source_prefix_without_context_never_proves_field_approval():
    tokens = ["datasheet:l78.pdf#p4", "reviewer_to_confirm:foo", "pdf:l78.pdf#p4"]
    results = classify_evidence_tokens(tokens)
    assert all(item.source_class == "profile_candidate" for item in results)
    # The iterable is materialized once; a generator cannot approve only the first token.
    results = classify_evidence_tokens(tokens, reviewed_profile_tokens=(x for x in tokens))
    assert all(item.source_class == "reviewed_profile" for item in results)
