"""Agent tool manifest — structured surface the tool-use loop will call.

Each tool takes a Pydantic input and returns a Pydantic output. Lookups that
may not find their target return a discriminated union so the agent reads
`result.status` instead of guessing whether `result is None`. This materializes
the CLAUDE.md rule "Tools return structured null/unknown, never fabricated"
on the agent side.

Five tools ship in this module, wired against the Slice 3 stores and the
deterministic validator boundary:

  - list_components   → relational store query, optional filters
  - get_component     → relational store + registry; returns closest_matches on miss
  - get_nc_pins       → relational store query, optional refdes filter
  - search_datasheet  → vector store query, optional part_ref filter
  - run_component_validation → IR Design + explicit profile target validation

`TOOL_DEFINITIONS` exposes them in Anthropic-SDK `tools=[...]` shape; runner.py
registers it directly with `messages.create(tools=...)`.
"""

from __future__ import annotations

import difflib
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from hardwise.adapters.base import BoardRegistry
from hardwise.store.relational import query_components, query_nc_pins
from hardwise.store.vector import query_chunks

# ─────────────────────────── Common output shapes ──────────────────────────


class ComponentSummary(BaseModel):
    """Minimal component fields the agent actually needs in a tool reply."""

    refdes: str
    value: str = ""
    footprint: str = ""
    datasheet: str = ""


class NcPinSummary(BaseModel):
    """Minimal NC pin fields the agent actually needs in a tool reply."""

    refdes: str
    pin_number: str
    pin_name: str = ""
    pin_electrical_type: str = ""


class DatasheetHit(BaseModel):
    """One vector-store hit with provenance the Evidence Ledger will check."""

    text: str
    page: int
    source_pdf: str
    part_ref: str | None = None
    distance: float


# ─────────────────────────── 1. list_components ────────────────────────────


class ListComponentsInput(BaseModel):
    """Filter the registry by value substring or refdes prefix."""

    name_filter: str | None = Field(
        default=None,
        description="Substring matched case-insensitively against the value field.",
    )
    refdes_prefix: str | None = Field(
        default=None,
        description="Refdes prefix (e.g. 'C', 'U', 'R'). Matched case-sensitively.",
    )


class ListComponentsResult(BaseModel):
    """Filtered components plus the total count matched."""

    found: bool
    components: list[ComponentSummary] = Field(default_factory=list)
    total: int = 0


def list_components(session: Session, tool_input: ListComponentsInput) -> ListComponentsResult:
    """Return components from the relational store, optionally filtered."""
    rows = query_components(session)
    if tool_input.refdes_prefix:
        prefix = tool_input.refdes_prefix
        rows = [r for r in rows if r.refdes.startswith(prefix)]
    if tool_input.name_filter:
        needle = tool_input.name_filter.lower()
        rows = [r for r in rows if needle in (r.value or "").lower()]
    summaries = [
        ComponentSummary(
            refdes=r.refdes,
            value=r.value,
            footprint=r.footprint,
            datasheet=r.datasheet,
        )
        for r in rows
    ]
    return ListComponentsResult(
        found=len(summaries) > 0,
        components=summaries,
        total=len(summaries),
    )


# ─────────────────────────── 2. get_component ──────────────────────────────


class GetComponentInput(BaseModel):
    """Lookup one component by exact refdes."""

    refdes: str


class ComponentFound(BaseModel):
    """Discriminated success branch."""

    status: Literal["found"] = "found"
    component: ComponentSummary


class ComponentNotFound(BaseModel):
    """Discriminated unknown branch — never fabricates the refdes."""

    status: Literal["not_found"] = "not_found"
    refdes: str
    closest_matches: list[str] = Field(default_factory=list)


def get_component(
    session: Session,
    registry: BoardRegistry,
    tool_input: GetComponentInput,
) -> ComponentFound | ComponentNotFound:
    """Lookup one component; on miss return the registry's closest matches.

    `closest_matches` comes from `difflib.get_close_matches` against the full
    refdes set — exactly the suggestions the model should pick from (CLAUDE.md
    "Tools never fabricate; return structured null + suggestions").
    """
    rows = query_components(session)
    target = tool_input.refdes
    for r in rows:
        if r.refdes == target:
            return ComponentFound(
                component=ComponentSummary(
                    refdes=r.refdes,
                    value=r.value,
                    footprint=r.footprint,
                    datasheet=r.datasheet,
                )
            )
    candidates = sorted(registry.refdes_set)
    suggestions = difflib.get_close_matches(target, candidates, n=5, cutoff=0.6)
    return ComponentNotFound(refdes=target, closest_matches=suggestions)


