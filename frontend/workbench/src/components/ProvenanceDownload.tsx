import { useEffect, useRef, useState } from "react";
import { fetchRunProvenance } from "../api";

export function ProvenanceDownload({ projectId, runId, historical = false }: {
  projectId: string | null; runId: string | null; historical?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    setBusy(false); setMessage(""); setError("");
    return () => { generation.current += 1; };
  }, [projectId, runId]);
  const download = async () => {
    if (busy) return;
    const requestedGeneration = generation.current;
    setBusy(true); setMessage(""); setError("");
    try {
      const payload = await fetchRunProvenance(projectId, runId);
      if (requestedGeneration !== generation.current) return;
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
    {!historical && <p>清单记录文件哈希、档案/规则及复核依赖合同版本（决定哪些变动需复核），不包含原始文件，不等于项目备份。</p>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
  </div>;
}
