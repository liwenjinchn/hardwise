import { useState } from "react";
import { Bot, MessageSquare, ShieldCheck } from "lucide-react";
import { askCopilot } from "../api";
import { TrustBadge } from "../components/ui";
import { sourceLabel } from "../lib/format";
import type { ChatMessage, ChatResponse, WorkbenchState } from "../types";

export function CopilotPanel({
  state,
  selectedRefdes,
  className = ""
}: {
  state: WorkbenchState;
  selectedRefdes: string | null;
  className?: string;
}) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const send = async (text: string) => {
    const clean = text.trim();
    if (!clean || busy) return;
    setBusy(true);
    setError("");
    const nextHistory: ChatMessage[] = [...messages, { role: "user", content: clean }];
    setMessages(nextHistory);
    setQuestion("");
    try {
      const response = await askCopilot(clean, selectedRefdes, messages);
      setLastResponse(response);
      setMessages([...nextHistory, { role: "assistant", content: response.answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Copilot 调用失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={`copilot ${className}`}>
      <div className="cop-main">
        <div className="cop-thread">
          <div className="cop-thread-inner">
            {messages.length === 0 && (
              <div className="msg ai">
                <div className="mavatar"><Bot size={17} /></div>
                <div className="mbody">
                  <div className="mname">Hardwise Copilot <TrustBadge tier="l1" /></div>
                  <div className="mtext">
                    <p>我只基于当前 netlist、规则结果和 evidence token 回答。无法锚定的 refdes 会被 Refdes Guard 包裹。</p>
                  </div>
                </div>
              </div>
            )}
            {messages.map((message, index) => (
              <div className={`msg ${message.role === "assistant" ? "ai" : "user"}`} key={`${message.role}-${index}`}>
                <div className="mavatar">{message.role === "assistant" ? <Bot size={17} /> : "LW"}</div>
                <div className="mbody">
                  <div className="mname">{message.role === "assistant" ? "Hardwise Copilot" : "You"}</div>
                  <div className="mtext"><p>{message.content}</p></div>
                </div>
              </div>
            ))}
            {lastResponse?.trace?.length ? (
              <details className="trace" open>
                <summary>tool trace · {lastResponse.trace.length}</summary>
                {lastResponse.trace.map((trace, index) => (
                  <div className="trace-row toolcall" key={`${trace.tool}-${index}`}>
                    <div className="tc-h">
                      <Bot size={13} />
                      <strong>{trace.tool}</strong>
                      <span>{trace.trust_label || "可信层级未标注"}</span>
                    </div>
                    <p>{trace.summary}</p>
                    <div className="evidence-tokens">
                      {trace.evidence_classification.map((item) => (
                        <span className="token" key={item.token}>{item.token} · {sourceLabel(item.source_class)}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </details>
            ) : null}
            {error && <p className="chat-error">{error}</p>}
          </div>
        </div>
        <form className="chat-form composer" onSubmit={(event) => { event.preventDefault(); void send(question); }}>
          <div className="composer-box">
            <MessageSquare size={15} />
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={`询问 ${selectedRefdes ?? "当前器件"}，例如：板上有没有 U999?`}
            />
            <button type="submit" disabled={busy}>{busy ? "处理中" : "发送"}</button>
          </div>
          <div className="cop-disclaimer">
            <ShieldCheck size={13} /> 回答必须被 netlist、规则或引用来源锚定；不可验证的问题会被标注。
          </div>
        </form>
      </div>
      <aside className="cop-side">
        <div className="eyebrow">Suggested probes</div>
        <div className="suggestions">
          {(lastResponse?.suggestions ?? [`这个 ${selectedRefdes ?? "器件"} 为什么是 ERROR/WARN?`, "板上有没有 U999?"]).slice(0, 4).map((item) => (
            <button type="button" key={item} onClick={() => void send(item)}>
              <span className="sg-k">probe</span>
              {item}
            </button>
          ))}
        </div>
        <div className="eyebrow trust-title">Trust tiers</div>
        <div className="trust-list">
          <p><TrustBadge tier="l1" /> 后端确定性规则和 netlist 事实。</p>
          <p><TrustBadge tier="l2" /> 有引用来源的 grounded evidence。</p>
          <p><TrustBadge tier="l3" /> 数据不足，交给 reviewer。</p>
        </div>
      </aside>
    </section>
  );
}
