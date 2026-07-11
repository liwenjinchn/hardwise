"""Export one deterministic JSON Schema bundle for the SPA API contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import create_model

from hardwise.workbench.api_contracts import ImportResponse
from hardwise.workbench.chat_contracts import ChatRequest, ChatResponse
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    bundle = create_model(
        "WorkbenchContracts",
        workbench_state=(WorkbenchState, ...),
        component_detail=(ComponentDetail, ...),
        import_response=(ImportResponse, ...),
        chat_request=(ChatRequest, ...),
        chat_response=(ChatResponse, ...),
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
