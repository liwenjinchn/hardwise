import type { ComparisonResult, RevisionChange } from "../generated/workbench-contracts";

export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const UPLOAD_KEYS = ["before_netlist", "before_bom", "after_netlist", "after_bom"] as const;
export type UploadKey = typeof UPLOAD_KEYS[number];
export type UploadFiles = Record<UploadKey, File | null>;
export type ChangeFilter = "all" | RevisionChange["kind"];
export const KIND_LABELS: Record<RevisionChange["kind"], string> = {
  component_added: "器件新增",
  component_removed: "器件移除",
  attribute_changed: "属性变化",
  connection_changed: "连接变化",
  net_renamed: "网络改名"
};

export function validateFile(key: UploadKey, file: Pick<File, "name" | "size">): string | null {
  const netlist = key.endsWith("_netlist");
  if (!(netlist ? /\.(net|txt)$/i : /\.(csv|tsv)$/i).test(file.name)) {
    return netlist ? "请选择 .net 或 .txt 格式的 Telesis 网表。" : "请选择 .csv 或 .tsv 格式的 BOM。";
  }
  if (file.size === 0) return "文件为空，请重新选择。";
  if (file.size > MAX_FILE_BYTES) return "单文件不能超过 10 MiB。";
  return null;
}

export function fileSize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KiB` : `${(bytes / 1024 / 1024).toFixed(2)} MiB`;
}

export function filterChanges(changes: RevisionChange[], kind: ChangeFilter, query: string) {
  const needle = query.trim().toLowerCase();
  return changes.filter(change => (kind === "all" || change.kind === kind) &&
    (!needle || change.refdes.toLowerCase().includes(needle)));
}

export type CompareState = {
  files: UploadFiles;
  fileErrors: Partial<Record<UploadKey, string>>;
  result: ComparisonResult | null;
  resultSource: "files" | "demo" | null;
  busy: "files" | "demo" | null;
  activeRequest: number | null;
  error: string;
  notice: string;
};
export const initialState: CompareState = {
  files: { before_netlist: null, before_bom: null, after_netlist: null, after_bom: null },
  fileErrors: {}, result: null, resultSource: null, busy: null, activeRequest: null, error: "", notice: ""
};
export type CompareAction =
  | { type: "file"; key: UploadKey; file: File | null; error?: string }
  | { type: "start"; requestId: number; source: "files" | "demo" }
  | { type: "success"; requestId: number; result: ComparisonResult }
  | { type: "failure"; requestId: number; error: string };

export function compareReducer(state: CompareState, action: CompareAction): CompareState {
  switch (action.type) {
    case "file":
      return { ...state, files: { ...state.files, [action.key]: action.file },
        fileErrors: { ...state.fileErrors, [action.key]: action.error }, result: null, resultSource: null,
        activeRequest: null, busy: null, error: "",
        notice: state.result || state.busy || state.notice ? "输入已变更，旧结果已清除。请重新开始对比。" : "" };
    case "start":
      return { ...state, result: null, resultSource: null, activeRequest: action.requestId,
        busy: action.source, error: "", notice: "" };
    case "success":
      if (state.activeRequest !== action.requestId) return state;
      return { ...state, result: action.result, resultSource: state.busy, busy: null, activeRequest: null };
    case "failure":
      if (state.activeRequest !== action.requestId) return state;
      return { ...state, error: action.error, result: null, resultSource: null, busy: null, activeRequest: null };
  }
}
