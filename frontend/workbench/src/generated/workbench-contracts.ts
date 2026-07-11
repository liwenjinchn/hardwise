/* Generated from backend Pydantic contracts. Do not edit. */

export type Content = string;
export type Role = "user" | "assistant";
export type History = ChatMessage[];
export type Question = string;
export type SelectedRefdes = string | null;
export type Answer = string;
export type DatasheetSearchEnabled = boolean;
export type Mode = "fake" | "real" | "snapshot";
export type SelectedRefdes1 = string | null;
export type Suggestions = string[];
export type Evidence = string[];
export type AuditStatus = "ok" | "missing_local_source";
export type LocalSource = string | null;
export type Reason = string;
export type SourceClass = "live_retrieved" | "reviewed_profile" | "document_index" | "design_source" | "unknown";
export type Token = string;
export type EvidenceClassification = EvidenceClassification1[];
export type Status = string | null;
export type Summary = string;
export type Tool = string;
export type TrustLabel = string | null;
export type TrustTier = ("l1" | "l2" | "l3") | null;
export type Wrapped = number;
export type Trace = EvidenceTrace[];
export type UnsupportedEvidenceTokens = string[];
export type WrappedCount = number;
export type Description = string;
export type ItemNumber = string | null;
export type Manufacturer = string;
export type PartNumber = string;
export type Source = string;
export type SourceLine = number | null;
export type Value = string;
export type AuditStatus1 = string;
export type Label = string;
export type LocalSource1 = string | null;
export type Reason1 = string;
export type SourceClass1 = string;
export type Token1 = string;
export type TrustTier1 = "l1" | "l2" | "l3";
export type Evidence1 = EvidenceView[];
export type Status1 = string;
export type StatusGroup = "error" | "warn" | "pass" | "manual";
export type StatusLabel = string;
export type Subject = string;
export type Summary1 = string;
export type Checks = CheckView[];
export type DatasheetUrl = string | null;
export type Description1 = string | null;
export type LifecycleStatus = string | null;
export type Manufacturer1 = string | null;
export type Mpn = string;
export type PackageType = string | null;
export type ProductUrl = string | null;
export type ReviewStatus = string;
export type Source1 = string;
export type Title = string | null;
export type Candidates = DatasheetCandidateView[];
export type Count = number;
export type DirectDatasheetCount = number;
export type NextActions = string[];
export type Provider = string;
export type Query = string;
export type Reason2 = string | null;
export type RemainingMonth = number | null;
export type Status2 = string;
export type Candidates1 = number;
export type GroupId = string | null;
export type Identity = string;
export type IdentityKind = string;
export type Reason3 = string;
export type Source2 = string | null;
export type Status3 = string;
export type SuggestedFamily = string;
export type Title1 = string | null;
export type Url = string | null;
export type Body = string;
export type Evidence2 = EvidenceView[];
export type Kind = string;
export type Status4 = string;
export type StatusGroup1 = "error" | "warn" | "pass" | "manual";
export type Title2 = string;
export type TrustTier2 = "l1" | "l2" | "l3";
export type EvidenceChain = EvidenceChainItem[];
export type Manufacturer2 = string;
export type MatchReason = string;
export type MatchStatus = string;
export type Package = string;
export type PartNumber1 = string;
export type ElectricalType = string;
export type Evidence3 = EvidenceView[];
export type IsNc = boolean;
export type Name = string;
export type Net = string | null;
export type Number = string;
export type Status5 = string | null;
export type Summary2 = string;
export type Pins = PinView[];
export type PartNumber2 = string;
export type Path = string | null;
export type Reason4 = string;
export type Status6 = string;
export type ProfilePartNumber = string;
export type Refdes = string;
export type Body1 = string;
export type Refdes1 = string;
export type Severity = string | null;
export type Title3 = string;
export type WrappedRefdesCount = number;
export type RiskHints = RiskHintView[];
export type Status7 = string;
export type StatusGroup2 = "error" | "warn" | "pass" | "manual";
export type StatusLabel1 = string;
export type Error = number;
export type Manual = number;
export type PassCount = number;
export type Total = number;
export type Warn = number;
export type Body2 = string;
export type Check = string | null;
export type EvidenceChain1 = EvidenceChainItem[];
export type Id = string;
export type Kind1 = string;
export type PinNumber = string | null;
export type RecommendedAction = string;
export type Refdes2 = string;
export type SourceClasses = string[];
export type StableKey = string;
export type Status8 = string;
export type StatusGroup3 = "error" | "warn" | "pass" | "manual";
export type StatusLabel2 = string;
export type Subject1 = string | null;
export type Title4 = string;
export type TrustTier3 = "l1" | "l2" | "l3";
export type Tasks = ReviewTask[];
export type TrustTier4 = "l1" | "l2" | "l3";
export type Value1 = string;
export type Ok = boolean;
export type AcceptedFindings = number;
export type AcceptedRefdes = string[];
export type AffectedRefdes = number;
export type AffectedRefdesList = string[];
export type Message = string;
export type Net1 = string | null;
export type PinNumber1 = string | null;
export type Reason5 = string;
export type Refdes3 = string | null;
export type RuleId = string;
export type Rejected = RejectedPinTableFindingView[];
export type RejectedFindings = number;
export type RejectedUnknownRefdes = string[];
export type Source3 = string | null;
export type Status9 = "loaded" | "not_configured";
export type BomSource = string;
export type GeneratedAt = string;
export type Name1 = string;
export type NetlistSource = string;
export type NetlistType = string;
export type ProfilesDir = string;
export type Scope = string;
export type ExpectedSha256 = string | null;
export type Kind2 = string;
export type Name2 = string;
export type Note = string | null;
export type Path1 = string;
export type Required = boolean;
export type Sha256 = string | null;
export type Status10 = string;
export type Artifacts = ReviewPackageArtifactView[];
export type HashMismatch = number;
export type ManualGapCount = number;
export type MissingOptional = number;
export type MissingRequired = number;
export type PackageStatus = "not_configured" | "complete" | "optional_gap" | "missing_required" | "hash_mismatch";
export type Present = number;
export type RecommendedAction1 = string;
export type Source4 = string | null;
export type Status11 = "loaded" | "not_configured";
export type StatusGroup4 = "error" | "warn" | "pass" | "manual";
export type StatusLabel3 = string;
export type Total1 = number;
export type SelectedRefdes2 = string | null;
export type BomMatched = number;
export type Components = number;
export type ErrorCount = number;
export type Manual1 = number;
export type PassCount1 = number;
export type Validated = number;
export type WarnCount = number;
export type Error1 = number;
export type Manual2 = number;
export type PassCount2 = number;
export type Total2 = number;
export type Warn1 = number;
export type Chat = boolean;
export type DatasheetCandidateLookupEnabled = boolean;
export type DatasheetSearchEnabled1 = boolean;
export type DocumentIndexEnabled = boolean;
export type PinTableEnabled = boolean;
export type ReviewPackageEnabled = boolean;
export type RiskHintsEnabled = boolean;
export type Check1 = string;
export type Evidence4 = EvidenceView[];
export type NetName = string;
export type Nodes = string[];
export type Status12 = string;
export type StatusGroup5 = "error" | "warn" | "pass" | "manual";
export type StatusLabel4 = string;
export type Summary3 = string;
export type NetChecks = NetCheckView[];
export type DeterministicStatus = string;
export type DeterministicStatusGroup = "error" | "warn" | "pass" | "manual";
export type DeterministicStatusLabel = string;
export type DocumentStatus = string;
export type EvidenceCount = number;
export type IssueCount = number;
export type Manufacturer3 = string;
export type Package1 = string;
export type PartNumber3 = string;
export type PinTableTaskCount = number;
export type ProfilePath = string | null;
export type ProfileStatus = string;
export type Refdes4 = string;
export type RiskHintCount = number;
export type Status13 = string;
export type StatusGroup6 = "error" | "warn" | "pass" | "manual";
export type StatusLabel5 = string;
export type Subtitle = string;
export type TaskCount = number;
export type TaskIds = string[];
export type Title5 = string;
export type TopTaskId = string | null;
export type TrustTier5 = "l1" | "l2" | "l3";
export type Value2 = string;
export type Queue = ReviewQueueItem[];
export type ReviewTasks = ReviewTask[];
export type Accepted = RiskHintView[];
export type AcceptedExternalCount = number;
export type Count1 = number;
export type ExternalStatus = string;
export type Count2 = number;
export type Reason6 = string;
export type Rejected1 = RejectedRiskHintSummary[];
export type RejectedExternalCount = number;
export type WrappedRefdesCount1 = number;
export type AcceptedExternalCount1 = number;
export type Count3 = number;
export type ExternalStatus1 = string;
export type RejectedExternalCount1 = number;
export type SelectedRefdes3 = string | null;

