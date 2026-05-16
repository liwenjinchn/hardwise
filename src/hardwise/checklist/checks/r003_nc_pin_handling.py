"""R003 — NC pin handling with EDA + datasheet evidence chain (DR-009 closure).

For each NC-marked pin, R003 produces a `Finding`. When called with a board
registry and a Chroma collection, the finding carries:

  - An `evidence_chain` of one EDA step + up to 3 datasheet hits that mention
    the pin number (semantic hits about other pins are dropped from the chain,
    even when they survive the part_ref filter).
  - A `decision` ∈ {`likely_ok`, `likely_issue`, `reviewer_to_confirm`} derived
    from whether the relevant hits contain NC-keywords.

When `registry` or `collection` is None, R003 degrades to the Slice 3 EDA-only
shape (no `evidence_chain`, no `decision`) — used by checks-only tests and by
`hardwise review` runs without `--vector`.

`decision` is the rule-side machine judgment; `status` (default `open`) is the
human review flow state. R003 writes the former, never the latter (DR-009 §3).
"""

from __future__ import annotations

import re
from typing import Any

from hardwise.adapters.base import BoardRegistry, NcPinRecord
from hardwise.checklist.finding import EvidenceStep, Finding, FindingDecision

NC_PATTERN = re.compile(
    r"\b(?:N\.?C\.?|no[\s_-]?connect(?:ed)?|not\s+connected)\b", re.IGNORECASE
)
CONNECTOR_PREFIXES = ("J", "P", "CN")
IC_PREFIXES = ("U", "IC")
CONNECTOR_FOOTPRINT_HINTS = ("Connector", "Jumper", "MountingHole")


def _part_ref_for(refdes: str, registry: BoardRegistry) -> str | None:
    """Return a part-ref candidate from the registry, or None.

    Prefers `component.value` — in KiCad schematics for ICs, the value field
    typically holds the part number (e.g. `LM7805`, `PIC16F627`). Empty or
    unknown refdes returns None so the caller can fall back to unfiltered
    semantic search.
    """
    for comp in registry.components:
        if comp.refdes == refdes:
            return comp.value.strip() or None
    return None


def _classify(pin_number: str, hits: list[dict]) -> tuple[FindingDecision, list[dict]]:
    """Decide based on hits that explicitly mention this pin number.

    Returns (decision, relevant_hits) where relevant_hits is the subset whose
    text matches `\\bpin\\s*<N>\\b` (case-insensitive). Other top-k hits, even
    if semantically close, are not relevant evidence for this specific pin.

      - any relevant hit contains an NC variant → likely_ok
      - any relevant hit (no NC variant)        → likely_issue
      - no relevant hit                          → reviewer_to_confirm
    """
    pin_pattern = re.compile(rf"\bpin\s*{re.escape(pin_number)}\b", re.IGNORECASE)
    relevant: list[dict] = []
    nc_seen = False
    for h in hits:
        text = h.get("text", "") or ""
        if pin_pattern.search(text):
            relevant.append(h)
            if NC_PATTERN.search(text):
                nc_seen = True
    if relevant and nc_seen:
        return "likely_ok", relevant
    if relevant:
        return "likely_issue", relevant
    return "reviewer_to_confirm", []


def _is_connector_like(refdes: str, registry: BoardRegistry) -> bool:
    """Return True for connectors/sockets where bulk NC pins are usually intentional.

    ICs in DIP sockets (footprint contains "Socket") are still ICs — the socket
    is mechanical packaging, not an indicator that NC pins are benign.
    """

    if refdes.startswith(IC_PREFIXES):
        return False
    if refdes.startswith(CONNECTOR_PREFIXES):
        return True
    for comp in registry.components:
        if comp.refdes == refdes:
            footprint = f"{comp.footprint} {comp.value}"
            return any(hint.lower() in footprint.lower() for hint in CONNECTOR_FOOTPRINT_HINTS)
    return False


