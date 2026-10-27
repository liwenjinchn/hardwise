/* Generated from backend Pydantic contracts. Do not edit. */

export type Available = boolean;
export type ContextId = string | null;
export type DataCategories = string[];
export type Destination = string | null;
export type DisclosureId = string | null;
export type Mode = "real" | "fake" | "snapshot" | "unavailable";
export type Model = string | null;
export type Notice = string;
export type Version = string;
export type DisclosureId1 = string | null;
export type Content = string;
export type Role = "user" | "assistant";
export type History = ChatMessage[];
export type Question = string;
export type SelectedRefdes = string | null;
export type Answer = string;
export type ClaimVerification = "unverified";
export type DatasheetSearchEnabled = boolean;
export type Error = ("invalid_envelope" | "stale_scope" | "invalid_catalog") | null;
export type Code = "unknown_fact" | "binding_mismatch" | "unknown_conditions" | "duplicate_claim";
export type Index = number;
export type Issues = ClaimIssue[];
export type Notices = string[];
export type ObjectId = string;
export type ObjectKind = "component" | "net" | "project";
export type Topic =
  "rating" | "voltage_envelope" | "operating_condition" | "part_identity" | "connectivity" | "document";
export type Requests = EvidenceRequest[];
export type CallId = string;
export type JsonValue = unknown;
export type ConditionsStatus = "explicit" | "not_required" | "unknown";
export type Id = string;
export type Kind = "observation" | "assessment" | "approved_parameter" | "source_coverage" | "lookup_result";
export type ObjectId1 = string;
export type ObjectKind1 = "component" | "net" | "project";
export type PropertyKey = string;
export type RuleVersion = string | null;
export type ScopeId = string;
export type SourceTokens = string[];
export type Unit = string | null;
export type VerifiedFacts = EvidenceFact[];
export type Mode1 = "fake" | "real" | "snapshot";
export type ResponseKind = "model_explanation" | "structured_explanation" | "insufficient_evidence" | "offline_notice";
export type SelectedRefdes1 = string | null;
export type Suggestions = string[];
export type Evidence = string[];
export type AuditStatus = "ok" | "missing_local_source";
export type LocalSource = string | null;
export type Reason = string;
export type SourceClass =
  "live_retrieved" | "reviewed_profile" | "profile_candidate" | "document_index" | "design_source" | "unknown";
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
export type ContractVersion = "hardwise.assessment.v1";
export type EvidenceKind = "SOURCE_FACT" | "DERIVED" | "HYPOTHESIS";
export type LegacyStatus = ("PASS" | "WARN" | "ERROR" | "UNKNOWN" | "NOT_APPLICABLE") | null;
export type MigrationState = "current" | "legacy_needs_review";
export type NeedsReview = boolean;
export type NotApplicableReason = string | null;
export type Result = "PASS" | "FAIL" | "UNKNOWN" | "NOT_APPLICABLE";
export type RuleVersion1 = string;
export type Severity = "ERROR" | "WARNING" | "INFO";
/**
 * Legacy attention alias; use result/severity for new decisions.
 */
export type Status1 = "PASS" | "WARN" | "ERROR" | "UNKNOWN" | "NOT_APPLICABLE";
export type Description = string;
export type ItemNumber = string | null;
export type Manufacturer = string;
export type PartNumber = string;
export type ItemNumber1 = string | null;
export type RefdesList = string[];
export type Column = number;
export type Name = string;
export type Value = string;
export type SourceFields = BomSourceField[];
export type SourceFile = string;
export type SourceLine = number;
export type Source = string;
export type SourceLine1 = number | null;
export type Value1 = string;
export type AuditStatus1 = string;
export type Label = string;
export type LocalSource1 = string | null;
export type Reason1 = string;
export type SourceClass1 = string;
export type Token1 = string;
export type TrustTier1 = "l1" | "l2" | "l3";
export type Evidence1 = EvidenceView[];
export type Status2 = string;
export type StatusGroup = "error" | "warn" | "pass" | "manual";
export type StatusLabel = string;
export type Subject = string;
export type Summary1 = string;
export type Checks = CheckView[];
export type DeterministicStatus = string;
export type DeterministicStatusGroup = "error" | "warn" | "pass" | "manual";
export type DeterministicStatusLabel = string;
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
export type Status3 = string;
export type Candidates1 = number;
export type GroupId = string | null;
export type Identity = string;
export type IdentityKind = string;
export type Reason3 = string;
export type Source2 = string | null;
export type Status4 = string;
export type SuggestedFamily = string;
export type Title1 = string | null;
export type Url = string | null;
export type Body = string;
export type Evidence2 = EvidenceView[];
export type Kind1 = string;
export type Status5 = string;
export type StatusGroup1 = "error" | "warn" | "pass" | "manual";
export type Title2 = string;
export type TrustTier2 = "l1" | "l2" | "l3";
export type EvidenceChain = EvidenceChainItem[];
export type Manufacturer2 = string;
export type MatchReason = string;
export type MatchStatus = string;
export type Package = string;
export type PartNumber1 = string;
export type ConnectionAmbiguity = string[];
export type ElectricalType = string;
export type Evidence3 = EvidenceView[];
export type IsNc = boolean;
export type Name1 = string;
export type Net = string | null;
export type Number = string;
export type Status6 = string | null;
export type Summary2 = string;
export type Pins = PinView[];
export type LegacyReviewStatus = string | null;
export type Lifecycle = string | null;
export type PartNumber2 = string;
export type Path = string | null;
export type Reason4 = string;
export type Status7 = string;
export type ProfilePartNumber = string;
export type Refdes = string;
export type Body1 = string;
export type Refdes1 = string;
export type Severity1 = string | null;
export type Title3 = string;
export type WrappedRefdesCount = number;
export type RiskHints = RiskHintView[];
export type Status8 = string;
export type StatusGroup2 = "error" | "warn" | "pass" | "manual";
export type StatusLabel1 = string;
export type Error1 = number;
export type Manual = number;
export type PassCount = number;
export type Total = number;
export type Warn = number;
export type Body2 = string;
export type Check = string | null;
export type DerivedFromTaskId = string | null;
export type EvidenceChain1 = EvidenceChainItem[];
export type Id1 = string;
export type Kind2 = string;
export type PinNumber = string | null;
export type RecommendedAction = string;
export type Refdes2 = string;
export type CurrentFingerprint = string | null;
export type Fingerprint = string | null;
export type PreviousStatus = ("open" | "accepted_risk" | "false_positive" | "resolved" | "accepted" | "waived") | null;
export type Reason5 = string;
export type StableKey = string;
export type Status9 = "open" | "accepted_risk" | "false_positive" | "resolved" | "accepted" | "waived" | "needs_review";
export type UpdatedAt = string;
export type SourceClasses = string[];
export type StableKey1 = string;
export type Status10 = string;
export type StatusGroup3 = "error" | "warn" | "pass" | "manual";
export type StatusLabel2 = string;
export type Subject1 = string | null;
export type Title4 = string;
export type TrustTier3 = "l1" | "l2" | "l3";
export type Tasks = ReviewTask[];
export type TrustTier4 = "l1" | "l2" | "l3";
export type Value2 = string;
/**
 * @minItems 1
 * @maxItems 100
 */
