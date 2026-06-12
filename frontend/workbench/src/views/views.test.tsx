import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CopilotPanel, RichMessageText, TraceDetails } from "./CopilotPanel";
import { ExportView } from "./ExportView";
import { FindingsView } from "./FindingsView";
import { Header } from "./Header";
import { ImportView } from "./ImportView";
import { ParseView } from "./ParseView";
import { DetailColumn } from "./review/DetailColumn";
import { EvidenceColumn } from "./review/EvidenceColumn";
import { TaskQueueColumn } from "./review/TaskQueueColumn";
import {
  makeDetail,
  makeDocument,
  makeEvidence,
  makePinTable,
  makeQueueItem,
  makeRiskHints,
  makeState,
  makeTask,
  makeTaskCounts
} from "../testing/fixtures";

// Initial-render coverage for every component extracted from App.tsx.
// Interactions (clicks, fetches) are exercised by the Playwright E2E suite;
// these assertions pin the server-renderable contract of each view.

describe("Header", () => {
  it("renders brand, workflow nav, and summary metrics", () => {
    const html = renderToStaticMarkup(
      <Header state={makeState()} currentView="review" onNavigate={() => {}} />
    );
    expect(html).toContain("schematic review");
    for (const label of ["导入", "解析", "审查", "AI 助手", "问题清单", "导出"]) {
      expect(html).toContain(label);
    }
    expect(html).toContain("mixed_controller_power_stage");
    expect(html).toContain("Copilot 可用");
    expect(html).toContain("向量检索关闭");
  });

  it("counts non-pass components in the review pip", () => {
    const state = makeState({
      queue: [
        makeQueueItem({ refdes: "U1", status_group: "warn" }),
        makeQueueItem({ refdes: "U2", status_group: "pass" }),
        makeQueueItem({ refdes: "U3", status_group: "error" })
      ]
    });
    const html = renderToStaticMarkup(
      <Header state={state} currentView="review" onNavigate={() => {}} />
    );
    expect(html).toContain('<span class="pip">2</span>');
  });

  it("uses total task count for the findings pip and explains the blocking subset", () => {
    const state = makeState({
      task_counts: makeTaskCounts({ total: 9, error: 2, warn: 3, manual: 1, pass_count: 3 })
    });
    const html = renderToStaticMarkup(
      <Header state={state} currentView="review" onNavigate={() => {}} />
    );
    expect(html).toContain('title="全量任务 9；ERROR/WARN 5"');
    expect(html).toContain('<span class="pip">9</span>');
  });
});

describe("ImportView", () => {
  it("renders upload slots and the current snapshot numbers", () => {
    const html = renderToStaticMarkup(<ImportView state={makeState()} onImported={() => {}} />);
    expect(html).toContain("netlist / PST");
    expect(html).toContain("BOM CSV");
    expect(html).toContain("Capture 引脚表 CSV");
    expect(html).toContain("risk hints JSON");
    expect(html).toContain("25 components");
    expect(html).toContain("引脚表 未加载");
    expect(html).toContain("scripts/capture_pin_table_export.tcl");
    expect(html).toContain("导入并解析");
    expect(html).toContain("拖入文件或点击选择");
  });

  it("renders pin-table intake as a loaded first-class asset", () => {
    const html = renderToStaticMarkup(
      <ImportView
        state={makeState({
          capabilities: { ...makeState().capabilities, pin_table_enabled: true },
          pin_table: makePinTable({
            status: "loaded",
            source: "pin_table_demo.csv",
            accepted_findings: 3,
            rejected_findings: 1,
            affected_refdes: 2,
            checks: { R008: 1, R009: 1, R010: 1 }
          })
        })}
        onImported={() => {}}
      />
    );
    expect(html).toContain("引脚表 3 条任务");
    expect(html).toContain("3 条任务 · R008 1 / R009 1 / R010 1");
  });
});

