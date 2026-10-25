import type { AIConsent } from "../useAIConsent";

export function AIDisclosureNotice({ consent }: { consent: AIConsent }) {
  const current = consent.descriptor;
  return <section className="ai-disclosure" aria-label="AI 发送说明">
    <strong>{current?.mode === "real" ? "发送前确认 · 当前页面有效" : "AI 模式与发送边界"}</strong>
    {!current && <p>尚未取得发送说明，暂不发送问题。</p>}
    {current && <>
      {current.mode === "real" && <>
        <p>配置接收地址：<code>{current.destination ?? "不可用"}</code></p>
        <p>模型标识：<code>{current.model ?? "不可用"}</code>（配置值，不证明实际模型品牌）</p>
        <ul>{current.data_categories.map(item => <li key={item}>{item}</li>)}</ul>
      </>}
      <p>{current.notice}</p>
      {current.mode === "real" && current.available && <label>
        <input type="checkbox" checked={consent.confirmed} onChange={event => consent.acknowledge(event.target.checked)} />
        我已了解，允许本页面将上述内容发往该服务
      </label>}
      {current.mode === "real" && <p>刷新、切换项目或接收配置变化后需重新确认。确认不代表工程批准。</p>}
    </>}
    {consent.error && <p role="alert">{consent.error}</p>}
    <button type="button" onClick={() => { void consent.refresh().catch(() => {}); }}>刷新发送说明</button>
  </section>;
}
