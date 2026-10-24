import type { SavedProjectCatalog, SavedProjectView } from "./generated/workbench-contracts";
import type { WorkbenchState } from "./types";

async function projectRequest<T>(path: string, method = "GET"): Promise<T> {
  if (window.__HARDWISE_OFFLINE_SNAPSHOT__) throw new Error("离线报告不能保存或打开本地项目，请启动本地工作台。");
  const response = await fetch(path, { method });
  if (!response.ok) {
    let message = `${response.status} 项目操作失败`;
    try { const body = await response.json(); message = String(body.detail ?? message); } catch { /* Keep status when server response has no JSON. */ }
    throw new Error(message);
  }
  return await response.json() as T;
}

export function listSavedProjects(): Promise<SavedProjectCatalog> {
  return projectRequest("/api/workbench/projects");
}

function runQuery(run: string | null | undefined): string {
  if (!run) throw new Error("当前没有服务运行，请刷新工作台。");
  return new URLSearchParams({ expected_run_id: run }).toString();
}

export function saveCurrentProject(run: string | null | undefined): Promise<SavedProjectView> {
  return projectRequest(`/api/workbench/projects/save?${runQuery(run)}`, "POST");
}

export function openSavedProject(id: string, run: string | null | undefined): Promise<WorkbenchState> {
  return projectRequest(`/api/workbench/projects/${encodeURIComponent(id)}/open?${runQuery(run)}`, "POST");
}
