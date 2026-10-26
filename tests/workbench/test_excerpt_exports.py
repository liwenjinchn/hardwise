"""Actual download paths redact excerpts without rewriting local audit history."""

import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from hardwise.ir.excerpt_sharing import ExcerptSharingDeclaration, source_content_hash
from hardwise.workbench.chat import WorkbenchChatService, ChatRequest
from hardwise.workbench.excerpt_exports import share_chat_response
from hardwise.workbench.decision_fingerprints import _profile
from hardwise.workbench.run_provenance import build_run_provenance
from hardwise.workbench.server import create_workbench_app
from tests.agent.test_evidence_locator import _context
from tests.workbench.test_chat_claim_integration import CatalogModel
from tests.workbench.test_offline_report import _snapshot

SENTINEL = "SYNTHETIC_EXCERPT_NO_REAL_VENDOR_RIGHTS_83"


def configure(context, decision):
    profile = context.validation_targets["U8"]
    review = profile.field_review
    fields = []
    for field in review.fields:
        source = field.source.model_copy(update={"excerpt": SENTINEL, "sharing": None})
        if decision is not None:
            source = source.model_copy(
                update={
                    "sharing": ExcerptSharingDeclaration(
                        decision=decision,
                        source_sha256=source_content_hash(source),
                        declared_by="SYNTHETIC TEST RECORD",
                        declared_at="2026-10-26T00:00:00Z",
                        reason="Fictional permission for automated tests only",
                        actor="human",
                    )
                }
            )
        field = field.model_copy(update={"source": source})
        # Explicit fictional reapproval only for the modified test fixture.
        field = field.model_copy(
            update={
                "decisions": [
                    field.decisions[-1].model_copy(
                        update={"content_sha256": field.content_hash(review.identity)}
                    )
                ]
            }
        )
        fields.append(field)
    profile = profile.model_copy(
        update={"field_review": review.model_copy(update={"fields": fields})}
    )
    assert profile.approved_for_validation
    context.validation_targets["U8"] = profile
    return profile


def db_rows(journal):
    with sqlite3.connect(journal) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: db.execute('SELECT * FROM "' + t + '"').fetchall() for t in tables}


@pytest.mark.parametrize("decision", [None, "withhold", "allow"])
def test_current_and_history_downloads_and_nested_html_apply_declared_sharing(tmp_path, decision):
    context = _context()
    profile = configure(context, decision)
    local_before = profile.model_dump(mode="json")
    journal = tmp_path / "review.sqlite"
    service = WorkbenchChatService(context, mode="fake")
    with TestClient(create_workbench_app(context, service, review_db=journal)) as client:
        state = client.get("/api/workbench/state").json()
        ids = state["review_decisions"]
        raw_before = db_rows(journal)
        assert SENTINEL in str(raw_before)
        receipt = client.get(
            f"/api/workbench/review-runs/{ids['run_id']}/provenance",
            params={"expected_project_id": ids["project_id"]},
        )
        assert receipt.status_code == 200
        report = client.get(
            "/api/workbench/offline-report",
            params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
        )
        assert report.status_code == 200
        data = _snapshot(report.text)
        embedded_history = json.loads(data["exports"]["review_history"])
        assert embedded_history == data["review_history"]
        for text in [receipt.text, report.text, json.dumps(embedded_history)]:
            assert (SENTINEL in text) == (decision == "allow")
        if decision != "allow":
            assert "excerpt_delivery" in receipt.text
            assert "shared_values_sha256" in receipt.text
            projected = next(
                p
                for p in receipt.json()["provenance"]["profiles"]
                if p["part_number"] == profile.part_number
            )
            assert projected["sha256"] == projected["share_projection"]["original_local_sha256"]
        assert db_rows(journal) == raw_before
        assert context.validation_targets["U8"].model_dump(mode="json") == local_before


