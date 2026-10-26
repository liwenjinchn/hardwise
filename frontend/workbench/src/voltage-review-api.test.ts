import { afterEach, expect, it, vi } from "vitest";
import { confirmVoltageReview, editVoltageCandidates, fetchVoltageReview, VoltageReviewError } from "./voltage-review-api";
import type { VoltageBatchRequest, VoltageCandidatesRequest } from "./generated/workbench-contracts";
afterEach(() => vi.unstubAllGlobals());
it("reads the embedded offline candidate ledger without any fetch", async () => {
  const fetch = vi.fn(); const review = { editable: false, review: { candidates: ["sentinel"] } };
  vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: { voltage_review: review } }); vi.stubGlobal("fetch", fetch);
  expect(await fetchVoltageReview()).toBe(review); expect(fetch).not.toHaveBeenCalled();
});
it("keeps old offline reports readable when they lack the new view", async () => {
  vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} }); expect(await fetchVoltageReview()).toBeNull();
});
it("rejects both offline mutation routes before network access", () => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch); vi.stubGlobal("window", { __HARDWISE_OFFLINE_SNAPSHOT__: {} });
  expect(() => confirmVoltageReview({} as VoltageBatchRequest)).toThrow("离线报告只读");
  expect(() => editVoltageCandidates({} as VoltageCandidatesRequest)).toThrow("离线报告只读"); expect(fetch).not.toHaveBeenCalled();
});
it("does not retry or silently rebase a stale confirmation", async () => {
  vi.stubGlobal("window", {}); const fetch = vi.fn().mockResolvedValue({ ok: false, status: 409 }); vi.stubGlobal("fetch", fetch);
  await expect(confirmVoltageReview({ expected_run_id: "old" } as VoltageBatchRequest)).rejects.toMatchObject({ status: 409 }); expect(fetch).toHaveBeenCalledTimes(1);
});
it("treats a lost response as an uncertain outcome requiring refresh", async () => {
  vi.stubGlobal("window", {}); const fetch = vi.fn().mockRejectedValue(new TypeError("lost")); vi.stubGlobal("fetch", fetch);
  await expect(editVoltageCandidates({} as VoltageCandidatesRequest)).rejects.toBeInstanceOf(VoltageReviewError); expect(fetch).toHaveBeenCalledTimes(1);
});
it("sends only explicit caller metadata and selections", async () => {
  vi.stubGlobal("window", {}); const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ revision: "new" }) }); vi.stubGlobal("fetch", fetch);
  const body: VoltageBatchRequest = { expected_run_id: "old", expected_project_id: "project", expected_revision: "a".repeat(64), reviewer: "operator", reason: "explicit unknown", selections: [{ net: "P", mode: "dc", action: "unknown", candidate_id: null, expected_scope_sha256: "b".repeat(64) }] };
  expect(await confirmVoltageReview(body)).toEqual({ revision: "new" }); expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(body);
});
