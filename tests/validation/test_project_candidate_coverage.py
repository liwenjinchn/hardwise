"""Global plan, subcatalog provenance and missing execution cannot silently shrink."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hardwise.ir.types import Component, Design
from hardwise.validation.candidate_coverage import CandidateSnapshot, RuleCatalog
from hardwise.validation.candidate_summary import candidate_records, summarize_candidates
from hardwise.validation.net_candidates import NET_CATALOG, evaluate_net_candidates
from hardwise.validation.project_candidate_coverage import (
    PROJECT_CATALOG,
    enumerate_project_candidates,
    evaluate_project_candidates,
    merge_candidate_snapshots,
)
from hardwise.workbench.context import build_workbench_context, close_workbench_context


def test_empty_project_is_unassessed_and_roundtrips(tmp_path):
    design = Design(project_path=tmp_path, source_eda="allegro_netlist")
    result = evaluate_project_candidates(design, {}, {}, {})
    assert result.counts()["candidate_count"] == result.counts()["unknown_count"] == 1
    assert result.counts()["completed_count"] == 0
    assert CandidateSnapshot.model_validate_json(result.model_dump_json()) == result


def test_unmodeled_component_does_not_invent_electrical_checks(tmp_path):
    design = Design(
        project_path=tmp_path,
        source_eda="allegro_netlist",
        components={"U1": Component(refdes="U1", value="UNKNOWN")},
    )
    result = evaluate_project_candidates(design, {}, {}, {})
    own = [c for c in result.candidates if c.object_id == "U1"]
    assert len(own) == 1 and own[0].rule_id == "unmodeled_component_identity"
    assert result.counts()["unsupported_scope_count"] == 1
    assert "function remains unsupported" in result.outcomes[-1].reason


def test_dropped_output_stays_in_merged_denominator(tmp_path):
    design = Design(project_path=tmp_path, source_eda="allegro_netlist")
    net = evaluate_net_candidates(design)
    complete = merge_candidate_snapshots([net])
    missing = merge_candidate_snapshots(
        [CandidateSnapshot(catalog=NET_CATALOG, candidates=net.candidates)]
    )
    assert complete.candidates == missing.candidates
    assert missing.counts()["unexecuted_count"] == 1
    record = candidate_records(missing)[0]
    assert not record.executed and record.result == "UNKNOWN" and "未执行" in record.reason
    assert dict(missing.candidates[0].instance)["source_catalog"] == NET_CATALOG.version
    assert missing.candidates[0].catalog_version == PROJECT_CATALOG.version


def test_duplicate_scope_and_unregistered_catalog_are_rejected(tmp_path):
    design = Design(project_path=tmp_path, source_eda="allegro_netlist")
    net = evaluate_net_candidates(design)
    with pytest.raises(ValidationError, match="Duplicate candidate"):
        merge_candidate_snapshots([net, net])
    foreign = CandidateSnapshot(catalog=RuleCatalog(version="foreign", rules=()), candidates=())
    with pytest.raises(ValueError, match="Unregistered project subcatalog"):
        merge_candidate_snapshots([foreign])
    with pytest.raises(ValueError, match="foreign component"):
        enumerate_project_candidates(design, {"U9": None}, {})


def test_production_index_and_summary_preserve_plan_across_order_and_legacy_gap():
    root = Path("tests/fixtures/allegro")
    ctx = build_workbench_context(
        netlist_path=root / "mixed_controller_power_stage.net",
        bom_path=root / "mixed_controller_power_stage_bom.csv",
        profiles=Path("data/datasheet_profiles"),
    )
    try:
        snapshot = ctx.index.candidate_coverage
        assert snapshot is not None
        summary = summarize_candidates(snapshot)
        counts = summary.counts
        assert ctx.index.assessment_coverage.full_candidate_count == counts.candidate_count
        assert sum(c.candidate_count for c in summary.by_rule.values()) == counts.candidate_count
        assert sum(c.completed_count for c in summary.by_rule.values()) == counts.completed_count
        assert (
            counts.candidate_count
            == counts.completed_count + counts.unknown_count + counts.not_applicable_count
        )
        assert counts.unexecuted_count == 0
        from hardwise.validation.project_index import _generic_passive_families

        plan = enumerate_project_candidates(
            ctx.design, ctx.validation_targets, _generic_passive_families(ctx.bom)
        )
        assert {c.candidate_id for c in snapshot.candidates} == {
            c.candidate_id for c in plan.candidates
        }
        ctx.design.components = dict(reversed(list(ctx.design.components.items())))
        reordered = enumerate_project_candidates(
            ctx.design, ctx.validation_targets, _generic_passive_families(ctx.bom)
        )
        assert plan.candidates == reordered.candidates
        from hardwise.validation.project_index import ProjectValidationIndex

        old = ctx.index.model_dump()
        old.pop("candidate_coverage")
        legacy = ProjectValidationIndex.model_validate(old)
        assert legacy.candidate_coverage is None and legacy.candidate_summary is None
        assert legacy.assessment_coverage.full_candidate_count is None
    finally:
        close_workbench_context(ctx)
