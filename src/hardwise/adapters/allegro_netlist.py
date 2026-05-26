"""Allegro/Telesis third-party ASCII netlist parser.

This adapter reads schematic-exported connectivity facts only:
packages/refdes, optional properties, and net endpoints. It deliberately
does not parse Allegro ``.brd`` databases, boardview data, placement, or
layout geometry.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AllegroPackage(BaseModel):
    """One package/device declaration from the ``$PACKAGES`` section."""

    package_name: str
    device_name: str
    refdes_list: list[str] = Field(default_factory=list)


class AllegroProperty(BaseModel):
    """One preserved row from the optional ``$A_PROPERTIES`` section."""

    name: str
    value: str
    targets: list[str] = Field(default_factory=list)


class AllegroNet(BaseModel):
    """One net and its ``(refdes, pin_number)`` endpoints."""

    name: str
    nodes: list[tuple[str, str]] = Field(default_factory=list)


class AllegroNetlistRegistry(BaseModel):
    """Parse-level registry for one Allegro/Telesis netlist file."""

    packages: list[AllegroPackage] = Field(default_factory=list)
    properties: list[AllegroProperty] = Field(default_factory=list)
    nets: list[AllegroNet] = Field(default_factory=list)
    source_file: Path

    @property
    def refdes_set(self) -> set[str]:
        return {refdes for package in self.packages for refdes in package.refdes_list}


def parse_allegro_netlist(path: Path) -> AllegroNetlistRegistry:
    """Parse an Allegro/Telesis third-party ASCII netlist.

    The supported subset is intentionally scoped to pre-Layout review:
    ``$PACKAGES`` declares the legal refdes registry, optional
    ``$A_PROPERTIES`` rows are preserved, and ``$NETS`` supplies
    connectivity. A net endpoint whose refdes is absent from packages is
    rejected instead of being fabricated downstream.
    """

    text = path.read_text(encoding="utf-8")
    records = _section_records(text)

    packages = [_parse_package(record, line_no) for line_no, record in records["$PACKAGES"]]
    _validate_unique_refdes(packages)

    properties = [_parse_property(record, line_no) for line_no, record in records["$A_PROPERTIES"]]

    known_refdes = {refdes for package in packages for refdes in package.refdes_list}
    nets = [_parse_net(record, line_no, known_refdes) for line_no, record in records["$NETS"]]

    return AllegroNetlistRegistry(
        source_file=path,
        packages=packages,
        properties=properties,
        nets=nets,
    )


def _section_records(text: str) -> dict[str, list[tuple[int, str]]]:
    records: dict[str, list[tuple[int, str]]] = {
        "$PACKAGES": [],
        "$A_PROPERTIES": [],
        "$NETS": [],
    }
    current: str | None = None
    seen_packages = False
    seen_nets = False
    seen_end = False
    pending: list[str] = []
    pending_start = 0

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("$"):
            if pending:
                raise ValueError(f"line {line_no}: unterminated continuation before {line}")
            if line == "$PACKAGES":
                if seen_packages:
                    raise ValueError(f"line {line_no}: duplicate $PACKAGES section")
                seen_packages = True
                current = line
                continue
            if line == "$A_PROPERTIES":
                if not seen_packages:
                    raise ValueError(f"line {line_no}: $PACKAGES must appear before $A_PROPERTIES")
                if seen_nets:
                    raise ValueError(f"line {line_no}: $A_PROPERTIES must appear before $NETS")
                current = line
                continue
            if line == "$NETS":
                if not seen_packages:
                    raise ValueError(f"line {line_no}: $PACKAGES must appear before $NETS")
                seen_nets = True
                current = line
                continue
            if line == "$END":
                if not seen_packages:
                    raise ValueError(f"line {line_no}: $PACKAGES must appear before $END")
                if not seen_nets:
                    raise ValueError(f"line {line_no}: $NETS must appear before $END")
                seen_end = True
                current = None
                continue
            raise ValueError(f"line {line_no}: unsupported Allegro netlist section {line}")

        if seen_end:
            raise ValueError(f"line {line_no}: content after $END")
        if current is None:
            raise ValueError(f"line {line_no}: content outside Allegro netlist section")

        if not pending:
            pending_start = line_no
        pending.append(line)
        if line.endswith(","):
            continue
        records[current].append((pending_start, " ".join(pending)))
        pending = []

    if pending:
        raise ValueError(f"line {pending_start}: unterminated continuation")
    if not seen_end:
        raise ValueError("missing $END in Allegro netlist")
    if not records["$PACKAGES"]:
        raise ValueError("missing package rows in $PACKAGES")
    if not records["$NETS"]:
        raise ValueError("missing net rows in $NETS")
    return records


def _parse_package(record: str, line_no: int) -> AllegroPackage:
    head, refs_text = _split_head_items(record, line_no, "package")
    fields = [_strip_quotes(part.strip()) for part in head.split("!") if part.strip()]
    if len(fields) < 2:
        raise ValueError(f"line {line_no}: malformed package row")
    refdes_list = _split_items(refs_text)
    if not refdes_list:
        raise ValueError(f"line {line_no}: package row has no refdes")
    return AllegroPackage(
        package_name=fields[0],
        device_name=fields[1],
        refdes_list=refdes_list,
    )


def _parse_property(record: str, line_no: int) -> AllegroProperty:
    head, targets_text = _split_head_items(record, line_no, "property")
    fields = _parse_words(head)
    if len(fields) < 2:
        raise ValueError(f"line {line_no}: malformed property row")
    targets = _split_items(targets_text)
    if not targets:
        raise ValueError(f"line {line_no}: property row has no targets")
    return AllegroProperty(name=fields[0], value=fields[1], targets=targets)


def _parse_net(record: str, line_no: int, known_refdes: set[str]) -> AllegroNet:
    head, nodes_text = _split_head_items(record, line_no, "net")
    name = _strip_quotes(head.strip())
    if not name:
        raise ValueError(f"line {line_no}: net row has empty name")

    nodes: list[tuple[str, str]] = []
    seen_nodes: set[tuple[str, str]] = set()
    for token in _split_items(nodes_text):
        if "." not in token:
            raise ValueError(f"line {line_no}: malformed node {token!r}")
        refdes, pin_number = token.rsplit(".", 1)
        if not refdes or not pin_number:
            raise ValueError(f"line {line_no}: malformed node {token!r}")
        if refdes not in known_refdes:
            raise ValueError(f"line {line_no}: unknown refdes {refdes} in net {name}")
        node = (refdes, pin_number)
        if node in seen_nodes:
            raise ValueError(f"line {line_no}: duplicate node {token!r} in net {name}")
        seen_nodes.add(node)
        nodes.append(node)

    if not nodes:
        raise ValueError(f"line {line_no}: net row has no nodes")
    return AllegroNet(name=name, nodes=nodes)


def _split_head_items(record: str, line_no: int, kind: str) -> tuple[str, str]:
    if ";" not in record:
        raise ValueError(f"line {line_no}: malformed {kind} row")
    head, items = record.split(";", 1)
    return head.strip(), items.strip()


def _split_items(text: str) -> list[str]:
    return [item for item in text.replace(",", " ").replace(";", " ").split() if item]


def _strip_quotes(text: str) -> str:
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]
    return text


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


def _validate_unique_refdes(packages: list[AllegroPackage]) -> None:
    seen: set[str] = set()
    for package in packages:
        for refdes in package.refdes_list:
            if refdes in seen:
                raise ValueError(f"duplicate refdes {refdes} in $PACKAGES")
            seen.add(refdes)


__all__ = [
    "AllegroNet",
    "AllegroNetlistRegistry",
    "AllegroPackage",
    "AllegroProperty",
    "parse_allegro_netlist",
]
