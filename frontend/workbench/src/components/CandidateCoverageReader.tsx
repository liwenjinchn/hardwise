import type { CandidateRecord } from "../generated/workbench-contracts";

export function CandidateCoverageReader({ records, catalogVersion }: {
  records?: CandidateRecord[] | null;
  catalogVersion?: string;
}) {
  if (!records) return <p>此清单未记录目录候选，不使用当前结果补造历史。</p>;
  const complete = records.filter(r => r.result === "PASS" || r.result === "FAIL").length;
  const unknown = records.filter(r => r.result === "UNKNOWN").length;
  const na = records.filter(r => r.result === "NOT_APPLICABLE").length;
  const unexecuted = records.filter(r => !r.executed && r.result === "UNKNOWN").length;
  return <section aria-label="目录候选检查记录">
    <h4>该次运行的目录候选</h4>
    <p>目录 {catalogVersion ?? "未记录版本"}；候选 {records.length}，完成 {complete}，未知 {unknown}，不适用 {na}；未知中未执行 {unexecuted}。</p>
    <p>仅为本版本限定规则和分组检查，不代表全部工程检查或整板功能。</p>
    <details><summary>逐项核对候选、适用性和执行结果</summary>
      {records.map(r => <details key={r.candidate_id}>
        <summary>{r.object_id} · {r.rule_id} · {r.result}{!r.executed && r.result === "UNKNOWN" ? " · 未执行" : ""}</summary>
        <p>对象：{r.object_kind} / {r.object_id}；实例：{r.instance.map(([k, v]) => `${k}=${v}`).join(" / ")}</p>
        <p>适用性：{r.applicability}；{r.applicability_reason}</p>
        <p>{r.reason}</p><p>候选标识：{r.candidate_id}</p>
      </details>)}
    </details>
  </section>;
}
