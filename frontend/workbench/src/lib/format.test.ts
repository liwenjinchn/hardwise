import { describe, expect, it } from "vitest";
import {
  attentionLabel,
  chainKindLabel,
  documentStatusGroup,
  documentStatusLabel,
  evidenceNodeKind,
  formatSummary,
  pinStatusLabel,
  profileStatusLabel,
  queueSubtitle,
  sourceLabel,
  statusGroup,
  statusLabelFromRaw,
  taskKindLabel
} from "./format";
import { makeChainItem, makeEvidence, makeQueueItem } from "../testing/fixtures";

describe("statusGroup", () => {
  it("maps backend status strings onto the four UI groups", () => {
    expect(statusGroup("ERROR")).toBe("error");
    expect(statusGroup("WARN")).toBe("warn");
    expect(statusGroup("PASS")).toBe("pass");
    expect(statusGroup("manual_needed")).toBe("manual");
    expect(statusGroup("anything-else")).toBe("manual");
  });
});

describe("attentionLabel", () => {
  it("labels every status group in reviewer language", () => {
    expect(attentionLabel("error")).toBe("必须修");
    expect(attentionLabel("warn")).toBe("看证据");
    expect(attentionLabel("manual")).toBe("人工判断");
    expect(attentionLabel("pass")).toBe("已通过");
  });
});

describe("statusLabelFromRaw", () => {
  it("title-cases unknown snake_case statuses", () => {
    expect(statusLabelFromRaw("manual_needed")).toBe("Manual Needed");
    expect(statusLabelFromRaw("ok")).toBe("Ok");
  });
});

describe("pinStatusLabel", () => {
  it("uses the curated Chinese labels for known statuses", () => {
    expect(pinStatusLabel("ERROR")).toBe("必须修");
    expect(pinStatusLabel("bom_missing")).toBe("BOM 缺失");
    expect(pinStatusLabel("profile_missing")).toBe("待补档案");
  });

  it("falls back to title-cased raw status for unknown values", () => {
    expect(pinStatusLabel("foo_bar")).toBe("Foo Bar");
  });
});

describe("profileStatusLabel / documentStatusLabel", () => {
  it("maps known profile statuses", () => {
    expect(profileStatusLabel("ok")).toBe("已匹配");
    expect(profileStatusLabel("exact")).toBe("已匹配");
    expect(profileStatusLabel("ambiguous")).toBe("需确认");
    expect(profileStatusLabel("not_found")).toBe("未匹配");
  });

  it("maps known document statuses", () => {
    expect(documentStatusLabel("matched")).toBe("已索引");
    expect(documentStatusLabel("no_result")).toBe("未命中");
    expect(documentStatusLabel("ambiguous")).toBe("多候选");
    expect(documentStatusLabel("manual_needed")).toBe("需人工匹配");
    expect(documentStatusLabel("not_configured")).toBe("未配置");
  });

  it("groups document statuses onto badge colors", () => {
    expect(documentStatusGroup("matched")).toBe("pass");
    expect(documentStatusGroup("ambiguous")).toBe("warn");
    expect(documentStatusGroup("no_result")).toBe("manual");
    expect(documentStatusGroup("manual_needed")).toBe("manual");
    expect(documentStatusGroup("not_configured")).toBe("manual");
  });

  it("treats empty status as unknown instead of crashing", () => {
    expect(profileStatusLabel("")).toBe("Unknown");
    expect(documentStatusLabel("")).toBe("Unknown");
  });
});

describe("formatSummary", () => {
  it("translates exact deterministic check sentences", () => {
    expect(
      formatSummary("Exactly one local profile part_number matched this BOM identity.")
    ).toBe("已唯一匹配本地器件档案。");
    expect(formatSummary("Pin is not connected.")).toBe("引脚未连接。");
  });

  it("keeps regex capture groups such as net names", () => {
    expect(formatSummary("BJT collector is connected to VBUS_5V.")).toBe(
      "BJT 集电极连接到 VBUS_5V。"
    );
    expect(
      formatSummary("Diode reverse voltage rating is about 20 V, below required 42 V.")
    ).toBe("二极管反向耐压约 20 V，低于所需 42 V。");
  });

  it("translates embedded status tokens", () => {
    expect(formatSummary("profile status=ok")).toBe("profile 状态：通过");
    expect(formatSummary("lookup status=not_found")).toBe("lookup 状态：未找到");
  });

  it("passes unknown text through unchanged", () => {
    const text = "Some never-seen backend sentence.";
    expect(formatSummary(text)).toBe(text);
  });
});

describe("queueSubtitle", () => {
  it("joins identity and evidence cues", () => {
    expect(queueSubtitle(makeQueueItem())).toBe(
      "STM32F103C8T6 · LQFP48 · 2 条证据 / 1 条外部提示"
    );
  });

  it("omits the cue tail when there are no counts", () => {
    expect(queueSubtitle(makeQueueItem({ evidence_count: 0, risk_hint_count: 0 }))).toBe(
      "STM32F103C8T6 · LQFP48"
    );
  });

  it("falls back from part number to value, then to 无 MPN", () => {
    expect(
      queueSubtitle(makeQueueItem({ part_number: "", evidence_count: 0, risk_hint_count: 0 }))
    ).toBe("STM32F103 · LQFP48");
    expect(
      queueSubtitle(
        makeQueueItem({ part_number: "", value: "", evidence_count: 0, risk_hint_count: 0 })
      )
    ).toBe("无 MPN · LQFP48");
  });
});

describe("sourceLabel", () => {
  it("labels known evidence source classes", () => {
    expect(sourceLabel("live_retrieved")).toBe("本轮检索");
    expect(sourceLabel("reviewed_profile")).toBe("已审档案");
    expect(sourceLabel("design_source")).toBe("设计来源");
  });

  it("passes unknown source classes through", () => {
    expect(sourceLabel("mystery_class")).toBe("mystery_class");
  });
});

describe("evidenceNodeKind", () => {
  it("marks l3 and external/manual kinds as manual", () => {
    expect(evidenceNodeKind(makeChainItem({ trust_tier: "l3" }))).toBe("manual");
    expect(evidenceNodeKind(makeChainItem({ kind: "external_risk_hint" }))).toBe("manual");
    expect(evidenceNodeKind(makeChainItem({ kind: "manual_gap" }))).toBe("manual");
  });

  it("marks live retrieved evidence as grounded", () => {
    const item = makeChainItem({
      evidence: [makeEvidence({ source_class: "live_retrieved" })]
    });
    expect(evidenceNodeKind(item)).toBe("grounded");
  });

  it("defaults to deterministic", () => {
    expect(evidenceNodeKind(makeChainItem())).toBe("deterministic");
    expect(
      evidenceNodeKind(makeChainItem({ evidence: [makeEvidence()] }))
    ).toBe("deterministic");
  });
});

describe("chainKindLabel / taskKindLabel", () => {
  it("labels known kinds and falls back to the raw kind", () => {
    expect(chainKindLabel("component_check")).toBe("组件规则");
    expect(chainKindLabel("external_hint")).toBe("外部线索");
    expect(chainKindLabel("brand_new_kind")).toBe("brand_new_kind");
    expect(taskKindLabel("pin_check")).toBe("引脚检查");
    expect(taskKindLabel("cleared")).toBe("已通过");
    expect(taskKindLabel("brand_new_kind")).toBe("brand_new_kind");
  });
});
