"""Tests for R003 — NC pin handling (EDA-only stage + datasheet closure)."""

from pathlib import Path
from typing import Any

from hardwise.adapters.base import BoardRegistry, ComponentRecord, NcPinRecord
from hardwise.checklist.checks.r003_nc_pin_handling import check


def _nc_pin(
    refdes: str = "U1",
    pin_number: str = "3",
    pin_name: str = "NC",
    pin_electrical_type: str = "passive",
) -> NcPinRecord:
    return NcPinRecord(
        refdes=refdes,
        pin_number=pin_number,
        pin_name=pin_name,
        pin_electrical_type=pin_electrical_type,
        source_file=Path("/tmp/mock.kicad_sch"),
    )


def _registry(component_value: str = "LM7805", refdes: str = "U1") -> BoardRegistry:
    return BoardRegistry(
        project_dir=Path("/tmp/mock"),
        components=[
            ComponentRecord(
                refdes=refdes,
                value=component_value,
                footprint="",
                datasheet="",
                source_file=Path("/tmp/mock.kicad_sch"),
                source_kind="schematic",
            ),
        ],
    )


class _FakeCollection:
    """In-memory stand-in for a Chroma collection — matches the subset of the
    Chroma client API that `store.vector.query_chunks` actually calls.
    """

    def __init__(self, rows: list[dict]) -> None:
        # Each row: {"text": str, "metadata": {"part_ref":..., "page":..., "source_pdf":...}}
        self._rows = rows

    def count(self) -> int:
        return len(self._rows)

    def query(self, query_texts: list[str], n_results: int) -> dict[str, Any]:
        kept = self._rows[:n_results]
        return {
            "documents": [[r["text"] for r in kept]],
            "metadatas": [[r["metadata"] for r in kept]],
            "distances": [[r.get("distance", 0.5) for r in kept]],
        }


def test_check_produces_medium_finding_per_nc_pin() -> None:
    pins = [_nc_pin("U1", "3"), _nc_pin("U2", "5"), _nc_pin("J1", "4")]
    findings = check(pins)
    assert len(findings) == 3
    for f in findings:
        assert f.rule_id == "R003"
        assert f.severity == "medium"


def test_check_empty_input_returns_empty() -> None:
    assert check([]) == []


def test_finding_evidence_tokens_present() -> None:
    findings = check([_nc_pin("U1", "3")])
    assert len(findings) == 1
    assert findings[0].evidence_tokens
    assert "sch:" in findings[0].evidence_tokens[0]


def test_finding_message_contains_pin_info() -> None:
    findings = check([_nc_pin("U1", "3", "NC", "input")])
    f = findings[0]
    assert "U1" in f.message
    assert "pin 3" in f.message
    assert "NC" in f.message
    assert "input" in f.message


def test_finding_refdes_is_set() -> None:
    findings = check([_nc_pin("J1", "9")])
    assert findings[0].refdes == "J1"


def test_check_on_pic_programmer_nc_pins() -> None:
    from hardwise.adapters.kicad import parse_project

    registry = parse_project(Path("data/projects/pic_programmer"))
    findings = check(registry.nc_pins, registry=registry)
    assert len(findings) == 22
    refdes_set = {f.refdes for f in findings}
    assert "J1" in refdes_set
    assert "P2" in refdes_set
    assert "P3" in refdes_set
    assert "U1" in refdes_set
    assert "U4" in refdes_set
    assert "U5" in refdes_set
    assert "U6" in refdes_set
    connector_findings = [f for f in findings if f.severity == "low"]
    ic_findings = [f for f in findings if f.severity == "medium"]
    assert len(connector_findings) == 3
    assert len(ic_findings) == 19
    assert {f.decision for f in connector_findings} == {"likely_ok"}
    assert {f.decision for f in ic_findings} == {"reviewer_to_confirm"}


# ─── DR-009 datasheet closure tests ─────────────────────────────────────────


def test_no_registry_or_collection_degrades_to_eda_only() -> None:
    """Slice 3 backward-compat: no datasheet evidence, no decision."""
    findings = check([_nc_pin("U1", "3")])
    assert findings[0].evidence_chain == []
    assert findings[0].decision is None


def test_registry_only_no_collection_marks_reviewer_to_confirm() -> None:
    """Registry gives enough context to distinguish an IC from connector noise."""
    findings = check([_nc_pin("U1", "3")], registry=_registry())
    assert findings[0].evidence_chain == []
    assert findings[0].decision == "reviewer_to_confirm"


def test_collection_only_no_registry_still_degrades() -> None:
    coll = _FakeCollection([])
    findings = check([_nc_pin("U1", "3")], collection=coll)
    assert findings[0].evidence_chain == []
    assert findings[0].decision is None


