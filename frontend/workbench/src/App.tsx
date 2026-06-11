import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CircleHelp,
  Download,
  FileSearch,
  Layers3,
  Link2,
  Loader2,
  Search,
  ShieldCheck
} from "lucide-react";
import {
  fetchComponentDetail,
  fetchPrepPacketMarkdown,
  fetchWorkbenchState
} from "./api";
import type {
  ComponentDetail,
  ImportResponse,
  ReviewQueueItem,
  ReviewTask,
  RiskHintsView,
  StatusGroup,
  WorkbenchState
} from "./types";
import {
  CheckCard,
  EvidenceCard,
  EvidenceToken,
  InfoCell,
  StatusBadge,
  TrustBadge,
  VerdictBanner
} from "./components/ui";
import {
  TRUST_LABEL,
  attentionLabel,
  documentStatusLabel,
  formatSummary,
  pinStatusLabel,
  profileStatusLabel,
  queueSubtitle,
  statusGroup,
  taskKindLabel
} from "./lib/format";
import { CopilotPanel } from "./views/CopilotPanel";
import { ExportView } from "./views/ExportView";
import { FindingsView } from "./views/FindingsView";
import { Header } from "./views/Header";
import { ImportView } from "./views/ImportView";
import { ParseView } from "./views/ParseView";
import type { ViewId } from "./views/nav";

const FILTERS: Array<{ id: "all" | StatusGroup; label: string; hint: string }> = [
  { id: "all", label: "全部待看", hint: "所有被标记的器件" },
  { id: "error", label: "必须修", hint: "会阻塞签核的问题" },
  { id: "warn", label: "看证据", hint: "有引用的建议项" },
  { id: "manual", label: "人工判断", hint: "数据无法自动确认" },
  { id: "pass", label: "已通过", hint: "检查已满足" }
];

