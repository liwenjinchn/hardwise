import { CheckCircle2 } from "lucide-react";
import type { ImportResponse, WorkbenchState } from "../types";

export function ParseView({
  state,
  parseResult
}: {
  state: WorkbenchState;
  parseResult: ImportResponse | null;
}) {
  const summary = parseResult?.summary ?? state.summary;
  const pinTable = parseResult?.pin_table ?? state.pin_table;
  const steps = [
    ["解析网表", `${summary.components} 个器件进入注册表`],
    ["匹配 BOM", `${summary.bom_matched} 个 refdes 已锚定`],
    [
      "读取 Capture 引脚表",
      pinTable.status === "loaded"
        ? `${pinTable.accepted_findings} 条引脚表任务，${pinTable.rejected_findings} 条被拒绝`
        : "未加载 Capture 引脚表 CSV"
    ],
    ["运行确定性验证", `PASS/WARN/ERROR=${summary.pass_count}/${summary.warn_count}/${summary.error_count}`],
    ["生成 finding", `${parseResult?.task_counts.total ?? state.task_counts.total} 个任务已排队`]
  ];
  return (
    <section className="flow-page parse-page">
      <div className="flow-copy">
        <span className="eyebrow">Parse</span>
        <h2>重建证据工作台</h2>
        <p>这里只展示真实后端结果的解析过程；状态数字来自刚刚生成的 WorkbenchContext。</p>
      </div>
      <div className="parse-rail">
        {steps.map(([title, body], index) => (
          <article className="parse-step" key={title} style={{ animationDelay: `${index * 120}ms` }}>
            <CheckCircle2 size={18} />
            <strong>{title}</strong>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
