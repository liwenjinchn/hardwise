import { useEffect, useRef, useState } from "react";
import type { SavedProjectView } from "../generated/workbench-contracts";
import type { WorkbenchState } from "../types";
import { listSavedProjects, openSavedProject, saveCurrentProject } from "../project-api";

export function SavedProjects({ state, onOpened }: { state: WorkbenchState; onOpened: (state: WorkbenchState) => void }) {
  const [projects, setProjects] = useState<SavedProjectView[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const readId = useRef(0);
  const offline = typeof window !== "undefined" && !!window.__HARDWISE_OFFLINE_SNAPSHOT__;
  const enabled = !offline && state.review_decisions?.storage === "local_file" && !!state.review_decisions?.run_id;
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    const id = ++readId.current;
    listSavedProjects().then(result => { if (live && id === readId.current) setProjects(result.projects); })
      .catch(err => { if (live && id === readId.current) setError(err instanceof Error ? err.message : "读取失败"); });
    return () => { live = false; };
  }, [enabled, state.review_decisions?.run_id]);

  const operate = async (kind: "save" | "refresh" | "open", project?: SavedProjectView) => {
    if (busy) return;
    readId.current += 1;
    setBusy(true); setError(""); setNotice("");
    try {
      if (kind === "open" && project) {
        const next = await openSavedProject(project.id, state.review_decisions?.run_id);
        onOpened(next);
        return;
      }
      if (kind === "save") {
        const saved = await saveCurrentProject(state.review_decisions?.run_id);
        setNotice(`已保存 ${saved.name}。项目 ID：${saved.id}`);
      }
      const catalog = await listSavedProjects();
      setProjects(catalog.projects);
    } catch (err) { setError(err instanceof Error ? err.message : "项目操作失败"); }
    finally { setBusy(false); }
  };
  return <section className="saved-projects" aria-label="本地保存的项目" aria-busy={busy}>
    <h3>保存与重开</h3>
    <p>保存原始输入、当前档案及确认事实到本地日志旁，保留评审处理历史。重开会切换当前工作台；未保存的输入修改不会自动保留。</p>
    {!enabled ? <p>当前未启用可恢复项目存储。请启动带 --review-db 的本地服务；离线报告只供查看。</p> : <>
      <div className="saved-project-actions">
        <button className="icon-text-btn" disabled={busy} onClick={() => void operate("save")}>保存当前项目</button>
        <button className="icon-text-btn" disabled={busy} onClick={() => void operate("refresh")}>刷新已保存项目</button>
      </div>
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}。请刷新工作台核对当前项目后重试。</p>}
      {projects.length ? <ul>{projects.map(project => <li key={project.id}>
        <div><strong>{project.name}</strong><small>项目 {project.id}</small><small>输入版本 {project.snapshot}</small></div>
        <button className="icon-text-btn" disabled={busy} aria-label={`打开项目 ${project.name}`} onClick={() => void operate("open", project)}>打开</button>
      </li>)}</ul> : !error && <p>尚无已保存项目。先保存当前评审。</p>}
    </>}
    <p>这是本地项目保存，尚未提供完整备份包。外链原文未自动随附；请保留日志和相邻的 .inputs 目录。</p>
  </section>;
}
