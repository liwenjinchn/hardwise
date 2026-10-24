import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BomQuantityWarnings } from "./BomQuantityWarnings";

describe("BOM quantity warnings", () => {
  it("preserves each declared quantity and separates it from electrical results", () => {
    const html = renderToStaticMarkup(<BomQuantityWarnings conflicts={[{
      item_number: "1", refdes_list: ["C1"], source_file: "public.csv", source_line: 2,
      source_fields: [{ column: 2, name: "Quantity", value: "1" }, { column: 3, name: "Qty", value: "99" }]
    }]} />);
    for (const text of ["数量未确认", "public.csv#line2", "column2", "Quantity=1", "column3", "Qty=99", "独立电气判定不因此改变"]) {
      expect(html).toContain(text);
    }
  });
  it("adds no warning when the report has no conflicting declarations", () => {
    expect(renderToStaticMarkup(<BomQuantityWarnings conflicts={[]} />)).toBe("");
  });
});
