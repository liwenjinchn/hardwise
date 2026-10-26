"""Separate unverified model explanations from deterministic assessments."""

from typing import Literal

ResponseKind = Literal[
    "model_explanation", "structured_explanation", "insufficient_evidence", "offline_notice"
]
INSUFFICIENT_EVIDENCE = (
    "本回合未获得可展示的已核绑定，未展示模型的未核验回复。"
    "请查看确定性检查或补充资料；本回合未产生新的检查结论。"
)


def constrain_model_answer(text: str, *, has_tool_result: bool) -> tuple[str, ResponseKind]:
    """Legacy compatibility: a boolean lookup result never authorizes raw prose."""
    return INSUFFICIENT_EVIDENCE, "insufficient_evidence"


def usable_tool_payload(payload: dict) -> bool:
    """A structured miss is a lookup result; unavailable/error is not evidence.

    This receives only server-dispatched tool output, never model declarations.
    This is diagnostic trace metadata only; it never authorizes model prose.
    """
    return bool(payload) and "error" not in payload and payload.get("status") != "not_configured"
