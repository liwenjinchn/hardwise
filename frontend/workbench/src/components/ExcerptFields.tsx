import type { ExcerptEdit } from "../generated/workbench-contracts";

export function ExcerptFields({ edit, onChange, needsIdentity }: {
  edit: ExcerptEdit; onChange: (edit: ExcerptEdit) => void; needsIdentity: boolean;
}) {
  const text = (label: string, value: string, set: (value: string) => void, extra = {}) =>
    <label>{label}<input required aria-label={label} value={value} onChange={e => set(e.target.value)} {...extra} /></label>;
  const source = (key: keyof ExcerptEdit["source"], value: string | number) => onChange({ ...edit, source: { ...edit.source, [key]: value } });
  return <>
    {needsIdentity && <fieldset className="voltage-form-grid"><legend>首次录入：器件身份范围</legend>
      {text("摘录厂商", edit.identity?.manufacturer ?? "", v => onChange({ ...edit, identity: { ...edit.identity!, manufacturer: v } }))}
      {text("摘录型号范围（逗号分隔）", edit.identity?.part_numbers.join(", ") ?? "", v => onChange({ ...edit, identity: { ...edit.identity!, part_numbers: v.split(/[,，]/).map(s => s.trim()) as [string, ...string[]] } }))}
      {text("摘录封装范围（逗号分隔）", edit.identity?.packages.join(", ") ?? "", v => onChange({ ...edit, identity: { ...edit.identity!, packages: v.split(/[,，]/).map(s => s.trim()) as [string, ...string[]] } }))}
    </fieldset>}
    <div className="voltage-form-grid">
      {text("来源网址", edit.source.url, v => source("url", v), { type: "url", pattern: "https?://.+" })}
      {text("文档版本", edit.source.document_revision, v => source("document_revision", v))}
      {text("文档 SHA256", edit.source.document_sha256, v => source("document_sha256", v), { pattern: "[a-f0-9]{64}" })}
      <label>页码<input aria-label="摘录页码" required type="number" min="1" step="1" value={edit.source.page || ""} onChange={e => source("page", Number(e.target.value))} /></label>
      {text("表格或段落定位", edit.source.locator, v => source("locator", v))}
      {text("参数单位", edit.unit, v => onChange({ ...edit, unit: v }))}
      <label>参数角色<select aria-label="参数角色" value={edit.role} onChange={e => onChange({ ...edit, role: e.target.value as ExcerptEdit["role"] })}>
        <option value="identity">身份</option><option value="minimum">最小值</option><option value="typical">典型值</option><option value="maximum">最大值</option><option value="definition">定义</option><option value="relationship">关系</option>
      </select></label>
      <label>参数性质<select aria-label="参数性质" value={edit.nature} onChange={e => onChange({ ...edit, nature: e.target.value as ExcerptEdit["nature"] })}>
        <option value="intrinsic">器件固有参数</option><option value="application_recommendation">应用建议</option><option value="board_policy">板级策略</option>
      </select></label>
    </div>
    <label className="excerpt-text">原文摘录<textarea aria-label="原文摘录" required rows={5} value={edit.source.excerpt} onChange={e => source("excerpt", e.target.value)} /></label>
    <fieldset><legend>适用条件（逐项记录，不确定则保留待核）</legend>
      {edit.conditions.map((condition, index) => <div className="voltage-form-grid" key={index}>
        <label>条件类型<select aria-label={`条件类型 ${index + 1}`} value={condition.kind} onChange={e => onChange({ ...edit, conditions: edit.conditions.map((c, i) => i === index ? { ...c, kind: e.target.value as typeof c.kind } : c) as ExcerptEdit["conditions"] })}>
          <option value="unsupported">尚不支持／待核</option><option value="unconditional">无附加条件</option><option value="dc_relation">直流关系</option>
        </select></label>
        {text(`条件说明 ${index + 1}`, condition.description, value => onChange({ ...edit, conditions: edit.conditions.map((c, i) => i === index ? { ...c, description: value } : c) as ExcerptEdit["conditions"] }))}
        <button type="button" className="icon-text-btn" disabled={edit.conditions.length <= 1} onClick={() => onChange({ ...edit, conditions: edit.conditions.filter((_, i) => i !== index) as ExcerptEdit["conditions"] })}>移除条件 {index + 1}</button>
      </div>)}
      <button type="button" className="icon-text-btn" disabled={edit.conditions.length >= 100} onClick={() => onChange({ ...edit, conditions: [...edit.conditions, { kind: "unsupported", description: "" }] })}>添加适用条件</button>
    </fieldset>
    <div className="voltage-form-grid">
      <label>原文分享声明<select aria-label="原文分享声明" value={edit.sharing} onChange={e => onChange({ ...edit, sharing: e.target.value as ExcerptEdit["sharing"] })}>
        <option value="withhold">不允许随分享报告分发</option><option value="allow">我声明允许随分享报告分发</option>
      </select></label>
      {text("摘录声明人", edit.declared_by, v => onChange({ ...edit, declared_by: v }), { maxLength: 256 })}
      {text("摘录声明理由", edit.reason, v => onChange({ ...edit, reason: v }), { maxLength: 2000 })}
    </div>
  </>;
}
