"""Tests for project-level deterministic validation indexes."""

from __future__ import annotations

import json
from pathlib import Path

from hardwise.bom import match_bom_to_design, parse_bom
from hardwise.ir.types import Component, Design, Pin
from hardwise.validation.project_index import (
    build_project_validation_index,
    load_profile_catalog,
)


def test_project_index_validates_explicit_pca9548apw_catalog_match(
    tmp_path: Path,
) -> None:
    profile_path = _write_profile(tmp_path)
    catalog_path = _write_catalog(tmp_path, profile_path)
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                "U8,1,PCA9548APW,NXP,1318724",
                "C1,1,0.1uF,,",
            ]
        ),
        encoding="utf-8",
    )
    design = Design(
        components={
            "U8": _pca_component("U8"),
            "C1": Component(refdes="C1", value="0.1uF"),
        },
        project_path=Path("pst"),
        source_eda="allegro_netlist",
    )
    bom = parse_bom(bom_path)
    report = match_bom_to_design(bom, design)

    index = build_project_validation_index(
        design=design,
        report=report,
        catalog=load_profile_catalog(catalog_path),
        profile_catalog_path=catalog_path,
        project_name="pst",
        generated_at="2026-05-26T00:00:00+00:00",
        netlist_source="pst",
        netlist_type="fixture",
        detail_dir=tmp_path / "details",
    )

    rows = {row.refdes: row for row in index.rows}
    assert rows["U8"].status == "validated"
    assert rows["U8"].profile_part_number == "PCA9548A"
    assert rows["U8"].validation_template == "pca9548a"
    assert rows["U8"].counts == {"PASS": 5, "WARN": 0, "ERROR": 0, "manual_needed": 0}
    assert rows["U8"].detail_report == str(tmp_path / "details" / "U8.md")
    assert rows["C1"].status == "no_profile"
    assert index.totals == {"PASS": 5, "WARN": 0, "ERROR": 0, "manual_needed": 0}


def test_project_index_marks_unknown_components_as_no_profile(tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    catalog_path = _write_catalog(tmp_path, profile_path)
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "\n".join(["Reference,Quantity,Value", "R1,1,10K"]),
        encoding="utf-8",
    )
    design = Design(
        components={"R1": Component(refdes="R1", value="10K")},
        project_path=Path("pst"),
        source_eda="allegro_netlist",
    )

    index = build_project_validation_index(
        design=design,
        report=match_bom_to_design(parse_bom(bom_path), design),
        catalog=load_profile_catalog(catalog_path),
        profile_catalog_path=catalog_path,
        project_name="pst",
        generated_at="2026-05-26T00:00:00+00:00",
        netlist_source="pst",
        netlist_type="fixture",
    )

    assert len(index.validated_rows) == 0
    assert index.rows[0].status == "no_profile"
    assert "No profile catalog entry" in index.rows[0].reason


def test_project_index_dispatches_supported_templates(tmp_path: Path) -> None:
    pca_profile_path = _write_profile(tmp_path)
    pca9617a_profile_path = _write_pca9617a_profile(tmp_path)
    regulator_profile_path = _write_regulator_profile(tmp_path)
    nmos_profile_path = _write_nmos_profile(tmp_path)
    catalog_path = _write_multi_template_catalog(
        tmp_path,
        pca_profile_path=pca_profile_path,
        pca9617a_profile_path=pca9617a_profile_path,
        regulator_profile_path=regulator_profile_path,
        nmos_profile_path=nmos_profile_path,
    )
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                "U8,1,PCA9548APW,NXP,1318724",
                "U29,1,PCA9617ADP,NXP,PCA9617ADP",
                "U3,1,L7805,ST,L7805",
                "Q1,1,LN2312LT1G,LRC,LN2312LT1G",
            ]
        ),
        encoding="utf-8",
    )
    design = Design(
        components={
            "U8": _pca_component("U8"),
            "U29": _pca9617a_component("U29"),
            "U3": _regulator_component("U3"),
            "Q1": _nmos_component("Q1"),
        },
        project_path=Path("pst"),
        source_eda="allegro_netlist",
    )

    index = build_project_validation_index(
        design=design,
        report=match_bom_to_design(parse_bom(bom_path), design),
        catalog=load_profile_catalog(catalog_path),
        profile_catalog_path=catalog_path,
        project_name="pst",
        generated_at="2026-05-26T00:00:00+00:00",
        netlist_source="pst",
        netlist_type="fixture",
    )

    rows = {row.refdes: row for row in index.rows}
    assert rows["U8"].status == "validated"
    assert rows["U8"].validation_template == "pca9548a"
    assert rows["U29"].status == "validated"
    assert rows["U29"].profile_part_number == "PCA9617A"
    assert rows["U29"].validation_template == "pca9617a"
    assert rows["U29"].counts == {"PASS": 6, "WARN": 0, "ERROR": 0, "manual_needed": 0}
    assert rows["U3"].status == "validated"
    assert rows["U3"].profile_part_number == "L7805"
    assert rows["U3"].validation_template == "regulator"
    assert rows["U3"].counts == {"PASS": 3, "WARN": 0, "ERROR": 0, "manual_needed": 0}
    assert rows["Q1"].status == "validated"
    assert rows["Q1"].profile_part_number == "LN2312LT1G"
    assert rows["Q1"].validation_template == "nmos"
    assert rows["Q1"].counts == {"PASS": 4, "WARN": 0, "ERROR": 0, "manual_needed": 1}
    assert index.totals == {"PASS": 18, "WARN": 0, "ERROR": 0, "manual_needed": 1}


