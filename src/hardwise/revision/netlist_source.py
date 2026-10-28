"""Native netlist inputs for revision comparison, without converting away evidence."""

from dataclasses import dataclass
from pathlib import Path

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.adapters.allegro_pst import parse_allegro_pst
from hardwise.input_provenance import read_input_text
from hardwise.ir.build import build_design_from_netlist, build_design_from_pst
from hardwise.ir.types import Design

PST_NAMES = ("pstxnet.dat", "pstxprt.dat", "pstchip.dat")


@dataclass
class NetlistSource:
    design: Design
    files: tuple[Path, ...]
    part_file: Path
    net_file: Path
    package_file: Path
    devices: dict[str, str]
    # refdes, field, value, original file, source locator
    properties: list[tuple[str, str, str, Path, str]]
    part_section: str
    net_section: str
    input_format: str


def netlist_files(path: Path) -> tuple[Path, ...]:
    if path.is_dir() or path.name in PST_NAMES:
        directory = path if path.is_dir() else path.parent
        files = tuple(directory / name for name in PST_NAMES)
        missing = [p.name for p in files if not p.is_file()]
        if missing:
            raise ValueError("PST 改版复核需要同一次导出的三个文件，缺少：" + "、".join(missing))
        if len({p.resolve() for p in files}) != 3:
            raise ValueError("三个 PST 角色必须对应三个独立文件。")
        return files
    if path.suffix.lower() in {".net", ".txt"} and path.is_file():
        return (path,)
    raise ValueError("不支持的网表格式；请选择 Telesis .net/.txt，或包含三个 PST .dat 文件的目录。")


def read_netlist(path: Path) -> NetlistSource:
    files = netlist_files(path)
    for source in files:
        text = read_input_text(source, role="netlist", encoding="utf-8-sig", errors="strict")
        if not text.strip():
            raise ValueError(f"网表文件为空：{source.name}")
    if len(files) == 1:
        registry = parse_allegro_netlist(path, encoding="utf-8-sig")
        return NetlistSource(
            design=build_design_from_netlist(registry),
            files=files,
            part_file=path,
            net_file=path,
            package_file=path,
            devices={ref: p.device_name for p in registry.packages for ref in p.refdes_list},
            properties=[
                (ref, p.name, p.value, path, f"$A_PROPERTIES; {p.name}; refdes={ref}")
                for p in registry.properties
                for ref in p.targets
            ],
            part_section="$PACKAGES",
            net_section="$NETS",
            input_format="telesis_csv_v1",
        )
    pst = parse_allegro_pst(files[0].parent)
    assert pst.chip_file is not None
    return NetlistSource(
        design=build_design_from_pst(pst),
        files=files,
        part_file=pst.part_file,
        net_file=pst.net_file,
        package_file=pst.chip_file,
        # The primitive is a declared library identity, not an inferred VALUE.
        devices={p.refdes: p.primitive_name for p in pst.parts},
        properties=[
            (
                p.refdes,
                name,
                value,
                pst.chip_file,
                f"primitive={p.primitive_name}; body; {name}; refdes={p.refdes}",
            )
            for p in pst.parts
            for name, value in p.properties.items()
        ],
        part_section="PART_NAME",
        net_section="NET_NAME",
        input_format="pst_csv_v1",
    )