def check(
    nc_pins: list[NcPinRecord],
    registry: BoardRegistry | None = None,
    collection: Any | None = None,
    top_k: int = 5,
) -> list[Finding]:
    """Produce a Finding per NC pin; attach datasheet evidence when available.

    Backward-compatible: when `registry` or `collection` is None, the Finding
    shape matches Slice 3 (no `evidence_chain`, no `decision`). When both are
    provided, R003 queries the vector store, attaches up to 3 datasheet
    EvidenceSteps per finding, and writes `decision`.
    """
    from hardwise.store.vector import query_chunks

    findings: list[Finding] = []
    use_datasheet = registry is not None and collection is not None
    connector_groups: dict[str, list[NcPinRecord]] = {}
    remaining_pins = nc_pins

    if registry is not None:
        connector_groups = {}
        ic_pins: list[NcPinRecord] = []
        for pin in nc_pins:
            if _is_connector_like(pin.refdes, registry):
                connector_groups.setdefault(pin.refdes, []).append(pin)
            else:
                ic_pins.append(pin)
        remaining_pins = ic_pins

    for refdes in sorted(connector_groups):
        grouped = connector_groups[refdes]
        first = grouped[0]
        pin_list = ", ".join(pin.pin_number for pin in grouped)
        findings.append(
            Finding(
                rule_id="R003",
                severity="low",
                refdes=refdes,
                message=(
                    f"{refdes} has {len(grouped)} NC pins ({pin_list}) on a connector-like "
                    "part; these are typically intentional and should be checked only "
                    "against the design intent."
                ),
                evidence_tokens=[f"sch:{first.source_file.name}#{refdes}"],
                suggested_action=(
                    "For sockets/connectors, confirm the unused pins are intentionally "
                    "left NC and do not carry a required signal."
                ),
            )
        )

    for pin in remaining_pins:
        legacy_token = f"sch:{pin.source_file.name}#{pin.refdes}"
        eda_chain_token = f"sch:{pin.source_file.name}#{pin.refdes}.{pin.pin_number}"
        eda_claim = (
            f"{pin.refdes} pin {pin.pin_number} ({pin.pin_name}) marked "
            f"no_connect in schematic (electrical type: {pin.pin_electrical_type})."
        )

        evidence_chain: list[EvidenceStep] = []
        decision: FindingDecision | None = None

        if use_datasheet:
            assert registry is not None  # narrowed by use_datasheet
            part_ref = _part_ref_for(pin.refdes, registry)
            query = f"pin {pin.pin_number} {pin.pin_name}".strip()
            try:
                raw_hits = query_chunks(collection, query, top_k=top_k)
            except Exception:  # noqa: BLE001 — vector store optional; never crash review
                raw_hits = []
            if part_ref:
                filtered = [
                    h
                    for h in raw_hits
                    if (h.get("metadata") or {}).get("part_ref") == part_ref
                ]
                # If part_ref filtering nukes every hit, fall back to unfiltered
                # so reviewer_to_confirm still surfaces something to look at.
                hits = filtered or raw_hits
            else:
                hits = raw_hits

            decision, relevant = _classify(pin.pin_number, hits)
            evidence_chain.append(
                EvidenceStep(source="eda", claim=eda_claim, token=eda_chain_token)
            )
            for h in relevant[:3]:
                meta = h.get("metadata") or {}
                page = meta.get("page")
                src = meta.get("source_pdf") or "unknown.pdf"
                snippet = (h.get("text", "") or "").strip().replace("\n", " ")[:140]
                evidence_chain.append(
                    EvidenceStep(
                        source="datasheet",
                        claim=f"{src} p{page}: {snippet}",
                        token=f"pdf:{src}#p{page}",
                    )
                )

        findings.append(
            Finding(
                rule_id="R003",
                severity="medium",
                refdes=pin.refdes,
                message=(
                    f"{pin.refdes} pin {pin.pin_number} ({pin.pin_name}) "
                    f"marked NC (type: {pin.pin_electrical_type}). "
                    f"Confirm NC handling with datasheet."
                ),
                evidence_tokens=[legacy_token],
                suggested_action=(
                    "Review datasheet NC pin section. Confirm whether "
                    "pin should float, tie to GND, or tie to VCC."
                ),
                evidence_chain=evidence_chain,
                decision=decision,
            )
        )
    return findings
