import { useEffect, useReducer, useRef, useState } from "react";
import { ArrowRight, FileDiff, Loader2 } from "lucide-react";
import type { ComparisonResult } from "../generated/workbench-contracts";
import { compareFiles, loadDemo } from "./api";
import { ComparisonResults } from "./ComparisonResults";
import { compareReducer, fileSize, initialState, UPLOAD_KEYS, validateFile, type UploadKey } from "./state";
import "./compare.css";

function UploadSlot({ name, file, error, onChange }: {
  name: UploadKey; file: File | null; error?: string; onChange: (key: UploadKey, file: File | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const netlist = name.endsWith("_netlist");
  const label = `${name.startsWith("before") ? "旧版" : "新版"}${netlist ? "网表" : "BOM"}`;
  return <div className={`revision-upload ${error ? "has-error" : ""} ${file ? "has-file" : ""}`}>
    <label htmlFor={name}><strong>{netlist ? "Telesis 网表" : "BOM 物料清单"}</strong><span>{netlist ? ".net / .txt" : ".csv / .tsv"}</span></label>
    <input ref={input} id={name} type="file" name={name} aria-label={label} aria-invalid={!!error}
      aria-describedby={`${name}-help${error ? ` ${name}-error` : ""}`}
      accept={netlist ? ".net,.txt" : ".csv,.tsv"} onChange={event => {
        const selected = event.currentTarget.files?.[0];
        if (selected) {
          onChange(name, selected);
          if (validateFile(name, selected)) event.currentTarget.value = "";
        }
      }} />
    <div className="revision-file-meta" id={`${name}-help`}>
      {file ? <><span>{file.name} · {fileSize(file.size)}</span><button type="button" aria-label={`移除${label}`} onClick={() => {
        if (input.current) input.current.value = "";
        onChange(name, null);
      }}>移除</button></> : <span>每个文件最多 10 MiB；不接受空文件</span>}
    </div>
    {error && <p className="revision-file-error" id={`${name}-error`} role="alert">{error}</p>}
  </div>;
}

function ResultDownloads({ result, source }: { result: ComparisonResult; source: "files" | "demo" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const download = async (format: "json" | "html") => {
    setBusy(true); setError("");
    try {
      const { buildComparisonHtml, downloadFile } = await import("./report");
      if (!alive.current) return;
      const content = format === "json" ? JSON.stringify(result, null, 2) : buildComparisonHtml(result, source);
      downloadFile(content, format === "json" ? "application/json;charset=utf-8" : "text/html;charset=utf-8", `hardwise-compare-${source}.${format}`);
    } catch {
      if (alive.current) setError("报告生成失败，请重试。当前结果未更改。");
    } finally { if (alive.current) setBusy(false); }
  };
  return <div className="revision-downloads">
    <div><strong>{source === "demo" ? "内置合成示例结果" : "所选文件对比结果"}</strong>
      <p>{source === "demo" ? "服务实际运行示例；不代表上方所选文件。" : "结果与下方输入哈希绑定。"}下载包含全部变化，不受筛选影响。</p></div>
    <button className="revision-button" type="button" disabled={busy} onClick={() => void download("json")}>下载 JSON</button>
    <button className="revision-button" type="button" disabled={busy} onClick={() => void download("html")}>下载离线 HTML</button>
    {busy && <span role="status">正在生成报告…</span>}
    {error && <p role="alert" className="revision-file-error">{error}</p>}
  </div>;
}

export default function CompareApp() {
  const [state, dispatch] = useReducer(compareReducer, initialState);
  const requestSequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    document.title = "Hardwise 改版复核";
    return () => controller.current?.abort();
  }, []);
  const onFile = (key: UploadKey, file: File | null) => {
    controller.current?.abort();
    const error = file ? validateFile(key, file) : null;
    dispatch({ type: "file", key, file: error ? null : file, error: error ?? undefined });
  };
  const run = async (source: "files" | "demo") => {
    controller.current?.abort();
    const activeController = new AbortController();
    controller.current = activeController;
    const requestId = ++requestSequence.current;
    dispatch({ type: "start", requestId, source });
    try {
      const result = await (source === "demo" ? loadDemo(activeController.signal) : compareFiles(state.files, activeController.signal));
      dispatch({ type: "success", requestId, result });
    } catch (error) {
      if (!activeController.signal.aborted) dispatch({ type: "failure", requestId,
        error: error instanceof Error ? error.message : "无法连接对比服务，请检查本地服务后重试。" });
    }
  };
  const ready = UPLOAD_KEYS.every(key => state.files[key] && !state.fileErrors[key]);
  return <main className="revision-app">
    <header className="revision-topbar"><div className="revision-wordmark"><FileDiff size={19} aria-hidden="true" /><span>Hard<b>wise</b></span></div>
      <span className="revision-topbar-label">改版复核 / 双版本对照</span><span className="revision-neutral-badge">确定性对比 · 无需 AI</span></header>
    <div className="revision-content">
      <section className="revision-intro"><div><span className="revision-kicker">只看这次改了什么</span>
        <h1>Hardwise 改版复核</h1><p>两版网表与 BOM，逐项看清器件、属性和连接的变化。</p></div>
        <div className="revision-intro-note">不审整板，不判断改动对错。<br />无需规格书、引脚表或档案批准。</div>
      </section>
      <form className="revision-intake" onSubmit={event => { event.preventDefault(); if (ready && !state.busy) void run("files"); }} aria-busy={!!state.busy}>
        <div className="revision-pair revision-upload-pair">{(["before", "after"] as const).map(side => <fieldset className={`revision-version revision-${side}`} key={side}>
          <legend><span className="revision-version-index">{side === "before" ? "01" : "02"}</span>{side === "before" ? "旧版" : "新版"}<small>{side === "before" ? "对比基准" : "待复核版本"}</small></legend>
          <UploadSlot name={`${side}_netlist`} file={state.files[`${side}_netlist`]} error={state.fileErrors[`${side}_netlist`]} onChange={onFile} />
          <UploadSlot name={`${side}_bom`} file={state.files[`${side}_bom`]} error={state.fileErrors[`${side}_bom`]} onChange={onFile} />
        </fieldset>)}</div>
        <div className="revision-run-bar"><p>仅选取文件不会发送。开始后上传至当前服务；请仅使用公开或合成资料。</p>
          <button className="revision-button" type="button" disabled={!!state.busy} onClick={() => void run("demo")}>加载示例</button>
          <button className="revision-button revision-primary" type="submit" disabled={!ready || !!state.busy}>
            {state.busy === "files" ? <Loader2 size={16} className="revision-spin" aria-hidden="true" /> : <ArrowRight size={16} aria-hidden="true" />}开始对比
          </button></div>
        <p className="revision-intake-hint">{ready ? "四个文件已就绪。修改任一输入会清除旧结果。" : "选择旧版与新版各一份网表、一份 BOM；也可先加载内置合成示例。"}</p>
      </form>
      <div className="revision-feedback" aria-live="polite">
        {state.busy && <p className="revision-busy" role="status"><Loader2 size={18} className="revision-spin" aria-hidden="true" />
          {state.busy === "demo" ? "正在运行内置合成示例…" : "正在上传并比较声明内容…"} 修改输入将取消本次等待。</p>}
        {state.notice && <p className="revision-boundary" role="status">{state.notice}</p>}
      </div>
      {state.error && <section className="revision-error" role="alert"><strong>对比未完成</strong><p>{state.error}</p><p>没有生成新结果。可修正文件后重试，或加载示例检查服务。</p></section>}
      {state.result && state.resultSource ? <>
        <ResultDownloads key={`${state.result.comparison_id}-${state.resultSource}`} result={state.result} source={state.resultSource} />
        <ComparisonResults result={state.result} />
      </> : !state.busy && <section className="revision-awaiting"><FileDiff size={28} aria-hidden="true" /><div><h2>对照结果将在这里呈现</h2>
        <p>确定性变化与未解决项分开列出，每条变化都可展开旧版 / 新版声明及来源。</p></div></section>}
      <footer className="revision-footer">只比较输入实际声明的范围 · 按精确位号关联 · 直接同网线索不是完整电气影响</footer>
    </div>
  </main>;
}
