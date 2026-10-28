"""Revision comparison contracts: source differences, never electrical verdicts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceEvidence(Contract):
    file: str
    sha256: str
    locator: str


class SourceDigest(Contract):
    file: str
    role: Literal["netlist", "bom"]
    sha256: str
    size_bytes: int


class Observation(Contract):
    state: Literal["known", "missing", "ambiguous"] = "known"
    values: tuple[str, ...] = ()
    evidence: tuple[SourceEvidence, ...] = ()


class Endpoint(Contract):
    refdes: str
    pin: str


class NetworkView(Contract):
    name: str
    endpoints: tuple[Endpoint, ...]
    ambiguous: bool = False
    evidence: tuple[SourceEvidence, ...] = ()


class RevisionView(Contract):
    label: str
    component_count: int
    net_count: int
    bom_row_count: int
    sources: tuple[SourceDigest, ...]
    networks: tuple[NetworkView, ...]


ChangeKind = Literal[
    "component_added",
    "component_removed",
    "attribute_changed",
    "connection_changed",
    "net_renamed",
]


class RevisionChange(Contract):
    id: str
    kind: ChangeKind
    refdes: str
    pin: str | None = None
    field: str
    before: Observation | None = None
    after: Observation | None = None
    explanation: str
    # Direct shared-net neighbours, not a propagated electrical impact claim.
    related_refdes: tuple[str, ...] = ()
    related_count: int = 0


class ComparisonIssue(Contract):
    side: Literal["before", "after", "both"]
    code: str
    refdes: str | None = None
    explanation: str
    evidence: tuple[SourceEvidence, ...] = ()


class ComparisonSummary(Contract):
    added: int
    removed: int
    attribute_changes: int
    connection_changes: int
    net_renames: int
    changed_components: int
    unresolved: int
    unchanged_components: int


class ComparisonResult(Contract):
    schema_version: Literal["hardwise.revision.v1"] = "hardwise.revision.v1"
    comparison_id: str
    status: Literal["differences", "no_observed_difference", "needs_review"]
    before: RevisionView
    after: RevisionView
    summary: ComparisonSummary
    changes: tuple[RevisionChange, ...]
    issues: tuple[ComparisonIssue, ...]
    scope: tuple[str, ...] = (
        "仅比较 Telesis/PST 网表和 CSV/TSV BOM 中实际声明的器件、属性及引脚连接。",
        "按精确位号关联；位号重编号显示为增删，不自动认定同一物理器件。",
        "BOM 与网表分别比较，不用某个来源覆盖另一个；字段采用文本比较，不推断单位等价。",
        "未声明引脚不等于开路；网络改名不等于连接变化。未知和冲突单列。",
        "直接同网器件仅为复查线索，不代表完整电气影响；不判断改动正确性或整板安全。",
        "仅记录源文件名、哈希和定位；报告不包含原理图几何，不需要规格书、AI或档案批准。",
    )
    input_format: Literal["telesis_csv_v1", "pst_csv_v1"] = "telesis_csv_v1"
    electrical_verdict: Literal["not_evaluated"] = "not_evaluated"


class SnapshotComponent(Contract):
    refdes: str
    attributes: dict[str, Observation]
    evidence: tuple[SourceEvidence, ...]
    identity_ambiguous: bool = False


class RevisionSnapshot(Contract):
    input_format: Literal["telesis_csv_v1", "pst_csv_v1"] = "telesis_csv_v1"
    view: RevisionView
    components: dict[str, SnapshotComponent]
    issues: tuple[ComparisonIssue, ...] = ()
    # Endpoints can occur in multiple declarations; never pick the first.
    pin_networks: dict[str, dict[str, tuple[str, ...]]] = Field(default_factory=dict)
