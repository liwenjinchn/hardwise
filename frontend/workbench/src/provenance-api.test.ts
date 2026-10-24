import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchRunProvenance } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("run provenance downloads", () => {
  it("scopes a historical run and retains its explicit missing-record response", async () => {
    const payload = { project_id: "project /one", run_id: "run /two", status: "not_recorded", provenance: null };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)));
    vi.stubGlobal("window", {}); vi.stubGlobal("fetch", fetcher);
    expect(await fetchRunProvenance(payload.project_id, payload.run_id)).toEqual(payload);
    const url = new URL(fetcher.mock.calls[0][0], "http://localhost");
    expect(url.pathname).toBe("/api/workbench/review-runs/run%20%2Ftwo/provenance");
    expect(url.searchParams.get("expected_project_id")).toBe(payload.project_id);
  });

  it("rejects a mismatched response rather than downloading another project's evidence", async () => {
    vi.stubGlobal("window", {});
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ project_id: "other", run_id: "run" }))));
    await expect(fetchRunProvenance("project", "run")).rejects.toThrow("清单所属项目或运行已变化");
  });

  it("uses embedded export evidence without contacting a server or inventing a service run", async () => {
    const provenance = { raw_inputs_archived: false, inputs: { readset_sha256: "original" } };
    const fetcher = vi.fn();
    vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {
      run_provenance: provenance, state: { project: { generated_at: "export time" } }
    } }); vi.stubGlobal("fetch", fetcher);
    expect(await fetchRunProvenance(null, null)).toEqual({ origin: "offline_export", exported_at: "export time", provenance });
    await expect(fetchRunProvenance("project", "historical")).rejects.toThrow("该历史运行清单");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("downloads captured historical manifests and refuses project/run mismatches offline", async () => {
    const record = { project_id: "one", run_id: "old", status: "not_recorded", provenance: null };
    vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: { review_history: {
      project_id: "one", run_provenance: { old: record }
    } } });
    const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
    expect(await fetchRunProvenance("one", "old")).toEqual(record);
    await expect(fetchRunProvenance("two", "old")).rejects.toThrow("项目不匹配");
    await expect(fetchRunProvenance("one", "absent")).rejects.toThrow("未包含");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("reports old offline evidence as missing and preserves server failures", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("temporarily unavailable", { status: 503 }));
    vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} }); vi.stubGlobal("fetch", fetcher);
    await expect(fetchRunProvenance(null, null)).rejects.toThrow("旧离线快照未记录");
    expect(fetcher).not.toHaveBeenCalled();
    vi.stubGlobal("window", {});
    await expect(fetchRunProvenance("project", "run")).rejects.toThrow("temporarily unavailable");
  });
});
