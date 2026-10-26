import type { ExcerptRequest, ExcerptResponse } from "./generated/workbench-contracts";
import { isOfflineWorkbench } from "./api";

export class ExcerptError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function request(body?: ExcerptRequest): Promise<ExcerptResponse> {
  let response: Response;
  try {
    response = await fetch("/api/workbench/excerpts", {
      method: body ? "POST" : "GET", headers: { "Content-Type": "application/json" },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
  } catch { throw new ExcerptError(0, "连接中断，保存结果未确认。草稿保留，请刷新资料核对后再操作。"); }
  if (!response.ok) throw new ExcerptError(response.status, response.status === 409
    ? "项目、运行或来源已变化。草稿保留，请刷新资料并核对新版本。"
    : response.status >= 500 ? "服务异常，保存结果未确认。请刷新核对，勿直接重复提交。"
    : "本次未保存。请检查来源、器件身份、参数条件及声明人；草稿保留。");
  try { return await response.json() as ExcerptResponse; }
  catch { throw new ExcerptError(0, "响应无法读取，保存结果未确认。请刷新核对，勿直接重复提交。"); }
}
export function fetchExcerpts(): Promise<ExcerptResponse | null> {
  return isOfflineWorkbench() ? Promise.resolve(null) : request();
}
export function saveExcerpt(body: ExcerptRequest): Promise<ExcerptResponse> {
  if (isOfflineWorkbench()) return Promise.reject(new ExcerptError(400, "离线报告只读，不能修改摘录。"));
  return request(body);
}
