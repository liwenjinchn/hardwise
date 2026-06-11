import { useState, type FormEvent, type ReactNode } from "react";
import { FileArchive, FileUp, Loader2, Play, UploadCloud } from "lucide-react";
import { importWorkbench } from "../api";
import type { ImportResponse, WorkbenchState } from "../types";

export function ImportView({
  state,
  onImported
}: {
  state: WorkbenchState;
  onImported: (result: ImportResponse) => void;
}) {
  const [netlist, setNetlist] = useState<File | null>(null);
  const [bom, setBom] = useState<File | null>(null);
  const [riskHints, setRiskHints] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!netlist || busy) {
      setError("请选择 netlist/PST 文件。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await importWorkbench({ netlist, bom, riskHints });
      onImported(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flow-page import-page">
      <div className="flow-copy">
        <span className="eyebrow">Import</span>
        <h2>上传 netlist / BOM，重建当前工作台</h2>
        <p>
          文件只写入本进程临时目录。上传成功后后端会重新运行
          WorkbenchContext，浏览器进入 Parse 动画，再回到 Review。
        </p>
      </div>
      <form className="upload-board" onSubmit={(event) => void submit(event)}>
        <UploadSlot
          icon={<UploadCloud size={20} />}
          label="netlist / PST"
          required
          file={netlist}
          accept=".net,.dat,.txt,.pst"
          onPick={setNetlist}
        />
        <UploadSlot
          icon={<FileArchive size={20} />}
          label="BOM CSV"
          file={bom}
          accept=".csv,.tsv,.txt"
          onPick={setBom}
        />
        <UploadSlot
          icon={<FileUp size={20} />}
          label="risk hints JSON"
          file={riskHints}
          accept=".json"
          onPick={setRiskHints}
        />
        {error && <p className="form-error">{error}</p>}
        <button className="primary-action" type="submit" disabled={busy}>
          {busy ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
          {busy ? "正在导入" : "导入并解析"}
        </button>
      </form>
      <div className="current-snapshot">
        <span className="eyebrow">当前工作台</span>
        <strong>{state.summary.components} components</strong>
        <p>
          已验证 {state.summary.validated}，PASS/WARN/ERROR=
          {state.summary.pass_count}/{state.summary.warn_count}/{state.summary.error_count}，
          manual={state.summary.manual}
        </p>
      </div>
    </section>
  );
}

function UploadSlot(props: {
  icon: ReactNode;
  label: string;
  required?: boolean;
  file: File | null;
  accept: string;
  onPick: (file: File | null) => void;
}) {
  return (
    <label className="upload-slot">
      <span>{props.icon}</span>
      <strong>{props.label}{props.required ? " *" : ""}</strong>
      <small>{props.file?.name ?? "选择文件"}</small>
      <input
        type="file"
        accept={props.accept}
        onChange={(event) => props.onPick(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}
