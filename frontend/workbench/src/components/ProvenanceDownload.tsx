import { useEffect, useRef, useState } from "react";
import { fetchRunProvenance, type ProvenanceDownload as ProvenancePayload } from "../api";
import { SharedExcerptReader } from "./SharedExcerptReader";

export function ProvenanceDownload({ projectId, runId, historical = false }: {
  projectId: string | null; runId: string | null; historical?: boolean;
}) {
  const [preview, setPreview] = useState<ProvenancePayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    setBusy(false); setMessage(""); setError(""); setPreview(null);
    return () => { generation.current += 1; };
  }, [projectId, runId]);
  const download = async (read = false) => {
    if (busy) return;
    const requestedGeneration = generation.current;
    setBusy(true); setMessage(""); setError("");
    try {
      const payload = await fetchRunProvenance(projectId, runId);
      if (requestedGeneration !== generation.current) return;
      if (read) { setPreview(payload); return; }
      const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "hardwise-run-provenance.json";
      try { anchor.click(); } finally { URL.revokeObjectURL(url); }
      setMessage("status" in payload && payload.status === "not_recorded"
        ? "已下载缺失说明：该旧运行未记录清单，未使用当前文件补算。"
        : "已下载输入与版本清单；不包含原始文件。");
    } catch (err) {
      if (requestedGeneration === generation.current) setError(err instanceof Error ? err.message : "清单下载失败");
    } finally {
      if (requestedGeneration === generation.current) setBusy(false);
    }
  };
  return <div className="provenance-download">
    <button type="button" disabled={busy} onClick={() => void download()}>
      {busy ? "正在读取清单…" : historical ? "下载该次输入与版本清单" : "下载本次输入与版本清单"}
    </button>
    <button type="button" disabled={busy} onClick={() => void download(true)}>{historical ? "查看该次资料来源与摘录" : "查看本次资料来源与摘录"}</button>
    {preview && <><button type="button" onClick={() => setPreview(null)}>收起资料来源</button><SharedExcerptReader payload={preview} /></>}
    {!historical && <p>清单记录文件哈希、档案/规则及复核依赖合同版本（决定哪些变动需复核），不包含原始文件，不等于项目备份。</p>}
    <p>资料摘录只有有效允许分享声明才随清单导出；缺失项保留来源定位和省略原因。本地原内容哈希与分享后的内容哈希分别标明。</p>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
  </div>;
}
