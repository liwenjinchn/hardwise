import { useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { StatusBadge } from "../components/ui";
import { formatSummary } from "../lib/format";
import type {
  ReviewDecisionStatus,
  ReviewDecisionSummary,
  ReviewTask,
  ReviewTaskGroup
} from "../types";
import type { ViewId } from "./nav";
import { ReviewHistory } from "./ReviewHistory";

export function FindingsView({
  groups,
  tasks,
  onDecision,
  onRerun,
  onOpenTask,
  reviewSummary
}: {
  groups: ReviewTaskGroup[];
  reviewSummary?: ReviewDecisionSummary | null;
  tasks: ReviewTask[];
  onDecision: (
    stableKeys: string[],
    status: ReviewDecisionStatus,
    reason: string
  ) => Promise<void>;
  onRerun: () => Promise<void>;
  onOpenTask: (task: ReviewTask, view?: ViewId) => void;
}) {
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const offline = typeof window !== "undefined" && !!window.__HARDWISE_OFFLINE_SNAPSHOT__;
  const tasksById = new Map(tasks.map((task) => [task.id, task]));

  const decide = async (group: ReviewTaskGroup, status: ReviewDecisionStatus) => {
    setBusy(group.id);
    setError("");
    try {
      await onDecision(group.stable_keys, status, reasons[group.id] ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "评审决策更新失败");
    } finally {
      setBusy("");
    }
  };

  const rerun = async () => {
    setBusy("rerun");
    setError("");
    try {
      await onRerun();
    } catch (err) {
      setError(err instanceof Error ? err.message : "重新运行失败");
    } finally {
      setBusy("");
    }
  };

  return (
    <section className="flow-page findings-page">
      <div className="flow-copy findings-heading">
        <div>
          <span className="eyebrow">Findings · grouped reviewer workload</span>
          <h2>问题清单与评审决策</h2>
          <p>
            当前显示 {groups.length} 个审查组，保留 {tasks.length} 条原始任务用于审计。
            人工决定由后端保存，不改变机器检查结果。
          </p>
            <p role="status">
              {offline
                ? "离线只读快照：人工理由及已封存历史可查看；不能修改决定或重新运行。"
                : reviewSummary?.storage === "local_file"
                ? "人工决定已保存到本地日志。在“导入”页保存项目后可保留原始输入供重开；搬迁时请携带输入目录或完整项目备份。"
                : "人工决定仅保存在本次服务中；服务退出后不会自动恢复。"}
              {reviewSummary?.needs_review ? ` ${reviewSummary.needs_review} 条旧决定因输入或评审依据更新需要复核，原理由已保留。` : ""}
            </p>
            {error && <p className="form-error" role="alert">{error}</p>}

        </div>
        <button type="button" onClick={() => void rerun()} disabled={offline || busy !== ""}>
          {busy === "rerun" ? <Loader2 className="spin" size={15} /> : <RotateCcw size={15} />}
          重新运行确定性检查
        </button>
      </div>
      <div className="findings-list">
        <ReviewHistory projectId={reviewSummary?.project_id ?? null} runId={reviewSummary?.run_id ?? null}
          historyCount={reviewSummary?.history_count ?? 0} tasks={tasks} />
        {groups.map((group) => {
          const groupTasks = group.task_ids
            .map((taskId) => tasksById.get(taskId))
            .filter((task): task is ReviewTask => Boolean(task));
          const root = groupTasks.find((task) => !task.derived_from_task_id) ?? groupTasks[0];
          const decisionStatuses = new Set(
            groupTasks.map((task) => task.review_decision?.status ?? "open")
          );
          const decision = decisionStatuses.has("needs_review")
            ? "needs_review"
            : decisionStatuses.size === 1 ? [...decisionStatuses][0] : "mixed";
          const reason = reasons[group.id] ?? "";
          return (
            <article className={`finding-row ${group.status_group}`} key={group.id}>
              <div className="finding-copy">
                <span className="eyebrow">
                  {group.id} · {group.affected_refdes.join(", ")}
                </span>
                <strong>{formatSummary(group.title)}</strong>
                <p>{formatSummary(group.recommended_action)}</p>
                <small>
                  {group.raw_task_count} 条原始任务
                  {group.derived_task_count > 0
                    ? `；${group.derived_task_count} 条派生提示已并入根因`
                    : ""}
                </small>
              </div>
              <div className="finding-status-stack">
                <StatusBadge
                  group={group.status_group}
                  label={`${group.axis === "electrical" ? "电气" : "证据"} ${group.status_group.toUpperCase()}`}
                />
                <span className="source-badge">评审 {decision === "needs_review" ? "需复核" : decision}</span>
                {groupTasks.some((task) => task.review_decision?.reason) && (
                  <details>
                    <summary>已有处理理由</summary>
                    {groupTasks.filter((task) => task.review_decision?.reason).map((task) => (
                      <p key={task.stable_key}>{task.refdes}：{task.review_decision?.reason}</p>
                    ))}
                  </details>
                )}
              </div>
              <input
                aria-label={`${group.id} 评审理由`}
                value={reason}
                placeholder="填写接受、豁免或解决理由"
                onChange={(event) => setReasons((current) => ({
                  ...current,
                  [group.id]: event.target.value
                }))}
              />
              <div className="finding-actions">
                <button type="button" onClick={() => root && onOpenTask(root)} disabled={!root}>查看</button>
                <button type="button" onClick={() => root && onOpenTask(root, "copilot")} disabled={!root}>问 Copilot</button>
                <button type="button" onClick={() => void decide(group, "accepted")} disabled={offline || !reason || busy !== ""}>接受</button>
                <button type="button" onClick={() => void decide(group, "waived")} disabled={offline || !reason || busy !== ""}>豁免</button>
                <button type="button" onClick={() => void decide(group, "resolved")} disabled={offline || !reason || busy !== ""}>已解决</button>
                <button type="button" onClick={() => void decide(group, "open")} disabled={offline || busy !== ""}>重新打开</button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
