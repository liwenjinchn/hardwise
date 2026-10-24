import { BomQuantityWarnings } from "./BomQuantityWarnings";
import {
  BookOpenCheck,
  Database,
  FileSpreadsheet,
  PackageCheck,
  ShieldCheck,
  TableProperties,
  type LucideIcon
} from "lucide-react";
import type { EvidencePackageLane, EvidencePackageSummary } from "../types";

const LANE_ICONS: Record<EvidencePackageLane["id"], LucideIcon> = {
  netlist: Database,
  bom: TableProperties,
  validation: ShieldCheck,
  documents: BookOpenCheck,
  pin_table: FileSpreadsheet,
  review_package: PackageCheck
};

const LANE_ORDER: EvidencePackageLane["id"][] = [
  "netlist",
  "bom",
  "validation",
  "documents",
  "pin_table",
  "review_package"
];

export function EvidencePackageDashboard({
  summary,
  className = ""
}: {
  summary: EvidencePackageSummary;
  className?: string;
}) {
  const lanes = [...summary.lanes].sort(
    (left, right) => LANE_ORDER.indexOf(left.id) - LANE_ORDER.indexOf(right.id)
  );

  return (
    <section
      className={`evidence-package-dashboard ${className}`.trim()}
      aria-labelledby="evidence-package-title"
    >
      <header className="evidence-package-header">
        <div>
          <span className="eyebrow">Evidence package · six independent lanes</span>
          <h3 id="evidence-package-title">证据包完整性</h3>
          <p>
            每条 lane 保留自己的状态、计数和单位；不合并为 overall score，也不作为电气签核。
          </p>
        </div>
        <span className="coverage-only-badge" aria-label="Coverage only, no electrical sign-off">
          coverage only
        </span>
      </header>

      <div className="evidence-lane-grid" role="list" aria-label="六条证据覆盖 lane">
        {lanes.map((lane, index) => (
          <EvidenceLaneCard lane={lane} index={index} key={lane.id} />
        ))}
      </div>

      {!Array.isArray(summary.bom_quantity_conflicts) && <p className="scope-note">当前报告未记录数量列核对结果，不能据此判断数量一致。</p>}
      <BomQuantityWarnings conflicts={summary.bom_quantity_conflicts ?? []} />
      <section className="evidence-delivery" aria-label="来源核对和原文随附状态">
        <div>
        <strong>来源核对 · {summary.source_audit?.status === "observed" ? "生成时观察" : "未记录"}</strong>
        <p>{summary.source_audit?.reason ?? "旧报告未记录来源核对结果，需重新核查。"}</p>
        {summary.source_audit?.observed_at && <p>核对时间：{summary.source_audit.observed_at}</p>}
        <p>本机缺失引用 {summary.source_audit?.missing_tokens.length ?? "未知"}；待核查引用 {summary.source_audit?.unchecked_tokens.length ?? "未知"}</p>
        {summary.source_audit && !!(summary.source_audit.missing_tokens.length + summary.source_audit.unchecked_tokens.length) && <details>
          <summary>来源缺失及待核查项</summary>
          <ul>{summary.source_audit.missing_tokens.map(token => <li key={token}>本机缺失：<code>{token}</code></li>)}
          {summary.source_audit.unchecked_tokens.map(token => <li key={token}>待核查：<code>{token}</code></li>)}</ul>
        </details>}
        </div>
        <div>
        <strong>原文随附 · {summary.original_delivery?.status === "not_attached" ? "未附带 PDF 原文" : summary.original_delivery?.status === "no_pdf_citations" ? "当前无 PDF 引用" : "未记录"}</strong>
        <p>{summary.original_delivery?.reason ?? "旧报告未记录原文随附状态，不能判断原文已随包附带。"}</p>
        {!!summary.original_delivery?.missing_tokens.length && <details>
          <summary>缺少原文：{summary.original_delivery.missing_tokens.length} 个引用，需另行核查</summary>
          <ul>{summary.original_delivery.missing_tokens.map(token => <li key={token}><code>{token}</code></li>)}</ul>
        </details>}
        <p>允许导出；来源观察不证明内容、版本或人工审核，不能据此签核。</p>
        </div>
      </section>

      <footer className="evidence-package-guardrail">
        <ShieldCheck size={17} aria-hidden="true" />
        <p>
          <strong>Trust boundary</strong>
          Lane status 只描述输入证据覆盖；PASS/WARN/ERROR 仍只来自确定性验证。来源核对与原文随附分别记录，不重写电气结论。
        </p>
      </footer>
    </section>
  );
}

function EvidenceLaneCard({ lane, index }: { lane: EvidencePackageLane; index: number }) {
  const Icon = LANE_ICONS[lane.id];
  const titleId = `evidence-lane-${lane.id}`;

  return (
    <article
      className={`evidence-lane-card ${lane.status_group}`}
      role="listitem"
      aria-labelledby={titleId}
    >
      <div className="evidence-lane-heading">
        <span className="evidence-lane-icon" aria-hidden="true">
          <Icon size={18} />
        </span>
        <span className="evidence-lane-index">{String(index + 1).padStart(2, "0")}</span>
        <div>
          <span className="evidence-lane-status" aria-label={`Status: ${lane.status_label}`}>
            {lane.status_label}
          </span>
          <h4 id={titleId}>{lane.label}</h4>
        </div>
      </div>

      <p className="evidence-lane-summary">{lane.summary}</p>

      {lane.metrics.length > 0 ? (
        <dl className="evidence-lane-metrics" aria-label={`${lane.label} metrics`}>
          {lane.metrics.map((metric) => (
            <div key={metric.key}>
              <dt>{metric.label}</dt>
              <dd aria-label={`${metric.label}: ${metric.value}${metric.total === null ? "" : ` of ${metric.total}`} ${metric.unit}`}>
                <strong>
                  {metric.value}
                  {metric.total === null ? "" : ` / ${metric.total}`}
                </strong>
                <span>{metric.unit}</span>
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="evidence-lane-empty-metrics">未配置输入，因此没有可报告的 metric。</p>
      )}

      <dl className="evidence-lane-ledger">
        <div>
          <dt>Source token</dt>
          <dd>
            <code title={lane.source ?? undefined}>{lane.source_token ?? "not available"}</code>
          </dd>
        </div>
        <div>
          <dt>Next action</dt>
          <dd>{lane.recommended_action}</dd>
        </div>
        <div className="trust-boundary-row">
          <dt>Trust boundary</dt>
          <dd>{lane.trust_boundary}</dd>
        </div>
      </dl>
    </article>
  );
}