export type Conditions1 = [FieldCondition, ...FieldCondition[]];
export type Description2 = string;
export type Kind3 = "unconditional" | "dc_relation" | "unsupported";
export type DeclaredBy = string;
export type Manufacturer3 = string;
/**
 * @minItems 1
 */
export type Packages = [string, ...string[]];
/**
 * @minItems 1
 */
export type PartNumbers = [string, ...string[]];
export type Nature = "intrinsic" | "application_recommendation" | "board_policy";
export type Pointer = string;
export type Reason6 = string;
export type Role1 = "identity" | "minimum" | "typical" | "maximum" | "definition" | "relationship";
export type Sharing = "allow" | "withhold";
export type DocumentRevision = string;
export type DocumentSha256 = string;
export type Excerpt = string;
export type Locator = string;
export type Page = number;
export type Actor = "human";
export type Decision = "allow" | "withhold";
export type DeclaredAt = string;
export type DeclaredBy1 = string;
export type Reason7 = string;
export type SourceSha256 = string;
export type Url1 = string;
export type Unit1 = string;
export type ExpectedProjectId = string;
export type ExpectedRevision = string;
export type ExpectedRunId = string;
export type ProfileName = string;
export type Editable = boolean;
export type Lifecycle1 = "DRAFT" | "REVIEWED" | "READY" | "RETIRED";
export type Name2 = string;
export type ExtractedAt = string;
export type ExtractedModel = string;
/**
 * @minItems 1
 */
export type Conditions2 = [FieldCondition, ...FieldCondition[]];
export type Actor1 = "human";
export type ContentSha256 = string;
export type Decision1 = "approved" | "rejected" | "needs_information";
export type Reason8 = string;
export type ReviewedAt = string;
export type Reviewer = string;
export type Decisions = FieldDecision[];
export type Nature1 = "intrinsic" | "application_recommendation" | "board_policy";
export type Pointer1 = string;
export type Role2 = "identity" | "minimum" | "typical" | "maximum" | "definition" | "relationship";
export type DocumentRevision1 = string;
export type DocumentSha2561 = string;
export type Excerpt1 = string;
export type Locator1 = string;
export type Page1 = number;
export type Url2 = string;
export type Subject2 = string;
export type Unit2 = string;
export type Value3 = boolean | number | string;
export type Fields = ReviewedField[];
export type RetirementReason = string | null;
export type Status11 = "DRAFT" | "REVIEWED" | "READY" | "RETIRED";
export type Version1 = "hardwise.profile_review.v1";
export type PartNumber3 = string;
export type PartNumberAliases = string[];
export type Category = string;
export type Evidence5 = string[];
export type Function = string;
export type Name3 = string;
export type Number1 = string;
export type RecommendedTopology = string[];
export type SchematicPinAliases = string[];
export type Pins1 = PinProfile[];
export type ReviewStatus1 = "ready" | "needs_review";
export type SchemaVersion = string;
export type StorageIntegrity = "complete" | "legacy_incomplete";
export type DocumentRevision2 = string;
export type DocumentSha2562 = string;
export type Evidence6 = string;
export type GroundPin = string;
export type MinimumVoltage = number;
export type Page2 = number;
export type RequiredPackage = string;
export type SourceUrl = string;
export type SupplyPin = string;
export type TargetPin = string;
export type VoltageRelations = PinVoltageRelation[];
export type Profiles = ExcerptProfileView[];
export type ProjectId = string;
export type Revision = string;
export type RunId = string;
export type SavedProjectId = string | null;
export type BomQuantityConflicts = BomQuantityColumnConflict[] | null;
export type ElectricalVerdict = "not_applicable";
export type Guardrails = string[];
export type Id2 = "netlist" | "bom" | "validation" | "documents" | "pin_table" | "review_package";
export type Label1 = string;
export type Key = string;
export type Label2 = string;
export type Total1 = number | null;
export type Unit3 = string;
export type Value4 = number;
export type Metrics = EvidencePackageMetric[];
export type RecommendedAction1 = string;
export type Source3 = string | null;
export type SourceToken = string | null;
export type Status12 = "present" | "partial" | "gap" | "not_configured";
export type StatusGroup4 = "pass" | "warn" | "manual";
export type StatusLabel3 = string;
export type Summary3 = string;
export type TrustBoundary = string;
export type Lanes = EvidencePackageLane[];
export type AttachedTokens = string[];
export type CitedTokens = string[];
export type ExportAllowed = boolean;
export type MissingTokens = string[];
export type Reason9 = string;
export type Status13 = "not_attached" | "no_pdf_citations" | "unknown";
export type SchemaVersion1 = string;
export type Scope = string;
export type AffectedTasks = number;
export type MissingLocalSources = number;
export type MissingTokens1 = string[];
export type Reason10 = string;
export type SignoffReady = boolean;
export type Status14 = "ready" | "blocked";
export type LocallyPresentTokens = string[];
export type MissingTokens2 = string[];
export type ObservedAt = string | null;
export type Reason11 = string;
export type Status15 = "observed" | "unknown";
export type UncheckedTokens = string[];
export type Ok = boolean;
export type AcceptedFindings = number;
export type AcceptedRefdes = string[];
export type AffectedRefdes = number;
export type AffectedRefdesList = string[];
export type Message = string;
export type Net1 = string | null;
export type PinNumber1 = string | null;
export type Reason12 = string;
export type Refdes3 = string | null;
export type RuleId = string;
export type Rejected = RejectedPinTableFindingView[];
export type RejectedFindings = number;
export type RejectedUnknownRefdes = string[];
export type Source4 = string | null;
export type Status16 = "loaded" | "not_configured";
export type BomSource = string;
export type GeneratedAt = string;
export type Name4 = string;
export type NetlistSource = string;
export type NetlistType = string;
export type ProfilesDir = string;
export type Scope1 = string;
export type ExpectedSha256 = string | null;
export type Kind4 = string;
export type Name5 = string;
export type Note = string | null;
export type Path1 = string;
export type Required = boolean;
export type Sha256 = string | null;
export type Status17 = string;
export type Artifacts = ReviewPackageArtifactView[];
export type HashMismatch = number;
export type ManualGapCount = number;
export type MissingOptional = number;
export type MissingRequired = number;
export type PackageStatus = "not_configured" | "complete" | "optional_gap" | "missing_required" | "hash_mismatch";
export type Present = number;
export type RecommendedAction2 = string;
export type Source5 = string | null;
export type Status18 = "loaded" | "not_configured";
export type StatusGroup5 = "error" | "warn" | "pass" | "manual";
export type StatusLabel4 = string;
export type Total2 = number;
export type SelectedRefdes2 = string | null;
export type BomMatched = number;
export type Components = number;
export type ErrorCount = number;
export type Manual1 = number;
export type NotApplicableCount = number;
export type PassCount1 = number;
export type UnknownCount = number;
export type Validated = number;
export type WarnCount = number;
export type Error2 = number;
export type Manual2 = number;
export type PassCount2 = number;
export type Total3 = number;
export type Warn1 = number;
export type CapturedAt = string;
export type CreatedAt = string;
export type Event = "human_decision" | "inputs_changed" | "disappeared";
export type Id3 = number;
export type RunId1 = string;
export type StableKey2 = string;
export type Events = ReviewHistoryEvent[];
export type ProjectId1 = string;
export type RunId2 = string;
export type CreatedAt1 = string | null;
export type ProjectId2 = string;
export type Applicability = "applicable" | "unknown" | "not_applicable";
export type CatalogVersion = string;
export type Evidence7 = string[];
export type Instance = [unknown, unknown][];
export type ObjectId2 = string;
export type ObjectKind2 = "project" | "component" | "pin" | "net" | "relation";
export type Reason13 = string;
export type RuleId1 = string;
export type RuleVersion2 = string;
export type Candidates2 = Candidate[];
export type ObjectKind3 = "project" | "component" | "pin" | "net" | "relation";
export type RuleId2 = string;
export type Scope2 = string;
export type Version2 = string;
export type Rules = RuleDefinition[];
export type Version3 = string;
export type CandidateId = string;
export type Evidence8 = string[];
export type Reason14 = string;
export type Result1 = "PASS" | "FAIL" | "UNKNOWN" | "NOT_APPLICABLE";
export type Outcomes = CandidateOutcome[];
export type SchemaVersion2 = "hardwise.candidate_coverage.v1";
export type ObjectId3 = string;
export type ObjectKind4 = "project" | "component" | "pin" | "net" | "relation";
export type Reason15 = string;
export type Scope3 = string;
export type Unsupported = UnsupportedScope[];
export type CandidateRecords = CandidateRecord[] | null;
export type Applicability1 = string;
export type ApplicabilityReason = string;
export type CandidateId1 = string;
export type Executed = boolean;
export type Instance1 = [unknown, unknown][];
export type ObjectId4 = string;
export type ObjectKind5 = string;
export type Reason16 = string;
export type Result2 = "PASS" | "FAIL" | "UNKNOWN" | "NOT_APPLICABLE";
export type RuleId3 = string;
export type DeclarationIndices = number[];
export type Endpoints = [unknown, unknown][];
export type Kind5 = "duplicate_net_name" | "repeated_endpoint" | "multiple_declarations";
export type NetNames = string[];
export type Ambiguities = ConnectionAmbiguity1[];
export type AmbiguousEndpoints = [unknown, unknown][];
export type AmbiguousNetNames = string[];
export type Line = number | null;
export type NetName = string;
/**
 * @minItems 1
 */
