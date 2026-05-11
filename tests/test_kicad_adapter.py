from pathlib import Path

from hardwise.adapters.kicad import parse_project


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
