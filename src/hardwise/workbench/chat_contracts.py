"""Pydantic contracts shared by the workbench chat entrypoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from hardwise.guards.evidence_class import EvidenceClassification
from hardwise.trust import TrustTier


ChatMode = Literal["fake", "real", "snapshot"]


class ChatMessage(BaseModel):
    """One browser-held chat message sent back for short context."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """User question sent from the Copilot panel."""

    question: str
    selected_refdes: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class EvidenceTrace(BaseModel):
    """UI-friendly trace row derived from one Runner tool call."""

    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    summary: str
    status: str | None = None
    evidence: list[str] = Field(default_factory=list)
    evidence_classification: list[EvidenceClassification] = Field(default_factory=list)
    wrapped: int = 0
    trust_tier: TrustTier | None = None
    trust_label: str | None = None


class ChatResponse(BaseModel):
    """Answer returned to the Copilot panel."""

    answer: str
    mode: ChatMode
    selected_refdes: str | None = None
    trace: list[EvidenceTrace] = Field(default_factory=list)
    wrapped_count: int = 0
    suggestions: list[str] = Field(default_factory=list)
    datasheet_search_enabled: bool = False
    unsupported_evidence_tokens: list[str] = Field(default_factory=list)
