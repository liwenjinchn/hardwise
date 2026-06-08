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
  title: string;
  subtitle: string;
  status: string;
  status_label: string;
  status_group: StatusGroup;
  trust_tier: TrustTier;
  issue_count: number;
  evidence_count: number;
  risk_hint_count: number;
}

export interface ReviewTask {
  id: string;
  refdes: string;
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
