"""End-to-end: ``hardwise inspect-kicad --net`` default vs --all-nets口径.

Locks the PCB-side net-CLI contract:
- default ``--net`` shows only PCB signal nets (34 on pic_programmer)
- ``--all-nets`` exposes the full PCB net set (111 on pic_programmer,
  including ``unconnected-(Ref-Pad)`` auto-entries)
- the header always reports both counts and explicitly says the source
  is ``.kicad_pcb`` (post-Layout fact, not pre-Layout review evidence),
  so a future reader cannot mistake it for schematic-side data
"""

from __future__ import annotations

from typer.testing import CliRunner

from hardwise.cli import app

runner = CliRunner()


def test_inspect_kicad_net_default_is_pcb_signal_only() -> None:
    result = runner.invoke(
        app,
        ["inspect-kicad", "data/projects/pic_programmer", "--net", "--limit", "200"],
    )
    assert result.exit_code == 0, result.output

    # Header states the口径 explicitly — both counts visible, source labelled.
    assert "pcb nets: 34 signal (+77 unconnected = 111 total in PCB)" in result.output
    assert "source: .kicad_pcb" in result.output
    assert "not pre-Layout review evidence" in result.output
    assert "showing PCB signal nets only" in result.output

    # Signal nets present; no unconnected-* entry appears in the listing.
    assert "GND " in result.output
    assert "VCC " in result.output
    listing_lines = [ln for ln in result.output.splitlines() if ln.startswith("unconnected-")]
    assert listing_lines == []


def test_inspect_kicad_all_nets_includes_unconnected() -> None:
    result = runner.invoke(
        app,
        [
            "inspect-kicad",
            "data/projects/pic_programmer",
            "--net",
            "--all-nets",
            "--limit",
            "200",
        ],
    )
    assert result.exit_code == 0, result.output

    # Same header — counts and source label don't depend on the flag.
    assert "pcb nets: 34 signal (+77 unconnected = 111 total in PCB)" in result.output
    assert "source: .kicad_pcb" in result.output
    assert "showing all PCB nets" in result.output

    # All 77 unconnected-* entries now visible in the listing.
    listing_lines = [ln for ln in result.output.splitlines() if ln.startswith("unconnected-")]
    assert len(listing_lines) == 77
