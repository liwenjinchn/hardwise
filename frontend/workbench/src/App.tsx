import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import {
  fetchComponentDetail,
  fetchWorkbenchState,
  rerunWorkbench,
  updateReviewDecision
} from "./api";
import type {
  ComponentDetail,
  ImportResponse,
  ReviewDecisionStatus,
  ReviewQueueItem,
  ReviewTask,
  StatusGroup,
  WorkbenchState
} from "./types";
import { CopilotPanel } from "./views/CopilotPanel";
import { ExportView } from "./views/ExportView";
import { FindingsView } from "./views/FindingsView";
import { Header } from "./views/Header";
import { ImportView } from "./views/ImportView";
import { ParseView } from "./views/ParseView";
import type { ViewId } from "./views/nav";
import { DetailColumn } from "./views/review/DetailColumn";
import { EvidenceColumn } from "./views/review/EvidenceColumn";
import { TaskQueueColumn } from "./views/review/TaskQueueColumn";

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
  const detailRequestId = useRef(0);

  const applyState = (payload: WorkbenchState) => {
    const firstComponent = payload.queue[0] ?? null;
    const selected = payload.selected_refdes ?? firstComponent?.refdes ?? payload.review_tasks[0]?.refdes ?? null;
    const firstTask = payload.review_tasks.find((item) => item.refdes === selected) ?? payload.review_tasks[0] ?? null;
    setState(payload);
    setSelectedTaskId(firstTask?.id ?? null);
    setSelectedRefdes(selected);
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
      const filterMatch = filter === "all" || item.deterministic_status_group === filter;
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
    for (const item of state.queue) counts[item.deterministic_status_group] += 1;
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

  const handleReviewDecision = async (
    stableKeys: string[],
    status: ReviewDecisionStatus,
    reason: string
  ) => {
    const payload = await updateReviewDecision({ stableKeys, status, reason });
    applyState(payload);
  };

  const handleRerun = async () => {
    const payload = await rerunWorkbench();
    applyState(payload);
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
          groups={state.review_groups}
          tasks={state.review_tasks}
          onDecision={handleReviewDecision}
          onRerun={handleRerun}
          onOpenTask={openTask}
        />
      )}
      {view === "export" && <ExportView state={state} />}
    </main>
  );
}

export default App;