def test_project_index_groups_no_profile_candidates_by_bom_identity(tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    catalog_path = _write_catalog(tmp_path, profile_path)
    bom_path = tmp_path / "bom.csv"
    bom_path.write_text(
        "\n".join(
            [
                "Reference,Quantity,Value,Manufacturer,MPN",
                '"U20 U21 U22 U23",4,Mystery IC,Acme,MCU-123',
                '"R1 R2",2,10K,,',
            ]
        ),
        encoding="utf-8",
    )
    design = Design(
        components={
            "U20": Component(refdes="U20", value="Mystery IC"),
            "U21": Component(refdes="U21", value="Mystery IC"),
            "U22": Component(refdes="U22", value="Mystery IC"),
            "U23": Component(refdes="U23", value="Mystery IC"),
            "R1": Component(refdes="R1", value="10K"),
            "R2": Component(refdes="R2", value="10K"),
        },
        project_path=Path("pst"),
        source_eda="allegro_netlist",
    )

    index = build_project_validation_index(
        design=design,
        report=match_bom_to_design(parse_bom(bom_path), design),
        catalog=load_profile_catalog(catalog_path),
        profile_catalog_path=catalog_path,
        project_name="pst",
        generated_at="2026-05-26T00:00:00+00:00",
        netlist_source="pst",
        netlist_type="fixture",
    )

    groups = index.candidate_groups()
    assert [(group.kind, group.count, group.bom_value) for group in groups] == [
        ("active", 4, "Mystery IC"),
        ("passive", 2, "10K"),
    ]
    assert groups[0].sample_refdes == ["U20", "U21", "U22"]
    assert [group.bom_value for group in index.active_candidate_groups()] == ["Mystery IC"]


def _write_catalog(tmp_path: Path, profile_path: Path) -> Path:
    catalog_path = tmp_path / "profile_catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "profile_part_number": "PCA9548A",
                    "accepted_bom_values": ["PCA9548A", "PCA9548APW"],
                    "manufacturer": "NXP",
                    "profile_path": str(profile_path),
                    "validation_template": "pca9548a",
                }
            ]
        ),
        encoding="utf-8",
    )
    return catalog_path


def _write_multi_template_catalog(
    tmp_path: Path,
    *,
    pca_profile_path: Path,
    pca9617a_profile_path: Path,
    regulator_profile_path: Path,
    nmos_profile_path: Path,
) -> Path:
    catalog_path = tmp_path / "profile_catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "profile_part_number": "PCA9548A",
                    "accepted_bom_values": ["PCA9548A", "PCA9548APW"],
                    "manufacturer": "NXP",
                    "profile_path": str(pca_profile_path),
                    "validation_template": "pca9548a",
                },
                {
                    "profile_part_number": "PCA9617A",
                    "accepted_bom_values": ["PCA9617A", "PCA9617ADP"],
                    "manufacturer": "NXP",
                    "profile_path": str(pca9617a_profile_path),
                    "validation_template": "pca9617a",
                },
                {
                    "profile_part_number": "L7805",
                    "accepted_bom_values": ["L7805", "7805", "L78"],
                    "manufacturer": "ST",
                    "profile_path": str(regulator_profile_path),
                    "validation_template": "regulator",
                },
                {
                    "profile_part_number": "LN2312LT1G",
                    "accepted_bom_values": ["LN2312LT1G", "S-LN2312LT1G", "LN2312"],
                    "manufacturer": "LRC",
                    "profile_path": str(nmos_profile_path),
                    "validation_template": "nmos",
                },
            ]
        ),
        encoding="utf-8",
    )
    return catalog_path


