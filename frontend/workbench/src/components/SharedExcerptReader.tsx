import type { ProvenanceDownload } from "../api";
import { display, excerptRows, record } from "../shared-excerpt-view";

export function SharedExcerptReader({ payload }: { payload: ProvenanceDownload }) {
  const rows = excerptRows(payload);
  return <section className="shared-excerpt-reader" aria-label="运行资料来源与摘录">
    <h4>本次记录中的资料来源</h4>
    <p>仅显示此份分享清单已包含的内容。分享声明不等于电气批准；参数是否适用仍需结合器件身份、条件和复核记录核对。</p>
    {"run_id" in payload && <p>运行：{payload.run_id}</p>}
    {!payload.provenance ? <p>{"reason" in payload ? payload.reason : "该运行未记录清单。"} 不使用当前资料补造历史。</p> : !rows.length ? <p>该清单未记录逐字段来源与摘录，不能据此确认参数。</p> : rows.map(row => <details key={row.key}>
      <summary>{row.part} · {row.refs || "未记录绑定器件"} · {display(row.field.pointer)} · {row.excerpt === null ? "原文已省略" : "含允许分享的原文"}</summary>
      <div className="excerpt-current">
        <p>参数：{display(row.field.value)} {display(row.field.unit)}；对象：{display(row.field.subject)}；角色：{display(row.field.role)}；性质：{display(row.field.nature)}</p>
        <p>厂商：{display(row.identity.manufacturer)}；型号范围：{display(row.identity.part_numbers)}；封装范围：{display(row.identity.packages)}</p>
        <p>来源：{display(row.source.url)}</p>
        <p>版本：{display(row.source.document_revision)}；第 {display(row.source.page)} 页；定位：{display(row.source.locator)}</p>
        <p>文档 SHA256：{display(row.source.document_sha256)}</p>
        <h5>适用条件</h5>
        {Array.isArray(row.field.conditions) ? row.field.conditions.map((c, i) => <p key={i}>{display(record(c).kind)}：{display(record(c).description)}</p>) : <p>未记录</p>}
        <h5>原文摘录</h5>
        {row.excerpt !== null ? <><blockquote>{row.excerpt}</blockquote><p>分享声明人：{display(row.sharing.declared_by)}；时间：{display(row.sharing.declared_at)}；理由：{display(row.sharing.reason)}</p></> : <p>{row.omission}。保留上方来源定位，本地原记录未在此恢复。</p>}
        <p>电气复核历史共 {Array.isArray(row.field.decisions) ? row.field.decisions.length : 0} 条；此阅读页不重新判定批准是否有效。</p>
        <details><summary>内容校验标识</summary><p>原本地档案：{row.originalHash}</p>{row.sharedHash && <p>分享内容：{row.sharedHash}（与原本地内容不同）</p>}</details>
      </div>
    </details>)}
  </section>;
}
