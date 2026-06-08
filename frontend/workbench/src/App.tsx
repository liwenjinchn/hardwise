import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  CircleHelp,
  ExternalLink,
  FileSearch,
  Filter,
  Link2,
  Loader2,
  MessageSquare,
  Search,
  ShieldCheck
} from "lucide-react";
import { askCopilot, fetchComponentDetail, fetchWorkbenchState } from "./api";
import type {
  ChatMessage,
  ChatResponse,
  CheckView,
  ComponentDetail,
  EvidenceChainItem,
  EvidenceView,
  ReviewQueueItem,
  RiskHintsView,
  StatusGroup,
  TrustTier,
  WorkbenchState
} from "./types";

const FILTERS: Array<{ id: "all" | StatusGroup; label: string; hint: string }> = [
  { id: "all", label: "全部", hint: "所有器件" },
  { id: "error", label: "必须处理", hint: "ERROR" },
  { id: "warn", label: "需要复核", hint: "WARN" },
  { id: "manual", label: "人工线索", hint: "缺档案/外部提示" },
  { id: "pass", label: "已通过", hint: "PASS" }
];

const TRUST_LABEL: Record<TrustTier, string> = {
  l1: "L1 确定性",
  l2: "L2 有出处",
  l3: "L3 人工确认"
};

