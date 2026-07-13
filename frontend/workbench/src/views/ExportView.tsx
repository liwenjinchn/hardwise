import { useState } from "react";
import { Download, FileSearch, Loader2, PackageCheck } from "lucide-react";
import { exportWorkbench, fetchProjectPrepPacketMarkdown } from "../api";
import { EvidencePackageDashboard } from "../components/EvidencePackageDashboard";
import type { WorkbenchState } from "../types";

export function ExportView({ state }: { state: WorkbenchState }) {
  const [format, setFormat] = useState<"json" | "csv" | "annotations">("json");
  const [preview, setPreview] = useState("");
  const [downloadBody, setDownloadBody] = useState("");
  const [projectPacketPreview, setProjectPacketPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [packetBusy, setPacketBusy] = useState(false);
  const [error, setError] = useState("");
  const [packetError, setPacketError] = useState("");
  const pinTable = state.pin_table;
  const reviewPackage = state.review_package;
  const pinTableAffected = pinTable.affected_refdes_list.join(", ") || "-";
  const pinTableRejected = pinTable.rejected_unknown_refdes.join(", ") || "-";

  const loadPreview = async () => {
    setBusy(true);
    setError("");
    try {
      const body = await exportWorkbench(format);
      setDownloadBody(body);
      if (format === "json") {
        const payload = JSON.parse(body) as WorkbenchState;
        setPreview(JSON.stringify({
          project: payload.project.name,
          component_counts: payload.summary,
          raw_task_counts: payload.task_counts,
          grouped_review_workload: payload.review_groups.length,
          review_decisions: payload.review_decisions,
          signoff_readiness: payload.evidence_package.signoff_readiness,
          note: "预览仅显示交接摘要；下载保留完整 JSON、原始任务和 evidence chain。"
        }, null, 2));
      } else {
        setPreview(body);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!downloadBody) return;
    const extension = format === "json" ? "json" : format === "csv" ? "csv" : "txt";
    const blob = new Blob([downloadBody], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `hardwise-${format}.${extension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const loadProjectPacket = async (downloadPacket: boolean) => {
    if (packetBusy) return;
    setPacketBusy(true);
    setPacketError("");
    try {
      const markdown = await fetchProjectPrepPacketMarkdown();
      if (downloadPacket) {
        const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "hardwise-project-prep.md";
        anchor.click();
        URL.revokeObjectURL(url);
      } else {
        setProjectPacketPreview(markdown);
      }
    } catch (err) {
      setPacketError(err instanceof Error ? err.message : "项目准备包生成失败");
    } finally {
      setPacketBusy(false);
    }
  };

  return (
    <section className="flow-page export-page">
      <div className="flow-copy">
        <span className="eyebrow">Export</span>
        <h2>导出当前审查状态</h2>
        <p>
          输出来自真实后端接口：{state.review_groups.length} 个审查组、
          {state.task_counts.total} 条原始任务，其中 ERROR/WARN 原始任务
          {state.task_counts.error + state.task_counts.warn} 条。
          不包含 API key 或浏览器聊天密钥。
        </p>
      </div>
      <div className="export-stack">
        <section className="project-prep-card" aria-label="项目评审准备包">
          <div>
            <span className="eyebrow">Project Prep Packet</span>
            <strong>项目评审准备包</strong>
            <p>
              汇总全板摘要、重点器件组、review focus areas、开放问题、risk hints 和
              evidence token，适合评审会前交接。
            </p>
          </div>
          <div className="prep-button-row">
            <button type="button" onClick={() => void loadProjectPacket(false)} disabled={packetBusy}>
              {packetBusy ? <Loader2 className="spin" size={15} /> : <FileSearch size={15} />}
              预览项目包
            </button>
            <button type="button" onClick={() => void loadProjectPacket(true)} disabled={packetBusy}>
              <Download size={15} />
              下载 MD
            </button>
          </div>
        </section>
        <EvidencePackageDashboard summary={state.evidence_package} />
        <section className="project-prep-card" aria-label="Pin-table evidence summary">
          <div>
            <span className="eyebrow">Pin Table Evidence</span>
            <strong>Capture 引脚表证据摘要</strong>
            <p>
              {pinTable.status === "loaded"
                ? `accepted ${pinTable.accepted_findings}，rejected unknown ${pinTable.rejected_findings}，affected ${pinTable.affected_refdes}。`
                : "未加载 Capture 引脚表 CSV。"}
              {" "}未知位号只显示在 summary，不进入 L1 review queue。
            </p>
            {pinTable.status === "loaded" && (
              <p className="scope-note">
                Accepted refdes：{pinTableAffected}；Rejected unknown refdes：{pinTableRejected}
              </p>
            )}
          </div>
        </section>
        <section className="project-prep-card" aria-label="Review-package evidence summary">
          <div>
            <span className="eyebrow">Review Package Evidence</span>
            <strong>评审证据包状态</strong>
            <p>
              {reviewPackage.status === "loaded"
                ? `package_status ${reviewPackage.package_status}，manual gaps ${reviewPackage.manual_gap_count}，present ${reviewPackage.present}/${reviewPackage.total}。`
                : "未加载 review-package manifest。"}
              {" "}Package status 只说明交付证据是否齐备，不生成电气 finding。
            </p>
            {reviewPackage.status === "loaded" && (
              <p className="scope-note">
                Missing required：{reviewPackage.missing_required}；Hash mismatch：{reviewPackage.hash_mismatch}；{reviewPackage.recommended_action}
              </p>
            )}
          </div>
        </section>
        {packetError && <p className="form-error">{packetError}</p>}
        {projectPacketPreview && <pre className="project-prep-preview">{projectPacketPreview}</pre>}
        <div className="export-controls">
          {(["json", "csv", "annotations"] as const).map((item) => (
            <button
              type="button"
              className={format === item ? "active" : ""}
              key={item}
              onClick={() => {
                setFormat(item);
                setPreview("");
                setDownloadBody("");
              }}
            >
              {item}
            </button>
          ))}
          <button className="primary-action" type="button" onClick={() => void loadPreview()} disabled={busy}>
            {busy ? <Loader2 className="spin" size={16} /> : <PackageCheck size={16} />}
            生成预览
          </button>
          <button type="button" onClick={download} disabled={!downloadBody}>
            <Download size={15} />
            下载
          </button>
        </div>
        {error && <p className="form-error">{error}</p>}
        <pre className="export-preview">{preview || "选择格式后生成摘要预览；下载文件保留完整内容。"}</pre>
      </div>
    </section>
  );
}
