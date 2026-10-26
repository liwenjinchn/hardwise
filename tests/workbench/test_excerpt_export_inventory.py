"""Export inventory: distinguish excerpt-bearing shares from summaries and local reads."""

import json

import pytest
from fastapi.testclient import TestClient

from hardwise.report.validator_multi_ui import ValidatorUiResult, render as render_multi
from hardwise.report.validator_project_ui import render_project_workbench
from hardwise.report.workbench_spa_snapshot import render_spa_snapshot
from hardwise.workbench.chat import WorkbenchChatService
from hardwise.workbench.context import close_workbench_context
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.server import create_workbench_app
from tests.agent.test_evidence_locator import _context
from tests.workbench.test_excerpt_exports import configure, SENTINEL, db_rows
from tests.workbench.test_offline_report import _snapshot


SUMMARY_EXPORTS = [
    "/api/workbench/export?format=json",
    "/api/workbench/export?format=csv",
    "/api/workbench/export?format=annotations",
    "/api/workbench/prep-packet?format=json",
    "/api/workbench/prep-packet?format=markdown",
    "/api/workbench/components/U8/prep-packet?format=json",
    "/api/workbench/components/U8/prep-packet?format=markdown",
    "/api/workbench/review-decisions/history",
]


@pytest.mark.parametrize("decision", [None, "allow", "withhold"])
def test_summary_downloads_do_not_copy_profile_excerpt_or_mutate_history(tmp_path, decision):
    context = _context()
    configure(context, decision)
    journal = tmp_path / "review.sqlite"
    with TestClient(
        create_workbench_app(
            context,
            WorkbenchChatService(context, mode="fake"),
            review_db=journal,
            auto_datasheet_candidates=False,
        )
    ) as client:
        before = db_rows(journal)
        for path in SUMMARY_EXPORTS:
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
            assert SENTINEL not in response.text, path
        assert db_rows(journal) == before
        # Local provenance remains complete, regardless of what a share exposes.
        assert SENTINEL in build_run_provenance(context).model_dump_json()


@pytest.mark.parametrize("decision", [None, "allow", "withhold"])
def test_cli_spa_renderer_and_all_embedded_derivatives_follow_sharing(decision):
    context = _context()
    configure(context, decision)
    try:
        html = render_spa_snapshot(context)
        snapshot = _snapshot(html)
        assert (SENTINEL in html) == (decision == "allow")
        for key in ["components", "component_prep_markdown", "project_prep_markdown", "exports"]:
            assert SENTINEL not in json.dumps(snapshot[key]), key
        assert (SENTINEL in json.dumps(snapshot["run_provenance"])) == (decision == "allow")
        assert SENTINEL in build_run_provenance(context).model_dump_json()
    finally:
        close_workbench_context(context)


@pytest.mark.parametrize("decision", ["allow", "withhold"])
def test_legacy_component_renderer_does_not_embed_full_profile(decision):
    context = _context()
    profile = configure(context, decision)
    try:
        row = next(r for r in context.index.validated_rows if r.refdes == "U8")
        result = ValidatorUiResult(
            validation=row.validation, profile_path=context.netlist_source, profile=profile
        )
        html = render_multi(
            context.design,
            [result],
            project_name="Synthetic export inventory",
            netlist_source=context.netlist_source,
        )
        assert SENTINEL not in html
        project = render_project_workbench(
            context.design,
            context.index,
            project_name="Synthetic export inventory",
            netlist_source=context.netlist_source,
        )
        assert SENTINEL not in project
    finally:
        close_workbench_context(context)
