import { useState, type FormEvent } from "react";
import type { VoltageCandidate } from "../generated/workbench-contracts";

export function VoltageCandidateForm({ nets, candidates, mode, busy, onSave }: {
  nets: string[]; candidates: VoltageCandidate[]; mode: string; busy: boolean; onSave: (candidate: VoltageCandidate) => Promise<boolean>;
}) {
  const [draftId, setDraftId] = useState("");
  const [editing, setEditing] = useState<VoltageCandidate | null>(null);
  const [net, setNet] = useState(""); const [reference, setReference] = useState("");
  const [draftMode, setMode] = useState(mode);
  const [minimum, setMinimum] = useState(""); const [maximum, setMaximum] = useState("");
  const [typical, setTypical] = useState(""); const [source, setSource] = useState("");
  const [locator, setLocator] = useState(""); const [error, setError] = useState("");
  const populate = (candidate: VoltageCandidate) => {
    setEditing(candidate); setNet(candidate.fact.net); setReference(candidate.fact.reference_net);
    setMode(candidate.fact.mode); setMinimum(candidate.fact.minimum?.toString() ?? "");
    setMaximum(candidate.fact.maximum?.toString() ?? ""); setTypical(candidate.fact.typical?.toString() ?? "");
    setSource(candidate.fact.source); setLocator(candidate.locator); setError("");
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError("");
    if (editing && JSON.stringify(candidates.find(candidate => candidate.id === editing.id)) !== JSON.stringify(editing)) {
      setError("该候选在草稿填写后已变化。草稿仍保留；请重新读取候选，再核对修订。"); return;
    }
    const number = (text: string) => text.trim() === "" ? null : Number(text);
    const values = [number(minimum), number(maximum), number(typical)];
    if (values.some(value => value !== null && !Number.isFinite(value))) { setError("电压必须是有限数值；留空表示未知。"); return; }
    const [low, high, nominal] = values;
    if (low !== null && high !== null && low > high) { setError("最小电压不能大于最大电压。"); return; }
    if (nominal !== null && (low !== null && nominal < low || high !== null && nominal > high)) { setError("典型电压必须在已填写的上下限内。"); return; }
    if (net === reference && values.some(value => value !== null && value !== 0)) { setError("网络相对自身的电压只能是零或未知。"); return; }
    const id = editing?.id ?? (draftId || crypto.randomUUID()); if (!editing) setDraftId(id);
    const ok = await onSave({ id, origin: "manual", locator,
      fact: { net, reference_net: reference, mode: draftMode, unit: "V", minimum: values[0], maximum: values[1], typical: values[2], source, confirmed: false, confirmed_by: "" }
    });
    if (ok) { setDraftId(""); setEditing(null); setMinimum(""); setMaximum(""); setTypical(""); setSource(""); setLocator(""); }
  };
  return <div className="voltage-candidate-form">
    <form onSubmit={event => void submit(event)}>
      <h4>{editing ? `修订候选 ${editing.fact.net}` : "新增来源候选"}</h4>
      <p>来源候选不等于确认事实。典型值不能替代上下限；不确定的数值可留空。</p>
      <div className="voltage-form-grid">
        <label>网络<select aria-label="候选网络" required value={net} onChange={event => setNet(event.target.value)}><option value="">请选择</option>{nets.map(n => <option key={n}>{n}</option>)}</select></label>
        <label>参考网络<select aria-label="候选参考网络" required value={reference} onChange={event => setReference(event.target.value)}><option value="">请选择</option>{nets.map(n => <option key={n}>{n}</option>)}</select></label>
        <label>工况<input aria-label="候选工况" required value={draftMode} onChange={event => setMode(event.target.value)} /></label>
        <label>最小电压 V<input aria-label="候选最小电压" inputMode="decimal" value={minimum} onChange={event => setMinimum(event.target.value)} /></label>
        <label>最大电压 V<input aria-label="候选最大电压" inputMode="decimal" value={maximum} onChange={event => setMaximum(event.target.value)} /></label>
        <label>典型电压 V<input aria-label="候选典型电压" inputMode="decimal" value={typical} onChange={event => setTypical(event.target.value)} /></label>
        <label>来源<input aria-label="候选来源" required value={source} onChange={event => setSource(event.target.value)} /></label>
        <label>来源定位<input aria-label="候选来源定位" required value={locator} onChange={event => setLocator(event.target.value)} /></label>
      </div>
      {error && <p role="alert">{error}</p>}
      <button className="icon-text-btn" disabled={busy} type="submit">{editing ? "保存候选修订（需重新确认）" : "添加候选（尚未确认）"}</button>
      {editing && <>
        <button className="icon-text-btn" type="button" disabled={busy} onClick={() => {
          const latest = candidates.find(candidate => candidate.id === editing.id);
          if (latest) populate(latest); else setError("该候选已移除，不能覆盖保存。可取消修订后明确新增来源。");
        }}>重新读取选中候选（覆盖表单草稿）</button>
        <button className="icon-text-btn" type="button" onClick={() => setEditing(null)}>取消修订</button>
      </>}
    </form>
    <label>选择已有候选修订<select aria-label="选择已有候选修订" value={editing?.id ?? ""} onChange={event => {
      const candidate = candidates.find(item => item.id === event.target.value);
      if (candidate) populate(candidate); else setEditing(null);
    }}><option value="">新增候选</option>{candidates.map(candidate => <option value={candidate.id} key={candidate.id}>{candidate.fact.net} / {candidate.fact.mode} · {candidate.fact.source}</option>)}</select></label>
  </div>;
}

