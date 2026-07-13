import { useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { StatusBadge } from "../components/ui";
import { formatSummary } from "../lib/format";
import type {
  ReviewDecisionStatus,
  ReviewTask,
  ReviewTaskGroup
} from "../types";
import type { ViewId } from "./nav";

export function FindingsView({
  groups,
  tasks,
  onDecision,
  onRerun,
  onOpenTask
}: {
  groups: ReviewTaskGroup[];
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
            决策由后端保存，不改变确定性 PASS/WARN/ERROR。
          </p>
        </div>
        <button type="button" onClick={() => void rerun()} disabled={busy !== ""}>
          {busy === "rerun" ? <Loader2 className="spin" size={15} /> : <RotateCcw size={15} />}
          重新运行确定性检查
        </button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="findings-list">
        {groups.map((group) => {
          const groupTasks = group.task_ids
            .map((taskId) => tasksById.get(taskId))
            .filter((task): task is ReviewTask => Boolean(task));
          const root = groupTasks.find((task) => !task.derived_from_task_id) ?? groupTasks[0];
          const decisionStatuses = new Set(
            groupTasks.map((task) => task.review_decision?.status ?? "open")
          );
          const decision = decisionStatuses.size === 1
            ? [...decisionStatuses][0]
            : "mixed";
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
                <span className="source-badge">评审 {decision}</span>
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
                <button type="button" onClick={() => void decide(group, "accepted")} disabled={!reason || busy !== ""}>接受</button>
                <button type="button" onClick={() => void decide(group, "waived")} disabled={!reason || busy !== ""}>豁免</button>
                <button type="button" onClick={() => void decide(group, "resolved")} disabled={!reason || busy !== ""}>已解决</button>
                <button type="button" onClick={() => void decide(group, "open")} disabled={busy !== ""}>重新打开</button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