def test_datasheet_says_nc_yields_likely_ok() -> None:
    coll = _FakeCollection(
        [
            {
                "text": "Pin 2 is N.C. and should be left floating.",
                "metadata": {"part_ref": "LM7805", "page": 4, "source_pdf": "l78.pdf"},
            }
        ]
    )
    findings = check(
        [_nc_pin("U1", "2")], registry=_registry(component_value="LM7805"), collection=coll
    )
    f = findings[0]
    assert f.decision == "likely_ok"
    assert len(f.evidence_chain) == 2  # 1 EDA + 1 datasheet
    assert f.evidence_chain[0].source == "eda"
    assert f.evidence_chain[1].source == "datasheet"
    assert f.evidence_chain[1].token == "pdf:l78.pdf#p4"


def test_datasheet_describes_function_yields_likely_issue() -> None:
    coll = _FakeCollection(
        [
            {
                "text": "Pin 2 is the feedback signal (FB-) — connect to output divider.",
                "metadata": {"part_ref": "LM7805", "page": 4, "source_pdf": "l78.pdf"},
            }
        ]
    )
    findings = check(
        [_nc_pin("U1", "2", "FB-")], registry=_registry(component_value="LM7805"), collection=coll
    )
    assert findings[0].decision == "likely_issue"
    # EDA + 1 datasheet step
    assert len(findings[0].evidence_chain) == 2


def test_no_relevant_pin_hit_yields_reviewer_to_confirm() -> None:
    """Hits don't mention pin 7 → reviewer_to_confirm, evidence_chain has only EDA step."""
    coll = _FakeCollection(
        [
            {
                "text": "Pin 2 is VCC, pin 3 is GND. Output stage is rated for 1A.",
                "metadata": {"part_ref": "LM7805", "page": 1, "source_pdf": "l78.pdf"},
            }
        ]
    )
    findings = check(
        [_nc_pin("U1", "7")], registry=_registry(component_value="LM7805"), collection=coll
    )
    assert findings[0].decision == "reviewer_to_confirm"
    assert len(findings[0].evidence_chain) == 1  # EDA only
    assert findings[0].evidence_chain[0].source == "eda"


def test_part_ref_filter_drops_other_parts() -> None:
    """Hit for a different part is filtered out, falls back to no part-match → reviewer."""
    coll = _FakeCollection(
        [
            {
                "text": "Pin 2 is NC on this device.",
                "metadata": {"part_ref": "DIFFERENT_PART", "page": 1, "source_pdf": "other.pdf"},
            }
        ]
    )
    findings = check(
        [_nc_pin("U1", "2")], registry=_registry(component_value="LM7805"), collection=coll
    )
    # Part_ref filter rules out the only hit; fallback path takes unfiltered
    # hits; that single unfiltered hit mentions "pin 2" + "NC" so we get likely_ok.
    # This documents the part_ref fallback behavior (see _classify docstring).
    assert findings[0].decision == "likely_ok"


def test_classify_caps_at_three_datasheet_steps() -> None:
    """Even if 5 hits mention pin 2 NC, evidence_chain holds at most 3 datasheet steps."""
    rows = [
        {
            "text": f"Pin 2 is NC (chunk {i}).",
            "metadata": {"part_ref": "LM7805", "page": i, "source_pdf": "l78.pdf"},
        }
        for i in range(1, 6)
    ]
    coll = _FakeCollection(rows)
    findings = check(
        [_nc_pin("U1", "2")], registry=_registry(component_value="LM7805"), collection=coll
    )
    # 1 EDA + 3 datasheet capped = 4 max
    assert len(findings[0].evidence_chain) == 4


def test_query_chunks_exception_does_not_crash() -> None:
    class _ExplodingCollection:
        def count(self) -> int:
            return 1

        def query(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("simulated chroma fault")

    findings = check(
        [_nc_pin("U1", "2")],
        registry=_registry(component_value="LM7805"),
        collection=_ExplodingCollection(),
    )
    # Failure isolated to vector store; finding still produced, decision is
    # reviewer_to_confirm because no hits.
    assert findings[0].decision == "reviewer_to_confirm"
    assert len(findings[0].evidence_chain) == 1  # EDA only


def test_finding_status_stays_open_when_decision_set() -> None:
    """DR-009 §3: rule code writes decision, never status."""
    coll = _FakeCollection(
        [
            {
                "text": "Pin 2 is NC.",
                "metadata": {"part_ref": "LM7805", "page": 1, "source_pdf": "l78.pdf"},
            }
        ]
    )
    findings = check(
        [_nc_pin("U1", "2")], registry=_registry(component_value="LM7805"), collection=coll
    )
    assert findings[0].decision == "likely_ok"
    assert findings[0].status == "open"  # untouched by the rule


def test_empty_collection_handles_gracefully() -> None:
    """When the vector store has no chunks, decision is reviewer_to_confirm."""
    findings = check(
        [_nc_pin("U1", "2")],
        registry=_registry(component_value="LM7805"),
        collection=_FakeCollection([]),
    )
    assert findings[0].decision == "reviewer_to_confirm"
    assert len(findings[0].evidence_chain) == 1
