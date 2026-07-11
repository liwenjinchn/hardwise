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

      <footer className="evidence-package-guardrail">
        <ShieldCheck size={17} aria-hidden="true" />
        <p>
          <strong>Trust boundary</strong>
          Lane status 只描述输入证据覆盖；PASS/WARN/ERROR 仍只来自确定性验证。
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
