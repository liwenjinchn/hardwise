"""Snapshot effective provider settings without exposing credentials to the browser."""

from dataclasses import dataclass
import json
import os
from urllib.parse import urlsplit

from hardwise.agent.router import ModelRouter
from hardwise.workbench.chat_client import WorkbenchAIUnavailable


@dataclass(frozen=True, repr=False)
class ProviderConfig:
    api_key: str
    auth_token: str
    base_url: str
    model_slots: tuple[tuple[str, str], ...]
    headers: tuple[tuple[str, str], ...]

    @classmethod
    def current(cls):
        headers = {}
        for line in os.environ.get("ANTHROPIC_CUSTOM_HEADERS", "").splitlines():
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip()] = value.strip()
        return cls(
            os.environ.get("ANTHROPIC_API_KEY", "").strip(),
            os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip(),
            os.environ.get("ANTHROPIC_BASE_URL", "").strip() or "https://api.anthropic.com",
            tuple(
                (name, os.environ.get(name, ""))
                for name in ("HARDWISE_MODEL_FAST", "HARDWISE_MODEL_NORMAL", "HARDWISE_MODEL_DEEP")
            ),
            tuple(sorted(headers.items())),
        )

    def router(self):
        return ModelRouter(env=dict(self.model_slots))

    def identity(self):
        # Only used inside the opaque, server-keyed disclosure digest.
        return json.dumps(
            [self.api_key, self.auth_token, self.base_url, self.model_slots, self.headers]
        )


def safe_destination(raw: str) -> str | None:
    """Display only scheme/host/port; paths, URL credentials and queries stay private."""
    try:
        if any(ord(char) < 33 for char in raw):
            return None
        parsed = urlsplit(raw)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            return None
        port = parsed.port
        if port is not None and not 0 < port <= 65535:
            return None
        host = parsed.hostname
        host = f"[{host}]" if ":" in host else host
        return f"{parsed.scheme}://{host}" + (f":{port}" if port else "")
    except ValueError:
        return None


def create_provider_client(config: ProviderConfig):
    from anthropic import Anthropic

    if not config.api_key or config.api_key == "replace_me":
        raise WorkbenchAIUnavailable("未配置有效的 ANTHROPIC_API_KEY；本地评审仍可使用。")
    if safe_destination(config.base_url) is None:
        raise WorkbenchAIUnavailable("AI 接收地址配置无效；本地评审仍可使用。")
    try:
        # Explicit arguments prevent delayed SDK credential/base-url environment fallback.
        return Anthropic(
            api_key=config.api_key,
            auth_token=config.auth_token or "",
            base_url=config.base_url,
            default_headers=dict(config.headers),
        )
    except (ValueError, TypeError) as exc:
        raise WorkbenchAIUnavailable("AI 客户端配置无效；本地评审仍可使用。") from exc