describe("ParseView", () => {
  it("renders the four parse steps from the live summary", () => {
    const html = renderToStaticMarkup(<ParseView state={makeState()} parseResult={null} />);
    expect(html).toContain("解析网表");
    expect(html).toContain("25 个器件进入注册表");
    expect(html).toContain("读取 Capture 引脚表");
    expect(html).toContain("未加载 Capture 引脚表 CSV");
    expect(html).toContain("PASS/WARN/ERROR=5/13/4");
    expect(html).toContain("1 个任务已排队");
  });

  it("renders pin-table import counts from the latest parse result", () => {
    const html = renderToStaticMarkup(
      <ParseView
        state={makeState()}
        parseResult={{
          ok: true,
          project: makeState().project,
          summary: makeState().summary,
          selected_refdes: "U8",
          task_counts: makeTaskCounts({ total: 4, warn: 4 }),
          pin_table: makePinTable({
            status: "loaded",
            accepted_findings: 3,
            rejected_findings: 1
          })
        }}
      />
    );
    expect(html).toContain("3 条引脚表任务，1 条被拒绝");
  });
});

describe("CopilotPanel", () => {
  it("renders the guard welcome, default probes, and trust legend", () => {
    const html = renderToStaticMarkup(
      <CopilotPanel state={makeState()} selectedRefdes="U8" />
    );
    expect(html).toContain("Refdes Guard 包裹");
    expect(html).toContain("这个 U8 为什么是 ERROR/WARN?");
    expect(html).toContain("板上有没有 U999?");
    expect(html).toContain("Trust tiers");
    expect(html).toContain("回答必须被 netlist、规则或引用来源锚定");
  });

  it("renders structured assistant text with lists and evidence tokens", () => {
    const html = renderToStaticMarkup(
      <RichMessageText
        text={[
          "结论",
          "",
          "- 检查 `BOOT0`。",
          "- 证据 datasheet:stm32g030.pdf#p33 和 EV-BOOT。",
          "",
          "| 项目 | 数值 |",
          "|---|---|",
          "| **ERROR** | 4 |",
          "",
          "1. 先看规则结果",
          "2. 再看 trace"
        ].join("\n")}
      />
    );
    expect(html).toContain("<ul");
    expect(html).toContain("<ol");
    expect(html).toContain("message-table");
    expect(html).toContain("<strong>ERROR</strong>");
    expect(html).toContain("<code>BOOT0</code>");
    expect(html).toContain("evidence-inline");
    expect(html).toContain("datasheet:stm32g030.pdf#p33");
  });

  it("keeps tool trace collapsed by default", () => {
    const html = renderToStaticMarkup(
      <TraceDetails
        response={{
          answer: "ok",
          mode: "real",
          selected_refdes: "U8",
          trace: [
            {
              tool: "run_component_validation",
              input: { refdes: "U8" },
              summary: "status=validated",
              status: "ERROR",
              evidence: [],
              evidence_classification: [],
              wrapped: 0,
              trust_tier: "l1",
              trust_label: "L1 deterministic"
            }
          ],
          wrapped_count: 0,
          suggestions: [],
          datasheet_search_enabled: false
        }}
      />
    );
    expect(html).toContain("工具调用 / 证据 · 1");
    expect(html).toContain("<details");
    expect(html).not.toContain("<details open");
  });
});

describe("FindingsView", () => {
  it("renders open and locally-resolved rows differently", () => {
    const tasks = [makeTask(), makeTask({ id: "T2", title: "second", status_group: "error" })];
    const html = renderToStaticMarkup(
      <FindingsView
        tasks={tasks}
        resolvedTaskIds={new Set(["T2"])}
        onToggleResolved={() => {}}
        onOpenTask={() => {}}
      />
    );
    expect(html).toContain("全部任务登记册");
    expect(html).toContain("标记处理");
    expect(html).toContain("本地已处理");
    expect(html).toContain("重新打开");
    expect(html).toContain("finding-row error resolved");
  });
});

