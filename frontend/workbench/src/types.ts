export type StatusGroup = "error" | "warn" | "pass" | "manual";
export type TrustTier = "l1" | "l2" | "l3";
export type EvidenceLaneStatus = "present" | "partial" | "gap" | "not_configured";
export type EvidenceLaneStatusGroup = "pass" | "warn" | "manual";

export interface EvidencePackageMetric {
  key: string;
  label: string;
  value: number;
  total: number | null;
  unit: string;
}

export interface EvidencePackageLane {
  id: "netlist" | "bom" | "validation" | "documents" | "pin_table" | "review_package";
  label: string;
  status: EvidenceLaneStatus;
  status_group: EvidenceLaneStatusGroup;
  status_label: string;
  source: string | null;
  source_token: string | null;
  summary: string;
  recommended_action: string;
  trust_boundary: string;
  metrics: EvidencePackageMetric[];
}

export interface EvidencePackageSummary {
  schema_version: string;
  scope: string;
  electrical_verdict: "not_applicable";
  lanes: EvidencePackageLane[];
  signoff_readiness: SignoffReadiness;
  guardrails: string[];
}

export interface SignoffReadiness {
  status: "ready" | "blocked";
  signoff_ready: boolean;
  affected_tasks: number;
  missing_local_sources: number;
  missing_tokens: string[];
  reason: string;
}

export interface WorkbenchProject {
  name: string;
  generated_at: string;
  netlist_source: string;
  netlist_type: string;
  bom_source: string;
  profiles_dir: string;
  scope: string;
}

export interface WorkbenchSummary {
  components: number;
  bom_matched: number;
  validated: number;
  manual: number;
  pass_count: number;
  warn_count: number;
  error_count: number;
}

export interface WorkbenchCapabilities {
  chat: boolean;
  datasheet_search_enabled: boolean;
  datasheet_candidate_lookup_enabled: boolean;
  document_index_enabled: boolean;
  risk_hints_enabled: boolean;
  pin_table_enabled: boolean;
  review_package_enabled: boolean;
}

export interface PinTableSummary {
  status: "loaded" | "not_configured";
  source: string | null;
  accepted_findings: number;
  rejected_findings: number;
  affected_refdes: number;
  accepted_refdes: string[];
  affected_refdes_list: string[];
  rejected_unknown_refdes: string[];
  rejected: RejectedPinTableFinding[];
  checks: Record<string, number>;
}

export interface RejectedPinTableFinding {
  rule_id: string;
  refdes: string | null;
  pin_number: string | null;
  net: string | null;
  message: string;
  reason: string;
}

export interface ReviewPackageArtifact {
  kind: string;
  status: string;
  required: boolean;
  name: string;
  path: string;
  sha256: string | null;
  expected_sha256: string | null;
  note: string | null;
}

export interface ReviewPackageSummary {
  status: "loaded" | "not_configured";
  source: string | null;
  package_status: "not_configured" | "complete" | "optional_gap" | "missing_required" | "hash_mismatch";
  status_group: StatusGroup;
  status_label: string;
  total: number;
  present: number;
  missing_required: number;
  missing_optional: number;
  hash_mismatch: number;
  manual_gap_count: number;
  recommended_action: string;
  artifacts: ReviewPackageArtifact[];
}

export interface EvidenceView {
  token: string;
  source_class: string;
  audit_status: string;
  local_source: string | null;
  reason: string;
  trust_tier: TrustTier;
  label: string;
}

export interface ReviewQueueItem {
  refdes: string;
  value: string;
  part_number: string;
  manufacturer: string;
  package: string;
  title: string;
  subtitle: string;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  deterministic_status: string;
  deterministic_status_label: string;
  deterministic_status_group: StatusGroup;
  trust_tier: TrustTier;
  issue_count: number;
  evidence_count: number;
  risk_hint_count: number;
  pin_table_task_count: number;
  task_count: number;
  task_counts: ReviewTaskCounts;
  task_ids: string[];
  top_task_id: string | null;
  profile_status: string;
  profile_path: string | null;
  document_status: string;
}

export interface ReviewTask {
  id: string;
  stable_key: string;
  refdes: string;
  kind: string;
  check: string | null;
  pin_number: string | null;
  subject: string | null;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  trust_tier: TrustTier;
  title: string;
  body: string;
  recommended_action: string;
  source_classes: string[];
  evidence_chain: EvidenceChainItem[];
  derived_from_task_id: string | null;
  review_decision: ReviewDecision | null;
}

export type ReviewDecisionStatus = "open" | "accepted" | "waived" | "resolved";

export interface ReviewDecision {
  stable_key: string;
  status: ReviewDecisionStatus;
  reason: string;
  updated_at: string;
}

