import type {
  CheckView,
  ComponentDetail,
  DocumentCoverageView,
  EvidenceChainItem,
  EvidencePackageLane,
  EvidencePackageSummary,
  EvidenceView,
  PinView,
  PinTableSummary,
  ReviewPackageSummary,
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
    pin_table_task_count: 0,
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
    derived_from_task_id: null,
    review_decision: null,
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
    datasheet_candidate_lookup_enabled: false,
    document_index_enabled: false,
    risk_hints_enabled: false,
    pin_table_enabled: false,
    review_package_enabled: false,
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

export function makePinTable(overrides: Partial<PinTableSummary> = {}): PinTableSummary {
  return {
    status: "not_configured",
    source: null,
    accepted_findings: 0,
    rejected_findings: 0,
    affected_refdes: 0,
    accepted_refdes: [],
    affected_refdes_list: [],
    rejected_unknown_refdes: [],
    rejected: [],
    checks: {},
    ...overrides
  };
}

export function makeReviewPackage(
  overrides: Partial<ReviewPackageSummary> = {}
): ReviewPackageSummary {
  return {
    status: "not_configured",
    source: null,
    package_status: "not_configured",
    status_group: "manual",
    status_label: "not configured",
    total: 0,
    present: 0,
    missing_required: 0,
    missing_optional: 0,
    hash_mismatch: 0,
    manual_gap_count: 0,
    recommended_action: "Provide a review-package manifest if this review requires handoff evidence.",
    artifacts: [],
    ...overrides
  };
}

export function makeEvidenceLane(
  overrides: Partial<EvidencePackageLane> = {}
): EvidencePackageLane {
  return {
    id: "netlist",
    label: "Netlist / PST registry",
    status: "present",
    status_group: "pass",
    status_label: "parsed",
    source: "mixed_controller_power_stage.net",
    source_token: "netlist:mixed_controller_power_stage.net#summary",
    summary: "Parsed 25 registry-verified components from allegro_third_party.",
    recommended_action: "Keep the original Cadence/Allegro export with the review packet.",
    trust_boundary: "Parsing confirms source identity and registry coverage, not correctness.",
    metrics: [
      {
        key: "components",
        label: "Registry components",
        value: 25,
        total: null,
        unit: "components"
      }
    ],
    ...overrides
  };
}

export function makeEvidencePackage(
  overrides: Partial<EvidencePackageSummary> = {}
): EvidencePackageSummary {
  return {
    schema_version: "hardwise.evidence_package.v1",
    scope: "input_evidence_completeness",
    electrical_verdict: "not_applicable",
    lanes: [
      makeEvidenceLane(),
      makeEvidenceLane({
        id: "bom",
        label: "BOM identity",
        status: "partial",
        status_group: "warn",
        status_label: "identity gaps",
        source: "mixed_controller_power_stage_bom.csv",
        source_token: "bom:mixed_controller_power_stage_bom.csv#summary",
        summary: "Matched 24/25 design refdes; registry clean=false.",
        recommended_action: "Resolve the remaining identity gap.",
        trust_boundary: "BOM matching proves refdes identity consistency, not part suitability.",
        metrics: [
          {
            key: "matched_refdes",
            label: "Matched refdes",
            value: 24,
            total: 25,
            unit: "refdes"
          },
          {
            key: "design_only_refdes",
            label: "Design-only refdes",
            value: 1,
            total: null,
            unit: "refdes"
          }
        ]
      }),
      makeEvidenceLane({
        id: "validation",
        label: "Profile + deterministic validation",
        status: "partial",
        status_group: "warn",
        status_label: "coverage gaps",
        source: "data/datasheet_profiles",
        source_token: "public_profile:datasheet_profiles#summary",
        summary: "Ready profiles cover 22/25 components; deterministic validation covers 22/25.",
        recommended_action: "Review unmatched profile groups separately.",
        trust_boundary: "Profile and validator coverage are separate facts.",
        metrics: [
          {
            key: "validated_components",
            label: "Deterministically validated",
            value: 22,
            total: 25,
            unit: "components"
          }
        ]
      }),
      makeEvidenceLane({
        id: "documents",
        label: "Public document index",
        status: "not_configured",
        status_group: "manual",
        status_label: "not configured",
        source: null,
        source_token: null,
        summary: "No reviewed public document index was supplied.",
        recommended_action: "Upload a reviewed document-index CSV when coverage matters.",
        trust_boundary: "Missing document coverage is a manual gap, not an electrical finding.",
        metrics: []
      }),
      makeEvidenceLane({
        id: "pin_table",
        label: "Capture pin-table evidence",
        status: "not_configured",
        status_group: "manual",
        status_label: "not configured",
        source: null,
        source_token: null,
        summary: "No optional Capture pin-table CSV was supplied.",
        recommended_action: "Upload a Capture pin table when pin evidence is available.",
        trust_boundary: "Absence creates no finding and does not change validation totals.",
        metrics: []
      }),
      makeEvidenceLane({
        id: "review_package",
        label: "Review-package artifacts",
        status: "not_configured",
        status_group: "manual",
        status_label: "not configured",
        source: null,
        source_token: null,
        summary: "No review-package manifest was supplied.",
        recommended_action: "Upload a manifest when formal handoff evidence is required.",
        trust_boundary: "Package completeness is provenance metadata, not an electrical verdict.",
        metrics: []
      })
    ],
    signoff_readiness: {
      status: "ready",
      signoff_ready: true,
      affected_tasks: 0,
      missing_local_sources: 0,
      missing_tokens: [],
      reason: "Every L1 evidence token is reproducible."
    },
    guardrails: [
      "Lane statuses describe input evidence coverage, not electrical correctness.",
      "Counts with different units are never combined into one percentage or score.",
      "Missing optional inputs remain visible coverage gaps and create no review finding.",
      "PASS/WARN/ERROR totals come only from deterministic validation."
    ],
    ...overrides
  };
}

export function makeState(overrides: Partial<WorkbenchState> = {}): WorkbenchState {
  return {
    project: makeProject(),
    summary: makeSummary(),
    capabilities: makeCapabilities(),
    evidence_package: makeEvidencePackage(),
    pin_table: makePinTable(),
    review_package: makeReviewPackage(),
    selected_refdes: "U8",
    queue: [makeQueueItem()],
    review_tasks: [makeTask()],
    review_groups: [
      {
        id: "G-001",
        stable_key: "group|st|stm32|component_check",
        title: "MCU power pins",
        status_group: "warn",
        trust_tier: "l1",
        axis: "electrical",
        identity: "st|stm32f103c8t6",
        check: "component_check",
        affected_refdes: ["U8"],
        task_ids: ["T1"],
        stable_keys: ["T1-key"],
        raw_task_count: 1,
        derived_task_count: 0,
        recommended_action: "review the net"
      }
    ],
    task_counts: makeTaskCounts(),
    review_decisions: {
      total_tasks: 1,
      open: 1,
      accepted: 0,
      waived: 0,
      resolved: 0,
      stale_removed_on_rerun: 0
    },
    net_checks: [],
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

export function makeDocument(overrides: Partial<DocumentCoverageView> = {}): DocumentCoverageView {
  return {
    status: "matched",
    group_id: "1",
    identity: "L7805",
    identity_kind: "mpn",
    suggested_family: "ic",
    title: "L78 series public ST datasheet (l78.pdf)",
    url: "https://www.st.com/resource/en/datasheet/l78.pdf",
    source: "st.com",
    candidates: 1,
    reason: "Exactly one local document-index row matched this BOM identity.",
    candidate_search: null,
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
    deterministic_status: "WARN",
    deterministic_status_label: "看证据",
    deterministic_status_group: "warn",
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