# ─────────────────────────── 3. get_nc_pins ────────────────────────────────


class GetNcPinsInput(BaseModel):
    """Optionally filter NC pins to one refdes."""

    refdes_filter: str | None = Field(
        default=None,
        description="If set, only NC pins whose refdes equals this value are returned.",
    )


class GetNcPinsResult(BaseModel):
    """NC pins that passed the filter, plus the total count."""

    found: bool
    pins: list[NcPinSummary] = Field(default_factory=list)
    total: int = 0


def get_nc_pins(session: Session, tool_input: GetNcPinsInput) -> GetNcPinsResult:
    """Return NC pins from the relational store, optionally filtered to one refdes."""
    rows = query_nc_pins(session)
    if tool_input.refdes_filter:
        rows = [r for r in rows if r.refdes == tool_input.refdes_filter]
    summaries = [
        NcPinSummary(
            refdes=r.refdes,
            pin_number=r.pin_number,
            pin_name=r.pin_name,
            pin_electrical_type=r.pin_electrical_type,
        )
        for r in rows
    ]
    return GetNcPinsResult(
        found=len(summaries) > 0,
        pins=summaries,
        total=len(summaries),
    )


# ─────────────────────────── 4. search_datasheet ───────────────────────────


class SearchDatasheetInput(BaseModel):
    """Semantic query against the datasheet vector store."""

    query: str
    part_ref: str | None = Field(
        default=None,
        description="If set, only hits whose part_ref equals this value are returned.",
    )
    top_k: int = Field(default=5, ge=1, le=50)


class SearchDatasheetResult(BaseModel):
    """Datasheet hits + the original query echoed back for provenance."""

    found: bool
    hits: list[DatasheetHit] = Field(default_factory=list)
    query: str


def search_datasheet(collection: Any, tool_input: SearchDatasheetInput) -> SearchDatasheetResult:
    """Run a vector-store query, optionally filtered to one part_ref."""
    raw_hits = query_chunks(collection, tool_input.query, top_k=tool_input.top_k)
    hits: list[DatasheetHit] = []
    for r in raw_hits:
        meta = r.get("metadata") or {}
        if tool_input.part_ref and meta.get("part_ref") != tool_input.part_ref:
            continue
        hits.append(
            DatasheetHit(
                text=r.get("text", ""),
                page=int(meta.get("page", 0)),
                source_pdf=str(meta.get("source_pdf", "")),
                part_ref=meta.get("part_ref"),
                distance=float(r.get("distance", 0.0)),
            )
        )
    return SearchDatasheetResult(found=len(hits) > 0, hits=hits, query=tool_input.query)


# ─────────────────────────── 5. run_component_validation ───────────────────


class RunComponentValidationInput(BaseModel):
    """Run the deterministic family validator for one assigned component."""

    refdes: str


class ValidationCheckSummary(BaseModel):
    """One check row (pin or component-level) flattened for the agent reply."""

    check: str
    status: Literal["PASS", "WARN", "ERROR"]
    summary: str
    evidence: list[str] = Field(default_factory=list)


class ValidationRan(BaseModel):
    """Discriminated success branch — the validator produced a report."""

    status: Literal["validated"] = "validated"
    refdes: str
    profile_part_number: str
    overall: Literal["PASS", "WARN", "ERROR"]
    counts: dict[str, int]
    checks: list[ValidationCheckSummary] = Field(default_factory=list)


class ValidationNoProfile(BaseModel):
    """Refdes exists in the design but has no assigned validation profile."""

    status: Literal["no_profile"] = "no_profile"
    refdes: str
    reason: str = "No validation profile is assigned to this refdes; manual review."


class ValidationRefdesNotFound(BaseModel):
    """Refdes is not in the design — never fabricates it."""

    status: Literal["not_found"] = "not_found"
    refdes: str
    closest_matches: list[str] = Field(default_factory=list)