def test_current_withholding_overrides_old_allow_but_does_not_rewrite_old_run(tmp_path):
    context = _context()
    allow = configure(context, "allow")
    before_fingerprint = _profile(allow)
    journal = tmp_path / "review.sqlite"
    with TestClient(
        create_workbench_app(context, WorkbenchChatService(context, mode="fake"), review_db=journal)
    ) as client:
        ids = client.get("/api/workbench/state").json()["review_decisions"]
        raw_before = db_rows(journal)
        url = f"/api/workbench/review-runs/{ids['run_id']}/provenance"
        assert SENTINEL in client.get(url).text
        withheld = configure(context, "withhold")
        assert _profile(withheld) == before_fingerprint
        assert SENTINEL not in client.get(url).text
        report = client.get(
            "/api/workbench/offline-report",
            params={"expected_project_id": ids["project_id"], "expected_run_id": ids["run_id"]},
        )
        assert report.status_code == 200 and SENTINEL not in report.text
        assert db_rows(journal) == raw_before
        assert SENTINEL in json.dumps(build_run_provenance(context).model_dump(mode="json"))


@pytest.mark.parametrize("decision", [None, "withhold", "allow"])
def test_shared_chat_withholds_whole_binding_and_rebuilds_prose(decision):
    context = _context()
    try:
        configure(context, decision)
        model = CatalogModel([("locate_component_evidence", {"refdes": "U8", "topic": "abs_max"})])
        response = WorkbenchChatService(
            context, mode="fake", client=SimpleNamespace(messages=model)
        ).ask(ChatRequest(question="查看 U8 的 abs_max 证据链", selected_refdes="U8"))
        assert SENTINEL in response.model_dump_json()
        original = response.model_dump_json()
        shared = share_chat_response(response, context)
        assert (SENTINEL in shared.model_dump_json()) == (decision == "allow")
        assert response.model_dump_json() == original
        assert all(f.id == f.digest() for f in shared.explanation_review.verified_facts)
        if decision != "allow":
            assert "分享报告省略" in shared.answer
    finally:
        context.session.close()


def test_new_allow_does_not_backfill_permission_into_an_undeclared_old_run(tmp_path):
    context = _context()
    configure(context, None)
    journal = tmp_path / "review.sqlite"
    with TestClient(
        create_workbench_app(context, WorkbenchChatService(context, mode="fake"), review_db=journal)
    ) as client:
        ids = client.get("/api/workbench/state").json()["review_decisions"]
        old = db_rows(journal)
        configure(context, "allow")
        response = client.get(f"/api/workbench/review-runs/{ids['run_id']}/provenance")
        assert response.status_code == 200 and SENTINEL not in response.text
        assert "undeclared" in response.text
        assert db_rows(journal) == old


def test_retrieved_text_without_manual_permission_is_not_shared():
    from tests.agent.test_runner import StubCollection

    context = _context()
    try:
        collection = StubCollection(
            {
                "ids": [["synthetic"]],
                "documents": [[SENTINEL]],
                "metadatas": [[{"page": 1, "source_pdf": "synthetic.pdf", "part_ref": "U8"}]],
                "distances": [[0.1]],
            }
        )
        model = CatalogModel([("search_datasheet", {"query": "rating"})])
        response = WorkbenchChatService(
            context, mode="fake", client=SimpleNamespace(messages=model), collection=collection
        ).ask(ChatRequest(question="rating", selected_refdes="U8"))
        assert SENTINEL in response.model_dump_json()
        shared = share_chat_response(response, context)
        assert SENTINEL not in shared.model_dump_json()
        assert "检索片段" in shared.answer
        assert shared.trace[0].evidence == response.trace[0].evidence
    finally:
        context.session.close()


@pytest.mark.parametrize("change", ["remove_declaration", "remove_profile"])
def test_old_allow_cannot_resurrect_after_current_permission_is_removed(tmp_path, change):
    context = _context()
    configure(context, "allow")
    with TestClient(
        create_workbench_app(
            context,
            WorkbenchChatService(context, mode="fake"),
            review_db=tmp_path / "review.sqlite",
        )
    ) as client:
        ids = client.get("/api/workbench/state").json()["review_decisions"]
        url = f"/api/workbench/review-runs/{ids['run_id']}/provenance"
        assert SENTINEL in client.get(url).text
        if change == "remove_declaration":
            configure(context, None)
        else:
            context.validation_targets.pop("U8")
        response = client.get(url)
        assert response.status_code == 200 and SENTINEL not in response.text
        assert "not_currently_allowed" in response.text
