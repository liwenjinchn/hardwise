import { expect, it } from "vitest";
import type { ProvenanceDownload } from "./api";
import { excerptRows } from "./shared-excerpt-view";
const make = (source: unknown) => ({ provenance: { profile_bindings: { U1: "sha" }, profiles: [{ sha256: "sha", part_number: "Synthetic", values: { field_review: { fields: [{ pointer: "/abs_max/vin", value: 35, unit: "V", source }] } } }] } }) as unknown as ProvenanceDownload;
it("only declared human allowed original appears, with precise binding", () => {
  const rows = excerptRows(make({ excerpt: "synthetic", sharing: { decision: "allow", actor: "human" } }));
  expect(rows[0].excerpt).toBe("synthetic"); expect(rows[0].refs).toBe("U1"); expect(rows[0].field.value).toBe(35);
});
it.each([{}, { decision: "withhold", actor: "human" }, { decision: "allow", actor: "model" }])("old or unpermitted records do not display original", sharing => {
  expect(excerptRows(make({ excerpt: "hidden", sharing }))[0].excerpt).toBeNull();
});
it("omission wins over a conflicting declaration", () => {
  const row = excerptRows(make({ excerpt: "hidden", sharing: { decision: "allow", actor: "human" }, excerpt_delivery: { reason: "stale" } }))[0];
  expect(row.excerpt).toBeNull(); expect(row.omission).toContain("失效");
});
it("missing historical provenance is not replaced with current fields", () => {
  expect(excerptRows({ provenance: null } as ProvenanceDownload)).toEqual([]);
});
it("malformed fields remain readable without inventing values", () => {
  expect(excerptRows(make(null))[0].excerpt).toBeNull();
});
