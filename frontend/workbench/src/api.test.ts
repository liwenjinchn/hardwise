import { afterEach, describe, expect, it, vi } from "vitest";
import { importWorkbench, rerunWorkbench, updateReviewDecision } from "./api";

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
      reason: "fixture defect retained"
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workbench/review-decisions");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({
      stable_keys: ["component_check|U12|buck_inductor|-|L1"],
      status: "waived",
      reason: "fixture defect retained"
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
