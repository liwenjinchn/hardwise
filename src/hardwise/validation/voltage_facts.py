"""Use explicit voltage envelopes for DC checks; preserve unknown conditions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from fractions import Fraction
from hardwise.validation.passive_numeric import finite_quantity
from hardwise.input_provenance import read_input_text

from hardwise.ir.types import Component, Design
from hardwise.ir.voltage import VoltageFactsDocument
from hardwise.ir.voltage_review import VoltageReviewDocument


def load_voltage_facts(path: Path, design: Design) -> None:
    """Reject invalid/foreign-net inputs before assigning any new facts."""
    raw = json.loads(read_input_text(path, role="voltage_facts"))
    review = (
        VoltageReviewDocument.model_validate(raw)
        if isinstance(raw, dict) and raw.get("schema_version") == "hardwise.voltage_review.v1"
        else None
    )
    document = review.project() if review is not None else VoltageFactsDocument.model_validate(raw)
    known_nets = set(design.nets) | {
        pin.net for component in design.components.values() for pin in component.pins if pin.net
    }
    # Validate even unresolved or unselected candidates, never hide foreign nets
    # by projecting them away first. The previous design remains untouched on error.
    candidates = [candidate.fact for candidate in review.candidates] if review else document.facts
    unknown = {
        name
        for fact in candidates
        for name in (fact.net, fact.reference_net)
        if name not in known_nets
    }
    if review:
        unknown.update(d.net for d in review.confirmations if d.net not in known_nets)
    if unknown:
        raise ValueError(f"voltage facts reference unknown nets: {', '.join(sorted(unknown))}")
    design.voltage_facts = document
    design.voltage_review = review


@dataclass(frozen=True)
class TerminalStress:
    maximum_delta: float | None
    reason: str
    evidence: tuple[str, ...] = ()
    exact_delta: Fraction | None = None


def terminal_dc_stress(component: Component, design: Design) -> TerminalStress:
    """Conservative interval difference in a shared reference and selected mode."""
    if len(component.pins) != 2 or any(not pin.net for pin in component.pins):
        return TerminalStress(None, "requires exactly two connected terminals")
    document = design.voltage_facts
    by_net = {fact.net: fact for fact in document.facts if fact.mode == document.active_mode}
    facts = [by_net.get(pin.net) for pin in component.pins]
    if any(fact is None or not fact.confirmed for fact in facts):
        return TerminalStress(
            None,
            "both terminal voltages require explicit confirmation; net names and voltage_hint are candidates only",
        )
    left, right = facts
    assert left is not None and right is not None
    evidence = tuple(
        f"voltage_fact:{fact.net}#mode={fact.mode};reference={fact.reference_net};"
        f"range={fact.minimum},{fact.maximum}V;source={fact.source};confirmed_by={fact.confirmed_by}"
        for fact in (left, right)
    )
    if left.reference_net != right.reference_net:
        return TerminalStress(
            None, "terminal reference domains differ; their relationship is unknown", evidence
        )
    if any(fact.minimum is None or fact.maximum is None for fact in (left, right)):
        return TerminalStress(
            None,
            "minimum and maximum are required; a typical value alone is not a voltage envelope",
            evidence,
        )
    # The same electrical net has zero differential, even if its common mode varies.
    try:
        exact_delta = (
            Fraction(0)
            if left.net == right.net
            else max(
                abs(Fraction(str(left.minimum)) - Fraction(str(right.maximum))),
                abs(Fraction(str(left.maximum)) - Fraction(str(right.minimum))),
            )
        )
    except (ValueError, OverflowError):
        return TerminalStress(None, "DC difference exceeds the finite numeric range", evidence)
    delta = finite_quantity(exact_delta)
    if delta is None:
        return TerminalStress(None, "DC difference exceeds the finite numeric range", evidence)
    return TerminalStress(
        delta,
        f"confirmed DC envelope in mode {document.active_mode}, reference {left.reference_net}; "
        "transients, ripple, polarity and thermal suitability are not evaluated",
        evidence,
        exact_delta,
    )
