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

  it("provides accessible names for status and metric values", () => {
    const html = renderToStaticMarkup(
      <EvidencePackageDashboard summary={makeEvidencePackage()} />
    );

    expect(html).toContain('aria-label="六条证据覆盖 lane"');
    expect(html).toContain('aria-label="Status: identity gaps"');
    expect(html).toContain('aria-label="Matched refdes: 24 of 25 refdes"');
  });
});
