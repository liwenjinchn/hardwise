import type { ComparisonResult } from "../generated/workbench-contracts";
import { UPLOAD_KEYS, validateFile, type UploadFiles } from "./state";

async function readResult(response: Response): Promise<ComparisonResult> {
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (typeof body.detail?.message === "string") detail = body.detail.message;
      else if (typeof body.message === "string") detail = body.message;
    } catch { /* HTML/proxy failures must not become report content. */ }
    const hint = response.status === 413 ? "单文件不能超过 10 MiB。" :
      response.status === 404 ? "当前服务未提供改版对比接口，请启动改版对比服务。" : "请核对网表和 BOM 格式后重试。";
    throw new Error(`对比请求失败（HTTP ${response.status}）。${detail || hint}`);
  }
  let result: ComparisonResult;
  try { result = await response.json(); }
  catch { throw new Error("服务未返回有效 JSON；请确认已连接改版对比服务。"); }
  if (!result || result.schema_version !== "hardwise.revision.v1" ||
    result.electrical_verdict !== "not_evaluated" || result.input_format !== "telesis_csv_v1" ||
    typeof result.comparison_id !== "string" ||
    !["differences", "no_observed_difference", "needs_review"].includes(result.status) ||
    !result.summary || !Array.isArray(result.before?.sources) || !Array.isArray(result.after?.sources) ||
    !Array.isArray(result.before?.networks) || !Array.isArray(result.after?.networks) ||
    !Array.isArray(result.changes) || !Array.isArray(result.issues) || !Array.isArray(result.scope)) {
    throw new Error("对比结果契约不匹配，请确认前后端版本一致。");
  }
  return result;
}

export async function compareFiles(files: UploadFiles, signal?: AbortSignal): Promise<ComparisonResult> {
  const body = new FormData();
  for (const key of UPLOAD_KEYS) {
    const file = files[key];
    if (!file) throw new Error("请先选择旧版和新版的网表、BOM，共四个文件。");
    const error = validateFile(key, file);
    if (error) throw new Error(`${file.name}：${error}`);
    body.append(key, file);
  }
  return readResult(await fetch("/api/compare", { method: "POST", body, signal }));
}

export async function loadDemo(signal?: AbortSignal): Promise<ComparisonResult> {
  return readResult(await fetch("/api/compare/demo", { method: "GET", cache: "no-store", signal }));
}