export type Nodes = [[unknown, unknown], ...[unknown, unknown][]];
export type Source6 = string;
export type Declarations = ConnectionDeclaration[];
export type SchemaVersion3 = "hardwise.connectivity.v1";
export type EmittedRecords = number;
export type ImplementationIdentityAssurance = "declared_rule_versions";
export type InputCaptureStatus = "captured" | "unavailable";
export type Assurance = "observed_readset_verified";
export type Path2 = string;
export type ResolvedPath = string;
export type Roles = string[];
export type Sha2561 = string;
export type SizeBytes = number;
export type Files = InputFileDigest[];
export type ReadsetSha256 = string;
export type SchemaVersion4 = "hardwise.input_reads.v1";
export type StartedAt = string;
export type VerifiedAt = string;
export type PackageVersion = string;
export type ProfileSnapshotEncoding = "json_with_nonfinite_float_tags";
export type PartNumber4 = string;
export type ReviewStatus2 = string;
export type Sha2562 = string;
export type ShareProjection = {
  [k: string]: string;
} | null;
export type Profiles1 = ProfileModelSnapshot[];
export type PythonVersion = string;
export type RawInputsArchived = false;
export type ReviewDependencyContract = string | null;
export type EmittedCount = number;
export type Name6 = string;
export type Scope4 = "pin" | "component" | "net";
export type Version4 = string;
export type RuleVersions = EmittedRuleVersion[];
export type SchemaVersion5 = "hardwise.run_provenance.v1";
export type ActiveMode = string;
export type Confirmed = boolean;
export type ConfirmedBy = string;
export type Maximum = number | null;
export type Minimum = number | null;
export type Mode2 = string;
export type Net2 = string;
export type ReferenceNet = string;
export type Source7 = string;
export type Typical = number | null;
export type Unit4 = "V";
export type Id4 = string;
export type Locator2 = string;
export type Origin = "manual" | "import" | "net_name" | "legacy_v1";
export type Candidates3 = VoltageCandidate[];
export type Action = "confirm" | "unknown";
export type CandidateId2 = string | null;
export type CandidateSha256 = string | null;
export type Id5 = string;
export type Mode3 = string;
export type Net3 = string;
export type Origin1 = "human" | "legacy_v1";
export type Reason17 = string;
export type RecordedAt = string | null;
export type Reviewer1 = string;
export type ScopeSha256 = string;
export type Confirmations = VoltageConfirmation[];
export type ActiveMode1 = string;
export type Changes = VoltageCandidateChange[];
export type Id6 = string;
export type InvalidatedConfirmationIds = string[];
export type PreviousMode = string;
export type PreviousRevision = string;
export type Reason18 = string;
export type RecordedAt1 = string;
export type Reviewer2 = string;
export type Edits = VoltageReviewEdit[];
export type SchemaVersion6 = "hardwise.voltage_review.v1";
export type Reason19 = string;
export type RunId3 = string;
export type Status19 = "recorded" | "not_recorded";
export type Total4 = number;
export type Journal = string;
export type CommandPosix = string;
export type CommandPowershell = string;
export type SavedId = string;
export type Launches = RestoredProjectLaunch[];
export type RestoreId = string;
export type SavedProjectIds = string[];
export type SourceUnownedProjectIds = string[];
export type Events1 = ReviewHistoryEvent[];
export type Limit = number;
export type Offset = number;
export type ProjectId3 = string;
export type RunId4 = string;
export type Total5 = number;
export type Id7 = string;
export type Name7 = string;
export type ProjectId4 = string;
export type Snapshot = string;
export type Projects = SavedProjectView[];
export type ExpectedProjectId1 = string;
export type ExpectedRevision1 = string;
export type ExpectedRunId1 = string;
export type Reason20 = string;
export type Reviewer3 = string;
/**
 * @minItems 1
 * @maxItems 1000
 */