export interface ReviewDecisionSummary {
  total_tasks: number;
  open: number;
  accepted: number;
  waived: number;
  resolved: number;
  stale_removed_on_rerun: number;
}

export interface ReviewTaskGroup {
  id: string;
  stable_key: string;
  title: string;
  status_group: StatusGroup;
  trust_tier: TrustTier;
  axis: "electrical" | "evidence";
  identity: string;
  check: string | null;
  affected_refdes: string[];
  task_ids: string[];
  stable_keys: string[];
  raw_task_count: number;
  derived_task_count: number;
  recommended_action: string;
}

export interface ReviewTaskCounts {
  total: number;
  error: number;
  warn: number;
  manual: number;
  pass_count: number;
}

export interface PinView {
  number: string;
  name: string;
  electrical_type: string;
  net: string | null;
  is_nc: boolean;
  status: string | null;
  summary: string;
  evidence: EvidenceView[];
}

export interface CheckView {
  subject: string;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  summary: string;
  evidence: EvidenceView[];
}

export interface NetCheckView {
  net_name: string;
  check: string;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  summary: string;
  nodes: string[];
  evidence: EvidenceView[];
}

export interface EvidenceChainItem {
  kind: string;
  title: string;
  body: string;
  status: string;
  status_group: StatusGroup;
  trust_tier: TrustTier;
  evidence: EvidenceView[];
}

export interface RiskHintView {
  refdes: string;
  title: string;
  body: string;
  severity: string | null;
  source: EvidenceView | null;
  wrapped_refdes_count: number;
}

export interface RejectedRiskHintSummary {
  reason: string;
  count: number;
}

export interface RiskHintsView {
  external_status: string;
  count: number;
  accepted_external_count: number;
  rejected_external_count: number;
  wrapped_refdes_count: number;
  accepted: RiskHintView[];
  rejected: RejectedRiskHintSummary[];
}

export interface RiskHintsSummary {
  external_status: string;
  count: number;
  accepted_external_count: number;
  rejected_external_count: number;
}

export interface BomView {
  value: string;
  part_number: string;
  manufacturer: string;
  description: string;
  source: string;
  item_number: string | null;
  source_line: number | null;
}

export interface ProfileView {
  status: string;
  reason: string;
  path: string | null;
  part_number: string;
}

export interface DocumentCoverageView {
  status: string;
  group_id: string | null;
  identity: string;
  identity_kind: string;
  suggested_family: string;
  title: string | null;
  url: string | null;
  source: string | null;
  candidates: number;
  reason: string;
  candidate_search: DatasheetCandidateSearchView | null;
}

export interface DatasheetCandidateView {
  mpn: string;
  manufacturer: string | null;
  title: string | null;
  description: string | null;
  datasheet_url: string | null;
  product_url: string | null;
  lifecycle_status: string | null;
  package_type: string | null;
  review_status: string;
  source: string;
}

export interface DatasheetCandidateSearchView {
  provider: string;
  status: string;
  reason: string | null;
  query: string;
  count: number;
  direct_datasheet_count: number;
  remaining_month: number | null;
  candidates: DatasheetCandidateView[];
  next_actions: string[];
}

export interface WorkbenchState {
  project: WorkbenchProject;
  summary: WorkbenchSummary;
  capabilities: WorkbenchCapabilities;
  evidence_package: EvidencePackageSummary;
  pin_table: PinTableSummary;
  review_package: ReviewPackageSummary;
  selected_refdes: string | null;
  queue: ReviewQueueItem[];
  review_tasks: ReviewTask[];
  review_groups: ReviewTaskGroup[];
  task_counts: ReviewTaskCounts;
  review_decisions: ReviewDecisionSummary | null;
  net_checks: NetCheckView[];
  risk_hints: RiskHintsSummary;
  risk_hint_details: RiskHintsView;
}

export interface ImportResponse {
  ok: boolean;
  project: WorkbenchProject;
  summary: WorkbenchSummary;
  evidence_package: EvidencePackageSummary;
  pin_table: PinTableSummary;
  review_package: ReviewPackageSummary;
  selected_refdes: string | null;
  task_counts: ReviewTaskCounts;
}

export interface ComponentDetail {
  refdes: string;
  value: string;
  part_number: string;
  manufacturer: string;
  package: string;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  deterministic_status: string;
  deterministic_status_label: string;
  deterministic_status_group: StatusGroup;
  trust_tier: TrustTier;
  profile_part_number: string;
  match_status: string;
  match_reason: string;
  pins: PinView[];
  checks: CheckView[];
  evidence_chain: EvidenceChainItem[];
  risk_hints: RiskHintView[];
  tasks: ReviewTask[];
  task_counts: ReviewTaskCounts;
  bom: BomView | null;
  profile: ProfileView | null;
  document: DocumentCoverageView | null;
}

