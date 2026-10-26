import type { VoltageBatchRequest, VoltageCandidatesRequest, VoltageReviewResponse } from "./generated/workbench-contracts";

export class VoltageReviewError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function request(path: string, body?: VoltageBatchRequest | VoltageCandidatesRequest): Promise<VoltageReviewResponse> {
  let response: Response;
  try { response = await fetch(`/api/workbench/voltage-review${path}`, {
    method: body ? "POST" : "GET", headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {})
  }); } catch { throw new VoltageReviewError(0, "连接中断，提交结果尚未确认。请刷新候选核对保存记录，勿直接重复提交。"); }
  if (!response.ok) throw new VoltageReviewError(response.status, response.status === 409
    ? "项目、运行或候选已变化。草稿已保留；请刷新候选、重新核对后提交。"
    : "未发布本次修改，原活动项目保留。请核对候选、确认人和理由后重试。");
  return response.json() as Promise<VoltageReviewResponse>;
}
export function fetchVoltageReview(): Promise<VoltageReviewResponse | null> {
  const snapshot = window.__HARDWISE_OFFLINE_SNAPSHOT__;
  return snapshot ? Promise.resolve(snapshot.voltage_review ?? null) : request("");
}
function requireLive() {
  if (window.__HARDWISE_OFFLINE_SNAPSHOT__) throw new Error("离线报告只读，不能修改候选或确认事实。");
}
export function confirmVoltageReview(body: VoltageBatchRequest) { requireLive(); return request("/confirm", body); }
export function editVoltageCandidates(body: VoltageCandidatesRequest) { requireLive(); return request("/candidates", body); }
