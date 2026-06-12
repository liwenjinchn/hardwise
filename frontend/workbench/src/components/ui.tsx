import { AlertTriangle, CheckCircle2, CircleHelp, ExternalLink } from "lucide-react";
import type { CheckView, EvidenceChainItem, EvidenceView, StatusGroup, TrustTier } from "../types";
import { TRUST_LABEL, chainKindLabel, evidenceNodeKind, formatSummary, sourceLabel } from "../lib/format";

// Shared chips, badges, evidence rows, and small presentational primitives —
// mirrors the reference prototype's ui.jsx role.

export function Metric({ label, value, tone }: { label: string; value: number; tone?: StatusGroup }) {
  return (
    <div className={`metric ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function StatusBadge({ group, label }: { group: StatusGroup; label: string }) {
  return <span className={`status-badge ${group}`}>{label}</span>;
}

export function TrustBadge({ tier }: { tier: TrustTier }) {
  const [level, ...labelParts] = TRUST_LABEL[tier].split(" ");
  return (
    <span className={`trust-badge ${tier}`}>
      <span className="trust-level">{level}</span>
      <span className="trust-name">{labelParts.join(" ")}</span>
    </span>
  );
}

export function StatusIcon({ group }: { group: StatusGroup }) {
  if (group === "pass") return <CheckCircle2 size={15} />;
  if (group === "manual") return <CircleHelp size={15} />;
  return <AlertTriangle size={15} />;
}

export function VerdictBanner({ group }: { group: StatusGroup }) {
  const copy: Record<StatusGroup, { title: string; body: string }> = {
    error: { title: "必须处理 · 阻塞项", body: "确定性检查已经失败，进入 layout handoff 前需要处理。" },
    warn: { title: "需要复核 · 有证据", body: "当前规则给出 WARN，请阅读 evidence token 后确认是否接受。" },
    manual: { title: "人工确认 · 数据不足", body: "后端没有足够公开档案生成结论，保留为人工线索。" },
    pass: { title: "已通过 · 当前覆盖", body: "已配置的规则没有发现 WARN/ERROR；这不是全板电气保证。" }
  };
  const item = copy[group];
  return (
    <div className={`verdict-banner ${group}`}>
      <span className="vb-icon"><StatusIcon group={group} /></span>
      <span className="vb-txt">
        <strong>{item.title}</strong>
        <small>{item.body}</small>
      </span>
    </div>
  );
}

export function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-cell">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function EvidenceToken({ evidence }: { evidence: EvidenceView }) {
  return (
    <span className={`token ${evidence.source_class}`}>
      <ExternalLink size={11} />
      {evidence.token}
      <small>{evidence.label} · {sourceLabel(evidence.source_class)}</small>
    </span>
  );
}

export function EvidenceCard({ item }: { item: EvidenceChainItem }) {
  return (
    <article className={`evidence-card evi-node ${item.status_group} ${evidenceNodeKind(item)}`}>
      <div className="card-line en-src">
        <StatusIcon group={item.status_group} />
        <span className="chain-kind">{chainKindLabel(item.kind)}</span>
        <strong>{formatSummary(item.title)}</strong>
        <TrustBadge tier={item.trust_tier} />
      </div>
      <p className="en-body">{formatSummary(item.body)}</p>
      <div className="evidence-tokens">
        {item.evidence.map((evidence) => <EvidenceToken evidence={evidence} key={evidence.token} />)}
        {item.evidence.length === 0 && <span className="muted">无 evidence token</span>}
      </div>
    </article>
  );
}

export function CheckCard({ check }: { check: CheckView }) {
  return (
    <article className={`check-card ${check.status_group}`}>
      <div className="card-line">
        <StatusIcon group={check.status_group} />
        <strong>{check.subject}</strong>
        <StatusBadge group={check.status_group} label={check.status_label} />
      </div>
      <p>{formatSummary(check.summary)}</p>
      <div className="evidence-tokens">
        {check.evidence.slice(0, 4).map((item) => <EvidenceToken evidence={item} key={item.token} />)}
      </div>
    </article>
  );
}
