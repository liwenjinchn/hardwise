import { useMemo, useState } from "react";
import type { ComparisonResult, RevisionChange } from "../generated/workbench-contracts";
import { NetworkDetails, networksForChange, ObservationDetail, observationText } from "./Evidence";
import { filterChanges, KIND_LABELS, type ChangeFilter } from "./state";

/** A same-named net can still gain or lose members; never display it as unchanged. */
function previewText(change: RevisionChange, side: "before" | "after") {
  const text = observationText(change[side]);
  const sameNames = JSON.stringify(change.before?.values) === JSON.stringify(change.after?.values);
  if (change.kind !== "connection_changed" || !sameNames) return text;
  return `${text} · 端点成员变化`;
}

export function ChangeRow({ change, result, expanded = false }: {
  change: RevisionChange; result: ComparisonResult; expanded?: boolean;
}) {
  const connection = change.kind === "connection_changed" || change.kind === "net_renamed";
  return <details className={`revision-change revision-kind-${change.kind}`} open={expanded || undefined}>
    <summary>
      <span className="revision-change-kind">{KIND_LABELS[change.kind]}</span>
      <span className="revision-change-identity"><strong className="revision-mono">{change.refdes || "网络"}{change.pin ? `.${change.pin}` : ""}</strong>
        <small>{change.field}</small></span>
      <span className="revision-preview revision-before"><small>旧版</small><code>{previewText(change, "before")}</code></span>
      <span className="revision-preview revision-after"><small>新版</small><code>{previewText(change, "after")}</code></span>
      <span className="revision-expand" aria-hidden="true">＋</span>
    </summary>
    <div className="revision-change-body">
      <p>{change.explanation}</p>
      <p className="revision-muted revision-mono">记录 ID：{change.id}</p>
      <div className="revision-pair">
        {(["before", "after"] as const).map(side => <section key={side} className={`revision-side revision-${side}`}>
          <h4>{side === "before" ? "旧版" : "新版"} · 声明值与来源</h4>
          <ObservationDetail observation={change[side]} />
          {connection && <><h4>实际网络与端点</h4>
            <NetworkDetails networks={networksForChange(change, result[side], side)} refdes={change.refdes} />
          </>}
        </section>)}
      </div>
      {connection && <div className="revision-boundary">
        <p>相关器件线索（接口记录 {change.related_count} 个）：<span className="revision-mono">{change.related_refdes.join("、") || "未提供"}</span></p>
        <p>仅直接同网，不是完整电气影响。上方端点逐侧读取实际网络声明；未声明引脚不等于开路。</p>
      </div>}
    </div>
  </details>;
}

export function ChangeList({ result, readOnly = false }: { result: ComparisonResult; readOnly?: boolean }) {
  const [kind, setKind] = useState<ChangeFilter>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const filtered = useMemo(() => filterChanges(result.changes, kind, query), [result.changes, kind, query]);
  const changes = readOnly ? result.changes : filtered.slice(0, page * 50);
  return <section className="revision-section" aria-labelledby="revision-changes-title">
    <div className="revision-section-heading">
      <div><span className="revision-kicker">逐项前后对照</span><h2 id="revision-changes-title">变化明细 <small>{result.changes.length} 项</small></h2></div>
      {!readOnly && <label className="revision-search">位号搜索
        <input type="search" value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} placeholder="输入位号" />
      </label>}
    </div>
    {!readOnly && <>
      <div className="revision-filters" role="group" aria-label="按变化种类过滤">
        {(["all", ...Object.keys(KIND_LABELS)] as ChangeFilter[]).map(value => <button type="button" key={value}
          aria-pressed={kind === value} onClick={() => { setKind(value); setPage(1); }}>
          {value === "all" ? "全部" : KIND_LABELS[value]}
          <span>{value === "all" ? result.changes.length : result.changes.filter(change => change.kind === value).length}</span>
        </button>)}
      </div>
      <p className="revision-list-hint" role="status">匹配 {filtered.length} 项 · 点击条目展开声明值、文件哈希与定位</p>
    </>}
    <div className="revision-change-list">{changes.map(change => <ChangeRow key={change.id} change={change} result={result} expanded={readOnly} />)}</div>
    {!changes.length && <p className="revision-empty">{result.changes.length ? "没有匹配的变化。请调整种类或位号搜索。" : "本次没有可列出的确定性变化；仍须查看未解决项与声明范围。"}</p>}
    {!readOnly && filtered.length > changes.length && <button className="revision-button revision-load-more" type="button" onClick={() => setPage(value => value + 1)}>
      再显示 50 项（已显示 {changes.length} / {filtered.length}）
    </button>}
  </section>;
}
