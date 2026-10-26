"""Current-context disclosure receipts: a send precondition, not authentication."""

from dataclasses import dataclass
import hashlib
import hmac
import json
from secrets import token_bytes
from threading import RLock
from typing import Literal

from pydantic import BaseModel

from hardwise.workbench.ai_config import ProviderConfig, create_provider_client, safe_destination
from hardwise.workbench.chat_client import DeferredWorkbenchClient
from hardwise.workbench.decision_fingerprints import review_project_key

DISCLOSURE_VERSION = "hardwise.ai_disclosure.v2"
DATA_CATEGORIES = [
    "当前问题、选中位号及最近最多6条短对话历史；系统规则、工具定义和模型标识。",
    "工具可能返回器件/BOM属性、引脚/网络/邻域/拓扑、已确认输入和确定性检查结果。",
    "可能包含来源文件定位/路径、证据token、文档元数据和已配置检索返回的资料片段。",
    "逐字段绑定还可能包含适用条件、文档摘录/版本/哈希，以及批准人的声明、理由和批准时间。",
    "不是原文件自动上传；用户在问题或历史中输入的内容也会发送。",
]


class AIDisclosure(BaseModel):
    version: str = DISCLOSURE_VERSION
    mode: Literal["real", "fake", "snapshot", "unavailable"]
    available: bool
    context_id: str | None = None
    disclosure_id: str | None = None
    destination: str | None = None
    model: str | None = None
    data_categories: list[str]
    notice: str


class AIConfirmationRequired(RuntimeError):
    def __init__(self, stale=False):
        super().__init__(
            "AI 发送说明已变化，请重新确认后再发送。"
            if stale
            else "请先阅读并确认 AI 发送说明，再主动发送问题。"
        )
        self.status_code = 409 if stale else 428


@dataclass(frozen=True, repr=False)
class ProviderSnapshot:
    config: ProviderConfig
    client: object


class DisclosureSession:
    """Shared by shallow request copies; never constructs an SDK client on GET."""

    def __init__(self, *, client=None, injected_destination=None, factory=create_provider_client):
        self._secret = token_bytes(32)
        self._lock = RLock()
        self._snapshot = None
        self._revision = 0
        self._injected = client
        self._injected_destination = injected_destination
        self._factory = factory

    def snapshot(self):
        with self._lock:
            config = ProviderConfig.current()
            if self._snapshot is None or self._snapshot.config != config:
                self._revision += 1
                client = (
                    self._injected
                    if self._injected is not None
                    else DeferredWorkbenchClient(lambda frozen=config: self._factory(frozen))
                )
                self._snapshot = ProviderSnapshot(config, client)
            return self._snapshot

    def _digest(self, payload):
        return hmac.new(
            self._secret, json.dumps(payload, sort_keys=True).encode(), hashlib.sha256
        ).hexdigest()

    def describe(self, context, *, mode, tier="normal", collection=False, snapshot=None):
        context_id = self._digest(
            [
                review_project_key(context),
                context.input_manifest.readset_sha256
                if context.input_manifest
                else context.generated_at,
            ]
        )
        if mode != "real":
            return AIDisclosure(
                mode=mode,
                available=True,
                context_id=context_id,
                data_categories=[],
                notice="离线审计快照，不调用云模型。"
                if mode == "snapshot"
                else "合成 fake 演示，通过真实工具流程，不调用云模型。",
            )
        active = snapshot or self.snapshot()
        config = active.config
        raw_destination = (
            self._injected_destination if self._injected is not None else config.base_url
        )
        destination = safe_destination(raw_destination or "")
        available = bool(destination) and (
            self._injected is not None or bool(config.api_key and config.api_key != "replace_me")
        )
        model = config.router().select(tier)
        sensitive_model = False
        for secret in [config.api_key, config.auth_token]:
            if secret and secret in model:
                model = "模型标识含敏感配置，未展示"
                available = False
                sensitive_model = True
        notice = "配置的接收地址；若为代理，后续转发目的地不可知。修改 .env 后需重启服务。"
        if self._injected is not None:
            notice += " 当前为显式声明的注入客户端，不能据此证明真实供应商调用。"
        if not destination:
            notice = "AI 接收地址无效或注入客户端未声明目的地；本地评审仍可使用。"
        elif sensitive_model:
            notice = "模型标识含敏感配置，请修正配置后重启服务；本地评审仍可使用。"
        elif not available:
            notice = "未配置有效的 ANTHROPIC_API_KEY；本地评审仍可使用。"
        receipt = (
            self._digest(
                [
                    DISCLOSURE_VERSION,
                    context_id,
                    config.identity(),
                    self._revision,
                    raw_destination,
                    tier,
                    bool(collection),
                ]
            )
            if available
            else None
        )
        return AIDisclosure(
            mode="real",
            available=available,
            context_id=context_id,
            disclosure_id=receipt,
            destination=destination,
            model=model,
            data_categories=DATA_CATEGORIES,
            notice=notice,
        )
