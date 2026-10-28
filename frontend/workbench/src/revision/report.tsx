import { renderToStaticMarkup } from "react-dom/server";
import type { ComparisonResult } from "../generated/workbench-contracts";
import { ComparisonResults } from "./ComparisonResults";
import tokens from "../styles/tokens-base.css?raw";
import styles from "./compare.css?raw";

export function buildComparisonHtml(result: ComparisonResult, source: "files" | "demo" = "files"): string {
  // All source-controlled text is rendered by React's escaping. No data is
  // interpolated into HTML attributes, styles, JSON script blocks or executable code.
  const content = renderToStaticMarkup(<main className="revision-app revision-report">
    <header className="revision-report-heading"><span className="revision-kicker">离线只读报告</span>
      <h1>Hardwise 改版复核</h1>
      <p>{source === "demo" ? "内置合成示例结果，不是上传文件的结果。" : "上传文件的版本对比结果。"}所有变化完整列出，不应用页面筛选。</p>
      <p>只对照输入声明，不评估电气正确性或整板安全。报告包含文件名、声明值及来源定位，分享前请核对内容。</p>
    </header>
    <ComparisonResults result={result} readOnly />
  </main>);
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Hardwise 改版复核 · 离线报告</title><style>${tokens}\n${styles}\nbody{overflow:auto;height:auto}body::before{display:none}</style></head><body>${content}</body></html>`;
}

export function downloadFile(contents: string, type: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  // Delay revocation until the browser has started consuming the download.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
