import { Search } from "lucide-react";
import { StatusBadge, TrustBadge } from "../../components/ui";
import { attentionLabel, formatSummary, queueSubtitle } from "../../lib/format";
import type { ReviewQueueItem, StatusGroup } from "../../types";

const FILTERS: Array<{ id: "all" | StatusGroup; label: string; hint: string }> = [
  { id: "all", label: "全部待看", hint: "所有被标记的器件" },
  { id: "error", label: "必须修", hint: "会阻塞签核的问题" },
  { id: "warn", label: "看证据", hint: "有引用的建议项" },
  { id: "manual", label: "人工判断", hint: "数据无法自动确认" },
  { id: "pass", label: "已通过", hint: "检查已满足" }
];

export function TaskQueueColumn(props: {
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
