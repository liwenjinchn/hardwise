import type { BomQuantityColumnConflict } from "../generated/workbench-contracts";

export function BomQuantityWarnings({ conflicts }: { conflicts: BomQuantityColumnConflict[] }) {
  if (!conflicts.length) return null;
  return <section className="bom-quantity-warnings" aria-label="BOM 数量列冲突">
    <strong>BOM 数量列冲突 · 数量未确认</strong>
    <p>不按列顺序选择数量；独立电气判定不因此改变。</p>
    {conflicts.map((item, index) => <div key={index}>
      <p>{item.source_file}#line{item.source_line} · {item.refdes_list.join(", ") || "无位号"}</p>
      <ul>{item.source_fields.map(field => <li key={field.column}>column{field.column} [{field.name}={field.value}]</li>)}</ul>
    </div>)}
  </section>;
}
