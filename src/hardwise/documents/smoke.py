"""Project-level smoke report for document-candidate review flow."""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

from hardwise.documents.candidates import (
    DocumentCandidateLookup,
    build_document_candidate_report,
    render_document_candidate_csv,
)
from hardwise.report.project_validation_markdown import write_json
from hardwise.workbench.context import build_workbench_context, close_workbench_context
from hardwise.workbench.view_model import build_workbench_state


class DocumentCandidateSmokeSummary(BaseModel):
    """One smoke run over S2 candidate generation plus S3 workbench queueing."""

    project_name: str
    netlist: str
    bom: str
    profiles: str
    baseline_document_index: str | None = None
    candidate_csv: str
    families: list[str] = Field(default_factory=list)
    datasheets_com_enabled: bool = False
    components: int
    bom_matched: int
    validated: int
    manual: int
    pass_count: int
    warn_count: int
    error_count: int
    candidate_rows: int
    candidate_document_status: dict[str, int]
    candidate_review_status: dict[str, int]
    candidate_approved: int
    candidate_needs_review: int
    candidate_rows_with_url: int
    workbench_document_candidate_tasks: int
    workbench_document_status: dict[str, int]
    pass_warn_error_unchanged: bool

    @property
    def headline(self) -> str:
        """Return a compact product-facing smoke headline."""

        return (
            f"approved={self.candidate_approved}, "
            f"needs_review={self.candidate_needs_review}, "
            f"no_result={self.candidate_document_status.get('no_result', 0)}, "
            f"queue={self.workbench_document_candidate_tasks}, "
            f"PASS/WARN/ERROR={self.pass_count}/{self.warn_count}/{self.error_count}"
        )


def run_document_candidate_smoke(
    *,
    netlist_path: Path,
    bom_path: Path | None,
    profiles: Path,
    baseline_document_index: Path | None = None,
    candidate_csv: Path | None = None,
    families: list[str] | None = None,
    datasheets_com_lookup: DocumentCandidateLookup | None = None,
    datasheets_com_enabled: bool = False,
) -> DocumentCandidateSmokeSummary:
    """Run S2 candidate generation and S3 workbench projection as one smoke."""

    base_context = build_workbench_context(
        netlist_path=netlist_path,
        bom_path=bom_path,
        profiles=profiles,
        document_index=baseline_document_index,
    )
    try:
        totals = base_context.index.totals
        if candidate_csv is None:
            candidate_csv = Path("reports") / (
                f"{base_context.project_name}-document-candidate-smoke.csv"
            )
        with tempfile.TemporaryDirectory(prefix="hardwise-document-smoke-") as tmp:
            tmp_root = Path(tmp)
            index_json = tmp_root / "project-index.json"
            write_json(base_context.index, index_json)
            report = build_document_candidate_report(
                index_json,
                families=families,
                datasheets_com_lookup=datasheets_com_lookup,
            )
            candidate_csv.parent.mkdir(parents=True, exist_ok=True)
            candidate_csv.write_text(render_document_candidate_csv(report), encoding="utf-8")

            if any(row.url for row in report.candidates):
                queue_context = build_workbench_context(
                    netlist_path=netlist_path,
                    bom_path=bom_path,
                    profiles=profiles,
                    document_index=candidate_csv,
                )
                try:
                    state = build_workbench_state(
                        queue_context,
                        datasheet_search_enabled=False,
                        datasheet_candidate_lookup_enabled=datasheets_com_enabled,
                    )
                finally:
                    close_workbench_context(queue_context)
            else:
                state = build_workbench_state(
                    base_context,
                    datasheet_search_enabled=False,
                    datasheet_candidate_lookup_enabled=datasheets_com_enabled,
                )
    finally:
        close_workbench_context(base_context)

    candidate_document_status = Counter(row.document_status for row in report.candidates)
    candidate_review_status = Counter(row.review_status for row in report.candidates)
    workbench_document_status = Counter(item.document_status for item in state.queue)
    doc_tasks = [task for task in state.review_tasks if task.kind == "document_candidate"]
    return DocumentCandidateSmokeSummary(
        project_name=base_context.project_name,
        netlist=str(base_context.netlist_source),
        bom=str(base_context.bom.source_file),
        profiles=str(profiles),
        baseline_document_index=str(baseline_document_index) if baseline_document_index else None,
        candidate_csv=str(candidate_csv),
        families=sorted({family.strip().lower() for family in families or [] if family.strip()}),
        datasheets_com_enabled=datasheets_com_enabled,
        components=base_context.index.components_in_design,
        bom_matched=base_context.index.bom_matched,
        validated=len(base_context.index.validated_rows),
        manual=len(base_context.index.manual_rows),
        pass_count=totals["PASS"],
        warn_count=totals["WARN"],
        error_count=totals["ERROR"],
        candidate_rows=len(report.candidates),
        candidate_document_status=dict(candidate_document_status),
        candidate_review_status=dict(candidate_review_status),
        candidate_approved=candidate_review_status.get("approved", 0),
        candidate_needs_review=sum(
            count for status, count in candidate_review_status.items() if status != "approved"
        ),
        candidate_rows_with_url=sum(1 for row in report.candidates if row.url),
        workbench_document_candidate_tasks=len(doc_tasks),
        workbench_document_status=dict(workbench_document_status),
        pass_warn_error_unchanged=(
            state.summary.pass_count == totals["PASS"]
            and state.summary.warn_count == totals["WARN"]
            and state.summary.error_count == totals["ERROR"]
        ),
    )


def write_document_candidate_smoke_summary(
    summary: DocumentCandidateSmokeSummary,
    output: Path,
) -> None:
    """Write smoke summary JSON."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
