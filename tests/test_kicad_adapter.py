from pathlib import Path

from hardwise.adapters.kicad import is_unconnected_pcb_net, parse_project, pcb_signal_nets


def test_parse_pic_programmer_registry() -> None:
    registry = parse_project(Path("data/projects/pic_programmer"))

    assert registry.has_refdes("U3")
    assert registry.has_refdes("C1")
    assert registry.has_refdes("D11")
    assert not registry.has_refdes("U999")
    assert len(registry.components) > 40


def test_merges_pcb_footprint_into_schematic_record() -> None:
    registry = parse_project(Path("data/projects/pic_programmer"))
    c1 = next(component for component in registry.components if component.refdes == "C1")

    assert c1.value == "100µF"
    assert c1.footprint == "Capacitor_THT:CP_Axial_L18.0mm_D6.5mm_P25.00mm_Horizontal"


def test_registry_exposes_raw_schematic_and_pcb_records() -> None:
    registry = parse_project(Path("data/projects/pic_programmer"))

    assert registry.schematic_records, "schematic_records should be populated"
    assert registry.pcb_records, "pcb_records should be populated"
    assert all(r.source_kind == "schematic" for r in registry.schematic_records)
    assert all(r.source_kind == "pcb" for r in registry.pcb_records)


def test_registry_stores_full_pcb_net_set() -> None:
    """PCB parser keeps every ``(net "NAME")`` entry KiCad emits — 111 on pic_programmer.

    The registry is the source of truth for the PCB-side fact: signal nets
    AND auto ``unconnected-(Ref-Pad)`` entries are preserved so downstream
    PCB-side diagnostics can read them. (Pre-Layout schematic-review rules
    must use a different parser; this field is post-Layout only.)
    """
    registry = parse_project(Path("data/projects/pic_programmer"))
    names = {n.name for n in registry.pcb_nets}

    assert len(registry.pcb_nets) == 111
    assert "GND" in names
    assert "VCC" in names
    # An unconnected-* entry must survive into the registry untouched.
    assert any(n.startswith("unconnected-") for n in names)

    gnd = next(n for n in registry.pcb_nets if n.name == "GND")
    assert len(gnd.members) == 40
    assert all(m.refdes and m.pad for m in gnd.members)


def test_pcb_signal_nets_filters_unconnected_only() -> None:
    """pcb_signal_nets() drops KiCad's unconnected-* auto-nets and nothing else."""
    registry = parse_project(Path("data/projects/pic_programmer"))
    signal = pcb_signal_nets(registry.pcb_nets)

    assert len(signal) == 34
    assert not any(is_unconnected_pcb_net(n.name) for n in signal)
    # Signal + unconnected partition the full registry.
    unconnected = [n for n in registry.pcb_nets if is_unconnected_pcb_net(n.name)]
    assert len(signal) + len(unconnected) == len(registry.pcb_nets) == 111
    assert len(unconnected) == 77
