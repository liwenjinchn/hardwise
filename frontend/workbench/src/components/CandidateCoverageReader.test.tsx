import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { CandidateCoverageReader } from "./CandidateCoverageReader";

it("keeps missing execution inside unknown and shows its stable identity", () => {
  const html = renderToStaticMarkup(<CandidateCoverageReader catalogVersion="synthetic-v1" records={[
    { candidate_id: "candidate-synthetic", rule_id: "example", object_kind: "pin", object_id: "U1",
      instance: [["pin", "2"]], applicability: "unknown", applicability_reason: "来源缺失",
      executed: false, result: "UNKNOWN", reason: "未执行：来源缺失" },
    { candidate_id: "candidate-na", rule_id: "exempt", object_kind: "pin", object_id: "U1",
      instance: [["pin", "3"]], applicability: "not_applicable", applicability_reason: "明确豁免",
      executed: true, result: "NOT_APPLICABLE", reason: "明确豁免" }
  ]} />);
  expect(html).toContain("候选 2，完成 0，未知 1，不适用 1");
  expect(html).toContain("未知中未执行 1");
  expect(html).toContain("candidate-synthetic");
  expect(html).toContain("pin=2");
  expect(html).toContain("来源缺失");
});

it("does not reconstruct old candidates or claim an empty set passed", () => {
  expect(renderToStaticMarkup(<CandidateCoverageReader />)).toContain("不使用当前结果补造历史");
  const empty = renderToStaticMarkup(<CandidateCoverageReader records={[]} />);
  expect(empty).toContain("候选 0，完成 0");
  expect(empty).not.toContain("100%");
});
