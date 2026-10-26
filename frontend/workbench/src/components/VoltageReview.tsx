import { useEffect, useState } from "react";
import type { VoltageBatchRequest, VoltageCandidate, VoltageCandidatesRequest, VoltageReviewResponse } from "../generated/workbench-contracts";
import type { WorkbenchState } from "../types";
import { fetchWorkbenchState } from "../api";
import { confirmVoltageReview, editVoltageCandidates, fetchVoltageReview, VoltageReviewError } from "../voltage-review-api";
import { VoltageCandidateForm } from "./VoltageCandidateForm";

const labels = { unconfirmed: "待确认", conflict: "来源冲突", confirmed: "已确认", unknown: "保留未知", needs_review: "需重新复核" };
const scopeKey = (net: string, mode: string) => JSON.stringify([net, mode]);
export function VoltageReview({ state, onUpdated }: { state: WorkbenchState; onUpdated: (state: WorkbenchState) => void }) {
  const offline = typeof window !== "undefined" && !!window.__HARDWISE_OFFLINE_SNAPSHOT__;
  const [data, setData] = useState<VoltageReviewResponse | null>(null);
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(""); const [notice, setNotice] = useState(""); const [stale, setStale] = useState(false);
  const [reviewer, setReviewer] = useState(""); const [reason, setReason] = useState("");
  const [choices, setChoices] = useState<Record<string, string>>({}); const [mode, setMode] = useState("");
  useEffect(() => {
    let live = true; setLoading(true); setChoices({});
    fetchVoltageReview().then(value => { if (live) { setData(value); setMode(value?.review.active_mode ?? "");
        const changed = !!value && !offline && (value.project_id !== state.review_decisions?.project_id || value.run_id !== state.review_decisions?.run_id);
        setStale(changed); if (changed) setError("项目或运行已变化，请刷新候选和当前检查结果后继续。"); } })
      .catch(err => { if (live) setError(String(err.message)); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [state.review_decisions?.project_id, state.review_decisions?.run_id]);
  const reload = async () => {
    setBusy(true); setError("");
    try {
      const next = await fetchVoltageReview();
      if (next && !offline) {
        const current = await fetchWorkbenchState();
        if (current.review_decisions?.project_id !== next.project_id || current.review_decisions?.run_id !== next.run_id) throw new Error("刷新期间项目再次变化，请重试。");
        onUpdated(current);
      }
      setData(next); setMode(next?.review.active_mode ?? ""); setChoices({}); setStale(false);
      setNotice("候选与检查结果已刷新；请重新选择并核对。确认人和理由草稿仍保留。");
    }
    catch (err) { setStale(true); setError((err as Error).message); } finally { setBusy(false); }
  };
  const editable = !!data?.editable && !stale && !busy && !loading;
  const metadata = () => {
    if (!data || !reviewer.trim() || !reason.trim()) throw new Error("请填写确认人和本次操作理由。");
    return { expected_project_id: data.project_id, expected_run_id: data.run_id, expected_revision: data.revision, reviewer, reason };
  };
  const operate = async (action: () => Promise<VoltageReviewResponse>): Promise<boolean> => {
    setBusy(true); setError(""); setNotice(""); let saved = false;
    try {
      const next = await action(); saved = true; setData(next); setChoices({}); setMode(next.review.active_mode);
      const current = await fetchWorkbenchState();
      if (current.review_decisions?.project_id !== next.project_id || current.review_decisions?.run_id !== next.run_id) throw new Error("保存后当前项目或运行已变化。");
      onUpdated(current); setNotice("已保存独立输入版本并重跑检查；原输入和历史保留。更改候选不会自动确认。"); return true;
    } catch (err) {
      if (saved || err instanceof VoltageReviewError && (err.status === 409 || err.status === 0 || err.status >= 500)) setStale(true);
      setError(saved ? "修改已保存，但界面同步未完成。请刷新当前项目，勿重复提交。" : (err as Error).message); return false;
    } finally { setBusy(false); }
  };
  const confirm = () => void operate(async () => {
    const selections = (data?.scopes ?? []).flatMap(scope => {
      const value = choices[scopeKey(scope.net, scope.mode)]; if (!value) return [];
      const choice = JSON.parse(value) as { action: "confirm" | "unknown"; id?: string };
      return [{ net: scope.net, mode: scope.mode, action: choice.action, candidate_id: choice.id ?? null, expected_scope_sha256: scope.scope_sha256 }];
    });
    if (!selections.length) throw new Error("请至少选择一项候选或保留未知操作。");
    return confirmVoltageReview({ ...metadata(), selections } as VoltageBatchRequest);
  });
  const edit = (upserts: VoltageCandidate[], remove_ids: string[], active_mode: string | null = null) => operate(async () => editVoltageCandidates({ ...metadata(), upserts, remove_ids, active_mode } as VoltageCandidatesRequest));
  return <section className="current-snapshot voltage-review" aria-label="多来源电压事实确认">
    <h3>电压事实 · 多来源复核</h3>
    <p>按网络和工况选择有依据的来源后批量确认。冲突未解决时保持未知，其余检查继续。确认是用户声明，不等于测量或器件档案批准。</p>
    <button className="icon-text-btn" disabled={busy} onClick={() => void reload()}>刷新电压候选</button>
    {loading && <p>正在读取候选和确认记录…</p>}
    {error && <p role="alert" className="form-error">{error}</p>}{notice && <p role="status">{notice}</p>}
    {!loading && !data && <p>此旧离线报告未包含候选账本；已确认数值仍可在下方查看。请从新版工作台重新导出。</p>}
    {data && <>
      {!data.editable && <p>当前只读。离线报告不能确认；在线编辑需启用本地 SQLite 日志。已有候选与历史仍可查看。</p>}
      <p>活动工况：<strong>{data.review.active_mode}</strong> · 候选 {data.review.candidates.length} 条 · 确认／撤回记录 {data.review.confirmations.length} 条 · 修订 {data.review.edits?.length ?? 0} 次</p>
      {data.editable && <fieldset className="voltage-metadata" disabled={!editable}>
        <legend>本次人工操作记录</legend>
        <label>确认人<input aria-label="电压确认人" value={reviewer} onChange={event => setReviewer(event.target.value)} /></label>
        <label>理由<input aria-label="电压操作理由" value={reason} onChange={event => setReason(event.target.value)} /></label>
        <label>活动工况<input aria-label="活动工况" value={mode} onChange={event => setMode(event.target.value)} /></label>
        <button className="icon-text-btn" disabled={mode.trim() === data.review.active_mode} onClick={() => void edit([], [], mode)}>保存工况并重跑</button>
      </fieldset>}
      <div className="voltage-scopes">
        {data.scopes.map(scope => <article className={`voltage-scope status-${scope.status}`} key={scopeKey(scope.net, scope.mode)}>
          <header><strong>{scope.net} / {scope.mode}</strong><span>{labels[scope.status]}</span></header>
          {scope.candidate_ids.map(id => {
            const c = data.review.candidates.find(item => item.id === id); if (!c) return null;
            return <div className="voltage-candidate" key={id}>
              {scope.selected_candidate_id === id && <p><strong>当前已确认来源</strong></p>}
              <p><strong>{c.fact.minimum ?? "未知"} 至 {c.fact.maximum ?? "未知"} V</strong> · 典型 {c.fact.typical ?? "未知"} V · 参考 {c.fact.reference_net}</p>
              <p>来源：{c.fact.source} · 定位：{c.locator} · {c.origin === "legacy_v1" ? "旧版输入保留" : c.origin === "net_name" ? "网名候选，不自动确认" : "来源候选"}</p>
              {data.editable && <button className="icon-text-btn" disabled={!editable} onClick={() => void edit([], [c.id])} aria-label={`移除候选 ${c.fact.net} ${c.locator}`}>移除候选（保留历史）</button>}
            </div>;
          })}
          {!scope.candidate_ids.length && <p>当前候选已移除；原确认记录仍保留。</p>}
          {data.editable && <label>本次处理<select aria-label={`电压处理 ${scope.net} ${scope.mode}`} disabled={!editable} value={choices[scopeKey(scope.net, scope.mode)] ?? ""} onChange={event => setChoices({ ...choices, [scopeKey(scope.net, scope.mode)]: event.target.value })}>
            <option value="">不处理此项</option><option value={JSON.stringify({ action: "unknown" })}>保留未知／撤回确认</option>
            {scope.candidate_ids.map(id => { const c = data.review.candidates.find(item => item.id === id); return c && <option value={JSON.stringify({ action: "confirm", id })} key={id}>确认 {c.fact.source} · {c.fact.minimum ?? "?"} 至 {c.fact.maximum ?? "?"} V（{c.fact.reference_net}）</option>; })}
          </select></label>}
        </article>)}
      </div>
      {!data.scopes.length && <p>尚无来源候选。可添加已知网络的资料或人工输入；不会根据网名自动确认电压。</p>}
      {data.editable && <>
        <button className="icon-text-btn" disabled={!editable} onClick={() => {
          const next = { ...choices }; for (const scope of data.scopes) {
            const c = data.review.candidates.find(item => item.id === scope.candidate_ids[0]);
            if (scope.mode === data.review.active_mode && scope.candidate_ids.length === 1 && c && c.origin !== "net_name") next[scopeKey(scope.net, scope.mode)] = JSON.stringify({ action: "confirm", id: c.id });
          } setChoices(next);
        }}>选中本工况单一候选（待提交）</button>
        <button className="primary-action" disabled={!editable || !Object.values(choices).some(Boolean)} onClick={confirm}>提交所选电压操作并重跑</button>
        <VoltageCandidateForm key={data.review.active_mode} nets={data.nets} candidates={data.review.candidates} mode={data.review.active_mode} busy={!editable} onSave={candidate => edit([candidate], [])} />
      </>}
      <details><summary>确认与修订历史（{data.review.confirmations.length + (data.review.edits?.length ?? 0)}）</summary>
        {data.review.confirmations.map(d => <p key={d.id}>{d.net} / {d.mode} · {d.action === "confirm" ? "确认候选" : "保留未知／撤回"} · {d.reviewer} · {d.reason} · {d.origin === "legacy_v1" ? "旧声明保留，不是新批准" : d.recorded_at}</p>)}
        {data.review.edits?.map(edit => <div key={edit.id}><p>候选修订／工况：{edit.reviewer} · {edit.reason} · {edit.recorded_at} · {edit.previous_mode} → {edit.active_mode}</p>
          {edit.changes.map((change, index) => <p key={index}>{change.before ? `${change.before.fact.net}: ${change.before.fact.minimum ?? "?"} 至 ${change.before.fact.maximum ?? "?"} V / ${change.before.fact.source}` : "新增"} → {change.after ? `${change.after.fact.net}: ${change.after.fact.minimum ?? "?"} 至 ${change.after.fact.maximum ?? "?"} V / ${change.after.fact.source}` : "移除（原值保留）"}</p>)}
        </div>)}
      </details>
    </>}
  </section>;
}