function App() {
  const [state, setState] = useState<WorkbenchState | null>(null);
  const [view, setView] = useState<ViewId>("review");
  const [selectedRefdes, setSelectedRefdes] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ComponentDetail | null>(null);
  const [filter, setFilter] = useState<"all" | StatusGroup>("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [parseResult, setParseResult] = useState<ImportResponse | null>(null);
  const [resolvedTaskIds, setResolvedTaskIds] = useState<Set<string>>(new Set());
  const detailRequestId = useRef(0);

  const applyState = (payload: WorkbenchState) => {
    const firstComponent = payload.queue[0] ?? null;
    const selected = payload.selected_refdes ?? firstComponent?.refdes ?? payload.review_tasks[0]?.refdes ?? null;
    const firstTask = payload.review_tasks.find((item) => item.refdes === selected) ?? payload.review_tasks[0] ?? null;
    setState(payload);
    setSelectedTaskId(firstTask?.id ?? null);
    setSelectedRefdes(selected);
    setResolvedTaskIds(new Set());
  };

  const loadState = async () => {
    const payload = await fetchWorkbenchState();
    applyState(payload);
  };

  useEffect(() => {
    loadState()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRefdes) {
      detailRequestId.current += 1;
      setDetail(null);
      return;
    }
    const requestId = detailRequestId.current + 1;
    detailRequestId.current = requestId;
    setDetailLoading(true);
    fetchComponentDetail(selectedRefdes)
      .then((nextDetail) => {
        if (detailRequestId.current === requestId) setDetail(nextDetail);
      })
      .catch((err: Error) => {
        if (detailRequestId.current === requestId) setError(err.message);
      })
      .finally(() => {
        if (detailRequestId.current === requestId) setDetailLoading(false);
      });
  }, [selectedRefdes]);

  const selectedComponentTasks = useMemo(() => {
    if (!state || !selectedRefdes) return [];
    return state.review_tasks.filter((item) => item.refdes === selectedRefdes);
  }, [selectedRefdes, state]);

  const selectedTask = useMemo(() => {
    if (!state) return null;
    return (
      selectedComponentTasks.find((item) => item.id === selectedTaskId) ??
      selectedComponentTasks[0] ??
      null
    );
  }, [selectedComponentTasks, selectedTaskId, state]);

  const filteredComponents = useMemo(() => {
    if (!state) return [];
    const needle = query.trim().toLowerCase();
    return state.queue.filter((item) => {
      const filterMatch = filter === "all" || item.status_group === filter;
      const queryMatch =
        !needle ||
        item.refdes.toLowerCase().includes(needle) ||
        item.subtitle.toLowerCase().includes(needle) ||
        item.title.toLowerCase().includes(needle) ||
        item.value.toLowerCase().includes(needle) ||
        item.part_number.toLowerCase().includes(needle);
      return filterMatch && queryMatch;
    });
  }, [filter, query, state]);

  const componentCounts = useMemo(() => {
    const counts: Record<"all" | StatusGroup, number> = { all: 0, error: 0, warn: 0, manual: 0, pass: 0 };
    if (!state) return counts;
    counts.all = state.queue.length;
    for (const item of state.queue) counts[item.status_group] += 1;
    return counts;
  }, [state]);

  const pickComponent = (component: ReviewQueueItem) => {
    const firstTaskId =
      component.top_task_id ??
      state?.review_tasks.find((item) => item.refdes === component.refdes)?.id ??
      null;
    setSelectedRefdes(component.refdes);
    setSelectedTaskId(firstTaskId);
  };

  const pickTask = (task: ReviewTask) => {
    setSelectedTaskId(task.id);
    setSelectedRefdes(task.refdes);
  };

  const openTask = (task: ReviewTask, nextView: ViewId = "review") => {
    pickTask(task);
    setView(nextView);
  };

  const handleImportComplete = async (result: ImportResponse) => {
    setParseResult(result);
    setView("parse");
    await loadState();
    window.setTimeout(() => setView("review"), 950);
  };

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
    <main className={`app-shell view-${view}`}>
      <Header state={state} currentView={view} onNavigate={setView} />
      {view === "import" && (
        <ImportView state={state} onImported={(result) => void handleImportComplete(result)} />
      )}
      {view === "parse" && <ParseView state={state} parseResult={parseResult} />}
      {view === "review" && (
        <section className="workspace" aria-label="Hardwise 三栏审查工作台">
          <TaskQueueColumn
            items={filteredComponents}
            allItems={state.queue}
            counts={componentCounts}
            selectedRefdes={selectedRefdes}
            filter={filter}
            query={query}
            onFilter={setFilter}
            onQuery={setQuery}
            onPick={pickComponent}
          />
          <DetailColumn detail={detail} loading={detailLoading} onAsk={() => setView("copilot")} />
          <EvidenceColumn
            tasks={selectedComponentTasks}
            selectedTaskId={selectedTask?.id ?? null}
            selectedRefdes={selectedRefdes}
            onPickTask={setSelectedTaskId}
            detail={detail}
            riskHints={state.risk_hint_details}
          />
        </section>
      )}
      {view === "copilot" && (
        <CopilotPanel state={state} selectedRefdes={selectedRefdes} className="copilot-full" />
      )}
      {view === "findings" && (
        <FindingsView
          tasks={state.review_tasks}
          resolvedTaskIds={resolvedTaskIds}
          onToggleResolved={(taskId) => {
            setResolvedTaskIds((current) => {
              const next = new Set(current);
              if (next.has(taskId)) next.delete(taskId);
              else next.add(taskId);
              return next;
            });
          }}
          onOpenTask={openTask}
        />
      )}
      {view === "export" && <ExportView state={state} />}
    </main>
  );
}

