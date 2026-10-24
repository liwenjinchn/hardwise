import { useState } from "react";
import type { ProjectRestoreReceipt } from "../generated/workbench-contracts";
import { downloadProjectBackup, restoreProjectBackup } from "../project-api";

export function ProjectArchive({ runId, busy, onBusy }: { runId: string | null | undefined; busy: boolean; onBusy: (value: boolean) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [receipt, setReceipt] = useState<ProjectRestoreReceipt | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [shell, setShell] = useState<"posix" | "powershell">("posix");
  const act = async (kind: "backup" | "restore") => {
    if (busy || (kind === "restore" && !file)) return;
    onBusy(true); setError(""); setNotice("");
    try {
      if (kind === "backup") {
        const result = await downloadProjectBackup(runId);
        const url = URL.createObjectURL(result.blob);
        const anchor = document.createElement("a");
        anchor.href = url; anchor.download = "hardwise-projects.zip";
        document.body.appendChild(anchor); anchor.click(); anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        setNotice(result.sourceUnownedCount ? `备份已生成；其中 ${result.sourceUnownedCount} 个旧项目仅有历史、未拥有其原始输入。` : "备份已生成，仅包含已保存的输入版本和评审历史。请保留下载文件。");
      } else if (file) {
        const next = await restoreProjectBackup(file, runId);
        setReceipt(next);
        setNotice("已恢复为独立副本，当前评审未切换。打开方式见下方。");
      }
    } catch (err) { setError(err instanceof Error ? err.message : "备份或恢复失败"); }
    finally { onBusy(false); }
  };
  return <section className="project-archive" aria-label="项目备份与恢复">
    <h4>备份与恢复</h4>
    <p>请先保存本次输入。下载包含此日志中所有已保存项目及处理历史；未保存的输入和未随附的外链原文不保证可恢复。</p>
    <button className="icon-text-btn" disabled={busy} onClick={() => void act("backup")}>下载已保存项目备份</button>
    <p>上传备份会先验证，再恢复到独立的新目录；不会覆盖当前项目或原日志。</p>
    <div className="saved-project-actions">
      <input type="file" accept=".zip" aria-label="选择项目备份 ZIP" disabled={busy} onChange={event => setFile(event.target.files?.[0] ?? null)} />
      <button className="icon-text-btn" disabled={busy || !file} onClick={() => void act("restore")}>恢复到新目录</button>
    </div>
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}。当前评审未被恢复操作替换，可重新选择有效备份后重试。</p>}
    {receipt && <div className="restore-receipt">
      <strong>恢复副本</strong><p>{receipt.journal}</p>
      {receipt.source_unowned_project_ids.length > 0 && <p>有 {receipt.source_unowned_project_ids.length} 个旧项目仅含历史，没有可恢复的原始输入。</p>}
      <p>在本地终端运行以下命令，以新服务打开副本。当前浏览器仍连接原项目；打开方式也保存在副本目录的 restore-info.json。</p>
      <label>终端类型 <select aria-label="恢复命令终端类型" value={shell} onChange={event => setShell(event.target.value as "posix" | "powershell")}>
        <option value="posix">macOS / Linux</option><option value="powershell">Windows PowerShell</option>
      </select></label>
      {receipt.launches.map(launch => <pre key={launch.saved_id}><code>{shell === "powershell" ? launch.command_powershell : launch.command_posix}</code></pre>)}
    </div>}
  </section>;
}