export interface WorkbenchContracts {
  chat_request: ChatRequest;
  chat_response: ChatResponse;
  component_detail: ComponentDetail;
  import_response: ImportResponse;
  workbench_state: WorkbenchState;
}
/**
 * User question sent from the Copilot panel.
 */
export interface ChatRequest {
  history?: History;
  question: Question;
  selected_refdes?: SelectedRefdes;
}
/**
 * One browser-held chat message sent back for short context.
 */
export interface ChatMessage {
  content: Content;
  role: Role;
}
/**
 * Answer returned to the Copilot panel.
 */
export interface ChatResponse {
  answer: Answer;
  datasheet_search_enabled: DatasheetSearchEnabled;
  mode: Mode;
  selected_refdes: SelectedRefdes1;
  suggestions: Suggestions;
  trace: Trace;
  unsupported_evidence_tokens: UnsupportedEvidenceTokens;
  wrapped_count: WrappedCount;
}
/**
 * UI-friendly trace row derived from one Runner tool call.
 */
export interface EvidenceTrace {
  evidence: Evidence;
  evidence_classification: EvidenceClassification;
  input: Input;
  status: Status;
  summary: Summary;
  tool: Tool;
  trust_label: TrustLabel;
  trust_tier: TrustTier;
  wrapped: Wrapped;
}
/**
 * One evidence token's source class plus filesystem audit state.
 */
