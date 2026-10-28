import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ComparisonResult, RevisionChange } from "../generated/workbench-contracts";
import { ChangeRow } from "./ChangeList";
import { buildComparisonHtml } from "./report";
import { compareReducer, filterChanges, initialState, validateFile, type CompareState } from "./state";

const evidence = [{ file: "<img src=x onerror=alert(1)>.net", locator: "line 3; <script>alert(1)</script>", sha256: "a".repeat(64) }];
const observation = { state: "known", values: ["<script>alert(1)</script>"], evidence };
const view = {
  label: "旧版", component_count: 1, net_count: 1, bom_row_count: 1,
  sources: [{ file: "<b>.net</b>", role: "netlist", sha256: "b".repeat(64), size_bytes: 10 }],
  networks: [{ name: "VCC", ambiguous: false, evidence, endpoints: [{ refdes: "U1", pin: "1" }] }]
};
const change = {
  id: "change-1", kind: "connection_changed", refdes: "U1", pin: "1", field: "pin.connection",
  before: observation, after: observation, explanation: "<script>alert(1)</script>",
  related_refdes: ["R1"], related_count: 1
} as unknown as RevisionChange;
const result = {
  schema_version: "hardwise.revision.v1", comparison_id: "id", status: "needs_review",
  electrical_verdict: "not_evaluated", input_format: "telesis_csv_v1",
  before: { ...view }, after: { ...view, label: "新版" },
  summary: { added: 0, removed: 0, attribute_changes: 0, connection_changes: 1, net_renames: 0,
    changed_components: 1, unresolved: 0, unchanged_components: 0 },
  changes: [change], issues: [{ side: "both", code: "x", refdes: null, explanation: "<script>alert(1)</script>", evidence }],
  scope: ["<script>alert(1)</script>"]
} as unknown as ComparisonResult;

describe("revision comparison client", () => {
  it("clears prior results when an input changes and ignores stale responses", () => {
    const running = compareReducer(initialState, { type: "start", requestId: 2, source: "files" });
    const stale = compareReducer(running, { type: "success", requestId: 1, result });
    expect(stale).toEqual(running);
    const changed = compareReducer({ ...running, result }, {
      type: "file", key: "before_bom", file: null, error: "bad"
    } as Parameters<typeof compareReducer>[1]);
    expect(changed.result).toBeNull();
    expect(changed.fileErrors.before_bom).toBe("bad");
    expect(changed.notice).toContain("旧结果已清除");
  });

  it("validates only the four first-slice formats and size bounds", () => {
    expect(validateFile("before_netlist", { name: "A.NET", size: 1 })).toBeNull();
    expect(validateFile("after_bom", { name: "b.TSV", size: 1 })).toBeNull();
    expect(validateFile("after_netlist", { name: "board.dsn", size: 1 })).toContain(".net");
    expect(validateFile("before_bom", { name: "b.csv", size: 0 })).toContain("为空");
    expect(validateFile("before_bom", { name: "b.csv", size: 10 * 1024 * 1024 + 1 })).toContain("10 MiB");
  });

  it("filters by kind and refdes without changing server results", () => {
    expect(filterChanges([change], "connection_changed", "u1")).toHaveLength(1);
    expect(filterChanges([change], "attribute_changed", "u1")).toHaveLength(0);
    expect(filterChanges([change], "all", "r9")).toHaveLength(0);
  });

  it("labels a same-name membership change instead of showing an unchanged pin", () => {
    const html = renderToStaticMarkup(<ChangeRow change={change} result={result} />);
    expect(html).toContain("端点成员变化");
    expect(html).toContain("U1.1");
  });

  it("escapes source-controlled text in the offline report and embeds no executable data", () => {
    const state = { ...initialState, result } as CompareState;
    expect(state.result).not.toBeNull();
    const html = buildComparisonHtml(result);
    expect(html).not.toContain("<script>alert(1)</script>");
    expect(html).not.toContain("<img src=x");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).toContain("不评估电气正确性");
    expect(html.match(/<script/g) ?? []).toHaveLength(0);
  });
});
