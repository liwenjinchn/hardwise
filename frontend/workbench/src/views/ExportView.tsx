import { useState } from "react";
import { Download, FileSearch, Loader2, PackageCheck } from "lucide-react";
import { exportWorkbench, fetchProjectPrepPacketMarkdown } from "../api";
import type { WorkbenchState } from "../types";

export function ExportView({ state }: { state: WorkbenchState }) {
  const [format, setFormat] = useState<"json" | "csv" | "annotations">("json");
  const [preview, setPreview] = useState("");
  const [projectPacketPreview, setProjectPacketPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [packetBusy, setPacketBusy] = useState(false);
  const [error, setError] = useState("");
  const [packetError, setPacketError] = useState("");

  const loadPreview = async () => {
    setBusy(true);
    setError("");
    try {
      const body = await exportWorkbench(format);
      setPreview(format === "json" ? JSON.stringify(JSON.parse(body), null, 2) : body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!preview) return;
    const extension = format === "json" ? "json" : format === "csv" ? "csv" : "txt";
    const blob = new Blob([preview], { type: "text/plain;charset=utf-8" });
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
          输出来自真实后端接口：{state.review_tasks.length} 个 finding，
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
              }}
            >
              {item}
            </button>
          ))}
          <button className="primary-action" type="button" onClick={() => void loadPreview()} disabled={busy}>
            {busy ? <Loader2 className="spin" size={16} /> : <PackageCheck size={16} />}
            生成预览
          </button>
          <button type="button" onClick={download} disabled={!preview}>
            <Download size={15} />
            下载
          </button>
        </div>
        {error && <p className="form-error">{error}</p>}
        <pre className="export-preview">{preview || "选择格式后生成预览。"}</pre>
      </div>
    </section>
  );
}
