import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { makeEvidencePackage } from "../testing/fixtures";
import { EvidencePackageDashboard } from "./EvidencePackageDashboard";

describe("EvidencePackageDashboard", () => {
  it("renders six independent lanes with explicit metrics and trust boundaries", () => {
    const html = renderToStaticMarkup(
      <EvidencePackageDashboard summary={makeEvidencePackage()} />
    );

    expect(html.match(/class="evidence-lane-card /g)).toHaveLength(6);
    for (const label of [
      "Netlist / PST registry",
      "BOM identity",
      "Profile + deterministic validation",
      "Public document index",
      "Capture pin-table evidence",
      "Review-package artifacts"
    ]) {
      expect(html).toContain(label);
    }
    expect(html).toContain("identity gaps");
    expect(html).toContain("24 / 25");
    expect(html).toContain("refdes");
    expect(html).toContain("bom:mixed_controller_power_stage_bom.csv");
    expect(html).toContain("Resolve the remaining identity gap.");
    expect(html).toContain("BOM matching proves refdes identity consistency, not part suitability.");
    expect(html).toContain("not available");
    expect(html).toContain("coverage only");
    expect(html).toContain("不合并为 overall score，也不作为电气签核");
    expect(html).not.toContain("100%");
  });

  it("keeps local observations separate from original delivery and ignores legacy ready", () => {
    const summary = makeEvidencePackage();
    summary.source_audit = { status: "observed", observed_at: "2026-10-24T12:00:00Z",
      missing_tokens: [], locally_present_tokens: ["datasheet:synthetic.pdf#p1"], unchecked_tokens: [], reason: "仅核对路径存在" };
    summary.original_delivery = { status: "not_attached", cited_tokens: ["datasheet:synthetic.pdf#p1"],
      attached_tokens: [], missing_tokens: ["datasheet:synthetic.pdf#p1"], export_allowed: true, reason: "未附带原文" };
    const html = renderToStaticMarkup(<EvidencePackageDashboard summary={summary} />);
    expect(html).toContain("来源核对 · 生成时观察");
    expect(html).toContain("原文随附 · 未附带 PDF 原文");
    expect(html).toContain("datasheet:synthetic.pdf#p1");
    expect(html).toContain("允许导出");
    expect(html).not.toContain("交付证据可复核");
    const legacy = { ...summary };
    delete (legacy as Partial<typeof summary>).bom_quantity_conflicts;
    delete (legacy as Partial<typeof summary>).source_audit;
    delete (legacy as Partial<typeof summary>).original_delivery;
    const oldHtml = renderToStaticMarkup(<EvidencePackageDashboard summary={legacy} />);
    expect(oldHtml).toContain("旧报告未记录原文随附状态");
    expect(oldHtml).toContain("当前报告未记录数量列核对结果");
    expect(oldHtml).not.toContain("交付证据可复核");
  });

  it("provides accessible names for status and metric values", () => {
    const html = renderToStaticMarkup(
      <EvidencePackageDashboard summary={makeEvidencePackage()} />
    );

    expect(html).toContain('aria-label="六条证据覆盖 lane"');
    expect(html).toContain('aria-label="Status: identity gaps"');
    expect(html).toContain('aria-label="Matched refdes: 24 of 25 refdes"');
  });
});
