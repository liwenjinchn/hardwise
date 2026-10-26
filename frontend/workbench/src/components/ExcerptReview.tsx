import { useEffect, useState } from "react";
import type { ExcerptEdit, ExcerptResponse } from "../generated/workbench-contracts";
import type { WorkbenchState } from "../types";
import { fetchWorkbenchState, isOfflineWorkbench } from "../api";
import { ExcerptError, fetchExcerpts, saveExcerpt } from "../excerpt-api";
import { ExcerptFields } from "./ExcerptFields";

interface Draft { project: string; name: string; value: unknown; edit: ExcerptEdit; needsIdentity: boolean }
const sharingLabels: Record<string, string> = { allowed: "允许分享", withheld: "不分享", undeclared: "未声明", stale: "声明失效" };
export function ExcerptReview({ state, onUpdated }: { state: WorkbenchState; onUpdated: (state: WorkbenchState) => void }) {
  const offline = isOfflineWorkbench();
  const [data, setData] = useState<ExcerptResponse | null>(null);
  const [name, setName] = useState(""); const [pointer, setPointer] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false); const [stale, setStale] = useState(false);
  const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [checkedRevision, setCheckedRevision] = useState("");
  useEffect(() => {
    let active = true;
    fetchExcerpts().then(next => { if (active) setData(next); }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);
  const outOfSync = !!data && (data.project_id !== state.review_decisions?.project_id || data.run_id !== state.review_decisions?.run_id);
  const selected = data?.profiles.find(p => p.name === name);
  const current = data?.profiles.find(p => p.name === draft?.name);
  const currentField = current?.profile.field_review?.fields.find(f => f.pointer === draft?.edit.pointer);
  const compatible = !!draft && !!data && draft.project === data.project_id && !!current &&
    Object.hasOwn(current.values, draft.edit.pointer) && JSON.stringify(current.values[draft.edit.pointer]) === JSON.stringify(draft.value);
  const editable = !!data?.editable && !offline && !busy && !stale && !outOfSync && compatible &&
    current?.lifecycle !== "RETIRED" && checkedRevision === data.revision;
  const loadField = () => {
    if (!selected || !pointer || !data) return;
    const field = selected.profile.field_review?.fields.find(f => f.pointer === pointer);
    const source = field ? { ...field.source } : { url: "", document_revision: "", document_sha256: "", page: 1, locator: "", excerpt: "" };
    delete source.sharing;
    setDraft({ project: data.project_id, name, value: selected.values[pointer], needsIdentity: !selected.profile.field_review,
      edit: { pointer, source, unit: field?.unit ?? "", role: field?.role ?? "definition", nature: field?.nature ?? "intrinsic",
        conditions: field?.conditions ?? [{ kind: "unsupported", description: "" }],
        identity: selected.profile.field_review?.identity ?? { manufacturer: "", part_numbers: [selected.profile.part_number], packages: [""] },
        sharing: "withhold", declared_by: "", reason: "" }
    });
    setCheckedRevision(""); setError(""); setNotice("已读取字段；请明确选择本次分享范围并核对后保存。");
  };
  const reload = async () => {
    setBusy(true); setError(""); setCheckedRevision("");
    try {
      const next = await fetchExcerpts();
      const currentState = await fetchWorkbenchState();
      if (!next || next.project_id !== currentState.review_decisions?.project_id || next.run_id !== currentState.review_decisions?.run_id) throw new Error("刷新期间项目再次变化，请重试。");
      setData(next); onUpdated(currentState); setStale(false);
      setNotice("已刷新当前资料，草稿保持不变。请对照当前记录重新核对；跨项目或参数值变化的草稿不能直接提交。");
    } catch (err) { setStale(true); setError((err as Error).message); } finally { setBusy(false); }
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); if (!editable || !draft || !data) return;
    setBusy(true); setError(""); setNotice(""); let saved = false;
    try {
      const next = await saveExcerpt({ expected_project_id: data.project_id, expected_run_id: data.run_id,
        expected_revision: data.revision, profile_name: draft.name, edit: draft.edit });
      saved = true; setData(next); setCheckedRevision("");
      const currentState = await fetchWorkbenchState();
      if (next.project_id !== currentState.review_decisions?.project_id || next.run_id !== currentState.review_decisions?.run_id) throw new Error("保存后运行已变化");
      onUpdated(currentState); setNotice("摘录与分享声明已保存，检查已重跑；原输入和历史保留。此操作不批准电气参数。");
    } catch (err) {
      if (saved || err instanceof ExcerptError && (err.status === 409 || err.status === 0 || err.status >= 500)) setStale(true);
      setCheckedRevision(""); setError(saved ? "修改已保存，但界面同步未完成。草稿保留，请刷新核对，勿重复提交。" : (err as Error).message);
    } finally { setBusy(false); }
  };
  return <section className="current-snapshot excerpt-review" aria-label="人工资料摘录">
    <h3>资料摘录 · 人工录入与分享范围</h3>
    <p>将来源原文与现有参数、单位和适用条件一起核对。分享声明是人工声明，不是权利认证或电气批准。仅使用公开或合成资料。</p>
    {offline ? <p>离线报告只读；允许分享的摘录可在运行清单中查看。录入和修订请打开本地工作台。</p> : <>
      <button className="icon-text-btn" disabled={busy} onClick={() => void reload()}>刷新资料，保留草稿</button>
      {error && <p role="alert" className="form-error">{error}</p>}{notice && <p role="status">{notice}</p>}
      {(stale || outOfSync) && <p role="alert">当前版本已变化或保存结果未确认。草稿保留，请刷新核对后继续。</p>}
      {data && <>
        {!data.editable && <p>当前只读，启用本地评审日志后才可保存。</p>}
        <div className="voltage-form-grid">
          <label>器件档案<select aria-label="摘录器件档案" value={name} disabled={busy} onChange={e => { setName(e.target.value); setPointer(""); }}><option value="">选择档案</option>{data.profiles.map(p => <option key={p.name} value={p.name}>{p.profile.part_number} · {p.name} · {p.lifecycle}</option>)}</select></label>
          <label>现有参数<select aria-label="摘录参数字段" value={pointer} disabled={busy} onChange={e => setPointer(e.target.value)}><option value="">选择字段</option>{Object.entries(selected?.values ?? {}).filter(([, v]) => v !== null).map(([key, value]) => <option key={key} value={key}>{key} = {String(value)}</option>)}</select></label>
        </div>
        <button className="icon-text-btn" disabled={!pointer || busy || stale || outOfSync} onClick={loadField}>{draft ? "读取所选字段并替换草稿" : "读取所选字段"}</button>
      </>}
      {draft && <form onSubmit={event => void submit(event)}>
        <h4>{draft.name} · {draft.edit.pointer}</h4><p>参数值：<strong>{String(draft.value)}</strong>（由档案提供，此处不改值）</p>
        <details open><summary>当前已保存记录（与下方草稿独立）</summary>
          {!compatible ? <p>项目或参数值已变；请保留所需文字后重新读取字段。</p> : currentField ? <div className="excerpt-current">
            <p>原文分享：{sharingLabels[current?.sharing_states[draft.edit.pointer] ?? "undeclared"]}；档案状态：{current?.lifecycle}</p>
            <p>单位 {currentField.unit}；角色 {currentField.role}；主体 {currentField.subject}</p>
            <p>{currentField.source.url} · {currentField.source.document_revision} · 第 {currentField.source.page} 页 · {currentField.source.locator}</p>
            <p>文档 SHA256：{currentField.source.document_sha256}</p>
            <blockquote>{currentField.source.excerpt}</blockquote>
            {currentField.conditions.map((c, i) => <p key={i}>{c.kind}：{c.description}</p>)}
            {currentField.source.sharing && <p>声明人 {currentField.source.sharing.declared_by} · {currentField.source.sharing.declared_at} · {currentField.source.sharing.reason}</p>}
          </div> : <p>该字段尚无人工来源记录。</p>}
        </details>
        <fieldset disabled={busy || !data?.editable} className="excerpt-editor"><legend>本次草稿</legend>
          <ExcerptFields edit={draft.edit} needsIdentity={draft.needsIdentity} onChange={edit => { setDraft({ ...draft, edit }); setCheckedRevision(""); }} />
          <p>改动来源或参数解释后，原电气批准会失效；仅改分享声明不改变原电气批准。完整本地备份仍保留原文，已发出的旧报告无法追回。</p>
          <label><input type="checkbox" aria-label="已核对当前来源和草稿" checked={!!data && checkedRevision === data.revision} disabled={!compatible || stale || outOfSync} onChange={e => setCheckedRevision(e.target.checked ? data!.revision : "")} />我已对照当前记录核对来源、参数条件和本次分享声明</label>
          <button className="primary-action" type="submit" disabled={!editable}>{busy ? "正在保存" : "保存摘录与分享声明"}</button>
        </fieldset>
      </form>}
    </>}
  </section>;
}