export interface ReviewPrepPacket {
  schema_version: string;
  project: WorkbenchProject;
  scope: string;
  component: ComponentDetail;
  tasks: ReviewTask[];
  pins: PinView[];
  checks: CheckView[];
  risk_hints: RiskHintsView;
  evidence: EvidenceView[];
  guardrails: string[];
}

export interface ProjectPrepComponentGroup {
  group_id: string;
  title: string;
  refdes: string[];
  refdes_count: number;
  refdes_sample: string[];
  value: string;
  part_number: string;
  manufacturer: string;
  suggested_family: string;
  profile_status: string;
  validation_status: string;
  document_status: string;
  status_group: StatusGroup;
  task_count: number;
}

export interface ProjectPrepFocusArea {
  area: string;
  title: string;
  summary: string;
  refdes: string[];
  task_count: number;
  status_group: StatusGroup;
  open_questions: string[];
}

export interface ProjectPrepOpenQuestion {
  source: string;
  priority: StatusGroup;
  refdes?: string | null;
  question: string;
}

export type DraftSummaryConfidence = "high" | "medium" | "low";

export interface DraftSummaryItem {
  kind: string;
  title: string;
  summary: string;
  refdes: string[];
  nets: string[];
  task_ids: string[];
  evidence: EvidenceView[];
  confidence: DraftSummaryConfidence;
  uncertainty: string;
  basis: string[];
  status_group: StatusGroup;
}

export interface ProjectDraftSummaries {
  schema_version: string;
  scope: string;
  modules: DraftSummaryItem[];
  key_groups: DraftSummaryItem[];
  power: DraftSummaryItem[];
  interface: DraftSummaryItem[];
  clock_reset: DraftSummaryItem[];
  open_questions: DraftSummaryItem[];
}

export type PromotionStatus =
  | "ready_for_draft"
  | "needs_public_document"
  | "needs_document_selection"
  | "already_l1"
  | "covered_by_generic_passive";

export interface ProfilePromotionCandidate {
  group_id: string;
  title: string;
  identity: string;
  identity_kind: string;
  suggested_family: string;
  refdes: string[];
  refdes_count: number;
  refdes_sample: string[];
  profile_status: string;
  validation_status: string;
  document_status: string;
  document_title?: string | null;
  document_url?: string | null;
  document_source?: string | null;
  status: PromotionStatus;
  draft_review_status: "needs_review";
  recommended_action: string;
  draft_command: string;
  required_checks: string[];
  guardrails: string[];
}

export interface ProjectReviewPrepPacket {
  schema_version: string;
  project: WorkbenchProject;
  scope: string;
  summary: WorkbenchSummary;
  task_counts: ReviewTaskCounts;
  review_decisions: ReviewDecisionSummary | null;
  queue: ReviewQueueItem[];
  priority_tasks: ReviewTask[];
  key_component_groups: ProjectPrepComponentGroup[];
  focus_areas: ProjectPrepFocusArea[];
  draft_summaries: ProjectDraftSummaries;
  profile_promotion_candidates: ProfilePromotionCandidate[];
  open_questions: ProjectPrepOpenQuestion[];
  risk_hints: RiskHintsView;
  evidence_package: EvidencePackageSummary;
  pin_table: PinTableSummary;
  review_package: ReviewPackageSummary;
  evidence: EvidenceView[];
  guardrails: string[];
}

export interface EvidenceClassification {
  token: string;
  source_class:
    | "live_retrieved"
    | "reviewed_profile"
    | "document_index"
    | "design_source"
    | "unknown";
  audit_status: "ok" | "missing_local_source";
  local_source: string | null;
  reason: string;
}

export interface EvidenceTrace {
  tool: string;
  input: Record<string, unknown>;
  summary: string;
  status: string | null;
  evidence: string[];
  evidence_classification: EvidenceClassification[];
  wrapped: number;
  trust_tier: TrustTier | null;
  trust_label: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  question: string;
  selected_refdes?: string | null;
  history?: ChatMessage[];
}

export interface ChatResponse {
  answer: string;
  mode: "fake" | "real" | "snapshot";
  selected_refdes: string | null;
  trace: EvidenceTrace[];
  wrapped_count: number;
  suggestions: string[];
  datasheet_search_enabled: boolean;
  unsupported_evidence_tokens: string[];
}

export interface WorkbenchOfflineSnapshot {
  schema_version: string;
  mode: "snapshot";
  state: WorkbenchState;
  components: Record<string, ComponentDetail>;
  component_prep_markdown: Record<string, string>;
  project_prep_markdown: string;
  chat_responses: Record<string, ChatResponse>;
  exports: Record<"json" | "csv" | "annotations", string>;
}

declare global {
  interface Window {
    __HARDWISE_OFFLINE_SNAPSHOT__?: WorkbenchOfflineSnapshot;
  }
}
