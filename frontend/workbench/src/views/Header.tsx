import { ShieldCheck } from "lucide-react";
import { Metric } from "../components/ui";
import type { WorkbenchState } from "../types";
import { NAV_ITEMS, type ViewId } from "./nav";

export function Header({
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
    state.capabilities.pin_table_enabled ? "引脚表已加载" : "引脚表未加载",
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
          {capabilityText.slice(0, 3).map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </div>
    </header>
  );
}