def _write_profile(tmp_path: Path) -> Path:
    profile_path = tmp_path / "pca9548a.json"
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PCA9548A",
                "recommended": {"vdd_min": 2.3, "vdd_max": 5.5},
                "pin_function": _pin_function(),
                "evidence": {
                    "recommended.vdd_min": "datasheet:pca9548a.pdf#p15",
                    "recommended.vdd_max": "datasheet:pca9548a.pdf#p15",
                    **{
                        f"pin_function.{pin}": "datasheet:pca9548a.pdf#p4"
                        for pin in _pin_function()
                    },
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
            }
        ),
        encoding="utf-8",
    )
    return profile_path


def _write_pca9617a_profile(tmp_path: Path) -> Path:
    profile_path = tmp_path / "pca9617a.json"
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "PCA9617A",
                "recommended": {
                    "vcca_min": 0.8,
                    "vcca_max": 5.5,
                    "vccb_min": 2.2,
                    "vccb_max": 5.5,
                },
                "pin_function": {
                    "1": "VCCA (Port A supply voltage)",
                    "2": "SCLA (Port A serial clock input/output)",
                    "3": "SDAA (Port A serial data input/output)",
                    "4": "GND (ground)",
                    "5": "EN (active HIGH repeater enable input referenced to VCCB)",
                    "6": "SDAB (Port B serial data input/output)",
                    "7": "SCLB (Port B serial clock input/output)",
                    "8": "VCCB (Port B supply voltage)",
                },
                "evidence": {
                    "recommended.vcca_min": "datasheet:pca9617a.pdf#p1",
                    "recommended.vcca_max": "datasheet:pca9617a.pdf#p1",
                    "recommended.vccb_min": "datasheet:pca9617a.pdf#p1",
                    "recommended.vccb_max": "datasheet:pca9617a.pdf#p1",
                    **{
                        f"pin_function.{pin}": "datasheet:pca9617a.pdf#p4"
                        for pin in range(1, 9)
                    },
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
            }
        ),
        encoding="utf-8",
    )
    return profile_path


def _write_regulator_profile(tmp_path: Path) -> Path:
    profile_path = tmp_path / "l78.json"
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "L7805",
                "recommended": {"vin_min": 7.5, "vin_max": 25.0, "vout_nominal": 5.0},
                "pin_function": {
                    "1": "VI (input)",
                    "2": "GND (ground)",
                    "3": "VO (5 V output)",
                },
                "evidence": {
                    "recommended.vin_min": "datasheet:l78.pdf#p6",
                    "recommended.vin_max": "datasheet:l78.pdf#p6",
                    "recommended.vout_nominal": "datasheet:l78.pdf#p6",
                    "pin_function.1": "datasheet:l78.pdf#p3",
                    "pin_function.2": "datasheet:l78.pdf#p3",
                    "pin_function.3": "datasheet:l78.pdf#p3",
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
            }
        ),
        encoding="utf-8",
    )
    return profile_path


def _write_nmos_profile(tmp_path: Path) -> Path:
    profile_path = tmp_path / "ln2312lt1g.json"
    profile_path.write_text(
        json.dumps(
            {
                "part_number": "LN2312LT1G",
                "abs_max": {"vds": 20.0, "id": 4.9, "pd": 0.75},
                "pin_function": {
                    "1": "G (gate)",
                    "2": "S (source)",
                    "3": "D (drain)",
                },
                "evidence": {
                    "abs_max.vds": "datasheet:ln2312lt1g.pdf#p1",
                    "pin_function.1": "datasheet:ln2312lt1g.pdf#p1",
                    "pin_function.2": "datasheet:ln2312lt1g.pdf#p1",
                    "pin_function.3": "datasheet:ln2312lt1g.pdf#p1",
                },
                "extracted_at": "2026-05-26T00:00:00+00:00",
                "extracted_model": "unit-test",
            }
        ),
        encoding="utf-8",
    )
    return profile_path


