import { CircleHelp, Link2, ShieldCheck } from "lucide-react";
import { EvidenceCard, EvidenceToken, StatusBadge, TrustBadge } from "../../components/ui";
import { TRUST_LABEL, attentionLabel, formatSummary, taskKindLabel } from "../../lib/format";
import type { ComponentDetail, ReviewTask, RiskHintsView } from "../../types";

export function EvidenceColumn({
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
