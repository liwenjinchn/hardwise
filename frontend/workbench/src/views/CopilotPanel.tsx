import { useState, type KeyboardEvent } from "react";
import { Bot, MessageSquare, ShieldCheck } from "lucide-react";
import { askCopilot } from "../api";
import { TrustBadge } from "../components/ui";
import { sourceLabel } from "../lib/format";
import type { ChatMessage, ChatResponse, WorkbenchState } from "../types";

type MessageBlock =
  | { kind: "heading"; text: string }
  | { kind: "ordered"; items: string[] }
  | { kind: "paragraph"; text: string }
  | { headers: string[]; kind: "table"; rows: string[][] }
  | { kind: "unordered"; items: string[] };

type ThreadMessage = ChatMessage & {
  response?: ChatResponse;
};

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
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const send = async (text: string) => {
    const clean = text.trim();
    if (!clean || busy) return;
    setBusy(true);
    setError("");
    const nextHistory: ThreadMessage[] = [...messages, { role: "user", content: clean }];
    setMessages(nextHistory);
    setQuestion("");
    try {
      const response = await askCopilot(clean, selectedRefdes, chatHistory(messages));
      setLastResponse(response);
      setMessages([...nextHistory, { role: "assistant", content: response.answer, response }]);
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
                  <RichMessageText text="我只基于当前 netlist、规则结果和 evidence token 回答。无法锚定的 refdes 会被 Refdes Guard 包裹。" />
                </div>
              </div>
            )}
            {messages.map((message, index) => (
              <div
                className={`msg ${message.role === "assistant" ? "ai" : "user"}`}
                key={`${message.role}-${index}`}
              >
                <div className="mavatar">
                  {message.role === "assistant" ? <Bot size={17} /> : "LW"}
                </div>
                <div className="mbody">
                  <div className="mname">
                    {message.role === "assistant" ? "Hardwise Copilot" : "You"}
                  </div>
                  <RichMessageText text={message.content} />
                  {message.response?.trace?.length ? (
                    <TraceDetails response={message.response} />
                  ) : null}
                </div>
              </div>
            ))}
            {error && <p className="chat-error">{error}</p>}
          </div>
        </div>
        <form className="chat-form composer" onSubmit={(event) => { event.preventDefault(); void send(question); }}>
          <div className="composer-box">
            <MessageSquare size={15} />
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  void send(question);
                }
              }}
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
          {(lastResponse?.suggestions ?? [
            `这个 ${selectedRefdes ?? "器件"} 为什么是 ERROR/WARN?`,
            "板上有没有 U999?"
          ])
            .slice(0, 4)
            .map((item) => (
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

function chatHistory(messages: ThreadMessage[]): ChatMessage[] {
  return messages
    .slice(-6)
    .map(({ role, content }) => ({ role, content }));
}

export function TraceDetails({ response }: { response: ChatResponse }) {
  return (
    <details className="trace">
      <summary>工具调用 / 证据 · {response.trace.length}</summary>
      {response.trace.map((trace, index) => (
        <div className="trace-row toolcall" key={`${trace.tool}-${index}`}>
          <div className="tc-h">
            <Bot size={13} />
            <strong>{trace.tool}</strong>
            <span>{trace.trust_label || "可信层级未标注"}</span>
          </div>
          <p>{trace.summary}</p>
          <div className="evidence-tokens">
            {trace.evidence_classification.map((item) => (
              <span className="token" key={item.token}>
                {item.token} · {sourceLabel(item.source_class)}
              </span>
            ))}
          </div>
        </div>
      ))}
    </details>
  );
}

export function RichMessageText({ text }: { text: string }) {
  const blocks = messageBlocks(text);
  return (
    <div className="mtext">
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          return (
            <strong className="message-heading" key={`${block.kind}-${index}`}>
              {renderInline(block.text)}
            </strong>
          );
        }
        if (block.kind === "ordered") {
          return (
            <ol className="message-list" key={`${block.kind}-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{renderInline(item)}</li>
              ))}
            </ol>
          );
        }
        if (block.kind === "unordered") {
          return (
            <ul className="message-list" key={`${block.kind}-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{renderInline(item)}</li>
              ))}
            </ul>
          );
        }
        if (block.kind === "table") {
          return (
            <div className="message-table-wrap" key={`${block.kind}-${index}`}>
              <table className="message-table">
                <thead>
                  <tr>
                    {block.headers.map((header, headerIndex) => (
                      <th key={`${header}-${headerIndex}`}>{renderInline(header)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rowIndex) => (
                    <tr key={`row-${rowIndex}`}>
                      {block.headers.map((_header, cellIndex) => (
                        <td key={`cell-${rowIndex}-${cellIndex}`}>
                          {renderInline(row[cellIndex] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return <p key={`${block.kind}-${index}`}>{renderInline(block.text)}</p>;
      })}
    </div>
  );
}

function messageBlocks(text: string): MessageBlock[] {
  const blocks: MessageBlock[] = [];
  const paragraphs = text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);

  for (const paragraph of paragraphs.length ? paragraphs : [text.trim()].filter(Boolean)) {
    const lines = paragraph.split("\n").map((line) => line.trim()).filter(Boolean);
    const table = tableBlock(lines);
    if (table) {
      blocks.push(table);
      continue;
    }
    const ordered = lines
      .map((line) => line.match(/^\d+[.)]\s+(.+)$/)?.[1]?.trim())
      .filter((line): line is string => Boolean(line));
    if (ordered.length === lines.length && ordered.length > 0) {
      blocks.push({ kind: "ordered", items: ordered });
      continue;
    }
    const unordered = lines
      .map((line) => line.match(/^[-*]\s+(.+)$/)?.[1]?.trim())
      .filter((line): line is string => Boolean(line));
    if (unordered.length === lines.length && unordered.length > 0) {
      blocks.push({ kind: "unordered", items: unordered });
      continue;
    }
    const heading = paragraph.match(/^#{1,3}\s+(.+)$/)?.[1]?.trim();
    if (heading) {
      blocks.push({ kind: "heading", text: heading });
      continue;
    }
    blocks.push({ kind: "paragraph", text: lines.join(" ") });
  }
  return blocks;
}

function tableBlock(lines: string[]): MessageBlock | null {
  if (lines.length < 2 || !lines[0].includes("|") || !/^\|?\s*:?-{3,}:?\s*\|/.test(lines[1])) {
    return null;
  }
  const headers = tableCells(lines[0]);
  if (headers.length === 0) return null;
  const rows = lines
    .slice(2)
    .filter((line) => line.includes("|"))
    .map(tableCells)
    .filter((row) => row.length > 0);
  return { kind: "table", headers, rows };
}

function tableCells(line: string): string[] {
  return line
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function renderInline(text: string) {
  const parts = text.split(/(`[^`]+`|\b(?:datasheet|doc):[^\s,;，。)）]+|EV-[A-Z0-9_-]+)/g);
  return parts.filter(Boolean).map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>;
    }
    if (/^(?:datasheet|doc):|^EV-[A-Z0-9_-]+/.test(part)) {
      return <code className="evidence-inline" key={`${part}-${index}`}>{part}</code>;
    }
    return renderEmphasis(part, index);
  });
}

function renderEmphasis(text: string, index: number) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  if (parts.length === 1 && text.startsWith("**") && text.endsWith("**")) {
    return <strong key={`strong-${index}`}>{text.slice(2, -2)}</strong>;
  }
  if (parts.length === 1) return text;
  return parts.map((part, partIndex) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`strong-${index}-${partIndex}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