def _pca_component(refdes: str) -> Component:
    nets = {
        "1": "A0",
        "2": "A1",
        "3": "RESET_N",
        "12": "GND",
        "21": "A2",
        "22": "I2C_SCL",
        "23": "I2C_SDA",
        "24": "P3V3_STBY",
    }
    for channel, sd_pin, sc_pin in _channel_pins():
        nets[str(sd_pin)] = f"I2C_CH{channel}_SDA"
        nets[str(sc_pin)] = f"I2C_CH{channel}_SCL"
    return Component(
        refdes=refdes,
        value="PCA9548APW",
        manufacturer="NXP",
        pins=[
            Pin(number=pin, name=_pin_name(pin), electrical_type="passive", is_nc=False, net=net)
            for pin, net in sorted(nets.items(), key=lambda item: int(item[0]))
        ],
    )


def _regulator_component(refdes: str) -> Component:
    return Component(
        refdes=refdes,
        value="L7805",
        manufacturer="ST",
        pins=[
            Pin(number="1", name="VI", electrical_type="power_in", is_nc=False, net="P12V"),
            Pin(number="2", name="GND", electrical_type="power_in", is_nc=False, net="GND"),
            Pin(number="3", name="VO", electrical_type="power_out", is_nc=False, net="P5V"),
        ],
    )


def _pca9617a_component(refdes: str) -> Component:
    return Component(
        refdes=refdes,
        value="PCA9617ADP",
        manufacturer="NXP",
        pins=[
            Pin(number="1", name="VCCA", electrical_type="power_in", is_nc=False, net="PEX0_P1V8"),
            Pin(number="2", name="SCLA", electrical_type="passive", is_nc=False, net="I2C_A_SCL"),
            Pin(number="3", name="SDAA", electrical_type="passive", is_nc=False, net="I2C_A_SDA"),
            Pin(number="4", name="GND", electrical_type="power_in", is_nc=False, net="GND"),
            Pin(number="5", name="EN", electrical_type="input", is_nc=False, net="EN_LOCAL"),
            Pin(number="6", name="SDAB", electrical_type="passive", is_nc=False, net="I2C_B_SDA"),
            Pin(number="7", name="SCLB", electrical_type="passive", is_nc=False, net="I2C_B_SCL"),
            Pin(number="8", name="VCCB", electrical_type="power_in", is_nc=False, net="P3V3_STBY"),
        ],
    )


def _nmos_component(refdes: str) -> Component:
    return Component(
        refdes=refdes,
        value="LN2312LT1G",
        manufacturer="LRC",
        pins=[
            Pin(number="1", name="G", electrical_type="input", is_nc=False, net="P3V3"),
            Pin(number="2", name="S", electrical_type="passive", is_nc=False, net="P0V"),
            Pin(number="3", name="D", electrical_type="passive", is_nc=False, net="P3V3"),
        ],
    )


def _pin_function() -> dict[str, str]:
    functions = {
        "1": "A0 (address input 0)",
        "2": "A1 (address input 1)",
        "3": "RESET (active-low reset input)",
        "12": "VSS (ground)",
        "21": "A2 (address input 2)",
        "22": "SCL (upstream serial clock input)",
        "23": "SDA (upstream serial data input/output)",
        "24": "VDD (supply voltage)",
    }
    for channel, sd_pin, sc_pin in _channel_pins():
        functions[str(sd_pin)] = f"SD{channel} (downstream channel {channel} serial data)"
        functions[str(sc_pin)] = f"SC{channel} (downstream channel {channel} serial clock)"
    return functions


def _pin_name(pin_number: str) -> str:
    functions = _pin_function()
    return functions[pin_number].split()[0]


def _channel_pins() -> list[tuple[int, int, int]]:
    return [
        (0, 4, 5),
        (1, 6, 7),
        (2, 8, 9),
        (3, 10, 11),
        (4, 13, 14),
        (5, 15, 16),
        (6, 17, 18),
        (7, 19, 20),
    ]
