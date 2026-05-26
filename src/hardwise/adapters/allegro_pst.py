"""Cadence Capture/Allegro PST schematic netlist parser.

PST exports are the Capture-to-Allegro text handoff: ``pstxprt.dat``
declares placed schematic parts, ``pstxnet.dat`` declares nets and pin
endpoints, and optional ``pstchip.dat`` carries primitive properties such
as VALUE and JEDEC_TYPE. This adapter reads those schematic facts only;
it does not parse Allegro PCB databases, boardview data, placement, or
layout geometry.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AllegroPstPart(BaseModel):
    """One placed schematic part from ``pstxprt.dat``."""

    refdes: str
    primitive_name: str
    properties: dict[str, str] = Field(default_factory=dict)


class AllegroPstNode(BaseModel):
    """One ``NODE_NAME`` endpoint from ``pstxnet.dat``."""

    refdes: str
    pin_number: str
    pin_name: str = ""


class AllegroPstNet(BaseModel):
    """One PST net and its schematic endpoints."""

    name: str
    nodes: list[AllegroPstNode] = Field(default_factory=list)


class AllegroPstRegistry(BaseModel):
    """Parse-level registry for one Allegro PST netlist directory."""

    source_dir: Path
    part_file: Path
    net_file: Path
    chip_file: Path | None = None
    parts: list[AllegroPstPart] = Field(default_factory=list)
    nets: list[AllegroPstNet] = Field(default_factory=list)

    @property
    def refdes_set(self) -> set[str]:
        return {part.refdes for part in self.parts}


def parse_allegro_pst(path: Path) -> AllegroPstRegistry:
    """Parse a Capture/Allegro PST directory or one file inside it."""

    source_dir = path if path.is_dir() else path.parent
    part_file = _required_file(source_dir, "pstxprt.dat")
    net_file = _required_file(source_dir, "pstxnet.dat")
    chip_file = source_dir / "pstchip.dat"
    chip_properties = _parse_chip_properties(chip_file) if chip_file.exists() else {}

    parts = _parse_parts(part_file, chip_properties)
    _validate_unique_refdes(parts)

    known_refdes = {part.refdes for part in parts}
    nets = _parse_nets(net_file, known_refdes)

    return AllegroPstRegistry(
        source_dir=source_dir,
        part_file=part_file,
        net_file=net_file,
        chip_file=chip_file if chip_file.exists() else None,
        parts=parts,
        nets=nets,
    )


def is_allegro_pst_input(path: Path) -> bool:
    """Return True when ``path`` looks like an Allegro PST directory or file."""

    if path.is_dir():
        return (path / "pstxnet.dat").exists() and (path / "pstxprt.dat").exists()
    if path.name in {"pstxnet.dat", "pstxprt.dat", "pstchip.dat"}:
        return (path.parent / "pstxnet.dat").exists() and (path.parent / "pstxprt.dat").exists()
    return False


def _required_file(source_dir: Path, filename: str) -> Path:
    path = source_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"missing Allegro PST file: {path}")
    return path


def _parse_parts(
    part_file: Path,
    chip_properties: dict[str, dict[str, str]],
) -> list[AllegroPstPart]:
    lines = _read_lines(part_file)
    parts: list[AllegroPstPart] = []
    for index, raw_line in enumerate(lines):
        if raw_line.strip() != "PART_NAME":
            continue
        line_no = index + 2
        try:
            part_line = lines[index + 1].strip()
        except IndexError as exc:
            raise ValueError(f"line {line_no}: PART_NAME missing part row") from exc
        refdes, primitive_name = _parse_part_row(part_line, line_no)
        properties = dict(chip_properties.get(primitive_name, {}))
        parts.append(
            AllegroPstPart(
                refdes=refdes,
                primitive_name=primitive_name,
                properties=properties,
            )
        )

    if not parts:
        raise ValueError(f"{part_file}: missing PART_NAME rows")
    return parts


def _parse_part_row(line: str, line_no: int) -> tuple[str, str]:
    fields = _parse_words(line.rstrip(":"))
    if len(fields) < 2:
        raise ValueError(f"line {line_no}: malformed PART_NAME row")
    refdes, primitive_name = fields[0], fields[1]
    if not refdes or not primitive_name:
        raise ValueError(f"line {line_no}: malformed PART_NAME row")
    return refdes, primitive_name


def _parse_chip_properties(chip_file: Path) -> dict[str, dict[str, str]]:
    primitives: dict[str, dict[str, str]] = {}
    current: str | None = None
    in_body = False

    for line_no, raw_line in enumerate(_read_lines(chip_file), start=1):
        line = raw_line.strip()
        if line.startswith("primitive "):
            fields = _parse_words(line.rstrip(";"))
            if len(fields) < 2:
                raise ValueError(f"line {line_no}: malformed primitive row")
            current = fields[1]
            primitives[current] = {}
            in_body = False
            continue
        if current is None:
            continue
        if line == "body":
            in_body = True
            continue
        if line == "end_body;":
            in_body = False
            continue
        if line == "end_primitive;":
            current = None
            in_body = False
            continue
        if in_body and "=" in line:
            key, value = _parse_assignment(line)
            primitives[current][key] = value

    return primitives


def _parse_nets(net_file: Path, known_refdes: set[str]) -> list[AllegroPstNet]:
    lines = _read_lines(net_file)
    nets: list[AllegroPstNet] = []
    seen_net_names: set[str] = set()
    current: AllegroPstNet | None = None
    seen_nodes: set[tuple[str, str]] = set()
    i = 0

    while i < len(lines):
        line_no = i + 1
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "NET_NAME":
            name, i = _read_net_name(lines, i, line_no)
            if name in seen_net_names:
                raise ValueError(f"line {line_no}: duplicate net {name}")
            current = AllegroPstNet(name=name)
            nets.append(current)
            seen_net_names.add(name)
            seen_nodes = set()
            continue
        if line.startswith("NODE_NAME"):
            if current is None:
                raise ValueError(f"line {line_no}: NODE_NAME before NET_NAME")
            node, i = _read_node(lines, i, line_no, current.name, known_refdes)
            key = (node.refdes, node.pin_number)
            if key in seen_nodes:
                raise ValueError(f"line {line_no}: duplicate node {node.refdes}.{node.pin_number}")
            seen_nodes.add(key)
            current.nodes.append(node)
            continue
        i += 1

    if not nets:
        raise ValueError(f"{net_file}: missing NET_NAME rows")
    return nets


def _read_net_name(lines: list[str], index: int, line_no: int) -> tuple[str, int]:
    if index + 1 >= len(lines):
        raise ValueError(f"line {line_no}: NET_NAME missing net row")
    name_line = lines[index + 1].strip()
    name = _strip_quoted_label(name_line)
    if not name:
        raise ValueError(f"line {line_no + 1}: empty net name")
    return name, index + 2


def _read_node(
    lines: list[str],
    index: int,
    line_no: int,
    net_name: str,
    known_refdes: set[str],
) -> tuple[AllegroPstNode, int]:
    fields = lines[index].strip().split()
    if len(fields) < 3:
        raise ValueError(f"line {line_no}: malformed NODE_NAME row")
    refdes, pin_number = fields[1], fields[2]
    if refdes not in known_refdes:
        raise ValueError(f"line {line_no}: unknown refdes {refdes} in net {net_name}")

    pin_name = ""
    next_index = index + 1
    if index + 2 < len(lines):
        maybe_pin = lines[index + 2].strip()
        if maybe_pin.startswith("'"):
            pin_name = _strip_quoted_label(maybe_pin)
            next_index = index + 3
    return AllegroPstNode(refdes=refdes, pin_number=pin_number, pin_name=pin_name), next_index


def _parse_assignment(line: str) -> tuple[str, str]:
    key, raw_value = line.rstrip(",;").split("=", 1)
    return key.strip(), _strip_quoted_label(raw_value.strip())


def _strip_quoted_label(text: str) -> str:
    text = text.strip().rstrip(",;")
    if len(text) >= 2 and text[0] == "'":
        end = text.find("'", 1)
        if end != -1:
            return text[1:end]
    return text.rstrip(":")


def _parse_words(text: str) -> list[str]:
    words: list[str] = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text[i] == "'":
            i += 1
            value: list[str] = []
            while i < len(text):
                if text[i] == "'":
                    i += 1
                    break
                value.append(text[i])
                i += 1
            else:
                raise ValueError("unterminated quoted string")
            words.append("".join(value))
            continue
        start = i
        while i < len(text) and not text[i].isspace():
            i += 1
        words.append(text[start:i])
    return words


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _validate_unique_refdes(parts: list[AllegroPstPart]) -> None:
    seen: set[str] = set()
    for part in parts:
        if part.refdes in seen:
            raise ValueError(f"duplicate refdes {part.refdes} in pstxprt.dat")
        seen.add(part.refdes)
