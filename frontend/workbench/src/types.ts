export type StatusGroup = "error" | "warn" | "pass" | "manual";
export type TrustTier = "l1" | "l2" | "l3";

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
  document_index_enabled: boolean;
  risk_hints_enabled: boolean;
  pin_table_enabled: boolean;
}

export interface EvidenceView {
  token: string;
  source_class: string;
  audit_status: string;
  local_source?: string | null;
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
  task_count: number;
  task_counts: ReviewTaskCounts;
  task_ids: string[];
  top_task_id?: string | null;
  profile_status: string;
  profile_path?: string | null;
  document_status: string;
}

export interface ReviewTask {
  id: string;
  stable_key: string;
  refdes: string;
  kind: string;
  check?: string | null;
  pin_number?: string | null;
  subject?: string | null;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  trust_tier: TrustTier;
  title: string;
  body: string;
  recommended_action: string;
  source_classes: string[];
  evidence_chain: EvidenceChainItem[];
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
  net?: string | null;
  is_nc: boolean;
  status?: string | null;
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
  severity?: string | null;
  source?: EvidenceView | null;
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
  item_number?: string | null;
  source_line?: number | null;
}

export interface ProfileView {
  status: string;
  reason: string;
  path?: string | null;
  part_number: string;
}

export interface DocumentCoverageView {
  status: string;
  title?: string | null;
  url?: string | null;
  source?: string | null;
  candidates: number;
  reason: string;
}

export interface WorkbenchState {
  project: WorkbenchProject;
  summary: WorkbenchSummary;
  capabilities: WorkbenchCapabilities;
  selected_refdes?: string | null;
  queue: ReviewQueueItem[];
  review_tasks: ReviewTask[];
  task_counts: ReviewTaskCounts;
  risk_hints: RiskHintsSummary;
  risk_hint_details: RiskHintsView;
}

export interface ImportResponse {
  ok: boolean;
  project: WorkbenchProject;
  summary: WorkbenchSummary;
  selected_refdes?: string | null;
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
  bom?: BomView | null;
  profile?: ProfileView | null;
  document?: DocumentCoverageView | null;
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
  queue: ReviewQueueItem[];
  priority_tasks: ReviewTask[];
  key_component_groups: ProjectPrepComponentGroup[];
  focus_areas: ProjectPrepFocusArea[];
  draft_summaries: ProjectDraftSummaries;
  profile_promotion_candidates: ProfilePromotionCandidate[];
  open_questions: ProjectPrepOpenQuestion[];
  risk_hints: RiskHintsView;
  evidence: EvidenceView[];
  guardrails: string[];
}

export interface EvidenceClassification {
  token: string;
  source_class: string;
  audit_status: string;
  local_source?: string | null;
  reason: string;
}

export interface EvidenceTrace {
  tool: string;
  input: Record<string, unknown>;
  summary: string;
  status?: string | null;
  evidence: string[];
  evidence_classification: EvidenceClassification[];
  wrapped: number;
  trust_tier?: TrustTier | null;
  trust_label?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  mode: "fake" | "real" | "snapshot";
  selected_refdes?: string | null;
  trace: EvidenceTrace[];
  wrapped_count: number;
  suggestions: string[];
  datasheet_search_enabled: boolean;
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