export interface EvidenceClassification1 {
  audit_status: AuditStatus;
  local_source: LocalSource;
  reason: Reason;
  source_class: SourceClass;
  token: Token;
}
export interface Input {
  [k: string]: unknown;
}
/**
 * Full component detail consumed by the SPA.
 */
export interface ComponentDetail {
  bom: BomView | null;
  checks: Checks;
  document: DocumentCoverageView | null;
  evidence_chain: EvidenceChain;
  manufacturer: Manufacturer2;
  match_reason: MatchReason;
  match_status: MatchStatus;
  package: Package;
  part_number: PartNumber1;
  pins: Pins;
  profile: ProfileView | null;
  profile_part_number: ProfilePartNumber;
  refdes: Refdes;
  risk_hints: RiskHints;
  status: Status7;
  status_group: StatusGroup2;
  status_label: StatusLabel1;
  task_counts: ComponentTaskCounts;
  tasks: Tasks;
  trust_tier: TrustTier4;
  value: Value1;
}
/**
 * BOM identity shown in detail and prep packet views.
 */
export interface BomView {
  description: Description;
  item_number: ItemNumber;
  manufacturer: Manufacturer;
  part_number: PartNumber;
  source: Source;
  source_line: SourceLine;
  value: Value;
}
/**
 * Validation check detail shown in the component panel.
 */
export interface CheckView {
  evidence: Evidence1;
  status: Status1;
  status_group: StatusGroup;
  status_label: StatusLabel;
  subject: Subject;
  summary: Summary1;
}
/**
 * One visible evidence token plus its provenance classification.
 */
export interface EvidenceView {
  audit_status: AuditStatus1;
  label: Label;
  local_source: LocalSource1;
  reason: Reason1;
  source_class: SourceClass1;
  token: Token1;
  trust_tier: TrustTier1;
}
/**
 * Document-index coverage for one component's BOM identity.
 */
export interface DocumentCoverageView {
  candidate_search: DatasheetCandidateSearchView | null;
  candidates: Candidates1;
  group_id: GroupId;
  identity: Identity;
  identity_kind: IdentityKind;
  reason: Reason3;
  source: Source2;
  status: Status3;
  suggested_family: SuggestedFamily;
  title: Title1;
  url: Url;
}
/**
 * Provider lookup status embedded in component detail.
 */