export type Selections = [VoltageSelection, ...VoltageSelection[]];
export type Action1 = "confirm" | "unknown";
export type CandidateId3 = string | null;
export type ExpectedScopeSha256 = string;
export type Mode4 = string;
export type Net4 = string;
export type ActiveMode2 = string | null;
export type ExpectedProjectId2 = string;
export type ExpectedRevision2 = string;
export type ExpectedRunId2 = string;
export type Reason21 = string;
/**
 * @maxItems 1000
 */
export type RemoveIds = string[];
export type Reviewer4 = string;
/**
 * @maxItems 1000
 */
export type Upserts = VoltageCandidate[];
export type Editable1 = boolean;
export type Nets = string[];
export type ProjectId5 = string;
export type Revision1 = string;
export type RunId5 = string;
export type SavedProjectId1 = string | null;
export type CandidateIds = string[];
export type ConfirmationId = string | null;
export type Mode5 = string;
export type Net5 = string;
export type ScopeSha2561 = string;
export type SelectedCandidateId = string | null;
export type Status20 = "unconfirmed" | "conflict" | "confirmed" | "unknown" | "needs_review";
export type Scopes = VoltageReviewScope[];
export type Basis = "emitted_check_records";
export type Boundary = string;
export type CompletedChecks = number;
export type FullCandidateCount = number | null;
export type GeneratedChecks = number;
export type LegacyNeedsReview = number;
export type NeedsReviewChecks = number;
export type NotApplicableChecks = number;
export type RuleSetVersion = string;
export type UnknownChecks = number;
export type UnsupportedComponents = number;
export type Basis1 = "enumerated_rule_instances";
export type Boundary1 = string;
export type ApplicabilityUnknownCount = number;
export type ApplicableCount = number;
export type CandidateCount = number;
export type CompletedCount = number;
export type NotApplicableCount1 = number;
export type UnexecutedCount = number;
export type UnknownCount1 = number;
export type UnsupportedScopeCount = number;
export type CatalogVersion1 = string;
export type Chat = boolean;
export type DatasheetCandidateLookupEnabled = boolean;
export type DatasheetSearchEnabled1 = boolean;
export type DocumentIndexEnabled = boolean;
export type PinTableEnabled = boolean;
export type ReviewPackageEnabled = boolean;
export type RiskHintsEnabled = boolean;
export type Check1 = string;
export type Evidence9 = EvidenceView[];
export type NetName1 = string;
export type Nodes1 = string[];
export type Status21 = string;
export type StatusGroup6 = "error" | "warn" | "pass" | "manual";
export type StatusLabel5 = string;
export type Summary4 = string;
export type NetChecks = NetCheckView[];
export type DeterministicStatus1 = string;
export type DeterministicStatusGroup1 = "error" | "warn" | "pass" | "manual";
export type DeterministicStatusLabel1 = string;
export type DocumentStatus = string;
export type EvidenceCount = number;
export type IssueCount = number;
export type Manufacturer4 = string;
export type Package1 = string;
export type PartNumber5 = string;
export type PinTableTaskCount = number;
export type ProfilePath = string | null;
export type ProfileStatus = string;
export type Refdes4 = string;
export type RiskHintCount = number;
export type Status22 = string;
export type StatusGroup7 = "error" | "warn" | "pass" | "manual";
export type StatusLabel6 = string;
export type Subtitle = string;
export type TaskCount = number;
export type TaskIds = string[];
export type Title5 = string;
export type TopTaskId = string | null;
export type TrustTier5 = "l1" | "l2" | "l3";
export type Value5 = string;
export type Queue = ReviewQueueItem[];
export type Accepted = number;
export type AcceptedRisk = number;
export type FalsePositive = number;
export type HistoryCount = number;
export type NeedsReview1 = number;
export type Open = number;
export type ProjectId6 = string | null;
export type Resolved = number;
export type RunId6 = string | null;
export type StaleRemovedOnRerun = number;
export type Storage = "memory" | "local_file";
export type TotalTasks = number;
export type Waived = number;
export type AffectedRefdes1 = string[];
export type Axis = "electrical" | "evidence";
export type Check2 = string | null;
export type DerivedTaskCount = number;
export type Id8 = string;
export type Identity1 = string;
export type RawTaskCount = number;
export type RecommendedAction3 = string;
export type StableKey3 = string;
export type StableKeys = string[];
export type StatusGroup8 = "error" | "warn" | "pass" | "manual";
export type TaskIds1 = string[];
export type Title6 = string;
export type TrustTier6 = "l1" | "l2" | "l3";
export type ReviewGroups = ReviewTaskGroup[];
export type ReviewTasks = ReviewTask[];
export type Accepted1 = RiskHintView[];
export type AcceptedExternalCount = number;
export type Count1 = number;
export type ExternalStatus = string;
export type Count2 = number;
export type Reason22 = string;
export type Rejected1 = RejectedRiskHintSummary[];
export type RejectedExternalCount = number;
export type WrappedRefdesCount1 = number;
export type AcceptedExternalCount1 = number;
export type Count3 = number;
export type ExternalStatus1 = string;
export type RejectedExternalCount1 = number;
export type SelectedRefdes3 = string | null;
export type ActiveMode3 = string;
export type Facts = VoltageFact[];
export type SchemaVersion7 = "hardwise.voltage_facts.v1";

export interface WorkbenchContracts {
  ai_disclosure: AIDisclosure;
  chat_request: ChatRequest;
  chat_response: ChatResponse;
  component_detail: ComponentDetail;
  excerpt_request: ExcerptRequest;
  excerpts: ExcerptResponse;
  import_response: ImportResponse;
  offline_review_history: OfflineReviewHistory;
  project_restore: ProjectRestoreReceipt;
  review_history: ReviewHistoryPage;
  run_provenance: RunProvenanceResponse;
  saved_project: SavedProjectView;
  saved_project_catalog: SavedProjectCatalog;
  voltage_batch_request: VoltageBatchRequest;
  voltage_candidates_request: VoltageCandidatesRequest;
  voltage_review: VoltageReviewResponse;
  workbench_state: WorkbenchState;
}
export interface AIDisclosure {
  available: Available;
  context_id: ContextId;
  data_categories: DataCategories;
  destination: Destination;
  disclosure_id: DisclosureId;
  mode: Mode;
  model: Model;
  notice: Notice;
  version: Version;
}
/**
 * User question sent from the Copilot panel.
 */
export interface ChatRequest {
  disclosure_id?: DisclosureId1;
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
  claim_verification: ClaimVerification;
  datasheet_search_enabled: DatasheetSearchEnabled;
  explanation_review?: ExplanationReview | null;
  mode: Mode1;
  response_kind: ResponseKind;
  selected_refdes: SelectedRefdes1;
  suggestions: Suggestions;
  trace: Trace;
  unsupported_evidence_tokens: UnsupportedEvidenceTokens;
  wrapped_count: WrappedCount;
}
/**
 * Only server-owned matching facts escape; rejected model prose/values do not.
 */
