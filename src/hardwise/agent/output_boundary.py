"""Separate unverified model explanations from deterministic assessments."""

from typing import Literal

ResponseKind = Literal["model_explanation", "insufficient_evidence", "offline_notice"]
INSUFFICIENT_EVIDENCE = (
    "本回合没有获得可用的工具结果，未展示模型的未核验回复。"
    "请查看确定性检查或补充资料；本回合未产生新的检查结论。"
)


def constrain_model_answer(text: str, *, has_tool_result: bool) -> tuple[str, ResponseKind]:
    """No regex can establish prose truth; no-tool prose is withheld entirely."""
    if not has_tool_result:
        return INSUFFICIENT_EVIDENCE, "insufficient_evidence"
    return text, "model_explanation"


def usable_tool_payload(payload: dict) -> bool:
    """A structured miss is a lookup result; unavailable/error is not evidence.

    This receives only server-dispatched tool output, never model declarations.
    An available result permits an explanation, not a PASS/FAIL or sign-off.
    """
    return bool(payload) and "error" not in payload and payload.get("status") != "not_configured"
