import { afterEach, describe, expect, it, vi } from "vitest";
import { importWorkbench } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
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