describe("ExportView", () => {
  it("renders finding count, format switches, and prep packet card", () => {
    const html = renderToStaticMarkup(
      <ExportView
        state={makeState({
          task_counts: makeTaskCounts({ total: 7, error: 2, warn: 3, manual: 1, pass_count: 1 })
        })}
      />
    );
    expect(html).toContain("导出当前审查状态");
    expect(html).toContain("7 个任务");
    expect(html).toContain("其中 ERROR/WARN 5 个");
    for (const fmt of ["json", "csv", "annotations"]) {
      expect(html).toContain(`>${fmt}</button>`);
    }
    expect(html).toContain("项目评审准备包");
    expect(html).toContain("选择格式后生成预览。");
  });
});

describe("TaskQueueColumn", () => {
  const baseProps = {
    counts: { all: 2, error: 0, warn: 1, manual: 0, pass: 1 } as const,
    filter: "all" as const,
    query: "",
    onFilter: () => {},
    onQuery: () => {},
    onPick: () => {}
  };

  it("renders counts, filters, and queue rows with selection", () => {
    const items = [
      makeQueueItem({ refdes: "Q12", status_group: "warn" }),
      makeQueueItem({
        refdes: "U12",
        status_group: "pass",
        task_count: 0,
        top_task_id: null,
        pin_table_task_count: 2
      })
    ];
    const html = renderToStaticMarkup(
      <TaskQueueColumn {...baseProps} items={items} allItems={items} selectedRefdes="Q12" />
    );
    expect(html).toContain("组件审查队列");
    expect(html).toContain("2/2");
    expect(html).toContain("全部待看");
    expect(html).toContain("queue-row warn selected");
    expect(html).toContain("Q12");
    expect(html).toContain("1 项");
    expect(html).toContain("引脚表 × 2");
    expect(html).toContain("通过");
    expect(html).toContain("cleared");
  });

  it("shows a document badge only when an index status exists", () => {
    const withDoc = renderToStaticMarkup(
      <TaskQueueColumn
        {...baseProps}
        items={[makeQueueItem({ document_status: "matched" })]}
        allItems={[makeQueueItem({ document_status: "matched" })]}
        selectedRefdes={null}
      />
    );
    expect(withDoc).toContain("资料 已索引");
    const withoutIndex = renderToStaticMarkup(
      <TaskQueueColumn
        {...baseProps}
        items={[makeQueueItem({ document_status: "not_configured" })]}
        allItems={[makeQueueItem({ document_status: "not_configured" })]}
        selectedRefdes={null}
      />
    );
    expect(withoutIndex).not.toContain("资料 ");
  });
});

