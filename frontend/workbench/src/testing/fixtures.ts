import type {
  CheckView,
  ComponentDetail,
  EvidenceChainItem,
  EvidenceView,
  PinView,
  ReviewQueueItem,
  ReviewTask,
  ReviewTaskCounts,
  RiskHintsView,
  WorkbenchCapabilities,
  WorkbenchProject,
  WorkbenchState,
  WorkbenchSummary
} from "../types";

// Shared deterministic fixtures for node-side vitest suites. Defaults are
// stable on purpose: format.test.ts asserts on the exact composed strings.

export function makeEvidence(overrides: Partial<EvidenceView> = {}): EvidenceView {
  return {
    token: "EV-1",
    source_class: "design_source",
    audit_status: "ok",
    local_source: null,
    reason: "",
    trust_tier: "l1",
    label: "netlist",
    ...overrides
  };
}

export function makeChainItem(overrides: Partial<EvidenceChainItem> = {}): EvidenceChainItem {
  return {
    kind: "component_check",
    title: "title",
    body: "body",
    status: "WARN",
    status_group: "warn",
    trust_tier: "l1",
    evidence: [],
    ...overrides
  };
}

export function makeTaskCounts(overrides: Partial<ReviewTaskCounts> = {}): ReviewTaskCounts {
  return { total: 1, error: 0, warn: 1, manual: 0, pass_count: 0, ...overrides };
}

export function makeQueueItem(overrides: Partial<ReviewQueueItem> = {}): ReviewQueueItem {
  return {
    refdes: "U8",
    value: "STM32F103",
    part_number: "STM32F103C8T6",
    manufacturer: "ST",
    package: "LQFP48",
    title: "MCU power pins",
    subtitle: "subtitle",
    status: "WARN",
    status_label: "看证据",
    status_group: "warn",
    deterministic_status: "WARN",
    deterministic_status_label: "看证据",
    deterministic_status_group: "warn",
    trust_tier: "l1",
    issue_count: 1,
    evidence_count: 2,
    risk_hint_count: 1,
    task_count: 1,
    task_counts: makeTaskCounts(),
    task_ids: ["T1"],
    top_task_id: "T1",
    profile_status: "ok",
    profile_path: null,
    document_status: "matched",
    ...overrides
  };
}

export function makeTask(overrides: Partial<ReviewTask> = {}): ReviewTask {
  return {
    id: "T1",
    stable_key: "T1-key",
    refdes: "U8",
    kind: "component_check",
    check: null,
    pin_number: null,
    subject: null,
    status: "WARN",
    status_label: "看证据",
    status_group: "warn",
    trust_tier: "l1",
    title: "Pin is not connected.",
    body: "body text",
    recommended_action: "review the net",
    source_classes: ["design_source"],
    evidence_chain: [makeChainItem()],
    ...overrides
  };
}

export function makeCheck(overrides: Partial<CheckView> = {}): CheckView {
  return {
    subject: "VEBO",
    status: "WARN",
    status_label: "看证据",
    status_group: "warn",
    summary: "Pin is not connected.",
    evidence: [makeEvidence()],
    ...overrides
  };
}

export function makePin(overrides: Partial<PinView> = {}): PinView {
  return {
    number: "1",
    name: "VDD",
    electrical_type: "power",
    net: "VBUS_5V",
    is_nc: false,
    status: "PASS",
    summary: "",
    evidence: [],
    ...overrides
  };
}

export function makeSummary(overrides: Partial<WorkbenchSummary> = {}): WorkbenchSummary {
  return {
    components: 25,
    bom_matched: 24,
    validated: 22,
    manual: 3,
    pass_count: 5,
    warn_count: 13,
    error_count: 4,
    ...overrides
  };
}

export function makeProject(overrides: Partial<WorkbenchProject> = {}): WorkbenchProject {
  return {
    name: "mixed_controller_power_stage",
    generated_at: "2026-06-11T00:00:00Z",
    netlist_source: "mixed_controller_power_stage.net",
    netlist_type: "allegro_third_party",
    bom_source: "mixed_controller_power_stage_bom.csv",
    profiles_dir: "data/datasheet_profiles",
    scope: "component-first review prep",
    ...overrides
  };
}

export function makeCapabilities(
  overrides: Partial<WorkbenchCapabilities> = {}
): WorkbenchCapabilities {
  return {
    chat: true,
    datasheet_search_enabled: false,
    document_index_enabled: false,
    risk_hints_enabled: false,
    pin_table_enabled: false,
    ...overrides
  };
}

export function makeRiskHints(overrides: Partial<RiskHintsView> = {}): RiskHintsView {
  return {
    external_status: "not_configured",
    count: 0,
    accepted_external_count: 0,
    rejected_external_count: 0,
    wrapped_refdes_count: 0,
    accepted: [],
    rejected: [],
    ...overrides
  };
}

export function makeState(overrides: Partial<WorkbenchState> = {}): WorkbenchState {
  return {
    project: makeProject(),
    summary: makeSummary(),
    capabilities: makeCapabilities(),
    selected_refdes: "U8",
    queue: [makeQueueItem()],
    review_tasks: [makeTask()],
    task_counts: makeTaskCounts(),
    risk_hints: {
      external_status: "not_configured",
      count: 0,
      accepted_external_count: 0,
      rejected_external_count: 0
    },
    risk_hint_details: makeRiskHints(),
    ...overrides
  };
}

export function makeDetail(overrides: Partial<ComponentDetail> = {}): ComponentDetail {
  return {
    refdes: "U8",
    value: "STM32F103",
    part_number: "STM32F103C8T6",
    manufacturer: "ST",
    package: "LQFP48",
    status: "WARN",
    status_label: "看证据",
    status_group: "warn",
    trust_tier: "l1",
    profile_part_number: "STM32F103C8T6",
    match_status: "ok",
    match_reason: "Exactly one local profile part_number matched this BOM identity.",
    pins: [makePin()],
    checks: [makeCheck()],
    evidence_chain: [makeChainItem()],
    risk_hints: [],
    tasks: [makeTask()],
    task_counts: makeTaskCounts(),
    bom: {
      value: "STM32F103",
      part_number: "STM32F103C8T6",
      manufacturer: "ST",
      description: "MCU",
      source: "bom.csv",
      item_number: null,
      source_line: 3
    },
    profile: { status: "ok", reason: "", path: null, part_number: "STM32F103C8T6" },
    document: null,
    ...overrides
  };
}