export interface ExplanationReview {
  error: Error;
  issues: Issues;
  notices: Notices;
  requests: Requests;
  verified_facts: VerifiedFacts;
}
export interface ClaimIssue {
  code: Code;
  index: Index;
}
/**
 * Unverified follow-up proposals have no free-form verdict or numeric authority.
 */
export interface EvidenceRequest {
  object_id: ObjectId;
  object_kind: ObjectKind;
  topic: Topic;
}
/**
 * Created only from dispatched server data, never accepted as model authority.
 *
 * The digest detects accidental mutation/substitution; it is not a signature,
 * independent engineering review, or authentication of a datasheet field.
 */
export interface EvidenceFact {
  call_id: CallId;
  conditions: Conditions;
  conditions_status: ConditionsStatus;
  id: Id;
  kind: Kind;
  object_id: ObjectId1;
  object_kind: ObjectKind1;
  property_key: PropertyKey;
  rule_version: RuleVersion;
  scope_id: ScopeId;
  source_tokens: SourceTokens;
  unit: Unit;
  value: JsonValue;
}
export interface Conditions {
  [k: string]: JsonValue;
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
  assessment: Assessment | null;
  bom: BomView | null;
  checks: Checks;
  deterministic_status: DeterministicStatus;
  deterministic_status_group: DeterministicStatusGroup;
  deterministic_status_label: DeterministicStatusLabel;
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
  status: Status8;
  status_group: StatusGroup2;
  status_label: StatusLabel1;
  task_counts: ComponentTaskCounts;
  tasks: Tasks;
  trust_tier: TrustTier4;
  value: Value2;
}
/**
 * Canonical check contract; old status-only records cannot certify a result.
 */
export interface Assessment {
  contract_version: ContractVersion;
  evidence_kind: EvidenceKind;
  legacy_status: LegacyStatus;
  migration_state: MigrationState;
  needs_review: NeedsReview;
  not_applicable_reason: NotApplicableReason;
  result: Result;
  rule_version: RuleVersion1;
  severity: Severity;
  status: Status1;
}
/**
 * BOM identity shown in detail and prep packet views.
 */
export interface BomView {
  description: Description;
  item_number: ItemNumber;
  manufacturer: Manufacturer;
  part_number: PartNumber;
  quantity_column_conflict: BomQuantityColumnConflict | null;
  source: Source;
  source_line: SourceLine1;
  value: Value1;
}
/**
 * Unresolved table quantity declarations, separate from component identity.
 */
export interface BomQuantityColumnConflict {
  item_number: ItemNumber1;
  refdes_list: RefdesList;
  source_fields: SourceFields;
  source_file: SourceFile;
  source_line: SourceLine;
}
/**
 * One original table cell; ordinal preserves repeated column names.
 */
export interface BomSourceField {
  column: Column;
  name: Name;
  value: Value;
}
/**
 * Validation check detail shown in the component panel.
 */
export interface CheckView {
  assessment: Assessment | null;
  evidence: Evidence1;
  status: Status2;
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
  status: Status4;
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
  status: Status3;
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
  kind: Kind1;
  status: Status5;
  status_group: StatusGroup1;
  title: Title2;
  trust_tier: TrustTier2;
}
/**
 * Pin/net detail shown in the component panel.
 */
export interface PinView {
  assessment: Assessment | null;
  connection_ambiguity?: ConnectionAmbiguity;
  electrical_type: ElectricalType;
  evidence: Evidence3;
  is_nc: IsNc;
  name: Name1;
  net: Net;
  number: Number;
  status: Status6;
  summary: Summary2;
}
/**
 * Profile match metadata for one component.
 */
export interface ProfileView {
  legacy_review_status: LegacyReviewStatus;
  lifecycle: Lifecycle;
  part_number: PartNumber2;
  path: Path;
  reason: Reason4;
  status: Status7;
}
/**
 * Registry-verified external hint for read-only display.
 */
export interface RiskHintView {
  body: Body1;
  refdes: Refdes1;
  severity: Severity1;
  source: EvidenceView | null;
  title: Title3;
  wrapped_refdes_count: WrappedRefdesCount;
}
/**
 * Task counts scoped to one component.
 */
export interface ComponentTaskCounts {
  error: Error1;
  manual: Manual;
  pass_count: PassCount;
  total: Total;
  warn: Warn;
}
/**
 * One finding-first review task in the SPA workflow.
 */
export interface ReviewTask {
  assessment: Assessment | null;
  body: Body2;
  check: Check;
  derived_from_task_id: DerivedFromTaskId;
  evidence_chain: EvidenceChain1;
  id: Id1;
  kind: Kind2;
  pin_number: PinNumber;
  recommended_action: RecommendedAction;
  refdes: Refdes2;
  review_decision: ReviewDecisionView | null;
  source_classes: SourceClasses;
  stable_key: StableKey1;
  status: Status10;
  status_group: StatusGroup3;
  status_label: StatusLabel2;
  subject: Subject1;
  title: Title4;
  trust_tier: TrustTier3;
}
/**
 * One human workflow decision keyed by a stable finding key.
 */
export interface ReviewDecisionView {
  current_fingerprint: CurrentFingerprint;
  fingerprint: Fingerprint;
  previous_status: PreviousStatus;
  reason: Reason5;
  stable_key: StableKey;
  status: Status9;
  updated_at: UpdatedAt;
}
export interface ExcerptRequest {
  edit: ExcerptEdit;
  expected_project_id: ExpectedProjectId;
  expected_revision: ExpectedRevision;
  expected_run_id: ExpectedRunId;
  profile_name: ProfileName;
}
export interface ExcerptEdit {
  conditions: Conditions1;
  declared_by: DeclaredBy;
  identity: ReviewIdentity | null;
  nature: Nature;
  pointer: Pointer;
  reason: Reason6;
  role: Role1;
  sharing: Sharing;
  source: ManualSource;
  unit: Unit1;
}
export interface FieldCondition {
  description: Description2;
  kind: Kind3;
}
export interface ReviewIdentity {
  manufacturer: Manufacturer3;
  packages: Packages;
  part_numbers: PartNumbers;
}
export interface ManualSource {
  document_revision: DocumentRevision;
  document_sha256: DocumentSha256;
  excerpt: Excerpt;
  locator: Locator;
  page: Page;
  sharing?: ExcerptSharingDeclaration | null;
  url: Url1;
}
/**
 * A recorded human assertion, not authentication or proof of redistribution rights.
 */
