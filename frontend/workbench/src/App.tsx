import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  CircleHelp,
  Download,
  ExternalLink,
  FileArchive,
  FileSearch,
  FileUp,
  Layers3,
  Link2,
  Loader2,
  MessageSquare,
  PackageCheck,
  Play,
  Search,
  ShieldCheck,
  UploadCloud
} from "lucide-react";
import {
  askCopilot,
  exportWorkbench,
  fetchComponentDetail,
  fetchPrepPacketMarkdown,
  fetchProjectPrepPacketMarkdown,
  fetchWorkbenchState,
  importWorkbench
} from "./api";
import type {
  ChatMessage,
  ChatResponse,
  CheckView,
  ComponentDetail,
  EvidenceChainItem,
  EvidenceView,
  ImportResponse,
  ReviewQueueItem,
  ReviewTask,
  RiskHintsView,
  StatusGroup,
  TrustTier,
  WorkbenchState
} from "./types";

type ViewId = "import" | "parse" | "review" | "copilot" | "findings" | "export";

const NAV_ITEMS: Array<{ id: ViewId; label: string }> = [
  { id: "import", label: "导入" },
  { id: "parse", label: "解析" },
  { id: "review", label: "审查" },
  { id: "copilot", label: "AI 助手" },
  { id: "findings", label: "问题清单" },
  { id: "export", label: "导出" }
];

const FILTERS: Array<{ id: "all" | StatusGroup; label: string; hint: string }> = [
  { id: "all", label: "全部待看", hint: "所有被标记的器件" },
  { id: "error", label: "必须修", hint: "会阻塞签核的问题" },
  { id: "warn", label: "看证据", hint: "有引用的建议项" },
  { id: "manual", label: "人工判断", hint: "数据无法自动确认" },
  { id: "pass", label: "已通过", hint: "检查已满足" }
];

const TRUST_LABEL: Record<TrustTier, string> = {
  l1: "L1 确定性",
  l2: "L2 有出处",
  l3: "L3 人工确认"
};

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

