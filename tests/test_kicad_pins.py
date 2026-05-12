"""Tests for KiCad pin + no-connect parser."""

from pathlib import Path

from hardwise.adapters.kicad import parse_project
from hardwise.adapters.kicad_pins import _transform, parse_nc_pins

PIC_PROGRAMMER = Path("data/projects/pic_programmer")


class TestTransform:
    """Unit tests for the coordinate transform function."""

    def test_identity(self) -> None:
        ax, ay = _transform(1.0, 2.0, 10.0, 20.0, 0.0, False)
        assert abs(ax - 11.0) < 0.01
        assert abs(ay - 22.0) < 0.01

    def test_180_rotation(self) -> None:
        # J1/DB9: sym=(31.75, 91.44) rot=180, pin5=(-11.43, 10.16) -> (43.18, 81.28)
        ax, ay = _transform(-11.43, 10.16, 31.75, 91.44, 180.0, False)
        assert abs(ax - 43.18) < 0.01
        assert abs(ay - 81.28) < 0.01

    def test_90_rotation(self) -> None:
        ax, ay = _transform(1.0, 0.0, 0.0, 0.0, 90.0, False)
        assert abs(ax - 0.0) < 0.01
        assert abs(ay - 1.0) < 0.01

    def test_mirror_y(self) -> None:
        ax, ay = _transform(3.0, 0.0, 10.0, 20.0, 0.0, True)
        assert abs(ax - 7.0) < 0.01
        assert abs(ay - 20.0) < 0.01


class TestParseNcPinsMainSheet:
    """Tests against pic_programmer.kicad_sch (main sheet)."""

    def test_main_sheet_returns_6_nc_pins(self) -> None:
        path = PIC_PROGRAMMER / "pic_programmer.kicad_sch"
        nc_pins = parse_nc_pins(path)
        assert len(nc_pins) == 6

    def test_j1_db9_nc_pins(self) -> None:
        path = PIC_PROGRAMMER / "pic_programmer.kicad_sch"
        nc_pins = parse_nc_pins(path)
        j1_pins = {p.pin_number for p in nc_pins if p.refdes == "J1"}
        assert j1_pins == {"4", "5", "6", "9"}

    def test_lt1373_nc_pins(self) -> None:
        path = PIC_PROGRAMMER / "pic_programmer.kicad_sch"
        nc_pins = parse_nc_pins(path)
        u4_pins = {(p.pin_name, p.pin_number) for p in nc_pins if p.refdes == "U4"}
        assert u4_pins == {("FB-", "3"), ("S/S", "4")}


class TestParseNcPinsSubSheet:
    """Tests against pic_sockets.kicad_sch (sub-sheet)."""

    def test_sub_sheet_returns_71_nc_pins(self) -> None:
        path = PIC_PROGRAMMER / "pic_sockets.kicad_sch"
        nc_pins = parse_nc_pins(path)
        assert len(nc_pins) == 71


class TestParseProjectNcPins:
    """Tests via parse_project() integration."""

    def test_combined_nc_pins(self) -> None:
        registry = parse_project(PIC_PROGRAMMER)
        assert len(registry.nc_pins) == 77

    def test_nc_pin_has_required_fields(self) -> None:
        registry = parse_project(PIC_PROGRAMMER)
        assert registry.nc_pins
        pin = registry.nc_pins[0]
        assert pin.refdes
        assert pin.pin_number
        assert pin.source_file.exists()