describe("DetailColumn", () => {
  it("renders the loading and empty states", () => {
    const loading = renderToStaticMarkup(<DetailColumn detail={null} loading onAsk={() => {}} />);
    expect(loading).toContain("正在读取器件详情...");
    const empty = renderToStaticMarkup(
      <DetailColumn detail={null} loading={false} onAsk={() => {}} />
    );
    expect(empty).toContain("请选择一个器件查看审查详情。");
  });

  it("renders identity grid, pins, and checks for a full detail", () => {
    const html = renderToStaticMarkup(
      <DetailColumn detail={makeDetail()} loading={false} onAsk={() => {}} />
    );
    expect(html).toContain("器件详情");
    expect(html).toContain(">U8</h2>");
    expect(html).toContain("STM32F103C8T6");
    expect(html).toContain("已唯一匹配本地器件档案。");
    expect(html).toContain("评审准备包");
    expect(html).toContain("审查任务");
    expect(html).toContain("引脚 / 网络表");
    expect(html).toContain("VBUS_5V");
    expect(html).toContain("确定性检查");
    expect(html).toContain("VEBO");
    expect(html).toContain("问 Copilot");
  });

  it("renders pin-table tasks inside the detail task list", () => {
    const html = renderToStaticMarkup(
      <DetailColumn
        detail={makeDetail({
          task_counts: makeTaskCounts({ total: 1, error: 1, warn: 0 }),
          tasks: [
            makeTask({
              id: "F-005",
              kind: "pin_table_check",
              check: "R009",
              pin_number: "6",
              title: "R009 · Power pin is not connected.",
              status: "ERROR",
              status_label: "ERROR",
              status_group: "error"
            })
          ]
        })}
        loading={false}
        onAsk={() => {}}
      />
    );
    expect(html).toContain("Capture 引脚表 · 6脚");
    expect(html).toContain("R009");
  });

  it("renders a matched document-index block with title, source, and link", () => {
    const html = renderToStaticMarkup(
      <DetailColumn detail={makeDetail({ document: makeDocument() })} loading={false} onAsk={() => {}} />
    );
    expect(html).toContain("资料索引");
    expect(html).toContain("已索引");
    expect(html).toContain("L78 series public ST datasheet (l78.pdf)");
    expect(html).toContain("st.com");
    expect(html).toContain(
      'href="https://www.st.com/resource/en/datasheet/l78.pdf" target="_blank" rel="noreferrer"'
    );
    expect(html).toContain("不构成电气结论");
  });

  it("renders a no_result document gap with the matcher reason", () => {
    const html = renderToStaticMarkup(
      <DetailColumn
        detail={makeDetail({
          document: makeDocument({
            status: "no_result",
            title: null,
            url: null,
            source: null,
            candidates: 0,
            reason: "No local document-index row matched this BOM identity."
          })
        })}
        loading={false}
        onAsk={() => {}}
      />
    );
    expect(html).toContain("资料索引");
    expect(html).toContain("未命中");
    expect(html).toContain("No local document-index row matched this BOM identity.");
    expect(html).not.toContain("doc-link");
  });
});

describe("EvidenceColumn", () => {
  const noop = () => {};

  it("prompts for selection when nothing is picked", () => {
    const html = renderToStaticMarkup(
      <EvidenceColumn
        tasks={[]}
        selectedTaskId={null}
        selectedRefdes={null}
        onPickTask={noop}
        detail={null}
        riskHints={makeRiskHints()}
      />
    );
    expect(html).toContain("选择一个器件后显示 chain of custody。");
  });

  it("falls back to the component summary chain when there are no findings", () => {
    const html = renderToStaticMarkup(
      <EvidenceColumn
        tasks={[]}
        selectedTaskId={null}
        selectedRefdes="U8"
        onPickTask={noop}
        detail={makeDetail({ task_counts: makeTaskCounts({ total: 0 }) })}
        riskHints={makeRiskHints()}
      />
    );
    expect(html).toContain("U8 为什么被提醒");
    expect(html).toContain("当前器件没有 finding，显示组件级证据摘要。");
    expect(html).toContain("component-summary-chain");
  });

  it("renders finding tabs, guard note, and read-only risk hints", () => {
    const html = renderToStaticMarkup(
      <EvidenceColumn
        tasks={[makeTask()]}
        selectedTaskId="T1"
        selectedRefdes="U8"
        onPickTask={noop}
        detail={makeDetail()}
        riskHints={makeRiskHints({
          external_status: "loaded",
          count: 2,
          accepted_external_count: 1,
          rejected_external_count: 1,
          accepted: [
            {
              refdes: "U8",
              title: "supply note",
              body: "watch the rail",
              severity: null,
              source: makeEvidence({ token: "EV-EXT" }),
              wrapped_refdes_count: 0
            }
          ],
          rejected: [{ reason: "unanchored_refdes", count: 1 }]
        })}
      />
    );
    expect(html).toContain("evi-finding warn selected");
    expect(html).toContain("证据路径 · L1 确定性。");
    expect(html).toContain("建议动作");
    expect(html).toContain("外部提示 · 只读");
    expect(html).toContain("不改变 PASS/WARN/ERROR 结论");
    expect(html).toContain("U8 · supply note");
    expect(html).toContain("EV-EXT");
    expect(html).toContain("unanchored_refdes × 1");
  });
});
