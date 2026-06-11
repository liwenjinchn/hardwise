import { StatusBadge } from "../components/ui";
import { formatSummary } from "../lib/format";
import type { ReviewTask } from "../types";
import type { ViewId } from "./nav";

export function FindingsView({
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
