import type {
  EvidenceChainItem,
  ReviewQueueItem,
  StatusGroup,
  TrustTier
} from "../types";

export const TRUST_LABEL: Record<TrustTier, string> = {
  l1: "L1 确定性",
  l2: "L2 有出处",
  l3: "L3 人工确认"
};

export function attentionLabel(group: StatusGroup): string {
  const labels: Record<StatusGroup, string> = {
    error: "必须修",
    warn: "看证据",
    manual: "人工判断",
    pass: "已通过"
  };
  return labels[group];
}

export function statusGroup(status: string): StatusGroup {
  if (status === "ERROR") return "error";
  if (status === "WARN") return "warn";
  if (status === "PASS") return "pass";
  return "manual";
}

export function pinStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ERROR: "必须修",
    WARN: "看证据",
    PASS: "通过",
    manual_needed: "人工判断",
    profile_missing: "待补档案",
    bom_missing: "BOM 缺失"
  };
  return labels[status] ?? statusLabelFromRaw(status);
}

export function statusLabelFromRaw(status: string): string {
  return status
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function profileStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: "已匹配",
    exact: "已匹配",
    ambiguous: "需确认",
    not_found: "未匹配",
    manual_needed: "待补档案",
    profile_missing: "待补档案"
  };
  return labels[status] ?? statusLabelFromRaw(status || "unknown");
}

export function documentStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    matched: "已索引",
    loaded: "已索引",
    not_configured: "未配置",
    not_found: "未找到",
    unknown: "未知"
  };
  return labels[status] ?? statusLabelFromRaw(status || "unknown");
}

export function queueSubtitle(item: ReviewQueueItem): string {
  const identity = [
    item.part_number || item.value || "无 MPN",
    item.package
  ].filter(Boolean).join(" · ");
  const cues = [
    item.evidence_count ? `${item.evidence_count} 条证据` : "",
    item.risk_hint_count ? `${item.risk_hint_count} 条外部提示` : ""
  ].filter(Boolean).join(" / ");
  return `${identity}${cues ? ` · ${cues}` : ""}`;
}

export function sourceLabel(sourceClass: string): string {
  const labels: Record<string, string> = {
    live_retrieved: "本轮检索",
    reviewed_profile: "已审档案",
    document_index: "资料索引",
    design_source: "设计来源",
    unknown: "未知来源"
  };
  return labels[sourceClass] ?? sourceClass;
}

export function evidenceNodeKind(item: EvidenceChainItem): string {
  if (item.trust_tier === "l3" || item.kind.includes("external") || item.kind.includes("manual")) {
    return "manual";
  }
  if (item.evidence.some((evidence) => evidence.source_class === "live_retrieved")) {
    return "grounded";
  }
  return "deterministic";
}

const SUMMARY_REPLACEMENTS: Array<[RegExp, string]> = [
  [/Exactly one local profile part_number matched this BOM identity\./g, "已唯一匹配本地器件档案。"],
  [/BJT emitter pin is not connected\./g, "BJT 发射极未连接。"],
  [/BJT emitter pin is not connected; cannot check VEBO\./g, "BJT 发射极未连接，无法检查 VEBO。"],
  [/BJT emitter pin is not connected; cannot check VCEO\./g, "BJT 发射极未连接，无法检查 VCEO。"],
  [/BJT collector is connected to ([^.]+)\./g, "BJT 集电极连接到 $1。"],
  [/BJT base is connected to ([^.]+)\./g, "BJT 基极连接到 $1。"],
  [/BJT Vebo rating must exceed reverse base-emitter stress\./g, "BJT Vebo 额定值需要覆盖反向基极-发射极应力。"],
  [/MCU SWDIO is connected to SWCLK, expected SWDIO\./g, "MCU SWDIO 接到了 SWCLK，期望连接到 SWDIO。"],
  [/R(\d{3}) · ([A-Z]+\d*) pin (\d+) \(([^)]+)\) is a POWER pin with no net at ([^@.]+)@([^,]+),([^.]+)\./g, "R$1 · $2 的 $3 脚（$4）是电源脚，但在原理图 $5 页没有连接网络。"],
  [/([A-Z]+\d*) pin (\d+) \(([^)]+)\) is a POWER pin with no net at ([^@.]+)@([^,]+),([^.]+)\./g, "$1 的 $2 脚（$3）是电源脚，但在原理图 $4 页没有连接网络。"],
  [/Pin-table row: ([A-Z]+\d*)\.(\d+) type ([^,]+), net empty, nc_marker (\d+) \(page ([^,]+), x=([^,]+), y=([^)]+)\)\./g, "Capture 引脚表显示：$1.$2 类型为 $3，网络为空，NC 标记为 $4，位于原理图 $5 页。"],
  [/Connect the pin to its supply\/ground net, or document the omission with an explicit NC marker and a design note\./g, "把该引脚接到对应电源/地网络；如果确实不接，需要用明确 NC 标记和设计说明记录原因。"],
  [/No deterministic capacitance value could be parsed from '([^']+)'\./g, "无法从 '$1' 确定性解析电容值。"],
  [/Diode reverse voltage rating is about ([^,]+), below required ([^.]+)\./g, "二极管反向耐压约 $1，低于所需 $2。"],
  [/Input network voltage falls within the structured component profile limit\./g, "输入网络电压在结构化器件档案限制内。"],
  [/Output network voltage falls within the structured component profile limit\./g, "输出网络电压在结构化器件档案限制内。"],
  [/Pin is tied to an allowed net from the profile\./g, "引脚连接到器件档案允许的网络。"],
  [/Pin is not connected\./g, "引脚未连接。"],
  [/status=not_found/g, "状态：未找到"],
  [/status=ok/g, "状态：通过"]
];

export function formatSummary(text: string): string {
  return SUMMARY_REPLACEMENTS.reduce((current, [pattern, replacement]) => {
    return current.replace(pattern, replacement);
  }, text);
}

export function chainKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    component_check: "组件规则",
    pin_check: "引脚规则",
    manual_gap: "人工缺口",
    external_risk_hint: "外部线索",
    netlist_trace: "网表追踪",
    design_rule: "设计规则",
    datasheet_or_profile: "资料证据",
    external_hint: "外部线索",
    pin_table_row: "Capture 引脚表"
  };
  return labels[kind] ?? kind;
}

export function taskKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    component_check: "组件检查",
    pin_check: "引脚检查",
    manual_gap: "人工缺口",
    external_risk_hint: "外部线索",
    pin_table_check: "Capture 引脚表检查",
    cleared_summary: "已通过",
    cleared: "已通过"
  };
  return labels[kind] ?? kind;
}
