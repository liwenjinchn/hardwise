"""Net-name policy checks for the Allegro pre-Layout path.

Schematic naming conventions are a human-maintained machine-readable
layer: design teams encode topology semantics (differential pairs,
power rails, active-low) into net names, so the names themselves are
checkable review evidence before any deeper net semantics exist.

This module checks net *names* only — pure string policy over
``Design.nets`` keys, no connectivity, voltage, or datasheet input.
The default ``NamingPolicy`` keeps to public industry conventions: an
interop-safe charset, a conservative cross-tool length limit, and
``_DP``/``_DN`` differential-suffix pairing. Site-specific policies
load from a YAML mapping of ``NamingPolicy`` fields via
``load_naming_policy``; they are user-supplied configuration and are
never committed to this repo.

``_P``/``_N`` pairing is deliberately NOT in the default policy: the
``_N`` suffix collides with the equally common active-low convention
(``RST_N``, ``CS_N``), so pairing it by default would spray unpaired
WARNs over perfectly healthy control signals. A site policy that knows
its own conventions can opt in through ``diff_pair_suffixes``.

Power-rail and ground recognition are intentionally absent here:
``pins.voltage_for_net`` already infers rail voltage from net names
and ``pins.is_ground_net`` already recognizes ground families.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from hardwise.ir.types import Design
from hardwise.validation.nets import NetValidation

CHECK_NAME_CHARSET = "net_name_charset"
CHECK_NAME_LENGTH = "net_name_length"
CHECK_DIFF_PAIR = "net_diff_pair_unpaired"


class NamingPolicy(BaseModel):
    """Net-name policy: pure data, YAML-overridable per site.

    Defaults are intentionally permissive so public fixture boards stay
    noise-free; stricter house styles (uppercase-only, shorter limits,
    extra suffix pairs) belong in a site YAML, not in these defaults.
    """

    allowed_pattern: str = r"^[0-9A-Za-z_+\-./]+$"
    forbid_double_underscore: bool = True
    uppercase_only: bool = False
    max_length: int = 32
    diff_pair_suffixes: list[tuple[str, str]] = Field(default=[("DP", "DN")])


DEFAULT_NAMING_POLICY = NamingPolicy()


def load_naming_policy(yaml_path: Path) -> NamingPolicy:
    """Load a site naming policy from a YAML mapping of ``NamingPolicy`` fields."""

    if not yaml_path.exists():
        raise FileNotFoundError(f"naming policy yaml not found: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"naming policy yaml at {yaml_path} must be a mapping of policy fields")
    return NamingPolicy.model_validate(raw)


def validate_net_naming(
    design: Design, *, policy: NamingPolicy | None = None, source_label: str | None = None
) -> list[NetValidation]:
    """Run name-policy checks over ``design.nets`` keys.

    Every finding is WARN: a policy-breaking name is a legibility and
    tool-interop risk, not proof of an electrical fault — the decision
    stays with the reviewer. Results are deterministic: charset/length
    findings sorted by net name first, then unpaired-differential
    findings sorted by net name.
    """

    policy = policy or DEFAULT_NAMING_POLICY
    label = source_label or design.project_path.name
    results: list[NetValidation] = []
    allowed = re.compile(policy.allowed_pattern)

    for net_name in sorted(design.nets):
        reasons: list[str] = []
        if not allowed.fullmatch(net_name):
            reasons.append(f"contains characters outside the policy pattern {policy.allowed_pattern!r}")
        if policy.forbid_double_underscore and "__" in net_name:
            reasons.append("contains a double underscore")
        if policy.uppercase_only and net_name != net_name.upper():
            reasons.append("contains lowercase characters but the policy is uppercase-only")
        if reasons:
            results.append(
                NetValidation(
                    net_name=net_name,
                    check=CHECK_NAME_CHARSET,
                    status="WARN",
                    summary=(
                        f"Net name {net_name} {'; '.join(reasons)}. Off-policy names "
                        "risk breaking netlist interop and constraint matching. "
                        "Reviewer to confirm or rename."
                    ),
                    evidence=[f"netlist:{label}#net={net_name}"],
                )
            )
        if len(net_name) > policy.max_length:
            results.append(
                NetValidation(
                    net_name=net_name,
                    check=CHECK_NAME_LENGTH,
                    status="WARN",
                    summary=(
                        f"Net name {net_name} is {len(net_name)} characters, over the "
                        f"policy limit of {policy.max_length}. Long names get truncated "
                        "by some downstream tools. Reviewer to confirm or shorten."
                    ),
                    evidence=[f"netlist:{label}#net={net_name}"],
                )
            )

    names = set(design.nets)
    for positive_suffix, negative_suffix in policy.diff_pair_suffixes:
        pair_pattern = re.compile(
            rf"^(?P<stem>.+)_(?P<side>{re.escape(positive_suffix)}|{re.escape(negative_suffix)})"
            rf"(?P<index>\d*)$"
        )
        for net_name in sorted(names):
            match = pair_pattern.match(net_name)
            if match is None:
                continue
            mate_side = negative_suffix if match["side"] == positive_suffix else positive_suffix
            mate = f"{match['stem']}_{mate_side}{match['index']}"
            if mate in names:
                continue
            results.append(
                NetValidation(
                    net_name=net_name,
                    check=CHECK_DIFF_PAIR,
                    status="WARN",
                    summary=(
                        f"Net {net_name} carries the differential suffix _{match['side']}"
                        f"{match['index']} but its mate {mate} is not in the design. "
                        "An unpaired differential half usually means a P/N typo or a "
                        "missing line. Reviewer to confirm."
                    ),
                    evidence=[f"netlist:{label}#net={net_name}"],
                )
            )
    return results
