import { useEffect, useState } from "react";
import { fetchReviewHistory } from "../api";
import type { ReviewHistoryPage, ReviewTask } from "../types";
import { ProvenanceDownload } from "../components/ProvenanceDownload";

const statusLabels: Record<string, string> = {
  open: "待处理", accepted: "已接受", waived: "已豁免", resolved: "已解决", needs_review: "需复核"
};

export function ReviewHistory({ projectId, runId, historyCount, tasks }: {
  projectId: string | null; runId: string | null; historyCount: number; tasks: ReviewTask[];
}) {
  const [open, setOpen] = useState(false);
  return <section className="review-history" aria-label="评审处理历史">
    <ProvenanceDownload projectId={projectId} runId={runId} />
    <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
      {open ? "收起处理历史" : "查看处理历史"}
    </button>
    {open && <HistoryPages key={`${projectId}|${runId}|${historyCount}`}
      projectId={projectId} tasks={tasks} />}
  </section>;
}

function HistoryPages({ projectId, tasks }: { projectId: string | null; tasks: ReviewTask[] }) {
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState<ReviewHistoryPage | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    setPage(null);
    setError("");
    if (!projectId) {
      setError("当前没有可读取历史的项目。");
      setBusy(false);
      return;
    }
    fetchReviewHistory(projectId, offset).then((data) => {
      if (cancelled) return;
      if (data.project_id !== projectId) throw new Error("活动项目已变化，请刷新后查看历史。");
      setPage(data);
    }).catch((err: unknown) => {
      if (!cancelled) setError(err instanceof Error ? err.message : "历史读取失败");
    }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [projectId, offset, revision]);
  const byKey = new Map(tasks.map((task) => [task.stable_key, task]));
  return <div className="history-pages">
    <p>这里展示评审处理历史。输入变化、规则/依赖合同更新和问题撤下不代表工程师手工解决；机器判定不受历史状态修改。</p>
    {busy && <p role="status">正在读取历史…</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    <button type="button" disabled={busy} onClick={() => { setOffset(0); setRevision(revision + 1); }}>刷新历史</button>
    {page && <>
      <p role="status">共 {page.total} 条；当前 {page.events.length ? offset + 1 : 0}–{page.events.length ? offset + page.events.length : 0} 条</p>
      {!page.events.length && <p>本页没有处理历史。</p>}
      <ol className="history-events">
        {page.events.map((event) => {
          const task = byKey.get(event.stable_key);
          const decision = event.decision;
          const label = event.event === "disappeared" ? "从当前列表撤下（未视作人工解决）"
            : event.event === "inputs_changed" ? "输入变化或评审依据更新，原处理需复核" : "人工更新处理状态";
          const date = new Date(event.created_at);
          return <li className="history-event" key={event.id}>
            <strong>{label}</strong>
            <p>{task ? `当前对应问题：${task.refdes} · ${task.title}` : "历史问题（当前列表无对应项）"}</p>
            <p>{decision.previous_status ? `${statusLabels[decision.previous_status]} → ` : ""}
              {statusLabels[decision.status] ?? decision.status}</p>
            <p className="history-reason">原记录理由：{decision.reason || "未填写"}</p>
            <time dateTime={event.created_at}>{Number.isNaN(date.getTime()) ? event.created_at : date.toLocaleString("zh-CN", { hour12: false })}</time>
            <details><summary>追溯标识与输入指纹</summary>
              <p>问题标识：{event.stable_key}</p>
              <p>运行标识：{event.run_id}</p>
              <ProvenanceDownload projectId={projectId} runId={event.run_id} historical />
              <p>原输入指纹：{decision.fingerprint ?? "旧记录未提供"}</p>
              <p>事件时输入指纹：{decision.current_fingerprint ?? "旧记录未提供"}</p>
            </details>
          </li>;
        })}
      </ol>
      <nav aria-label="历史分页" className="history-pagination">
        <button type="button" disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>上一页历史</button>
        <button type="button" disabled={busy || offset + page.events.length >= page.total} onClick={() => setOffset(offset + 20)}>下一页历史</button>
      </nav>
    </>}
  </div>;
}