def run_component_validation(
    design: Any,
    targets: dict[str, Any],
    tool_input: RunComponentValidationInput,
) -> ValidationRan | ValidationNoProfile | ValidationRefdesNotFound:
    """Validate one assigned component against its structured profile.

    `targets` maps refdes -> DatasheetProfile (the explicit assignment, same
    concept as the V3.5 validation-targets manifest). The tool never auto-matches
    a profile and never fabricates a refdes:

      - refdes not in the design        -> not_found + closest_matches
      - refdes in design, no profile    -> no_profile (manual review)
      - refdes assigned a profile       -> validated + PASS/WARN/ERROR rows

    Importing the validator lazily keeps `agent/tools.py` import-cheap and mirrors
    the dispatch pattern in `validation/component.py`.
    """
    from hardwise.validation.component import validate_component_against_profile

    refdes = tool_input.refdes
    component = design.components.get(refdes)
    if component is None:
        candidates = sorted(design.components.keys())
        suggestions = difflib.get_close_matches(refdes, candidates, n=5, cutoff=0.6)
        return ValidationRefdesNotFound(refdes=refdes, closest_matches=suggestions)

    profile = targets.get(refdes)
    if profile is None:
        return ValidationNoProfile(refdes=refdes)

    report = validate_component_against_profile(component, profile, design)
    checks = [
        ValidationCheckSummary(
            check=pin.pin_name or pin.pin_number,
            status=pin.status,
            summary=pin.summary,
            evidence=pin.evidence,
        )
        for pin in report.pin_results
    ] + [
        ValidationCheckSummary(
            check=check.check,
            status=check.status,
            summary=check.summary,
            evidence=check.evidence,
        )
        for check in report.component_checks
    ]
    pin_counts = report.counts_by_status
    comp_counts = report.component_counts_by_status
    counts = {k: pin_counts[k] + comp_counts[k] for k in ("PASS", "WARN", "ERROR")}
    return ValidationRan(
        refdes=refdes,
        profile_part_number=report.profile_part_number,
        overall=report.status,
        counts=counts,
        checks=checks,
    )


# ─────────────────────────── Anthropic SDK manifest ────────────────────────


TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "list_components",
        "description": (
            "Return components from the schematic registry, optionally filtered by "
            "refdes prefix or value substring. Use this to enumerate caps, transistors, "
            "or any class of part by prefix."
        ),
        "input_schema": ListComponentsInput.model_json_schema(),
    },
    {
        "name": "get_component",
        "description": (
            "Look up one component by exact refdes (e.g. 'U3'). On hit, returns "
            "value/footprint/datasheet. On miss, returns the closest-matching refdes "
            "suggestions from the registry — NEVER fabricate a refdes; pick from "
            "suggestions or ask the user."
        ),
        "input_schema": GetComponentInput.model_json_schema(),
    },
    {
        "name": "get_nc_pins",
        "description": (
            "Return pins marked NC (no_connect) on the schematic, optionally filtered "
            "to one refdes. Use when checking R003 (NC pin handling) or verifying a "
            "specific device's NC strategy."
        ),
        "input_schema": GetNcPinsInput.model_json_schema(),
    },
    {
        "name": "search_datasheet",
        "description": (
            "Semantic query against the datasheet vector store; returns text chunks "
            "with page + source_pdf provenance. Optionally filter to one part_ref. "
            "Use for cross-checking schematic decisions against vendor specs."
        ),
        "input_schema": SearchDatasheetInput.model_json_schema(),
    },
    {
        "name": "run_component_validation",
        "description": (
            "Run the deterministic family validator for one component by exact refdes "
            "(e.g. 'Q1'). Returns structured pin/topology PASS/WARN/ERROR rows with "
            "evidence tokens — use this whenever asked whether a component is wired "
            "correctly, instead of reasoning about electrical limits yourself. On a "
            "refdes with no assigned profile, returns 'no_profile' (manual review); on "
            "an unknown refdes, returns closest-matching suggestions — NEVER fabricate "
            "a refdes or a PASS/FAIL verdict."
        ),
        "input_schema": RunComponentValidationInput.model_json_schema(),
    },
]