export interface DatasheetCandidateSearchView {
  candidates: Candidates;
  count: Count;
  direct_datasheet_count: DirectDatasheetCount;
  next_actions: NextActions;
  provider: Provider;
  query: Query;
  reason: Reason2;
  remaining_month: RemainingMonth;
  status: Status2;
}
/**
 * One provider candidate shown as reviewer-only data.
 */
export interface DatasheetCandidateView {
  datasheet_url: DatasheetUrl;
  description: Description1;
  lifecycle_status: LifecycleStatus;
  manufacturer: Manufacturer1;
  mpn: Mpn;
  package_type: PackageType;
  product_url: ProductUrl;
  review_status: ReviewStatus;
  source: Source1;
  title: Title;
}
/**
 * A reader-facing chain-of-custody card.
 */
export interface EvidenceChainItem {
  body: Body;
  evidence: Evidence2;
  kind: Kind;
  status: Status4;
  status_group: StatusGroup1;
  title: Title2;
  trust_tier: TrustTier2;
}
/**
 * Pin/net detail shown in the component panel.
 */
export interface PinView {
  electrical_type: ElectricalType;
  evidence: Evidence3;
  is_nc: IsNc;
  name: Name;
  net: Net;
  number: Number;
  status: Status5;
  summary: Summary2;
}
/**
 * Profile match metadata for one component.
 */
export interface ProfileView {
  part_number: PartNumber2;
  path: Path;
  reason: Reason4;
  status: Status6;
}
/**
 * Registry-verified external hint for read-only display.
 */
export interface RiskHintView {
  body: Body1;
  refdes: Refdes1;
  severity: Severity;
  source: EvidenceView | null;
  title: Title3;
  wrapped_refdes_count: WrappedRefdesCount;
}
/**
 * Task counts scoped to one component.
 */
export interface ComponentTaskCounts {
  error: Error;
  manual: Manual;
  pass_count: PassCount;
  total: Total;
  warn: Warn;
}
/**
 * One finding-first review task in the SPA workflow.
 */
export interface ReviewTask {
  body: Body2;
  check: Check;
  evidence_chain: EvidenceChain1;
  id: Id;
  kind: Kind1;
  pin_number: PinNumber;
  recommended_action: RecommendedAction;
  refdes: Refdes2;
  source_classes: SourceClasses;
  stable_key: StableKey;
  status: Status8;
  status_group: StatusGroup3;
  status_label: StatusLabel2;
  subject: Subject1;
  title: Title4;
  trust_tier: TrustTier3;
}
/**
 * Summary returned after an uploaded project becomes the active context.
 */
export interface ImportResponse {
  ok: Ok;
  pin_table: PinTableSummary;
  project: WorkbenchProject;
  review_package: ReviewPackageSummary;
  selected_refdes: SelectedRefdes2;
  summary: WorkbenchSummary;
  task_counts: ReviewTaskCounts;
}
/**
 * Capture pin-table intake status shown beside first-class imports.
 */
export interface PinTableSummary {
  accepted_findings: AcceptedFindings;
  accepted_refdes: AcceptedRefdes;
  affected_refdes: AffectedRefdes;
  affected_refdes_list: AffectedRefdesList;
  checks: Checks1;
  rejected: Rejected;
  rejected_findings: RejectedFindings;
  rejected_unknown_refdes: RejectedUnknownRefdes;
  source: Source3;
  status: Status9;
}
export interface Checks1 {
  [k: string]: number;
}
/**
 * One pin-table finding rejected before it can enter the L1 queue.
 */
export interface RejectedPinTableFindingView {
  message: Message;
  net: Net1;
  pin_number: PinNumber1;
  reason: Reason5;
  refdes: Refdes3;
  rule_id: RuleId;
}
/**
 * Project metadata shown in the SPA header.
 */
export interface WorkbenchProject {
  bom_source: BomSource;
  generated_at: GeneratedAt;
  name: Name1;
  netlist_source: NetlistSource;
  netlist_type: NetlistType;
  profiles_dir: ProfilesDir;
  scope: Scope;
}
/**
 * Review-package manifest status; not an electrical conclusion.
 */
