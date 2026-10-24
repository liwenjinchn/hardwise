import type { ProjectRestoreReceipt, SavedProjectCatalog, SavedProjectView } from "./generated/workbench-contracts";
import type { WorkbenchState } from "./types";

async function projectResponse(path: string, init: RequestInit): Promise<Response> {
  if (window.__HARDWISE_OFFLINE_SNAPSHOT__) throw new Error("离线报告不能保存、备份或恢复本地项目，请启动本地工作台。");
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = `${response.status} 项目操作失败`;
    try { const body = await response.json(); message = String(body.detail ?? message); } catch { /* Keep status for non-JSON errors. */ }
    throw new Error(message);
  }
  return response;
}

async function projectRequest<T>(path: string, method = "GET"): Promise<T> {
  return await (await projectResponse(path, { method })).json() as T;
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

export async function downloadProjectBackup(run: string | null | undefined): Promise<{ blob: Blob; sourceUnownedCount: number | null }> {
  const response = await projectResponse(`/api/workbench/projects/backup?${runQuery(run)}`, { method: "POST" });
  const count = response.headers.get("X-Hardwise-Backup-Unowned-Projects");
  return { blob: await response.blob(), sourceUnownedCount: count !== null && /^\d+$/.test(count) ? Number(count) : null };
}

export async function restoreProjectBackup(file: File, run: string | null | undefined): Promise<ProjectRestoreReceipt> {
  const form = new FormData(); form.append("archive", file);
  return await (await projectResponse(`/api/workbench/projects/restore?${runQuery(run)}`, { method: "POST", body: form })).json() as ProjectRestoreReceipt;
}