export interface ExcerptSharingDeclaration {
  actor: Actor;
  decision: Decision;
  declared_at: DeclaredAt;
  declared_by: DeclaredBy1;
  reason: Reason7;
  source_sha256: SourceSha256;
}
export interface ExcerptResponse {
  editable: Editable;
  profiles: Profiles;
  project_id: ProjectId;
  revision: Revision;
  run_id: RunId;
  saved_project_id: SavedProjectId;
}
export interface ExcerptProfileView {
  lifecycle: Lifecycle1;
  name: Name2;
  profile: DatasheetProfile;
  sharing_states: SharingStates;
  values: Values;
}
/**
 * Structured electrical limits extracted from one datasheet.
 */
export interface DatasheetProfile {
  abs_max: AbsMax;
  evidence: Evidence4;
  extracted_at: ExtractedAt;
  extracted_model: ExtractedModel;
  field_review: ProfileReview | null;
  part_number: PartNumber3;
  part_number_aliases: PartNumberAliases;
  pin_function: PinFunction;
  pins: Pins1;
  recommended: Recommended;
  review_status: ReviewStatus1;
  schema_version: SchemaVersion;
  storage_integrity: StorageIntegrity;
  voltage_relations: VoltageRelations;
}
export interface AbsMax {
  [k: string]: boolean | number | string;
}
export interface Evidence4 {
  [k: string]: string;
}
export interface ProfileReview {
  fields: Fields;
  identity: ReviewIdentity;
  retirement_reason: RetirementReason;
  status: Status11;
  version: Version1;
}
export interface ReviewedField {
  conditions: Conditions2;
  decisions: Decisions;
  nature: Nature1;
  pointer: Pointer1;
  role: Role2;
  source: FieldSource;
  subject: Subject2;
  unit: Unit2;
  value: Value3;
}
export interface FieldDecision {
  actor: Actor1;
  content_sha256: ContentSha256;
  decision: Decision1;
  reason: Reason8;
  reviewed_at: ReviewedAt;
  reviewer: Reviewer;
}
export interface FieldSource {
  document_revision: DocumentRevision1;
  document_sha256: DocumentSha2561;
  excerpt: Excerpt1;
  locator: Locator1;
  page: Page1;
  sharing?: ExcerptSharingDeclaration | null;
  url: Url2;
}
export interface PinFunction {
  [k: string]: string;
}
/**
 * Structured datasheet facts for one package pin.
 */
export interface PinProfile {
  category: Category;
  evidence: Evidence5;
  function: Function;
  limits: Limits;
  name: Name3;
  number: Number1;
  recommended_topology: RecommendedTopology;
  schematic_pin_aliases: SchematicPinAliases;
}
export interface Limits {
  [k: string]: boolean | number | string;
}
export interface Recommended {
  [k: string]: boolean | number | string;
}
/**
 * Target pin range relative to ground, with an upper bound at another pin.
 */
export interface PinVoltageRelation {
  document_revision: DocumentRevision2;
  document_sha256: DocumentSha2562;
  evidence: Evidence6;
  ground_pin: GroundPin;
  minimum_voltage: MinimumVoltage;
  page: Page2;
  required_package: RequiredPackage;
  source_url: SourceUrl;
  supply_pin: SupplyPin;
  target_pin: TargetPin;
}
export interface SharingStates {
  [k: string]: string;
}
export interface Values {
  [k: string]: unknown;
}
/**
 * Summary returned after an uploaded project becomes the active context.
 */
export interface ImportResponse {
  evidence_package: EvidencePackageSummary;
  ok: Ok;
  pin_table: PinTableSummary;
  project: WorkbenchProject;
  review_package: ReviewPackageSummary;
  selected_refdes: SelectedRefdes2;
  summary: WorkbenchSummary;
  task_counts: ReviewTaskCounts;
}
/**
 * Six evidence lanes that are intentionally not collapsed into one score.
 */
export interface EvidencePackageSummary {
  bom_quantity_conflicts: BomQuantityConflicts;
  electrical_verdict: ElectricalVerdict;
  guardrails: Guardrails;
  lanes: Lanes;
  original_delivery: OriginalDelivery;
  schema_version: SchemaVersion1;
  scope: Scope;
  signoff_readiness: SignoffReadiness;
  source_audit: SourceAudit;
}
/**
 * One independent evidence input or deterministic coverage lane.
 */
export interface EvidencePackageLane {
  id: Id2;
  label: Label1;
  metrics: Metrics;
  recommended_action: RecommendedAction1;
  source: Source3;
  source_token: SourceToken;
  status: Status12;
  status_group: StatusGroup4;
  status_label: StatusLabel3;
  summary: Summary3;
  trust_boundary: TrustBoundary;
}
/**
 * One count or ratio whose unit stays explicit.
 */
export interface EvidencePackageMetric {
  key: Key;
  label: Label2;
  total: Total1;
  unit: Unit3;
  value: Value4;
}
export interface OriginalDelivery {
  attached_tokens: AttachedTokens;
  cited_tokens: CitedTokens;
  export_allowed: ExportAllowed;
  missing_tokens: MissingTokens;
  reason: Reason9;
  status: Status13;
}
/**
 * Deprecated compatibility field; never certifies signoff or original delivery.
 */
export interface SignoffReadiness {
  affected_tasks: AffectedTasks;
  missing_local_sources: MissingLocalSources;
  missing_tokens: MissingTokens1;
  reason: Reason10;
  signoff_ready: SignoffReady;
  status: Status14;
}
export interface SourceAudit {
  locally_present_tokens: LocallyPresentTokens;
  missing_tokens: MissingTokens2;
  observed_at: ObservedAt;
  reason: Reason11;
  status: Status15;
  unchecked_tokens: UncheckedTokens;
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
  source: Source4;
  status: Status16;
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
  reason: Reason12;
  refdes: Refdes3;
  rule_id: RuleId;
}
/**
 * Project metadata shown in the SPA header.
 */
export interface WorkbenchProject {
  bom_source: BomSource;
  generated_at: GeneratedAt;
  name: Name4;
  netlist_source: NetlistSource;
  netlist_type: NetlistType;
  profiles_dir: ProfilesDir;
  scope: Scope1;
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
  recommended_action: RecommendedAction2;
  source: Source5;
  status: Status18;
  status_group: StatusGroup5;
  status_label: StatusLabel4;
  total: Total2;
}
/**
 * One exported review-package artifact shown as evidence coverage.
 */
export interface ReviewPackageArtifactView {
  expected_sha256: ExpectedSha256;
  kind: Kind4;
  name: Name5;
  note: Note;
  path: Path1;
  required: Required;
  sha256: Sha256;
  status: Status17;
}
/**
 * Count summary for the current workbench run.
 */
export interface WorkbenchSummary {
  bom_matched: BomMatched;
  components: Components;
  error_count: ErrorCount;
  manual: Manual1;
  not_applicable_count: NotApplicableCount;
  pass_count: PassCount1;
  unknown_count: UnknownCount;
  validated: Validated;
  warn_count: WarnCount;
}
/**
 * Stable task counts for filter chips and export summaries.
 */