function TaskQueueColumn(props: {
  items: ReviewQueueItem[];
  allItems: ReviewQueueItem[];
  counts: Record<"all" | StatusGroup, number>;
  selectedRefdes: string | null;
  filter: "all" | StatusGroup;
  query: string;
  onFilter: (value: "all" | StatusGroup) => void;
  onQuery: (value: string) => void;
  onPick: (component: ReviewQueueItem) => void;
}) {
  return (
    <aside className="panel queue-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Review Queue</span>
          <h2>组件审查队列</h2>
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
            <span className={`filter-swatch ${item.id}`} />
            <span>{item.label}</span>
            <small>{item.hint}</small>
            <b>{props.counts[item.id]}</b>
          </button>
        ))}
      </div>
      <label className="search-box">
        <Search size={15} />
        <input
          value={props.query}
          onChange={(event) => props.onQuery(event.target.value)}
          placeholder="按位号、器件、网络筛选..."
        />
      </label>
      <div className="queue-list">
        {props.items.map((item, index) => (
          <button
            type="button"
            key={item.refdes}
            className={`queue-row ${item.status_group} ${
              props.selectedRefdes === item.refdes ? "selected" : ""
            }`}
            style={{ animationDelay: `${Math.min(index, 10) * 16}ms` }}
            onClick={() => props.onPick(item)}
          >
            <span className="refdes">{item.refdes}</span>
            <span className="queue-copy">
              <strong>{formatSummary(item.title)}</strong>
              <small>{queueSubtitle(item)}</small>
              <span className="row-badges">
                <StatusBadge group={item.status_group} label={attentionLabel(item.status_group)} />
                <TrustBadge tier={item.trust_tier} />
              </span>
            </span>
            <span className="queue-side">
              <b>{item.task_count > 0 ? `${item.task_count} 项` : "通过"}</b>
              <small>{item.top_task_id ?? "cleared"}</small>
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}

function DetailColumn({
  detail,
  loading,
  onAsk
}: {
  detail: ComponentDetail | null;
  loading: boolean;
  onAsk: () => void;
}) {
  const [prepPreview, setPrepPreview] = useState("");
  const [prepBusy, setPrepBusy] = useState(false);
  const [prepError, setPrepError] = useState("");

  useEffect(() => {
    setPrepPreview("");
    setPrepError("");
  }, [detail?.refdes]);

  const loadPrepPacket = async (download: boolean) => {
    if (!detail || prepBusy) return;
    setPrepBusy(true);
    setPrepError("");
    try {
      const markdown = await fetchPrepPacketMarkdown(detail.refdes);
      if (download) {
        const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `hardwise-prep-${detail.refdes}.md`;
        anchor.click();
        URL.revokeObjectURL(url);
      } else {
        setPrepPreview(markdown);
      }
    } catch (err) {
      setPrepError(err instanceof Error ? err.message : "准备包生成失败");
    } finally {
      setPrepBusy(false);
    }
  };

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
        <p>请选择一个器件查看审查详情。</p>
      </section>
    );
  }

  return (
    <section className="panel detail-panel">
      <div className="detail-scroll" key={detail.refdes}>
        <div className="component-title detail-head">
          <span className="detail-glyph"><Layers3 size={24} /></span>
          <div className="detail-title">
            <span className="eyebrow">器件详情</span>
            <h2>{detail.refdes}</h2>
            <p>{detail.value}</p>
            <div className="detail-keyline">
              <span className="chip mono">{detail.part_number || "无 MPN"}</span>
              <span className="chip">{detail.package || "无封装"}</span>
              <span className="chip">{detail.manufacturer || "未知厂商"}</span>
              <span className="chip mono">{detail.profile_part_number || "待补档案"}</span>
            </div>
          </div>
          <div className="title-actions">
            <StatusBadge group={detail.status_group} label={detail.status_label} />
            <TrustBadge tier={detail.trust_tier} />
            <button className="icon-text-btn" type="button" onClick={onAsk}>
              <Bot size={14} />
              问 Copilot
            </button>
          </div>
        </div>
        <VerdictBanner group={detail.status_group} />
        <div className="identity-grid">
          <InfoCell label="MPN" value={detail.part_number || "-"} />
          <InfoCell label="厂商" value={detail.manufacturer || "-"} />
          <InfoCell label="封装" value={detail.package || "-"} />
          <InfoCell label="器件档案" value={detail.profile_part_number || "待补"} />
          <InfoCell label="BOM 来源" value={detail.bom?.source || "-"} />
          <InfoCell label="档案状态" value={profileStatusLabel(detail.profile?.status || detail.match_status)} />
          <InfoCell label="文档索引" value={documentStatusLabel(detail.document?.status || "not_configured")} />
          <InfoCell label="任务数" value={`${detail.task_counts.total} 项`} />
        </div>
        {detail.match_reason && <p className="scope-note">{formatSummary(detail.match_reason)}</p>}
        <section className="prep-actions" aria-label="评审准备包">
          <div>
            <span className="eyebrow">Prep Packet</span>
            <strong>评审准备包</strong>
            <p>把当前器件身份、BOM/profile/document 状态、tasks、risk hints 和 evidence 汇总成可交接资料。</p>
          </div>
          <button className="icon-text-btn" type="button" onClick={() => void loadPrepPacket(false)} disabled={prepBusy}>
            {prepBusy ? <Loader2 className="spin" size={14} /> : <FileSearch size={14} />}
            预览
          </button>
          <button className="icon-text-btn" type="button" onClick={() => void loadPrepPacket(true)} disabled={prepBusy}>
            <Download size={14} />
            下载 MD
          </button>
        </section>
        {prepError && <p className="form-error detail-error">{prepError}</p>}
        {prepPreview && <pre className="prep-preview">{prepPreview}</pre>}
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
            {detail.pins.map((pin) => (
              <div className="pin-row" key={`${pin.number}-${pin.name}`}>
                <span className="mono">{pin.number}</span>
                <span>{pin.name}</span>
                <span className="mono net-name">{pin.net || "-"}</span>
                <span>{pin.status ? <StatusBadge group={statusGroup(pin.status)} label={pinStatusLabel(pin.status)} /> : "-"}</span>
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
      </div>
    </section>
  );
}

function EvidenceColumn({
  tasks,
  selectedTaskId,
  selectedRefdes,
  onPickTask,
  detail,
  riskHints
}: {
  tasks: ReviewTask[];
  selectedTaskId: string | null;
  selectedRefdes: string | null;
  onPickTask: (taskId: string) => void;
  detail: ComponentDetail | null;
  riskHints: RiskHintsView;
}) {
  const selected = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null;
  const chainRefdes = detail?.refdes ?? selectedRefdes;
  return (
    <aside className="panel evidence-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Evidence Chain</span>
          <h2>{chainRefdes ? `${chainRefdes} 证据链` : "证据链"}</h2>
        </div>
        <Link2 size={17} />
      </div>
      {!chainRefdes ? (
        <div className="empty-panel compact">
          <CircleHelp size={28} />
          <p>选择一个器件后显示 chain of custody。</p>
        </div>
      ) : tasks.length === 0 ? (
        <div className="empty-panel compact">
          <CircleHelp size={28} />
          <p>当前器件没有 finding，显示组件级证据摘要。</p>
          <div className="evidence-list component-summary-chain">
            {detail?.evidence_chain.map((item, index) => (
              <EvidenceCard item={item} key={`${item.kind}-${index}`} />
            )) ?? <p className="muted">正在读取组件级证据摘要...</p>}
          </div>
        </div>
      ) : (
        <div className="finding-chain">
          <div className="task-tabs" aria-label="当前器件 findings">
            {tasks.map((task) => (
              <button
                type="button"
                key={task.id}
                className={task.id === selected?.id ? "active" : ""}
                onClick={() => onPickTask(task.id)}
              >
                <span className="mono">{task.id}</span>
                <StatusBadge group={task.status_group} label={attentionLabel(task.status_group)} />
              </button>
            ))}
          </div>
          {tasks.map((task) => (
            <article
              className={`evi-finding ${task.status_group} ${task.id === selected?.id ? "selected" : ""}`}
              key={task.id}
              onClick={() => onPickTask(task.id)}
            >
              <div className="task-brief">
                <div className="finding-meta">
                  <span className="eyebrow">{task.id} · {taskKindLabel(task.kind)} · {task.refdes}</span>
                  <StatusBadge group={task.status_group} label={attentionLabel(task.status_group)} />
                  <TrustBadge tier={task.trust_tier} />
                </div>
                <strong>{formatSummary(task.title)}</strong>
                <p>{formatSummary(task.body)}</p>
                <div className="guard-note">
                  <ShieldCheck size={15} />
                  <span>
                    <b>How this was reached · {TRUST_LABEL[task.trust_tier]}.</b>
                    {" "}结论只来自后端事实、规则和 evidence token；外部提示保持只读人工线索。
                  </span>
                </div>
              </div>
              <div className="evidence-list">
                {task.evidence_chain.length === 0 ? (
                  <p className="muted">该 finding 没有可展示 evidence node。</p>
                ) : (
                  task.evidence_chain.map((item, index) => (
                    <EvidenceCard item={item} key={`${task.id}-${item.kind}-${index}`} />
                  ))
                )}
              </div>
              <div className="recommended-action">
                <b>建议动作</b>
                <span>{formatSummary(task.recommended_action)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
      <RiskHintsPanel riskHints={riskHints} selectedRefdes={chainRefdes} />
    </aside>
  );
}

function RiskHintsPanel({ riskHints, selectedRefdes }: { riskHints: RiskHintsView; selectedRefdes: string | null }) {
  const visible = selectedRefdes ? riskHints.accepted.filter((item) => item.refdes === selectedRefdes) : [];
  return (
    <section className="risk-hints">
      <div className="section-title">
        <h3>外部提示 · 只读</h3>
        <span>已接收 {riskHints.accepted_external_count} / 已拒绝 {riskHints.rejected_external_count}</span>
      </div>
      <div className="risk-summary">
        <span>状态：{riskHints.external_status === "loaded" ? "已加载" : "未配置"}</span>
        <span>总数：{riskHints.count}</span>
        <span>已包裹位号：{riskHints.wrapped_refdes_count}</span>
      </div>
      <p className="scope-note">外部提示只作为人工线索，不改变 PASS/WARN/ERROR 结论。</p>
      {visible.map((hint) => (
        <div className="risk-card" key={`${hint.refdes}-${hint.title}`}>
          <strong>{hint.refdes} · {formatSummary(hint.title)}</strong>
          <p>{formatSummary(hint.body)}</p>
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

export default App;
