"""Tests for net-name policy checks (seeded violations = constructed gold)."""

from pathlib import Path

import pytest

from hardwise.ir.types import Design, Net
from hardwise.validation.net_naming import (
    CHECK_DIFF_PAIR,
    CHECK_NAME_CHARSET,
    CHECK_NAME_LENGTH,
    DEFAULT_NAMING_POLICY,
    NamingPolicy,
    load_naming_policy,
    validate_net_naming,
)


def _design_with_net_names(*names: str) -> Design:
    """Build a minimal in-memory Design carrying only net names."""

    return Design(
        components={},
        nets={name: Net(name=name, nodes=[("U1", "1"), ("R1", "1")]) for name in names},
        project_path=Path("synthetic_board"),
        source_eda="allegro_netlist",
    )


def test_clean_conventional_names_produce_no_findings():
    """Healthy industry-style names are policy-quiet, including paired diffs."""

    design = _design_with_net_names(
        "VCC_3V3",
        "GND",
        "RST_N",  # active-low, must NOT be treated as an unpaired diff half
        "CLK_100M_DP0",
        "CLK_100M_DN0",
        "PCIE_TX_DP",
        "PCIE_TX_DN",
    )
    assert validate_net_naming(design) == []


def test_charset_violation_warns_with_evidence_token():
    """A special character outside the policy pattern yields one WARN."""

    design = _design_with_net_names("CLK@33M", "GND")
    results = validate_net_naming(design, source_label="board.net")

    assert len(results) == 1
    result = results[0]
    assert result.net_name == "CLK@33M"
    assert result.check == CHECK_NAME_CHARSET
    assert result.status == "WARN"
    assert result.evidence == ["netlist:board.net#net=CLK@33M"]
    assert "Reviewer to confirm" in result.summary


def test_double_underscore_warns_under_default_policy():
    """A double underscore is flagged as a charset finding by default."""

    design = _design_with_net_names("CLK__33M", "GND")
    results = validate_net_naming(design)

    assert [r.check for r in results] == [CHECK_NAME_CHARSET]
    assert "double underscore" in results[0].summary


def test_lowercase_passes_by_default_and_warns_when_uppercase_only():
    """uppercase_only is a site opt-in, off in the public default policy."""

    design = _design_with_net_names("sw_node", "GND")

    assert validate_net_naming(design) == []

    strict = NamingPolicy(uppercase_only=True)
    results = validate_net_naming(design, policy=strict)
    assert [r.check for r in results] == [CHECK_NAME_CHARSET]
    assert "uppercase-only" in results[0].summary


def test_overlong_name_warns_with_length_check():
    """A name over max_length yields a length WARN naming both numbers."""

    long_name = "X" * 33
    design = _design_with_net_names(long_name, "GND")
    results = validate_net_naming(design)

    assert [r.check for r in results] == [CHECK_NAME_LENGTH]
    assert "33 characters" in results[0].summary
    assert "32" in results[0].summary


def test_unpaired_diff_half_warns_and_names_expected_mate():
    """A _DP net without its _DN mate is flagged, indexed suffixes included."""

    design = _design_with_net_names("PCIE_TX_DP3", "GND")
    results = validate_net_naming(design)

    assert [r.check for r in results] == [CHECK_DIFF_PAIR]
    assert results[0].net_name == "PCIE_TX_DP3"
    assert "PCIE_TX_DN3" in results[0].summary


def test_unpaired_negative_half_is_also_flagged():
    """Pairing is symmetric: an orphaned _DN points at the missing _DP."""

    design = _design_with_net_names("CLK_100M_DN0", "GND")
    results = validate_net_naming(design)

    assert [r.check for r in results] == [CHECK_DIFF_PAIR]
    assert "CLK_100M_DP0" in results[0].summary


def test_results_are_deterministic_and_grouped_by_check_family():
    """Charset/length findings come first sorted by net, then diff pairs."""

    design = _design_with_net_names("Z@BAD", "A@BAD", "PCIE_TX_DP", "GND")
    results = validate_net_naming(design)

    assert [(r.net_name, r.check) for r in results] == [
        ("A@BAD", CHECK_NAME_CHARSET),
        ("Z@BAD", CHECK_NAME_CHARSET),
        ("PCIE_TX_DP", CHECK_DIFF_PAIR),
    ]


def test_site_policy_loads_from_yaml(tmp_path):
    """A site YAML overrides defaults; unknown strictness stays user-supplied."""

    policy_file = tmp_path / "site_naming.yaml"
    policy_file.write_text(
        "uppercase_only: true\nmax_length: 24\n",
        encoding="utf-8",
    )
    policy = load_naming_policy(policy_file)

    assert policy.uppercase_only is True
    assert policy.max_length == 24
    # Untouched fields keep the public defaults.
    assert policy.diff_pair_suffixes == DEFAULT_NAMING_POLICY.diff_pair_suffixes


def test_site_policy_yaml_must_be_a_mapping(tmp_path):
    """A non-mapping YAML fails loudly instead of silently using defaults."""

    policy_file = tmp_path / "bad.yaml"
    policy_file.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_naming_policy(policy_file)
