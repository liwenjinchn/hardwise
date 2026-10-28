import type { ComparisonResult } from "../generated/workbench-contracts";
import { ChangeList } from "./ChangeList";
import { EvidenceList, RevisionSources } from "./Evidence";

const STATUS_LABELS: Record<ComparisonResult["status"], string> = {
  differences: "已观察到版本差异",
  no_observed_difference: "声明范围内未观察到差异",
  needs_review: "存在未解决项，需人工复核"
};

export function ComparisonResults({ result, readOnly = false }: { result: ComparisonResult; readOnly?: boolean }) {
  const summary = result.summary;
  const metrics = [
    ["器件新增", summary.added], ["器件移除", summary.removed], ["属性变化", summary.attribute_changes],
    ["连接变化", summary.connection_changes], ["网络改名", summary.net_renames], ["未解决项", summary.unresolved]
  ] as const;
  return <div className="revision-results">
    <section className="revision-section" aria-labelledby="revision-result-title">
      <div className="revision-section-heading">
        <div><span className="revision-kicker">对比结果</span><h2 id="revision-result-title">{STATUS_LABELS[result.status]}</h2></div>
        <span className="revision-neutral-badge">不评估电气正确性</span>
      </div>
      <p className="revision-result-id">对比 ID <code>{result.comparison_id}</code> · {result.schema_version}</p>
      {result.status === "no_observed_difference" && <p className="revision-boundary">
        仅限两版输入实际声明的器件、属性和连接；未声明内容未比较，不代表整板一致或安全。
      </p>}
      <div className="revision-metrics">{metrics.map(([label, value]) => <div key={label}
        className={label === "未解决项" && value > 0 ? "revision-metric-warning" : ""}>
        <span>{label}</span><strong>{value}</strong>
      </div>)}</div>
      <p className="revision-list-hint">{summary.changed_components} 个器件有变化 · {summary.unchanged_components} 个器件在声明范围内无已观察变化</p>
    </section>

    <section className={`revision-section revision-issues ${result.issues.length ? "has-issues" : ""}`} aria-labelledby="revision-issues-title">
      <div className="revision-section-heading"><h2 id="revision-issues-title">未解决项 <small>{summary.unresolved} 项</small></h2></div>
      {result.issues.length ? <>
        <p>以下缺失、歧义或来源冲突未被当作确定性变化。请先核对源文件；它们不会随变化筛选隐藏。</p>
        <ul>{result.issues.map((issue, index) => <li key={index}>
          <div className="revision-issue-heading"><strong>{{ before: "旧版", after: "新版", both: "两版" }[issue.side]}</strong>
            {issue.refdes && <code>{issue.refdes}</code>}<code>{issue.code}</code></div>
          <p>{issue.explanation}</p>
          <details open={readOnly || undefined}><summary>查看来源定位</summary><EvidenceList evidence={issue.evidence} /></details>
        </li>)}</ul>
      </> : <p className="revision-muted">本次未记录未解决项；这不是电气审查结论。</p>}
    </section>

    <ChangeList key={result.comparison_id} result={result} readOnly={readOnly} />

    <section className="revision-section" aria-labelledby="revision-sources-title">
      <div className="revision-section-heading"><h2 id="revision-sources-title">本次输入凭据</h2><span className="revision-muted">源文件名 / 大小 / SHA-256</span></div>
      <div className="revision-pair"><RevisionSources view={result.before} side="before" /><RevisionSources view={result.after} side="after" /></div>
    </section>
    <section className="revision-section revision-scope" aria-labelledby="revision-scope-title">
      <h2 id="revision-scope-title">声明范围与边界</h2>
      <p>只比较两个版本，不审整板。不判断改动是否正确；不推断未声明的引脚或跨网络影响。</p>
      <ul>{result.scope.map((line, index) => <li key={index}>{line}</li>)}</ul>
    </section>
  </div>;
}
