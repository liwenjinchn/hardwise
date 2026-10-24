import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchReviewHistory, importWorkbench, rerunWorkbench, updateReviewDecision } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("review closure API", () => {
  it("posts stable keys, decision, and reason to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ review_tasks: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("window", {});
    vi.stubGlobal("fetch", fetchMock);

    await updateReviewDecision({
      stableKeys: ["component_check|U12|buck_inductor|-|L1"],
      status: "waived",
      reason: "fixture defect retained",
      expectedRunId: "current-run"
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workbench/review-decisions");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({
      stable_keys: ["component_check|U12|buck_inductor|-|L1"],
      status: "waived",
      reason: "fixture defect retained",
      expected_run_id: "current-run"
    });
  });

  it("uses the real backend rerun endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ review_tasks: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("window", {});
    vi.stubGlobal("fetch", fetchMock);

    await rerunWorkbench();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workbench/rerun",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("importWorkbench", () => {
  it("posts the optional document index under the backend multipart field name", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("window", {});
    vi.stubGlobal("fetch", fetchMock);
    const netlist = new File(["netlist"], "board.net", { type: "text/plain" });
    const documentIndex = new File(["MPN,URL"], "documents.csv", { type: "text/csv" });

    await importWorkbench({ netlist, documentIndex });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workbench/import");
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect(body.get("netlist")).toBe(netlist);
    expect(body.get("document_index_csv")).toBe(documentIndex);
  });
});


describe("review history API", () => {
  it("requests the selected project's bounded page", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ events: [] }), { status: 200 }));
    vi.stubGlobal("window", {});
    vi.stubGlobal("fetch", fetchMock);
    await fetchReviewHistory("project / one", 20);
    const [url] = fetchMock.mock.calls[0];
    const query = new URL(String(url), "http://localhost").searchParams;
    expect(query.get("expected_project_id")).toBe("project / one");
    expect(query.get("limit")).toBe("20");
    expect(query.get("offset")).toBe("20");
  });

  it("does not query the static server for missing offline history", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} });
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchReviewHistory("one")).rejects.toThrow("离线快照未包含处理历史");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("pages all embedded history without network and rejects a foreign project", async () => {
    const fetcher = vi.fn();
    const events = Array.from({length: 25}, (_, id) => ({ id, decision: { reason: `原始理由${id}` } }));
    vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: { review_history: {
      project_id: "one", run_id: "run", total: 25, events
    } } });
    vi.stubGlobal("fetch", fetcher);
    expect((await fetchReviewHistory("one")).events).toHaveLength(20);
    const second = await fetchReviewHistory("one", 20);
    expect(second.events).toEqual(events.slice(20));
    expect(second.total).toBe(25);
    await expect(fetchReviewHistory("foreign")).rejects.toThrow("不属于当前项目");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("preserves a read failure for the retry UI", async () => {
    vi.stubGlobal("window", {});
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("History temporarily unavailable", { status: 503 })));
    await expect(fetchReviewHistory("one")).rejects.toThrow("History temporarily unavailable");
  });
});
