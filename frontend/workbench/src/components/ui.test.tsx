import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  CheckCard,
  EvidenceCard,
  EvidenceToken,
  InfoCell,
  Metric,
  StatusBadge,
  StatusIcon,
  TrustBadge,
  VerdictBanner
} from "./ui";
import { makeCheck, makeChainItem, makeEvidence } from "../testing/fixtures";

describe("Metric", () => {
  it("renders label, value, and tone class", () => {
    const html = renderToStaticMarkup(<Metric label="ERROR" value={4} tone="error" />);
    expect(html).toContain("metric error");
    expect(html).toContain("ERROR");
    expect(html).toContain("<strong>4</strong>");
  });
});

describe("StatusBadge", () => {
  it("carries the status group class and label", () => {
    const html = renderToStaticMarkup(<StatusBadge group="warn" label="看证据" />);
    expect(html).toContain("status-badge warn");
    expect(html).toContain("看证据");
  });
});

describe("TrustBadge", () => {
  it("splits the trust label into level and name", () => {
    const html = renderToStaticMarkup(<TrustBadge tier="l1" />);
    expect(html).toContain("trust-badge l1");
    expect(html).toContain(">L1<");
    expect(html).toContain("确定性");
  });

  it("renders the manual-confirmation tier", () => {
    const html = renderToStaticMarkup(<TrustBadge tier="l3" />);
    expect(html).toContain("trust-badge l3");
    expect(html).toContain("人工确认");
  });
});

describe("StatusIcon", () => {
  it("renders distinct icons per status group", () => {
    const pass = renderToStaticMarkup(<StatusIcon group="pass" />);
    const manual = renderToStaticMarkup(<StatusIcon group="manual" />);
    const error = renderToStaticMarkup(<StatusIcon group="error" />);
    expect(pass).toContain("<svg");
    expect(manual).toContain("<svg");
    expect(error).toContain("<svg");
    expect(pass).not.toEqual(error);
    expect(manual).not.toEqual(error);
  });
});

describe("VerdictBanner", () => {
  it.each([
    ["error", "必须处理 · 阻塞项"],
    ["warn", "需要复核 · 有证据"],
    ["manual", "人工确认 · 数据不足"],
    ["pass", "已通过 · 当前覆盖"]
  ] as const)("renders the %s verdict copy", (group, title) => {
    const html = renderToStaticMarkup(<VerdictBanner group={group} />);
    expect(html).toContain(`verdict-banner ${group}`);
    expect(html).toContain(title);
  });
});

describe("InfoCell", () => {
  it("renders label and value", () => {
    const html = renderToStaticMarkup(<InfoCell label="MPN" value="STM32F103C8T6" />);
    expect(html).toContain("info-cell");
    expect(html).toContain("MPN");
    expect(html).toContain("STM32F103C8T6");
  });
});

describe("EvidenceToken", () => {
  it("renders token text with source class styling", () => {
    const html = renderToStaticMarkup(
      <EvidenceToken evidence={makeEvidence({ source_class: "reviewed_profile", token: "EV-9" })} />
    );
    expect(html).toContain("token reviewed_profile");
    expect(html).toContain("EV-9");
    expect(html).toContain("netlist · reviewed_profile");
  });
});

describe("EvidenceCard", () => {
  it("classifies deterministic nodes and translates kind + summary", () => {
    const html = renderToStaticMarkup(
      <EvidenceCard item={makeChainItem({ title: "Pin is not connected." })} />
    );
    expect(html).toContain("evidence-card evi-node warn deterministic");
    expect(html).toContain("组件规则");
    expect(html).toContain("引脚未连接。");
    expect(html).toContain("无 evidence token");
  });

  it("classifies live-retrieved evidence as grounded and lists tokens", () => {
    const html = renderToStaticMarkup(
      <EvidenceCard
        item={makeChainItem({
          evidence: [makeEvidence({ source_class: "live_retrieved", token: "EV-LIVE" })]
        })}
      />
    );
    expect(html).toContain("grounded");
    expect(html).toContain("EV-LIVE");
    expect(html).not.toContain("无 evidence token");
  });

  it("classifies l3 nodes as manual", () => {
    const html = renderToStaticMarkup(<EvidenceCard item={makeChainItem({ trust_tier: "l3" })} />);
    expect(html).toContain("evidence-card evi-node warn manual");
  });
});

describe("CheckCard", () => {
  it("renders subject, badge, and translated summary", () => {
    const html = renderToStaticMarkup(<CheckCard check={makeCheck()} />);
    expect(html).toContain("check-card warn");
    expect(html).toContain("VEBO");
    expect(html).toContain("看证据");
    expect(html).toContain("引脚未连接。");
  });

  it("caps evidence tokens at four", () => {
    const evidence = [1, 2, 3, 4, 5].map((n) =>
      makeEvidence({ token: `EV-${n}` })
    );
    const html = renderToStaticMarkup(<CheckCard check={makeCheck({ evidence })} />);
    expect(html).toContain("EV-4");
    expect(html).not.toContain("EV-5");
  });
});
