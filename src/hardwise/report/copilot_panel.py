"""Render the Copilot-style workbench AI panel."""

from __future__ import annotations

import json
from html import escape

from hardwise.report.copilot_panel_assets import COPILOT_SCRIPT, COPILOT_STYLE
from hardwise.workbench.chat import ChatResponse


def render_copilot_panel(
    *,
    mode: str,
    selected_refdes: str | None,
    suggestions: list[str],
    api_endpoint: str | None = None,
    snapshot_responses: dict[str, ChatResponse] | None = None,
    datasheet_search_enabled: bool = False,
) -> str:
    """Return floating AI button + side panel HTML."""

    config = {
        "mode": mode,
        "selectedRefdes": selected_refdes or "",
        "suggestions": suggestions,
        "apiEndpoint": api_endpoint or "",
        "datasheetSearchEnabled": datasheet_search_enabled,
        "snapshotResponses": {
            key: value.model_dump(mode="json")
            for key, value in (snapshot_responses or {}).items()
        },
    }
    config_json = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    label = (
        "本地实时检验引擎"
        if mode == "live"
        else "离线审计快照"
    )
    return f"""
  <style>{COPILOT_STYLE}</style>
  <div class="ai-root" data-ai-root>
    <button class="ai-fab" type="button" data-ai-open aria-label="打开 Hardwise 助手">AI</button>
    <aside class="ai-panel" data-ai-panel aria-label="Hardwise 助手">
      <header class="ai-panel-head">
        <div>
          <h2>Hardwise 助手</h2>
          <p>{escape(label)} · 位号防护 / 证据链</p>
        </div>
        <button class="ai-close" type="button" data-ai-close aria-label="关闭">x</button>
      </header>
      <div class="ai-suggest" data-ai-suggest></div>
      <div class="ai-guide" aria-label="可询问范围">
        <strong>可询问范围</strong>
        <span>选中器件、验证证据、资料缺口，或某个位号是否存在。</span>
      </div>
      <section class="ai-stream" data-ai-stream aria-live="polite"></section>
      <div class="ai-compose">
        <form data-ai-form>
          <input class="ai-input" data-ai-input type="text" placeholder="问 Hardwise 助手..." autocomplete="off">
          <button class="ai-send" type="submit" aria-label="发送">&gt;</button>
        </form>
        <div class="ai-mode">{escape(label)}</div>
      </div>
    </aside>
    <script type="application/json" id="hardwise-copilot-config">{config_json}</script>
    <script>{COPILOT_SCRIPT}</script>
  </div>
"""