export interface ReviewTaskCounts {
  error: Error2;
  manual: Manual2;
  pass_count: PassCount2;
  total: Total3;
  warn: Warn1;
}
export interface OfflineReviewHistory {
  captured_at: CapturedAt;
  events: Events;
  project_id: ProjectId1;
  run_id: RunId2;
  run_provenance: RunProvenance;
  total: Total4;
}
export interface ReviewHistoryEvent {
  created_at: CreatedAt;
  decision: ReviewDecisionView;
  event: Event;
  id: Id3;
  run_id: RunId1;
  stable_key: StableKey2;
}
export interface RunProvenance {
  [k: string]: RunProvenanceResponse;
}
export interface RunProvenanceResponse {
  created_at: CreatedAt1;
  project_id: ProjectId2;
  provenance: RunProvenance1 | null;
  reason: Reason19;
  run_id: RunId3;
  status: Status19;
}
export interface RunProvenance1 {
  candidate_coverage: CandidateSnapshot | null;
  candidate_records: CandidateRecords;
  connectivity?: ConnectivityProjection | null;
  emitted_records: EmittedRecords;
  implementation_identity_assurance: ImplementationIdentityAssurance;
  input_capture_status: InputCaptureStatus;
  inputs: InputReadManifest | null;
  package_version: PackageVersion;
  profile_bindings: ProfileBindings;
  profile_snapshot_encoding: ProfileSnapshotEncoding;
  profiles: Profiles1;
  python_version: PythonVersion;
  raw_inputs_archived: RawInputsArchived;
  review_dependency_contract: ReviewDependencyContract;
  rule_versions: RuleVersions;
  schema_version: SchemaVersion5;
  voltage_review?: VoltageReviewDocument | null;
}
export interface CandidateSnapshot {
  candidates: Candidates2;
  catalog: RuleCatalog;
  outcomes: Outcomes;
  schema_version: SchemaVersion2;
  unsupported: Unsupported;
}
export interface Candidate {
  applicability: Applicability;
  catalog_version: CatalogVersion;
  evidence: Evidence7;
  instance: Instance;
  object_id: ObjectId2;
  object_kind: ObjectKind2;
  reason: Reason13;
  rule_id: RuleId1;
  rule_version: RuleVersion2;
}
export interface RuleCatalog {
  rules: Rules;
  version: Version3;
}
export interface RuleDefinition {
  object_kind: ObjectKind3;
  rule_id: RuleId2;
  scope: Scope2;
  version: Version2;
}
export interface CandidateOutcome {
  candidate_id: CandidateId;
  evidence: Evidence8;
  reason: Reason14;
  result: Result1;
}
export interface UnsupportedScope {
  object_id: ObjectId3;
  object_kind: ObjectKind4;
  reason: Reason15;
  scope: Scope3;
}
export interface CandidateRecord {
  applicability: Applicability1;
  applicability_reason: ApplicabilityReason;
  candidate_id: CandidateId1;
  executed: Executed;
  instance: Instance1;
  object_id: ObjectId4;
  object_kind: ObjectKind5;
  reason: Reason16;
  result: Result2;
  rule_id: RuleId3;
}
export interface ConnectivityProjection {
  ambiguities: Ambiguities;
  ambiguous_endpoints: AmbiguousEndpoints;
  ambiguous_net_names: AmbiguousNetNames;
  declarations: Declarations;
  resolved_nets: ResolvedNets;
  schema_version: SchemaVersion3;
}
export interface ConnectionAmbiguity1 {
  declaration_indices: DeclarationIndices;
  endpoints: Endpoints;
  kind: Kind5;
  net_names: NetNames;
}
/**
 * One logical source record; continuation lines remain one declaration.
 */
export interface ConnectionDeclaration {
  line: Line;
  net_name: NetName;
  nodes: Nodes;
  source: Source6;
}
export interface ResolvedNets {
  [k: string]: [unknown, unknown][];
}
export interface InputReadManifest {
  assurance: Assurance;
  files: Files;
  readset_sha256: ReadsetSha256;
  schema_version: SchemaVersion4;
  started_at: StartedAt;
  verified_at: VerifiedAt;
}
export interface InputFileDigest {
  path: Path2;
  resolved_path: ResolvedPath;
  roles: Roles;
  sha256: Sha2561;
  size_bytes: SizeBytes;
}
export interface ProfileBindings {
  [k: string]: string;
}
export interface ProfileModelSnapshot {
  part_number: PartNumber4;
  review_status: ReviewStatus2;
  sha256: Sha2562;
  share_projection?: ShareProjection;
  values: Values1;
}
export interface Values1 {
  [k: string]: unknown;
}
export interface EmittedRuleVersion {
  emitted_count: EmittedCount;
  name: Name6;
  scope: Scope4;
  version: Version4;
}
/**
 * Input order is audit order; latest declaration per net/mode supersedes old ones.
 */
export interface VoltageReviewDocument {
  active_mode: ActiveMode;
  candidates: Candidates3;
  confirmations: Confirmations;
  edits?: Edits;
  schema_version: SchemaVersion6;
}
export interface VoltageCandidate {
  fact: VoltageFact;
  id: Id4;
  locator: Locator2;
  origin: Origin;
}
/**
 * One user-supplied DC envelope relative to an identified reference net.
 */
export interface VoltageFact {
  confirmed: Confirmed;
  confirmed_by: ConfirmedBy;
  maximum: Maximum;
  minimum: Minimum;
  mode: Mode2;
  net: Net2;
  reference_net: ReferenceNet;
  source: Source7;
  typical: Typical;
  unit: Unit4;
}
/**
 * A recorded user assertion, not authenticated identity or engineering approval.
 */
