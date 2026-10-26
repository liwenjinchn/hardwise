"""Select real catalog bindings for the deterministic offline/fake model."""

import json

from hardwise.agent.claim_turn import CATALOG_PREFIX


def fake_claim_answer(blocks):
    directory = next(
        (
            b.get("text", "")
            for b in blocks
            if b.get("type") == "text" and b.get("text", "").startswith(CATALOG_PREFIX)
        ),
        None,
    )
    if directory is None:
        return None
    data = json.loads(directory[len(CATALOG_PREFIX) :])
    facts = data["facts"]
    preferred = [f for f in facts if f["kind"] == "approved_parameter"]
    if not preferred:
        preferred = [
            f for f in facts if f["kind"] == "assessment" or f["property_key"].endswith(".reason")
        ]
    if not preferred:
        preferred = [f for f in facts if f["property_key"].startswith("context.")]
    # The fake model only chooses fields returned by the real dispatch channel.
    # It does not synthesize values or receive a validator bypass.
    selected = preferred[:8] if preferred else facts[:16]
    claims = [
        {
            **{k: v for k, v in f.items() if k not in {"id", "scope_id", "call_id"}},
            "fact_id": f["id"],
        }
        for f in selected
    ]
    return json.dumps(
        dict(
            schema_version="hardwise.model_explanation.v1",
            scope_id=data["scope_id"],
            claims=claims,
            requests=[],
        ),
        ensure_ascii=False,
    )
