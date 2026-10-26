import type { ChatResponse } from "../types";

export function ChatBoundary({ response }: { response: ChatResponse }) {
  const label = response.response_kind === "insufficient_evidence"
    ? "本回合未产生新的检查结论"
    : response.response_kind === "offline_notice"
      ? "离线快照提示"
      : response.response_kind === "structured_explanation"
        ? "本回合结构化绑定已核对 · 来源和条件仍需工程复核，不授予整板签核。"
      : "AI 解释 · 参数和推断未经逐项核验，不改变确定性结果或人工决定。";
  const review = response.explanation_review;
  return <section className="message-boundary">
    <p className="cop-disclaimer">{label}</p>
    {review && <details className="claim-binding-detail">
      <summary>绑定核对明细 · {review.verified_facts.length} 项匹配 / {review.issues.length} 项未核</summary>
      <p>匹配仅表示与本回合工具返回字段一致，不证明来源独立正确，也不改变机器结果、批准或人工决定。</p>
      {review.error && <p>未展示模型原文：{review.error}</p>}
      {review.verified_facts.map(fact => <article key={fact.id}>
        <strong>{fact.object_id} · {fact.property_key} · {fact.kind}</strong>
        <pre>{JSON.stringify({ value: fact.value, unit: fact.unit, conditions: fact.conditions,
          conditions_status: fact.conditions_status, source_tokens: fact.source_tokens,
          rule_version: fact.rule_version, scope_id: fact.scope_id, call_id: fact.call_id }, null, 2)}</pre>
      </article>)}
      {review.issues.map(issue => <p key={issue.index}>待核声明 {issue.index + 1}：{issue.code}（模型数值与正文未展示）</p>)}
      {review.requests.map((request, index) => <p key={index}>待核补资料建议：{request.object_id} · {request.topic}</p>)}
    </details>}
  </section>;
}
