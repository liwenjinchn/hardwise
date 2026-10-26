import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { ConnectivityReader } from "./ConnectivityReader";

it("keeps conflicting declarations separate and labels them as observations", () => {
  const html = renderToStaticMarkup(<ConnectivityReader projection={{
    schema_version: "hardwise.connectivity.v1",
    declarations: [
      { source: "public.net", line: 4, net_name: "SIG", nodes: [["R1", "1"]] },
      { source: "public.net", line: 5, net_name: "SIG", nodes: [["R2", "1"]] },
      { source: "public.net", line: 6, net_name: "OTHER", nodes: [["R3", "1"]] }
    ],
    resolved_nets: { OTHER: [["R3", "1"]] },
    ambiguous_net_names: ["SIG"], ambiguous_endpoints: [["R1", "1"], ["R2", "1"]],
    ambiguities: [{ kind: "duplicate_net_name", net_names: ["SIG"], endpoints: [], declaration_indices: [0, 1] }]
  }} />);
  expect(html).toContain("R1.1");
  expect(html).toContain("R2.1");
  expect(html.match(/已隔离，成员待核对/g)).toHaveLength(2);
  expect(html).toContain("确定连接");
  expect(html).toContain("不代表开路");
  expect(html).toContain("public.net");
});

it("does not invent old connectivity", () => {
  expect(renderToStaticMarkup(<ConnectivityReader />)).toContain("不使用当前连接补造历史");
});
