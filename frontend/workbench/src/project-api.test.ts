import { afterEach, expect, it, vi } from "vitest";
import { listSavedProjects, openSavedProject, saveCurrentProject, downloadProjectBackup, restoreProjectBackup } from "./project-api";

afterEach(() => vi.unstubAllGlobals());

it("offline saved-project operations perform no fetch", async () => {
  vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} });
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  await expect(listSavedProjects()).rejects.toThrow("离线报告");
  await expect(saveCurrentProject("run")).rejects.toThrow("离线报告");
  await expect(openSavedProject("id", "run")).rejects.toThrow("离线报告");
  await expect(downloadProjectBackup("run")).rejects.toThrow("离线报告");
  await expect(restoreProjectBackup(new File(["ZIP"], "backup.zip"), "run")).rejects.toThrow("离线报告");
  expect(fetch).not.toHaveBeenCalled();
});

it("saved mutations carry the current run and encoded saved id", async () => {
  vi.stubGlobal("window", {});
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}", { status: 200 })));
  vi.stubGlobal("fetch", fetch);
  await saveCurrentProject("run/1"); await openSavedProject("id/2", "run/1");
  expect(fetch.mock.calls[0]).toEqual(["/api/workbench/projects/save?expected_run_id=run%2F1", { method: "POST" }]);
  expect(fetch.mock.calls[1][0]).toBe("/api/workbench/projects/id%2F2/open?expected_run_id=run%2F1");
});

it("catalog failures keep the server diagnostic", async () => {
  vi.stubGlobal("window", {});
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"detail":"catalog unavailable"}', { status: 503 })));
  await expect(listSavedProjects()).rejects.toThrow("catalog unavailable");
});


it("backup retains binary bytes and restore uploads multipart with the current run", async () => {
  vi.stubGlobal("window", {});
  const fetch = vi.fn().mockResolvedValueOnce(new Response(new Uint8Array([80, 75, 3, 4]), { status: 200, headers: { "X-Hardwise-Backup-Unowned-Projects": "2" } })).mockResolvedValueOnce(new Response('{}', { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  const backup = await downloadProjectBackup("current");
  expect([...new Uint8Array(await backup.blob.arrayBuffer())]).toEqual([80, 75, 3, 4]);
  expect(backup.sourceUnownedCount).toBe(2);
  await restoreProjectBackup(new File([backup.blob], "original.zip"), "current");
  expect(fetch.mock.calls[1][0]).toBe("/api/workbench/projects/restore?expected_run_id=current");
  const init = fetch.mock.calls[1][1] as RequestInit;
  expect(init.body).toBeInstanceOf(FormData);
  expect((init.body as FormData).get("archive")).toBeInstanceOf(File);
  expect(init.headers).toBeUndefined();
});
