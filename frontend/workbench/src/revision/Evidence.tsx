import type { NetworkView, Observation, RevisionChange, RevisionView, SourceEvidence } from "../generated/workbench-contracts";
import { fileSize } from "./state";

export function EvidenceList({ evidence }: { evidence: SourceEvidence[] }) {
  if (!evidence.length) return <p className="revision-muted">此项未提供来源定位。</p>;
  return <ul className="revision-evidence">{evidence.map((item, index) => <li key={index}>
    <span>{item.file}</span><span className="revision-mono">{item.locator}</span>
    <span className="revision-hash">SHA-256 <code>{item.sha256}</code></span>
  </li>)}</ul>;
}

export function observationText(observation: Observation | null): string {
  if (!observation) return "无此侧记录";
  if (observation.state === "missing") return "未声明";
  if (!observation.values.length) return observation.state === "ambiguous" ? "存在歧义" : "空值";
  return `${observation.state === "ambiguous" ? "存在歧义：" : ""}${observation.values.join(" / ")}`;
}

export function ObservationDetail({ observation }: { observation: Observation | null }) {
  if (!observation) return <p className="revision-muted">无此侧记录，不推断电气状态。</p>;
  return <>
    <p className={`revision-observation-state ${observation.state === "ambiguous" ? "revision-warning-text" : ""}`}>
      {{ known: "已声明", missing: "未声明", ambiguous: "存在歧义，不选取单一值" }[observation.state]}
    </p>
    {observation.values.length ? <ul className="revision-values">{observation.values.map((value, i) =>
      <li key={i}><code>{value || "（空字符串）"}</code></li>)}</ul> : <p className="revision-muted">未提供值；不等于开路。</p>}
    <EvidenceList evidence={observation.evidence} />
  </>;
}

// Use actual side-specific networks, never reconstruct endpoints from related_refdes.
export function networksForChange(change: RevisionChange, view: RevisionView, side: "before" | "after"): NetworkView[] {
  if (change.kind === "connection_changed") {
    return view.networks.filter(net => net.endpoints.some(endpoint =>
      endpoint.refdes === change.refdes && endpoint.pin === change.pin));
  }
  if (change.kind === "net_renamed") {
    const names = change[side]?.values ?? [];
    return view.networks.filter(net => names.includes(net.name));
  }
  return [];
}

export function NetworkDetails({ networks, refdes }: { networks: NetworkView[]; refdes: string }) {
  if (!networks.length) return <p className="revision-muted">此侧无可定位的网络声明；不表示开路。</p>;
  return <div className="revision-networks">{networks.map((net, index) => {
    const related = [...new Set(net.endpoints.map(endpoint => endpoint.refdes).filter(value => value !== refdes))];
    return <section key={index} className="revision-network">
      <h4><code>{net.name}</code>{net.ambiguous && <span className="revision-warning-text"> · 网络声明存在歧义</span>}</h4>
      <p className="revision-muted">实际端点 · {net.endpoints.length}</p>
      <ul className="revision-endpoints">{net.endpoints.map((endpoint, i) => <li key={i}>
        <code>{endpoint.refdes}.{endpoint.pin}</code>
      </li>)}</ul>
      <p>直接同网器件：<span className="revision-mono">{related.join("、") || "无其他已声明器件"}</span></p>
      <EvidenceList evidence={net.evidence} />
    </section>;
  })}</div>;
}

export function RevisionSources({ view, side }: { view: RevisionView; side: "before" | "after" }) {
  return <section className={`revision-side revision-${side}`}>
    <h3>{side === "before" ? "旧版" : "新版"}输入<span>{view.label === (side === "before" ? "旧版" : "新版") ? "" : ` · ${view.label}`}</span></h3>
    <p className="revision-muted">{view.component_count} 个器件 · {view.net_count} 个网络 · {view.bom_row_count} 行 BOM</p>
    <ul className="revision-sources">{view.sources.map((source, index) => <li key={index}>
      <strong>{source.role === "netlist" ? "网表" : "BOM"}</strong> <span>{source.file}</span>
      <small>{fileSize(source.size_bytes)}</small>
      <span className="revision-hash">SHA-256 <code>{source.sha256}</code></span>
    </li>)}</ul>
  </section>;
}