export interface ReviewPackageSummary {
  artifacts: Artifacts;
  hash_mismatch: HashMismatch;
  manual_gap_count: ManualGapCount;
  missing_optional: MissingOptional;
  missing_required: MissingRequired;
  package_status: PackageStatus;
  present: Present;
  recommended_action: RecommendedAction1;
  source: Source4;
  status: Status11;
  status_group: StatusGroup4;
  status_label: StatusLabel3;
  total: Total1;
}
/**
 * One exported review-package artifact shown as evidence coverage.
 */
export interface ReviewPackageArtifactView {
  expected_sha256: ExpectedSha256;
  kind: Kind2;
  name: Name2;
  note: Note;
  path: Path1;
  required: Required;
  sha256: Sha256;
  status: Status10;
}
/**
 * Count summary for the current workbench run.
 */
export interface WorkbenchSummary {
  bom_matched: BomMatched;
  components: Components;
  error_count: ErrorCount;
  manual: Manual1;
  pass_count: PassCount1;
  validated: Validated;
  warn_count: WarnCount;
}
/**
 * Stable task counts for filter chips and export summaries.
 */
export interface ReviewTaskCounts {
  error: Error1;
  manual: Manual2;
  pass_count: PassCount2;
  total: Total2;
  warn: Warn1;
}
/**
 * Top-level SPA state returned by ``/api/workbench/state``.
 */
export interface WorkbenchState {
  capabilities: WorkbenchCapabilities;
  net_checks: NetChecks;
  pin_table: PinTableSummary;
  project: WorkbenchProject;
  queue: Queue;
  review_package: ReviewPackageSummary;
  review_tasks: ReviewTasks;
  risk_hint_details: RiskHintsView;
  risk_hints: RiskHintsSummary;
  selected_refdes: SelectedRefdes3;
  summary: WorkbenchSummary;
  task_counts: ReviewTaskCounts;
}
/**
 * Feature flags surfaced to the SPA.
 */
export interface WorkbenchCapabilities {
  chat: Chat;
  datasheet_candidate_lookup_enabled: DatasheetCandidateLookupEnabled;
  datasheet_search_enabled: DatasheetSearchEnabled1;
  document_index_enabled: DocumentIndexEnabled;
  pin_table_enabled: PinTableEnabled;
  review_package_enabled: ReviewPackageEnabled;
  risk_hints_enabled: RiskHintsEnabled;
}
/**
 * Design-level net check shown in the project summary area.
 */
export interface NetCheckView {
  check: Check1;
  evidence: Evidence4;
  net_name: NetName;
  nodes: Nodes;
  status: Status12;
  status_group: StatusGroup5;
  status_label: StatusLabel4;
  summary: Summary3;
}
/**
 * One row in the SPA review queue.
 */
export interface ReviewQueueItem {
  deterministic_status: DeterministicStatus;
  deterministic_status_group: DeterministicStatusGroup;
  deterministic_status_label: DeterministicStatusLabel;
  document_status: DocumentStatus;
  evidence_count: EvidenceCount;
  issue_count: IssueCount;
  manufacturer: Manufacturer3;
  package: Package1;
  part_number: PartNumber3;
  pin_table_task_count: PinTableTaskCount;
  profile_path: ProfilePath;
  profile_status: ProfileStatus;
  refdes: Refdes4;
  risk_hint_count: RiskHintCount;
  status: Status13;
  status_group: StatusGroup6;
  status_label: StatusLabel5;
  subtitle: Subtitle;
  task_count: TaskCount;
  task_counts: ComponentTaskCounts;
  task_ids: TaskIds;
  title: Title5;
  top_task_id: TopTaskId;
  trust_tier: TrustTier5;
  value: Value2;
}
/**
 * Risk-hints state for the SPA.
 */
export interface RiskHintsView {
  accepted: Accepted;
  accepted_external_count: AcceptedExternalCount;
  count: Count1;
  external_status: ExternalStatus;
  rejected: Rejected1;
  rejected_external_count: RejectedExternalCount;
  wrapped_refdes_count: WrappedRefdesCount1;
}
/**
 * Safe rejected-hint summary without rejected free text.
 */
export interface RejectedRiskHintSummary {
  count: Count2;
  reason: Reason6;
}
/**
 * Backward-compatible compact risk-hints summary.
 */
export interface RiskHintsSummary {
  accepted_external_count: AcceptedExternalCount1;
  count: Count3;
  external_status: ExternalStatus1;
  rejected_external_count: RejectedExternalCount1;
}