function Header({
  state,
  currentView,
  onNavigate
}: {
  state: WorkbenchState;
  currentView: ViewId;
  onNavigate: (view: ViewId) => void;
}) {
  const { summary } = state;
  const reviewComponentCount = state.queue.filter((item) => item.status_group !== "pass").length || state.queue.length;
  const capabilityText = [
    state.capabilities.chat ? "Copilot 可用" : "Copilot 关闭",
    state.capabilities.datasheet_search_enabled ? "向量检索开启" : "向量检索关闭",
    state.capabilities.risk_hints_enabled ? "外部提示已加载" : "外部提示未配置",
    "Refdes Guard 在线"
  ];

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark"><ShieldCheck size={15} /></span>
        <div>
          <span className="brand-name">Hard<b>wise</b></span>
          <span className="brand-tag">schematic review</span>
        </div>
      </div>
      <nav className="flow-nav" aria-label="工作流导航">
        {NAV_ITEMS.map((item) => (
          <button
            type="button"
            key={item.id}
            className={currentView === item.id ? "active" : ""}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
            {item.id === "review" && <span className="pip">{reviewComponentCount}</span>}
            {item.id === "findings" && <span className="pip">{state.task_counts.error + state.task_counts.warn}</span>}
          </button>
        ))}
      </nav>
      <div className="topbar-right">
        <div className="project-pill" title={`${state.project.netlist_type} · ${state.project.netlist_source}`}>
          <span className="dot" />
          <span>{state.project.name}</span>
          <span className="src mono">真实数据</span>
        </div>
        <div className="mini-stats" aria-label="当前审查摘要">
          <Metric label="器件" value={summary.components} />
          <Metric label="已验证" value={summary.validated} />
          <Metric label="ERROR" value={summary.error_count} tone="error" />
          <Metric label="WARN" value={summary.warn_count} tone="warn" />
        </div>
        <div className="capability-strip" aria-label="工作台能力">
          {capabilityText.slice(0, 2).map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
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

function ImportView({
  state,
  onImported
}: {
  state: WorkbenchState;
  onImported: (result: ImportResponse) => void;
}) {
  const [netlist, setNetlist] = useState<File | null>(null);
  const [bom, setBom] = useState<File | null>(null);
  const [riskHints, setRiskHints] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!netlist || busy) {
      setError("请选择 netlist/PST 文件。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await importWorkbench({ netlist, bom, riskHints });
      onImported(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flow-page import-page">
      <div className="flow-copy">
        <span className="eyebrow">Import</span>
        <h2>上传 netlist / BOM，重建当前工作台</h2>
        <p>
          文件只写入本进程临时目录。上传成功后后端会重新运行
          WorkbenchContext，浏览器进入 Parse 动画，再回到 Review。
        </p>
      </div>
      <form className="upload-board" onSubmit={(event) => void submit(event)}>
        <UploadSlot
          icon={<UploadCloud size={20} />}
          label="netlist / PST"
          required
          file={netlist}
          accept=".net,.dat,.txt,.pst"
          onPick={setNetlist}
        />
        <UploadSlot
          icon={<FileArchive size={20} />}
          label="BOM CSV"
          file={bom}
          accept=".csv,.tsv,.txt"
          onPick={setBom}
        />
        <UploadSlot
          icon={<FileUp size={20} />}
          label="risk hints JSON"
          file={riskHints}
          accept=".json"
          onPick={setRiskHints}
        />
        {error && <p className="form-error">{error}</p>}
        <button className="primary-action" type="submit" disabled={busy}>
          {busy ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
          {busy ? "正在导入" : "导入并解析"}
        </button>
      </form>
      <div className="current-snapshot">
        <span className="eyebrow">当前工作台</span>
        <strong>{state.summary.components} components</strong>
        <p>
          已验证 {state.summary.validated}，PASS/WARN/ERROR=
          {state.summary.pass_count}/{state.summary.warn_count}/{state.summary.error_count}，
          manual={state.summary.manual}
        </p>
      </div>
    </section>
  );
}

function UploadSlot(props: {
  icon: ReactNode;
  label: string;
  required?: boolean;
  file: File | null;
  accept: string;
  onPick: (file: File | null) => void;
}) {
  return (
    <label className="upload-slot">
      <span>{props.icon}</span>
      <strong>{props.label}{props.required ? " *" : ""}</strong>
      <small>{props.file?.name ?? "选择文件"}</small>
      <input
        type="file"
        accept={props.accept}
        onChange={(event) => props.onPick(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}

function ParseView({
  state,
  parseResult
}: {
  state: WorkbenchState;
  parseResult: ImportResponse | null;
}) {
  const summary = parseResult?.summary ?? state.summary;
  const steps = [
    ["解析网表", `${summary.components} 个器件进入注册表`],
    ["匹配 BOM", `${summary.bom_matched} 个 refdes 已锚定`],
    ["运行确定性验证", `PASS/WARN/ERROR=${summary.pass_count}/${summary.warn_count}/${summary.error_count}`],
    ["生成 finding", `${parseResult?.task_counts.total ?? state.task_counts.total} 个任务已排队`]
  ];
  return (
    <section className="flow-page parse-page">
      <div className="flow-copy">
        <span className="eyebrow">Parse</span>
        <h2>重建证据工作台</h2>
        <p>这里只展示真实后端结果的解析过程；状态数字来自刚刚生成的 WorkbenchContext。</p>
      </div>
      <div className="parse-rail">
        {steps.map(([title, body], index) => (
          <article className="parse-step" key={title} style={{ animationDelay: `${index * 120}ms` }}>
            <CheckCircle2 size={18} />
            <strong>{title}</strong>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
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

function CopilotPanel({
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

function FindingsView({
  tasks,
  resolvedTaskIds,
  onToggleResolved,
  onOpenTask
}: {
  tasks: ReviewTask[];
  resolvedTaskIds: Set<string>;
  onToggleResolved: (taskId: string) => void;
  onOpenTask: (task: ReviewTask, view?: ViewId) => void;
}) {
  return (
    <section className="flow-page findings-page">
      <div className="flow-copy">
        <span className="eyebrow">Findings</span>
        <h2>全部任务登记册</h2>
        <p>resolved 是当前浏览器本地状态，不回写 deterministic 结论。</p>
      </div>
      <div className="findings-list">
        {tasks.map((task) => {
          const resolved = resolvedTaskIds.has(task.id);
          return (
            <article className={`finding-row ${task.status_group} ${resolved ? "resolved" : ""}`} key={task.id}>
              <div>
                <span className="eyebrow">{task.id} · {task.refdes}</span>
                <strong>{formatSummary(task.title)}</strong>
                <p>{formatSummary(task.recommended_action)}</p>
              </div>
              <StatusBadge group={resolved ? "pass" : task.status_group} label={resolved ? "本地已处理" : task.status_label} />
              <button type="button" onClick={() => onOpenTask(task)}>查看</button>
              <button type="button" onClick={() => onOpenTask(task, "copilot")}>问 Copilot</button>
              <button type="button" onClick={() => onToggleResolved(task.id)}>
                {resolved ? "重新打开" : "标记处理"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ExportView({ state }: { state: WorkbenchState }) {
  const [format, setFormat] = useState<"json" | "csv" | "annotations">("json");
  const [preview, setPreview] = useState("");
  const [projectPacketPreview, setProjectPacketPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [packetBusy, setPacketBusy] = useState(false);
  const [error, setError] = useState("");
  const [packetError, setPacketError] = useState("");

  const loadPreview = async () => {
    setBusy(true);
    setError("");
    try {
      const body = await exportWorkbench(format);
      setPreview(format === "json" ? JSON.stringify(JSON.parse(body), null, 2) : body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!preview) return;
    const extension = format === "json" ? "json" : format === "csv" ? "csv" : "txt";
    const blob = new Blob([preview], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `hardwise-${format}.${extension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const loadProjectPacket = async (downloadPacket: boolean) => {
    if (packetBusy) return;
    setPacketBusy(true);
    setPacketError("");
    try {
      const markdown = await fetchProjectPrepPacketMarkdown();
      if (downloadPacket) {
        const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "hardwise-project-prep.md";
        anchor.click();
        URL.revokeObjectURL(url);
      } else {
        setProjectPacketPreview(markdown);
      }
    } catch (err) {
      setPacketError(err instanceof Error ? err.message : "项目准备包生成失败");
    } finally {
      setPacketBusy(false);
    }
  };

  return (
    <section className="flow-page export-page">
      <div className="flow-copy">
        <span className="eyebrow">Export</span>
        <h2>导出当前审查状态</h2>
        <p>
          输出来自真实后端接口：{state.review_tasks.length} 个 finding，
          不包含 API key 或浏览器聊天密钥。
        </p>
      </div>
      <div className="export-stack">
        <section className="project-prep-card" aria-label="项目评审准备包">
          <div>
            <span className="eyebrow">Project Prep Packet</span>
            <strong>项目评审准备包</strong>
            <p>
              汇总全板摘要、重点器件组、review focus areas、开放问题、risk hints 和
              evidence token，适合评审会前交接。
            </p>
          </div>
          <div className="prep-button-row">
            <button type="button" onClick={() => void loadProjectPacket(false)} disabled={packetBusy}>
              {packetBusy ? <Loader2 className="spin" size={15} /> : <FileSearch size={15} />}
              预览项目包
            </button>
            <button type="button" onClick={() => void loadProjectPacket(true)} disabled={packetBusy}>
              <Download size={15} />
              下载 MD
            </button>
          </div>
        </section>
        {packetError && <p className="form-error">{packetError}</p>}
        {projectPacketPreview && <pre className="project-prep-preview">{projectPacketPreview}</pre>}
        <div className="export-controls">
          {(["json", "csv", "annotations"] as const).map((item) => (
            <button
              type="button"
              className={format === item ? "active" : ""}
              key={item}
              onClick={() => {
                setFormat(item);
                setPreview("");
              }}
            >
              {item}
            </button>
          ))}
          <button className="primary-action" type="button" onClick={() => void loadPreview()} disabled={busy}>
            {busy ? <Loader2 className="spin" size={16} /> : <PackageCheck size={16} />}
            生成预览
          </button>
          <button type="button" onClick={download} disabled={!preview}>
            <Download size={15} />
            下载
          </button>
        </div>
        {error && <p className="form-error">{error}</p>}
        <pre className="export-preview">{preview || "选择格式后生成预览。"}</pre>
      </div>
    </section>
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

function EvidenceCard({ item }: { item: EvidenceChainItem }) {
  return (
    <article className={`evidence-card evi-node ${item.status_group} ${evidenceNodeKind(item)}`}>
      <div className="card-line en-src">
        <StatusIcon group={item.status_group} />
        <span className="chain-kind">{chainKindLabel(item.kind)}</span>
        <strong>{formatSummary(item.title)}</strong>
        <TrustBadge tier={item.trust_tier} />
      </div>
      <p className="en-body">{formatSummary(item.body)}</p>
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
      <p>{formatSummary(check.summary)}</p>
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
  const [level, ...labelParts] = TRUST_LABEL[tier].split(" ");
  return (
    <span className={`trust-badge ${tier}`}>
      <span className="trust-level">{level}</span>
      <span className="trust-name">{labelParts.join(" ")}</span>
    </span>
  );
}

function VerdictBanner({ group }: { group: StatusGroup }) {
  const copy: Record<StatusGroup, { title: string; body: string }> = {
    error: { title: "必须处理 · 阻塞项", body: "确定性检查已经失败，进入 layout handoff 前需要处理。" },
    warn: { title: "需要复核 · 有证据", body: "当前规则给出 WARN，请阅读 evidence token 后确认是否接受。" },
    manual: { title: "人工确认 · 数据不足", body: "后端没有足够公开档案生成结论，保留为人工线索。" },
    pass: { title: "已通过 · 当前覆盖", body: "已配置的规则没有发现 WARN/ERROR；这不是全板电气保证。" }
  };
  const item = copy[group];
  return (
    <div className={`verdict-banner ${group}`}>
      <span className="vb-icon"><StatusIcon group={group} /></span>
      <span className="vb-txt">
        <strong>{item.title}</strong>
        <small>{item.body}</small>
      </span>
    </div>
  );
}

function StatusIcon({ group }: { group: StatusGroup }) {
  if (group === "pass") return <CheckCircle2 size={15} />;
  if (group === "manual") return <CircleHelp size={15} />;
  return <AlertTriangle size={15} />;
}

function attentionLabel(group: StatusGroup): string {
  const labels: Record<StatusGroup, string> = {
    error: "必须修",
    warn: "看证据",
    manual: "人工判断",
    pass: "已通过"
  };
  return labels[group];
}

function statusGroup(status: string): StatusGroup {
  if (status === "ERROR") return "error";
  if (status === "WARN") return "warn";
  if (status === "PASS") return "pass";
  return "manual";
}

function pinStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ERROR: "必须修",
    WARN: "看证据",
    PASS: "通过",
    manual_needed: "人工判断",
    profile_missing: "待补档案",
    bom_missing: "BOM 缺失"
  };
  return labels[status] ?? statusLabelFromRaw(status);
}

function statusLabelFromRaw(status: string): string {
  return status
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function profileStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: "已匹配",
    exact: "已匹配",
    ambiguous: "需确认",
    not_found: "未匹配",
    manual_needed: "待补档案",
    profile_missing: "待补档案"
  };
  return labels[status] ?? statusLabelFromRaw(status || "unknown");
}

function documentStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    matched: "已索引",
    loaded: "已索引",
    not_configured: "未配置",
    not_found: "未找到",
    unknown: "未知"
  };
  return labels[status] ?? statusLabelFromRaw(status || "unknown");
}

function queueSubtitle(item: ReviewQueueItem): string {
  const identity = [
    item.part_number || item.value || "无 MPN",
    item.package
  ].filter(Boolean).join(" · ");
  const cues = [
    item.evidence_count ? `${item.evidence_count} 条证据` : "",
    item.risk_hint_count ? `${item.risk_hint_count} 条外部提示` : ""
  ].filter(Boolean).join(" / ");
  return `${identity}${cues ? ` · ${cues}` : ""}`;
}

function countTaskEvidence(task: ReviewTask): number {
  return task.evidence_chain.reduce((count, item) => count + item.evidence.length, 0);
}

function sourceLabel(sourceClass: string): string {
  const labels: Record<string, string> = {
    live_retrieved: "本轮检索",
    reviewed_profile: "已审档案",
    document_index: "资料索引",
    design_source: "设计来源",
    unknown: "未知来源"
  };
  return labels[sourceClass] ?? sourceClass;
}

function evidenceNodeKind(item: EvidenceChainItem): string {
  if (item.trust_tier === "l3" || item.kind.includes("external") || item.kind.includes("manual")) {
    return "manual";
  }
  if (item.evidence.some((evidence) => evidence.source_class === "live_retrieved")) {
    return "grounded";
  }
  return "deterministic";
}

const SUMMARY_REPLACEMENTS: Array<[RegExp, string]> = [
  [/Exactly one local profile part_number matched this BOM identity\./g, "已唯一匹配本地器件档案。"],
  [/BJT emitter pin is not connected\./g, "BJT 发射极未连接。"],
  [/BJT emitter pin is not connected; cannot check VEBO\./g, "BJT 发射极未连接，无法检查 VEBO。"],
  [/BJT emitter pin is not connected; cannot check VCEO\./g, "BJT 发射极未连接，无法检查 VCEO。"],
  [/BJT collector is connected to ([^.]+)\./g, "BJT 集电极连接到 $1。"],
  [/BJT base is connected to ([^.]+)\./g, "BJT 基极连接到 $1。"],
  [/BJT Vebo rating must exceed reverse base-emitter stress\./g, "BJT Vebo 额定值需要覆盖反向基极-发射极应力。"],
  [/MCU SWDIO is connected to SWCLK, expected SWDIO\./g, "MCU SWDIO 接到了 SWCLK，期望连接到 SWDIO。"],
  [/No deterministic capacitance value could be parsed from '([^']+)'\./g, "无法从 '$1' 确定性解析电容值。"],
  [/Diode reverse voltage rating is about ([^,]+), below required ([^.]+)\./g, "二极管反向耐压约 $1，低于所需 $2。"],
  [/Input network voltage falls within the structured component profile limit\./g, "输入网络电压在结构化器件档案限制内。"],
  [/Output network voltage falls within the structured component profile limit\./g, "输出网络电压在结构化器件档案限制内。"],
  [/Pin is tied to an allowed net from the profile\./g, "引脚连接到器件档案允许的网络。"],
  [/Pin is not connected\./g, "引脚未连接。"],
  [/status=not_found/g, "状态：未找到"],
  [/status=ok/g, "状态：通过"]
];

function formatSummary(text: string): string {
  return SUMMARY_REPLACEMENTS.reduce((current, [pattern, replacement]) => {
    return current.replace(pattern, replacement);
  }, text);
}

function chainKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    component_check: "组件规则",
    pin_check: "引脚规则",
    manual_gap: "人工缺口",
    external_risk_hint: "外部线索",
    netlist_trace: "网表追踪",
    design_rule: "设计规则",
    datasheet_or_profile: "资料证据",
    external_hint: "外部线索"
  };
  return labels[kind] ?? kind;
}

function taskKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    component_check: "组件检查",
    pin_check: "引脚检查",
    manual_gap: "人工缺口",
    external_risk_hint: "外部线索",
    cleared: "已通过"
  };
  return labels[kind] ?? kind;
}

export default App;
