import type { ConnectivityProjection } from "../generated/workbench-contracts";

export function ConnectivityReader({ projection }: { projection?: ConnectivityProjection | null }) {
  if (!projection) return <p>此清单未记录连接声明，不使用当前连接补造历史。</p>;
  const blocked = new Set(projection.ambiguous_net_names);
  return <section aria-label="连接声明与隔离范围">
    <h5>连接声明与隔离范围</h5>
    <p>隔离网络 {blocked.size} 个；下面保留原始端点声明，歧义声明不代表确定成员，也不代表开路或 NC。</p>
    {projection.declarations.map((declaration, index) => <details key={index}>
      <summary>{declaration.net_name} · {blocked.has(declaration.net_name) ? "已隔离，成员待核对" : "确定连接"} · 声明 {index + 1}</summary>
      <p>来源：{declaration.source} · 第 {declaration.line} 行</p>
      <p>原始端点声明：{declaration.nodes.map(([ref, pin]) => `${ref}.${pin}`).join("、")}</p>
    </details>)}
  </section>;
}
