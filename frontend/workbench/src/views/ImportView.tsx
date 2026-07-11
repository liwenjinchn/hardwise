import { useState, type DragEvent, type FormEvent, type ReactNode } from "react";
import {
  BookOpenCheck,
  FileArchive,
  FileJson,
  FileSpreadsheet,
  Loader2,
  Play,
  UploadCloud
} from "lucide-react";
import { importWorkbench } from "../api";
import { EvidencePackageDashboard } from "../components/EvidencePackageDashboard";
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
  const [documentIndex, setDocumentIndex] = useState<File | null>(null);
  const [pinTable, setPinTable] = useState<File | null>(null);
  const [reviewPackage, setReviewPackage] = useState<File | null>(null);
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
      const result = await importWorkbench({
        netlist,
        bom,
        documentIndex,
        pinTable,
        reviewPackage,
        riskHints
      });
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
        <p className="import-note">
          Capture 引脚表 CSV 来自 Cadence Capture 导出脚本：
          <code>scripts/capture_pin_table_export.tcl</code>。它补充 pin 类型、NC 标记、
          页码和坐标，只生成 review tasks，不改变 PASS/WARN/ERROR 统计口径。
        </p>
      </div>
      <form className="upload-board" onSubmit={(event) => void submit(event)}>
        <UploadSlot
          icon={<UploadCloud size={20} />}
          label="netlist / PST"
          detail={state.project.netlist_type}
          status="required"
          required
          file={netlist}
          accept=".net,.dat,.txt,.pst"
          onPick={setNetlist}
        />
        <UploadSlot
          icon={<FileArchive size={20} />}
          label="BOM CSV"
          detail={`${state.summary.bom_matched} matched refdes`}
          status="optional"
          file={bom}
          accept=".csv,.tsv,.txt"
          onPick={setBom}
        />
        <UploadSlot
          icon={<FileSpreadsheet size={20} />}
          label="Capture 引脚表 CSV"
          detail={pinTableDetail(state)}
          status="optional"
          file={pinTable}
          accept=".csv,.txt"
          onPick={setPinTable}
        />
        <UploadSlot
          icon={<BookOpenCheck size={20} />}
          label="public document index CSV"
          detail={documentIndexDetail(state)}
          status="optional"
          file={documentIndex}
          accept=".csv,.tsv,.txt"
          onPick={setDocumentIndex}
        />
        <UploadSlot
          icon={<FileJson size={20} />}
          label="review-package manifest"
          detail={reviewPackageDetail(state)}
          status="optional"
          file={reviewPackage}
          accept=".yaml,.yml,.json,.txt"
          onPick={setReviewPackage}
        />
        <UploadSlot
          icon={<FileJson size={20} />}
          label="risk hints JSON"
          detail={
            state.capabilities.risk_hints_enabled
              ? `${state.risk_hints.accepted_external_count} accepted hints`
              : "optional external hints"
          }
          status="optional"
          file={riskHints}
          accept=".json"
          onPick={setRiskHints}
        />
        {error && <p className="form-error" role="alert">{error}</p>}
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
        <div className="snapshot-assets" aria-label="导入资产状态">
          <span>Netlist</span>
          <span>BOM {state.summary.bom_matched > 0 ? "loaded" : "pending"}</span>
          <span>引脚表 {state.pin_table.status === "loaded" ? `${state.pin_table.accepted_findings} 条任务` : "未加载"}</span>
          <span>Document index {state.capabilities.document_index_enabled ? "loaded" : "未加载"}</span>
          <span>Review package {state.review_package.status === "loaded" ? state.review_package.package_status : "未加载"}</span>
        </div>
      </div>
      <EvidencePackageDashboard summary={state.evidence_package} className="flow-evidence-dashboard" />
    </section>
  );
}

function UploadSlot(props: {
  icon: ReactNode;
  label: string;
  detail: string;
  status: "required" | "optional";
  required?: boolean;
  file: File | null;
  accept: string;
  onPick: (file: File | null) => void;
}) {
  const [dragging, setDragging] = useState(false);

  const handleDragOver = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setDragging(true);
  };

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    props.onPick(event.dataTransfer.files?.[0] ?? null);
  };

  return (
    <label
      className={`upload-slot ${props.file ? "loaded" : props.status}${
        dragging ? " dragging" : ""
      }`}
      onDragEnter={() => setDragging(true)}
      onDragLeave={() => setDragging(false)}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <span className="upload-icon">{props.icon}</span>
      <span className="upload-status">
        {props.file ? "本次已选择" : props.status === "required" ? "本次必选" : "本次可选"}
      </span>
      <strong>{props.label}{props.required ? " *" : ""}</strong>
      <em>当前工作台：{props.detail}</em>
      <small>
        {props.file ? `本次文件：${props.file.name}` : "本次未选择 · 拖入文件或点击选择"}
      </small>
      <input
        type="file"
        accept={props.accept}
        aria-label={`选择 ${props.label}`}
        onChange={(event) => props.onPick(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}

function pinTableDetail(state: WorkbenchState): string {
  if (state.pin_table.status !== "loaded") return "optional script export";
  const checks = Object.entries(state.pin_table.checks)
    .map(([rule, count]) => `${rule} ${count}`)
    .join(" / ");
  return `${state.pin_table.accepted_findings} 条任务 · ${checks || "引脚检查"}`;
}

function reviewPackageDetail(state: WorkbenchState): string {
  if (state.review_package.status !== "loaded") return "optional evidence manifest";
  return `${state.review_package.package_status} · manual gaps ${state.review_package.manual_gap_count}`;
}

function documentIndexDetail(state: WorkbenchState): string {
  const lane = state.evidence_package.lanes.find((item) => item.id === "documents");
  if (!lane || lane.status === "not_configured") return "optional reviewed public index";
  return `${lane.status_label} · ${lane.summary}`;
}
