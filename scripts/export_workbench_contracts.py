"""Export one deterministic JSON Schema bundle for the SPA API contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import create_model

from hardwise.workbench.api_contracts import ImportResponse
from hardwise.workbench.excerpt_routes import ExcerptRequest, ExcerptResponse
from hardwise.workbench.voltage_review_routes import (
    VoltageBatchRequest,
    VoltageReviewResponse,
    VoltageCandidatesRequest,
)
from hardwise.workbench.review_history import ReviewHistoryPage
from hardwise.workbench.offline_history import OfflineReviewHistory
from hardwise.workbench.run_provenance import RunProvenanceResponse
from hardwise.workbench.managed_project_contracts import (
    SavedProjectView,
    SavedProjectCatalog,
    ProjectRestoreReceipt,
)
from hardwise.workbench.chat_contracts import ChatRequest, ChatResponse
from hardwise.workbench.ai_disclosure import AIDisclosure
from hardwise.workbench.view_model import ComponentDetail, WorkbenchState


def _require_serialized_response_fields(schema: dict[str, object]) -> None:
    """Match FastAPI's default response serialization, which includes model defaults."""

    definitions = schema.get("$defs")
    if not isinstance(definitions, dict):
        return
    for name, definition in definitions.items():
        if name == "ChatRequest" or not isinstance(definition, dict):
            continue
        properties = definition.get("properties")
        if isinstance(properties, dict):
            definition["required"] = sorted(properties)
            if name in {"FieldSource", "ManualSource"}:
                definition["required"].remove("sharing")
            # These fields are omitted on old/v1-input runs or unedited ledgers
            # via exclude_if. Do not promise keys the API does not emit.
            if name in {
                "RunProvenance",
                "VoltageReviewDocument",
                "ChatResponse",
                "ProfileModelSnapshot",
            }:
                definition["required"] = [
                    key
                    for key in definition["required"]
                    if key
                    not in {"voltage_review", "edits", "explanation_review", "share_projection"}
                ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    bundle = create_model(
        "WorkbenchContracts",
        workbench_state=(WorkbenchState, ...),
        component_detail=(ComponentDetail, ...),
        import_response=(ImportResponse, ...),
        review_history=(ReviewHistoryPage, ...),
        offline_review_history=(OfflineReviewHistory, ...),
        run_provenance=(RunProvenanceResponse, ...),
        saved_project=(SavedProjectView, ...),
        saved_project_catalog=(SavedProjectCatalog, ...),
        project_restore=(ProjectRestoreReceipt, ...),
        chat_request=(ChatRequest, ...),
        excerpt_request=(ExcerptRequest, ...),
        excerpts=(ExcerptResponse, ...),
        voltage_batch_request=(VoltageBatchRequest, ...),
        voltage_candidates_request=(VoltageCandidatesRequest, ...),
        voltage_review=(VoltageReviewResponse, ...),
        chat_response=(ChatResponse, ...),
        ai_disclosure=(AIDisclosure, ...),
    )
    schema = bundle.model_json_schema(mode="serialization")
    _require_serialized_response_fields(schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
