"""Compatibility facade for workbench chat contracts and runtime services."""

from hardwise.workbench.chat_contracts import (
    ChatMessage,
    ChatMode,
    ChatRequest,
    ChatResponse,
    EvidenceTrace,
)
from hardwise.workbench.chat_fake_model import C5_L2_SNAPSHOT_QUESTION, FakeWorkbenchAnthropic
from hardwise.workbench.chat_service import (
    WorkbenchChatService,
    build_snapshot_responses,
    default_refdes,
)

__all__ = [
    "C5_L2_SNAPSHOT_QUESTION",
    "ChatMessage",
    "ChatMode",
    "ChatRequest",
    "ChatResponse",
    "EvidenceTrace",
    "FakeWorkbenchAnthropic",
    "WorkbenchChatService",
    "build_snapshot_responses",
    "default_refdes",
]
