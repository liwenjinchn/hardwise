import type { ChatResponse } from "../types";

export function ChatBoundary({ response }: { response: ChatResponse }) {
  const label = response.response_kind === "insufficient_evidence"
    ? "本回合未产生新的检查结论"
    : response.response_kind === "offline_notice"
      ? "离线快照提示"
      : "AI 解释 · 参数和推断未经逐项核验，不改变确定性结果或人工决定。";
  return <p className="cop-disclaimer message-boundary">{label}</p>;
}
