"""Source-capsule semantic evidence must detect drift that preserves totals."""

from pathlib import Path
import runpy

from hardwise.validation.candidate_coverage import (
    Candidate,
    CandidateOutcome,
    CandidateSnapshot,
    RuleCatalog,
    RuleDefinition,
)

ROOT = Path(__file__).parents[1]


def test_candidate_baseline_detects_swapped_results_and_ignores_order():
    helper = runpy.run_path(str(ROOT / "scripts/validate_source_bundle.py"))["candidate_baseline"]
    catalog = RuleCatalog(
        version="synthetic",
        rules=(
            RuleDefinition(rule_id="x", version="1", object_kind="net", scope="Synthetic only"),
        ),
    )
    candidates = tuple(
        Candidate(
            catalog_version="synthetic",
            rule_id="x",
            rule_version="1",
            object_kind="net",
            object_id=n,
            applicability="applicable",
            reason="Synthetic premise",
        )
        for n in ("A", "B")
    )

    def snapshot(states, reverse=False):
        return CandidateSnapshot(
            catalog=catalog,
            candidates=candidates[::-1] if reverse else candidates,
            outcomes=tuple(
                CandidateOutcome(
                    candidate_id=c.candidate_id, result=result, reason="Synthetic result"
                )
                for c, result in zip(candidates, states, strict=True)
            ),
        )

    before = helper(snapshot(("PASS", "UNKNOWN")))
    swapped = helper(snapshot(("UNKNOWN", "PASS")))
    assert before["counts"] == swapped["counts"]
    assert before["identity_state_sha256"] != swapped["identity_state_sha256"]
    assert helper(snapshot(("PASS", "UNKNOWN"), reverse=True)) == before


def test_recorded_bundle_baseline_matches_current_public_scoped_snapshot():
    from hardwise.workbench.context import build_workbench_context, close_workbench_context
    from hardwise.workbench.view_model import build_workbench_state

    builder = runpy.run_path(str(ROOT / "scripts/build_validation_bundle.py"))
    helper = runpy.run_path(str(ROOT / "scripts/validate_source_bundle.py"))["candidate_baseline"]
    ctx = build_workbench_context(
        netlist_path=ROOT / "tests/fixtures/allegro/mixed_controller_power_stage.net",
        bom_path=ROOT / "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv",
        profiles=ROOT / "data/datasheet_profiles",
    )
    try:
        state = build_workbench_state(ctx, datasheet_search_enabled=False)
        observed = dict(
            component_summary=state.summary.model_dump(mode="json"),
            assessment_coverage=state.assessment_coverage.model_dump(mode="json"),
            candidate_coverage=helper(ctx.index.candidate_coverage),
        )
        assert observed == builder["BASELINE"]
    finally:
        close_workbench_context(ctx)