export interface VoltageConfirmation {
  action: Action;
  candidate_id: CandidateId2;
  candidate_sha256: CandidateSha256;
  id: Id5;
  mode: Mode3;
  net: Net3;
  origin: Origin1;
  reason: Reason17;
  recorded_at: RecordedAt;
  reviewer: Reviewer1;
  scope_sha256: ScopeSha256;
}
export interface VoltageReviewEdit {
  active_mode: ActiveMode1;
  changes: Changes;
  id: Id6;
  invalidated_confirmation_ids: InvalidatedConfirmationIds;
  previous_mode: PreviousMode;
  previous_revision: PreviousRevision;
  reason: Reason18;
  recorded_at: RecordedAt1;
  reviewer: Reviewer2;
}
export interface VoltageCandidateChange {
  after: VoltageCandidate | null;
  before: VoltageCandidate | null;
}
export interface ProjectRestoreReceipt {
  journal: Journal;
  launches: Launches;
  restore_id: RestoreId;
  saved_project_ids: SavedProjectIds;
  source_unowned_project_ids: SourceUnownedProjectIds;
}
export interface RestoredProjectLaunch {
  command_posix: CommandPosix;
  command_powershell: CommandPowershell;
  saved_id: SavedId;
}
export interface ReviewHistoryPage {
  events: Events1;
  limit: Limit;
  offset: Offset;
  project_id: ProjectId3;
  run_id: RunId4;
  total: Total5;
}
export interface SavedProjectView {
  id: Id7;
  name: Name7;
  project_id: ProjectId4;
  snapshot: Snapshot;
}
export interface SavedProjectCatalog {
  projects: Projects;
}
export interface VoltageBatchRequest {
  expected_project_id: ExpectedProjectId1;
  expected_revision: ExpectedRevision1;
  expected_run_id: ExpectedRunId1;
  reason: Reason20;
  reviewer: Reviewer3;
  selections: Selections;
}
export interface VoltageSelection {
  action: Action1;
  candidate_id: CandidateId3;
  expected_scope_sha256: ExpectedScopeSha256;
  mode: Mode4;
  net: Net4;
}
export interface VoltageCandidatesRequest {
  active_mode: ActiveMode2;
  expected_project_id: ExpectedProjectId2;
  expected_revision: ExpectedRevision2;
  expected_run_id: ExpectedRunId2;
  reason: Reason21;
  remove_ids: RemoveIds;
  reviewer: Reviewer4;
  upserts: Upserts;
}
export interface VoltageReviewResponse {
  editable: Editable1;
  nets: Nets;
  project_id: ProjectId5;
  review: VoltageReviewDocument;
  revision: Revision1;
  run_id: RunId5;
  saved_project_id: SavedProjectId1;
  scopes: Scopes;
}
export interface VoltageReviewScope {
  candidate_ids: CandidateIds;
  confirmation_id: ConfirmationId;
  mode: Mode5;
  net: Net5;
  scope_sha256: ScopeSha2561;
  selected_candidate_id: SelectedCandidateId;
  status: Status20;
}
/**
 * Top-level SPA state returned by ``/api/workbench/state``.
 */
export interface WorkbenchState {
  assessment_coverage: CheckCoverage | null;
  candidate_coverage: CandidateCoverageSummary | null;
  capabilities: WorkbenchCapabilities;
  evidence_package: EvidencePackageSummary;
  net_checks: NetChecks;
  pin_table: PinTableSummary;
  project: WorkbenchProject;
  queue: Queue;
  review_decisions: ReviewDecisionSummary | null;
  review_groups: ReviewGroups;
  review_package: ReviewPackageSummary;
  review_tasks: ReviewTasks;
  risk_hint_details: RiskHintsView;
  risk_hints: RiskHintsSummary;
  selected_refdes: SelectedRefdes3;
  summary: WorkbenchSummary;
  task_counts: ReviewTaskCounts;
  voltage_facts: VoltageFactsDocument;
}
/**
 * An explicit emitted-record denominator, not claimed whole-design coverage.
 */
export interface CheckCoverage {
  basis: Basis;
  boundary: Boundary;
  completed_checks: CompletedChecks;
  full_candidate_count: FullCandidateCount;
  generated_checks: GeneratedChecks;
  legacy_needs_review: LegacyNeedsReview;
  needs_review_checks: NeedsReviewChecks;
  not_applicable_checks: NotApplicableChecks;
  result_counts: ResultCounts;
  rule_set_version: RuleSetVersion;
  unknown_checks: UnknownChecks;
  unsupported_components: UnsupportedComponents;
}
export interface ResultCounts {
  [k: string]: number;
}
export interface CandidateCoverageSummary {
  basis: Basis1;
  boundary: Boundary1;
  by_rule: ByRule;
  catalog_version: CatalogVersion1;
  counts: CandidateCounts;
}
export interface ByRule {
  [k: string]: CandidateCounts;
}
export interface CandidateCounts {
  applicability_unknown_count: ApplicabilityUnknownCount;
  applicable_count: ApplicableCount;
  candidate_count: CandidateCount;
  completed_count: CompletedCount;
  not_applicable_count: NotApplicableCount1;
  unexecuted_count: UnexecutedCount;
  unknown_count: UnknownCount1;
  unsupported_scope_count: UnsupportedScopeCount;
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
  assessment: Assessment | null;
  check: Check1;
  evidence: Evidence9;
  net_name: NetName1;
  nodes: Nodes1;
  status: Status21;
  status_group: StatusGroup6;
  status_label: StatusLabel5;
  summary: Summary4;
}
/**
 * One row in the SPA review queue.
 */
export interface ReviewQueueItem {
  assessment: Assessment | null;
  deterministic_status: DeterministicStatus1;
  deterministic_status_group: DeterministicStatusGroup1;
  deterministic_status_label: DeterministicStatusLabel1;
  document_status: DocumentStatus;
  evidence_count: EvidenceCount;
  issue_count: IssueCount;
  manufacturer: Manufacturer4;
  package: Package1;
  part_number: PartNumber5;
  pin_table_task_count: PinTableTaskCount;
  profile_path: ProfilePath;
  profile_status: ProfileStatus;
  refdes: Refdes4;
  risk_hint_count: RiskHintCount;
  status: Status22;
  status_group: StatusGroup7;
  status_label: StatusLabel6;
  subtitle: Subtitle;
  task_count: TaskCount;
  task_counts: ComponentTaskCounts;
  task_ids: TaskIds;
  title: Title5;
  top_task_id: TopTaskId;
  trust_tier: TrustTier5;
  value: Value5;
}
/**
 * Workflow counts kept separate from electrical task counts.
 */
export interface ReviewDecisionSummary {
  accepted: Accepted;
  accepted_risk: AcceptedRisk;
  false_positive: FalsePositive;
  history_count: HistoryCount;
  needs_review: NeedsReview1;
  open: Open;
  project_id: ProjectId6;
  resolved: Resolved;
  run_id: RunId6;
  stale_removed_on_rerun: StaleRemovedOnRerun;
  storage: Storage;
  total_tasks: TotalTasks;
  waived: Waived;
}
/**
 * One reviewer-facing group while preserving every raw task for audit.
 */
export interface ReviewTaskGroup {
  affected_refdes: AffectedRefdes1;
  axis: Axis;
  check: Check2;
  derived_task_count: DerivedTaskCount;
  id: Id8;
  identity: Identity1;
  raw_task_count: RawTaskCount;
  recommended_action: RecommendedAction3;
  stable_key: StableKey3;
  stable_keys: StableKeys;
  status_group: StatusGroup8;
  task_ids: TaskIds1;
  title: Title6;
  trust_tier: TrustTier6;
}
/**
 * Risk-hints state for the SPA.
 */
export interface RiskHintsView {
  accepted: Accepted1;
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
  reason: Reason22;
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
/**
 * Portable project input, validated atomically before replacing active state.
 */
export interface VoltageFactsDocument {
  active_mode: ActiveMode3;
  facts: Facts;
  schema_version: SchemaVersion7;
}
