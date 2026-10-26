import { useState } from "react";
import { Download } from "lucide-react";
import { downloadOfflineReport } from "../api";
import type { WorkbenchState } from "../types";

export function OfflineReportDownload({ state }: { state: WorkbenchState }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const snapshot = typeof window === "undefined" ? undefined : window.__HARDWISE_OFFLINE_SNAPSHOT__;
  const download = async () => {
    const { project_id: project, run_id: run } = state.review_decisions ?? {};
    if (!project || !run || busy) return;
    setBusy(true); setError("");
    try {
      const body = await downloadOfflineReport(project, run);
      const url = URL.createObjectURL(body);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = "hardwise-review-offline.html";
      try { anchor.click(); } finally { URL.revokeObjectURL(url); }
    } catch (err) { setError(err instanceof Error ? err.message : "离线评审包生成失败"); }
    finally { setBusy(false); }
  };
  return <section className="project-prep-card" aria-label="离线评审包">
    <div><strong>离线评审包 · 单文件 HTML</strong>
      <p>保留当前项目的检查结果、人工理由、完整处理历史和历史运行清单。只读，不包含原始 PDF，不替代项目备份。</p>
      <p>新生成报告会省略未声明、已撤回或声明失效的资料摘录；当前与历史清单采用同一分享规则。本地完整备份仍保留原记录。</p>
      {snapshot && <p>{snapshot.review_history ? `已封存 ${snapshot.review_history.total} 条历史；可在问题清单查看。` : "当前文件未封存处理历史，请从本地服务下载含历史的离线评审包。"}</p>}
      {error && <p role="alert" className="form-error">{error}</p>}
    </div>
    {!snapshot && <button type="button" disabled={busy || !state.review_decisions?.run_id} onClick={() => void download()}>
      <Download size={15} />{busy ? "正在封存…" : "下载离线评审包"}
    </button>}
  </section>;
}
