"""Minimal KiCad project parser for the Hardwise registry."""

from __future__ import annotations

from pathlib import Path

from hardwise.adapters.base import BoardRegistry, ComponentRecord

Sexp = str | list["Sexp"]


def parse_project(project_dir: Path) -> BoardRegistry:
    """Parse a KiCad project directory into a component registry."""

    project_dir = project_dir.expanduser().resolve()
    schematic_components: dict[str, ComponentRecord] = {}

    for schematic_path in sorted(project_dir.glob("*.kicad_sch")):
        for component in parse_schematic(schematic_path):
            schematic_components[component.refdes] = component

    pcb_components = {component.refdes: component for component in _parse_all_pcbs(project_dir)}

    merged = dict(schematic_components)
    for refdes, pcb_component in pcb_components.items():
        existing = merged.get(refdes)
        if existing is None:
            merged[refdes] = pcb_component
            continue
        if not existing.footprint:
            merged[refdes] = existing.model_copy(update={"footprint": pcb_component.footprint})

    return BoardRegistry(
        project_dir=project_dir,
        components=sorted(merged.values(), key=_refdes_sort_key),
        schematic_records=list(schematic_components.values()),
        pcb_records=list(pcb_components.values()),
    )


def parse_schematic(path: Path) -> list[ComponentRecord]:
    """Parse symbol instances from a `.kicad_sch` file."""

    root = _parse_file(path)
    components: list[ComponentRecord] = []
    for node in _walk(root):
        if not _is_list_with_head(node, "symbol"):
            continue
        properties = _properties(node)
        refdes = properties.get("Reference", "")
        if not refdes:
            continue
        if _is_library_symbol(node):
            continue
        components.append(
            ComponentRecord(
                refdes=refdes,
                value=properties.get("Value", ""),
                footprint=properties.get("Footprint", ""),
                datasheet=properties.get("Datasheet", ""),
                source_file=path,
                source_kind="schematic",
            )
        )
    return components


def parse_pcb(path: Path) -> list[ComponentRecord]:
    """Parse placed footprints from a `.kicad_pcb` file."""

    root = _parse_file(path)
    components: list[ComponentRecord] = []
    for node in _walk(root):
        if not _is_list_with_head(node, "footprint"):
            continue
        footprint = node[1] if len(node) > 1 and isinstance(node[1], str) else ""
        properties = _properties(node)
        refdes = properties.get("Reference", "")
        if not refdes:
            continue
        components.append(
            ComponentRecord(
                refdes=refdes,
                value=properties.get("Value", ""),
                footprint=footprint,
                datasheet=properties.get("Datasheet", ""),
                source_file=path,
                source_kind="pcb",
            )
        )
    return components


def _parse_all_pcbs(project_dir: Path) -> list[ComponentRecord]:
    components: list[ComponentRecord] = []
    for pcb_path in sorted(project_dir.glob("*.kicad_pcb")):
        components.extend(parse_pcb(pcb_path))
    return components


def _parse_file(path: Path) -> Sexp:
    return _parse_tokens(_tokenize(path.read_text(encoding="utf-8")))


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char.isspace():
            i += 1
            continue
        if char in "()":
            tokens.append(char)
            i += 1
            continue
        if char == '"':
            i += 1
            value: list[str] = []
            while i < len(text):
                if text[i] == "\\" and i + 1 < len(text):
                    value.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                value.append(text[i])
                i += 1
            tokens.append("".join(value))
            continue
        start = i
        while i < len(text) and not text[i].isspace() and text[i] not in "()":
            i += 1
        tokens.append(text[start:i])
    return tokens


def _parse_tokens(tokens: list[str]) -> Sexp:
    stack: list[list[Sexp]] = []
    root: Sexp | None = None

    for token in tokens:
        if token == "(":
            node: list[Sexp] = []
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("unexpected ')' in KiCad S-expression")
            node = stack.pop()
            if not stack:
                root = node
        elif stack:
            stack[-1].append(token)
        else:
            raise ValueError("token outside KiCad S-expression")

    if stack:
        raise ValueError("unterminated KiCad S-expression")
    if root is None:
        raise ValueError("empty KiCad S-expression")
    return root


def _walk(node: Sexp) -> list[list[Sexp]]:
    if not isinstance(node, list):
        return []
    nodes = [node]
    for child in node:
        nodes.extend(_walk(child))
    return nodes


def _is_list_with_head(node: Sexp, head: str) -> bool:
    return isinstance(node, list) and bool(node) and node[0] == head


def _properties(node: list[Sexp]) -> dict[str, str]:
    properties: dict[str, str] = {}
    for child in node:
        if not _is_list_with_head(child, "property"):
            continue
        if len(child) >= 3 and isinstance(child[1], str) and isinstance(child[2], str):
            properties[child[1]] = child[2]
    return properties


def _is_library_symbol(node: list[Sexp]) -> bool:
    return len(node) > 1 and isinstance(node[1], str)


def _refdes_sort_key(component: ComponentRecord) -> tuple[str, int, str]:
    prefix = "".join(ch for ch in component.refdes if ch.isalpha() or ch == "#")
    digits = "".join(ch for ch in component.refdes if ch.isdigit())
    virtual_rank = 1 if component.refdes.startswith("#") else 0
    return (str(virtual_rank), prefix, int(digits or 0), component.refdes)