function App() {
  const [state, setState] = useState<WorkbenchState | null>(null);
  const [selectedRefdes, setSelectedRefdes] = useState<string | null>(null);
  const [detail, setDetail] = useState<ComponentDetail | null>(null);
  const [filter, setFilter] = useState<"all" | StatusGroup>("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWorkbenchState()
      .then((payload) => {
        setState(payload);
        setSelectedRefdes(payload.selected_refdes ?? payload.queue[0]?.refdes ?? null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRefdes) return;
    setDetailLoading(true);
    fetchComponentDetail(selectedRefdes)
      .then(setDetail)
      .catch((err: Error) => setError(err.message))
      .finally(() => setDetailLoading(false));
  }, [selectedRefdes]);

  const filteredQueue = useMemo(() => {
    if (!state) return [];
    const needle = query.trim().toLowerCase();
    return state.queue.filter((item) => {
      const filterMatch = filter === "all" || item.status_group === filter;
      const queryMatch =
        !needle ||
        item.refdes.toLowerCase().includes(needle) ||
        item.title.toLowerCase().includes(needle) ||
        item.subtitle.toLowerCase().includes(needle);
      return filterMatch && queryMatch;
    });
  }, [filter, query, state]);

  if (loading) {
    return (
      <main className="center-screen">
        <Loader2 className="spin" size={28} />
        <span>正在加载 Hardwise 工作台...</span>
      </main>
    );
  }

  if (error || !state) {
    return (
      <main className="center-screen error-screen">
        <AlertTriangle size={32} />
        <strong>工作台加载失败</strong>
        <p>{error || "未收到后端状态。"}</p>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <Header state={state} />
      <section className="workspace" aria-label="Hardwise 三栏审查工作台">
        <QueueColumn
          items={filteredQueue}
          allItems={state.queue}
          selectedRefdes={selectedRefdes}
          filter={filter}
          query={query}
          onFilter={setFilter}
          onQuery={setQuery}
          onPick={setSelectedRefdes}
        />
        <DetailColumn detail={detail} loading={detailLoading} />
        <EvidenceColumn detail={detail} riskHints={state.risk_hint_details} />
      </section>
      <CopilotPanel state={state} selectedRefdes={selectedRefdes} />
    </main>
  );
}

function Header({ state }: { state: WorkbenchState }) {
  const { summary } = state;
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">
          <ShieldCheck size={19} />
        </div>
        <div>
          <h1>Hardwise 原理图审查</h1>
          <p>{state.project.name}</p>
        </div>
      </div>
      <div className="top-meta">
        <Metric label="器件" value={summary.components} />
        <Metric label="已验证" value={summary.validated} />
        <Metric label="待人工" value={summary.manual} />
        <Metric label="PASS" value={summary.pass_count} tone="pass" />
        <Metric label="WARN" value={summary.warn_count} tone="warn" />
        <Metric label="ERROR" value={summary.error_count} tone="error" />
      </div>
      <div className="source-line">
        <span>{state.project.netlist_type}</span>
        <span>{state.project.netlist_source}</span>
      </div>
    </header>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone?: StatusGroup }) {
  return (
    <div className={`metric ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function QueueColumn(props: {
  items: ReviewQueueItem[];
  allItems: ReviewQueueItem[];
  selectedRefdes: string | null;
  filter: "all" | StatusGroup;
  query: string;
  onFilter: (value: "all" | StatusGroup) => void;
  onQuery: (value: string) => void;
  onPick: (refdes: string) => void;
}) {
  const counts = useMemo(() => {
    const base: Record<"all" | StatusGroup, number> = {
      all: props.allItems.length,
      error: 0,
      warn: 0,
      manual: 0,
      pass: 0
    };
    props.allItems.forEach((item) => {
      base[item.status_group] += 1;
    });
    return base;
  }, [props.allItems]);

  return (
    <aside className="panel queue-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">队列</span>
          <h2>审查队列</h2>
        </div>
        <span className="count">{props.items.length}/{props.allItems.length}</span>
      </div>
      <div className="filter-grid">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            className={`filter-btn ${props.filter === item.id ? "active" : ""}`}
            onClick={() => props.onFilter(item.id)}
            type="button"
          >
            <Filter size={13} />
            <span>{item.label}</span>
            <small>{item.hint}</small>
            <b>{counts[item.id]}</b>
          </button>
        ))}
      </div>
      <label className="search-box">
        <Search size={15} />
        <input
          value={props.query}
          onChange={(event) => props.onQuery(event.target.value)}
          placeholder="搜索 refdes、器件、结论..."
        />
      </label>
      <div className="queue-list">
        {props.items.map((item) => (
          <button
            type="button"
            key={item.refdes}
            className={`queue-row ${item.status_group} ${
              props.selectedRefdes === item.refdes ? "selected" : ""
            }`}
            onClick={() => props.onPick(item.refdes)}
          >
            <span className="refdes">{item.refdes}</span>
            <span className="queue-copy">
              <strong>{item.title}</strong>
              <small>{item.subtitle}</small>
              <span className="row-badges">
                <StatusBadge group={item.status_group} label={item.status_label} />
                <TrustBadge tier={item.trust_tier} />
                {item.risk_hint_count > 0 && <span className="hint-badge">外部提示 {item.risk_hint_count}</span>}
              </span>
            </span>
            <span className="queue-counts">{item.evidence_count} 证据</span>
          </button>
        ))}
      </div>
    </aside>
  );
}

function DetailColumn({ detail, loading }: { detail: ComponentDetail | null; loading: boolean }) {
  if (loading) {
    return (
      <section className="panel detail-panel empty-panel">
        <Loader2 className="spin" />
        <p>正在读取器件详情...</p>
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="panel detail-panel empty-panel">
        <FileSearch size={32} />
        <p>请选择一个 refdes 查看详情。</p>
      </section>
    );
  }

  return (
    <section className="panel detail-panel">
      <div className="component-title">
        <div>
          <span className="eyebrow">器件详情</span>
          <h2>{detail.refdes}</h2>
          <p>{detail.value}</p>
        </div>
        <StatusBadge group={detail.status_group} label={detail.status_label} />
      </div>
      <div className="identity-grid">
        <InfoCell label="MPN" value={detail.part_number || "-"} />
        <InfoCell label="厂商" value={detail.manufacturer || "-"} />
        <InfoCell label="封装" value={detail.package || "-"} />
        <InfoCell label="器件档案" value={detail.profile_part_number || "待补"} />
      </div>
      {detail.match_reason && <p className="scope-note">{detail.match_reason}</p>}
      <section className="detail-section">
        <div className="section-title">
          <h3>引脚 / 网络表</h3>
          <span>{detail.pins.length} pins</span>
        </div>
        <div className="pin-table">
          <div className="pin-head">Pin</div>
          <div className="pin-head">Name</div>
          <div className="pin-head">Net</div>
          <div className="pin-head">状态</div>
          {detail.pins.slice(0, 24).map((pin) => (
            <div className="pin-row" key={`${pin.number}-${pin.name}`}>
              <span className="mono">{pin.number}</span>
              <span>{pin.name}</span>
              <span className="mono net-name">{pin.net || "-"}</span>
              <span>{pin.status ? <StatusBadge group={statusGroup(pin.status)} label={pin.status} /> : "—"}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="detail-section">
        <div className="section-title">
          <h3>确定性检查</h3>
          <span>{detail.checks.length} checks</span>
        </div>
        <div className="check-list">
          {detail.checks.length === 0 && <p className="muted">该器件没有组件级检查，或仍待人工补档案。</p>}
          {detail.checks.map((check) => (
            <CheckCard check={check} key={`${check.subject}-${check.summary}`} />
          ))}
        </div>
      </section>
    </section>
  );
}

function EvidenceColumn({
  detail,
  riskHints
}: {
  detail: ComponentDetail | null;
  riskHints: RiskHintsView;
}) {
  return (
    <aside className="panel evidence-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">证据来源</span>
          <h2>证据链</h2>
        </div>
        <Link2 size={17} />
      </div>
      {!detail ? (
        <div className="empty-panel compact">
          <CircleHelp size={28} />
          <p>选择器件后显示证据来源、可信层级和外部提示。</p>
        </div>
      ) : (
        <div className="evidence-list">
          {detail.evidence_chain.map((item, index) => (
            <EvidenceCard item={item} key={`${item.kind}-${index}`} />
          ))}
          {detail.evidence_chain.length === 0 && (
            <p className="muted">没有可展示证据；如果这是硬判断，应回到后端补 evidence token。</p>
          )}
        </div>
      )}
      <RiskHintsPanel riskHints={riskHints} selectedRefdes={detail?.refdes ?? null} />
    </aside>
  );
}

function CopilotPanel({ state, selectedRefdes }: { state: WorkbenchState; selectedRefdes: string | null }) {
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
    <section className="copilot">
      <div className="copilot-head">
        <Bot size={18} />
        <strong>Copilot</strong>
        <span>{state.capabilities.datasheet_search_enabled ? "向量检索已启用" : "未启用向量检索"}</span>
      </div>
      <div className="suggestions">
        {(lastResponse?.suggestions ?? [`这个 ${selectedRefdes ?? "器件"} 为什么是 ERROR/WARN?`, "板上有没有 U999?"]).slice(0, 3).map((item) => (
          <button type="button" key={item} onClick={() => send(item)}>{item}</button>
        ))}
      </div>
      <div className="chat-stream">
        {messages.slice(-4).map((message, index) => (
          <p className={`chat-msg ${message.role}`} key={`${message.role}-${index}`}>{message.content}</p>
        ))}
        {lastResponse?.trace?.length ? (
          <details className="trace" open>
            <summary>tool trace · {lastResponse.trace.length}</summary>
            {lastResponse.trace.map((trace, index) => (
              <div className="trace-row" key={`${trace.tool}-${index}`}>
                <strong>{trace.tool}</strong>
                <span>{trace.trust_label || "可信层级未标注"}</span>
                <p>{trace.summary}</p>
                <div className="evidence-tokens">
                  {trace.evidence_classification.map((item) => (
                    <span className="token" key={item.token}>{item.token} · {item.source_class}</span>
                  ))}
                </div>
              </div>
            ))}
          </details>
        ) : null}
        {error && <p className="chat-error">{error}</p>}
      </div>
      <form className="chat-form" onSubmit={(event) => { event.preventDefault(); void send(question); }}>
        <MessageSquare size={15} />
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={`询问 ${selectedRefdes ?? "当前器件"}，例如：板上有没有 U999?`}
        />
        <button type="submit" disabled={busy}>{busy ? "处理中" : "发送"}</button>
      </form>
    </section>
  );
}

function RiskHintsPanel({ riskHints, selectedRefdes }: { riskHints: RiskHintsView; selectedRefdes: string | null }) {
  const visible = selectedRefdes ? riskHints.accepted.filter((item) => item.refdes === selectedRefdes) : [];
  return (
    <section className="risk-hints">
      <div className="section-title">
        <h3>外部提示 · 只读</h3>
        <span>accepted {riskHints.accepted_external_count} / rejected {riskHints.rejected_external_count}</span>
      </div>
      <div className="risk-summary">
        <span>状态：{riskHints.external_status === "loaded" ? "已加载" : "未配置"}</span>
        <span>总数：{riskHints.count}</span>
        <span>已包裹位号：{riskHints.wrapped_refdes_count}</span>
      </div>
      <p className="scope-note">外部提示只作为人工线索，不改变 PASS/WARN/ERROR 结论。</p>
      {visible.map((hint) => (
        <div className="risk-card" key={`${hint.refdes}-${hint.title}`}>
          <strong>{hint.refdes} · {hint.title}</strong>
          <p>{hint.body}</p>
          {hint.source && <EvidenceToken evidence={hint.source} />}
        </div>
      ))}
      {visible.length === 0 && <p className="muted">当前器件没有已锚定的外部提示。</p>}
      {riskHints.rejected.length > 0 && (
        <div className="rejected-hints" aria-label="被拒绝外部提示汇总">
          <strong>已拒绝提示</strong>
          {riskHints.rejected.map((item) => (
            <span key={item.reason}>
              {item.reason} × {item.count}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function EvidenceCard({ item }: { item: EvidenceChainItem }) {
  return (
    <article className={`evidence-card ${item.status_group}`}>
      <div className="card-line">
        <StatusIcon group={item.status_group} />
        <strong>{item.title}</strong>
        <TrustBadge tier={item.trust_tier} />
      </div>
      <p>{item.body}</p>
      <div className="evidence-tokens">
        {item.evidence.map((evidence) => <EvidenceToken evidence={evidence} key={evidence.token} />)}
        {item.evidence.length === 0 && <span className="muted">无 evidence token</span>}
      </div>
    </article>
  );
}

function CheckCard({ check }: { check: CheckView }) {
  return (
    <article className={`check-card ${check.status_group}`}>
      <div className="card-line">
        <StatusIcon group={check.status_group} />
        <strong>{check.subject}</strong>
        <StatusBadge group={check.status_group} label={check.status_label} />
      </div>
      <p>{check.summary}</p>
      <div className="evidence-tokens">
        {check.evidence.slice(0, 4).map((item) => <EvidenceToken evidence={item} key={item.token} />)}
      </div>
    </article>
  );
}

function EvidenceToken({ evidence }: { evidence: EvidenceView }) {
  return (
    <span className={`token ${evidence.source_class}`}>
      <ExternalLink size={11} />
      {evidence.token}
      <small>{evidence.label} · {evidence.source_class}</small>
    </span>
  );
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-cell">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ group, label }: { group: StatusGroup; label: string }) {
  return <span className={`status-badge ${group}`}>{label}</span>;
}

function TrustBadge({ tier }: { tier: TrustTier }) {
  return <span className={`trust-badge ${tier}`}>{TRUST_LABEL[tier]}</span>;
}

function StatusIcon({ group }: { group: StatusGroup }) {
  if (group === "pass") return <CheckCircle2 size={15} />;
  if (group === "manual") return <CircleHelp size={15} />;
  return <AlertTriangle size={15} />;
}

function statusGroup(status: string): StatusGroup {
  if (status === "ERROR") return "error";
  if (status === "WARN") return "warn";
  if (status === "PASS") return "pass";
  return "manual";
}

export default App;
