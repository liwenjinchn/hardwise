import { afterEach, expect, it, vi } from "vitest";
import { fetchExcerpts, saveExcerpt } from "./excerpt-api";
import type { ExcerptRequest } from "./generated/workbench-contracts";
afterEach(() => vi.unstubAllGlobals());
function setup() { vi.stubGlobal("window", {}); const fetch = vi.fn(); vi.stubGlobal("fetch", fetch); return fetch; }
it("offline makes no network request for reads or writes", async () => {
  const fetch = setup(); vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} });
  expect(await fetchExcerpts()).toBeNull();
  await expect(saveExcerpt({} as ExcerptRequest)).rejects.toMatchObject({ status: 400 });
  expect(fetch).not.toHaveBeenCalled();
});
it.each([409, 422, 500])("preserves failure status %s without retry", async status => {
  const fetch = setup(); fetch.mockResolvedValue({ ok: false, status });
  await expect(saveExcerpt({} as ExcerptRequest)).rejects.toMatchObject({ status });
  expect(fetch).toHaveBeenCalledTimes(1);
});
it("network failure has unknown outcome and is never retried", async () => {
  const fetch = setup(); fetch.mockRejectedValue(new Error("network"));
  await expect(saveExcerpt({} as ExcerptRequest)).rejects.toMatchObject({ status: 0 });
  expect(fetch).toHaveBeenCalledTimes(1);
});
it("malformed success body is unknown outcome", async () => {
  const fetch = setup(); fetch.mockResolvedValue({ ok: true, json: () => Promise.reject(new Error("bad JSON")) });
  await expect(saveExcerpt({} as ExcerptRequest)).rejects.toMatchObject({ status: 0 });
});
it("submits the exact expected revision and manual declaration", async () => {
  const fetch = setup(); fetch.mockResolvedValue({ ok: true, json: async () => ({ revision: "next" }) });
  const body = { expected_revision: "old", edit: { sharing: "withhold" } } as ExcerptRequest;
  expect(await saveExcerpt(body)).toEqual({ revision: "next" });
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(body);
});
