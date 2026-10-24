import { afterEach, expect, it, vi } from "vitest";
import { listSavedProjects, openSavedProject, saveCurrentProject } from "./project-api";

afterEach(() => vi.unstubAllGlobals());

it("offline saved-project operations perform no fetch", async () => {
  vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} });
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  await expect(listSavedProjects()).rejects.toThrow("离线报告");
  await expect(saveCurrentProject("run")).rejects.toThrow("离线报告");
  await expect(openSavedProject("id", "run")).rejects.toThrow("离线报告");
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
