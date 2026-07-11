"""Versioned public/synthetic fixtures for seeded family calibration."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from hardwise.validation.types import PinValidationStatus

_BASE_BOM = """Reference,Quantity,Value,Manufacturer,MPN
C1,1,0.1uF 25V,Fixture,CAP-100N
R1,1,10K,Fixture,RES-10K
U1,1,TBD210419,Fixture,TBD210419
"""

FindingKind = Literal["pin", "component"]
SeededDefectFamily = Literal[
    "capacitor",
    "resistor",
    "mosfet",
    "diode",
    "i2c_mux",
    "dcdc_buck",
]
MutationTarget = Literal["bom", "netlist", "pstchip.dat"]
SUPPORTED_MATRIX_VERSION = 1


class SeededFindingSignature(BaseModel):
    """One expected or observed validation issue signature."""

    refdes: str
    kind: FindingKind
    check: str
    status: PinValidationStatus

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.refdes, self.kind, self.check, self.status)


class SeededDefectCaseSpec(BaseModel):
    """Declarative public/synthetic fixture mutation loaded from the matrix."""

    name: str
    description: str
    family: SeededDefectFamily
    fixture_name: str
    netlist: str
    bom: str | None = None
    mutation_target: MutationTarget
    mutation_old: str
    mutation_new: str
    expected: SeededFindingSignature


class SeededDefectMatrix(BaseModel):
    """Versioned seeded-case manifest."""

    version: int
    cases: list[SeededDefectCaseSpec]


@dataclass(frozen=True)
class SeededFixture:
    name: str
    netlist: Path
    bom: Path | None = None


@dataclass(frozen=True)
class SeededWorkspace:
    netlist: Path
    bom: Path


@dataclass(frozen=True)
class SeededDefectCase:
    name: str
    description: str
    family: SeededDefectFamily
    fixture: SeededFixture
    mutate: Callable[[SeededWorkspace], None]
    expected: SeededFindingSignature


def load_seeded_cases(
    *,
    fixture: Path,
    fixtures_root: Path,
    matrix: Path,
) -> list[SeededDefectCase]:
    """Load and bind the versioned matrix to local public/synthetic fixtures."""

    manifest = SeededDefectMatrix.model_validate_json(matrix.read_text(encoding="utf-8"))
    if manifest.version != SUPPORTED_MATRIX_VERSION:
        raise ValueError(
            f"{matrix}: unsupported seeded matrix version {manifest.version}; "
            f"expected {SUPPORTED_MATRIX_VERSION}"
        )
    return [
        SeededDefectCase(
            name=spec.name,
            description=spec.description,
            family=spec.family,
            fixture=SeededFixture(
                name=spec.fixture_name,
                netlist=(fixture if spec.netlist == "$fixture" else fixtures_root / spec.netlist),
                bom=fixtures_root / spec.bom if spec.bom is not None else None,
            ),
            mutate=partial(
                _apply_mutation,
                target=spec.mutation_target,
                old=spec.mutation_old,
                new=spec.mutation_new,
            ),
            expected=spec.expected,
        )
        for spec in manifest.cases
    ]


def materialize_seeded_fixture(source: SeededFixture, target: Path) -> SeededWorkspace:
    """Copy one clean fixture into an isolated mutation workspace."""

    if source.netlist.is_dir():
        shutil.copytree(source.netlist, target)
        bom = _write_base_bom(target) if source.bom is None else target / source.bom.name
        if source.bom is not None:
            shutil.copy2(source.bom, bom)
        return SeededWorkspace(netlist=target, bom=bom)

    target.mkdir(parents=True)
    netlist = target / source.netlist.name
    shutil.copy2(source.netlist, netlist)
    if source.bom is None:
        raise ValueError(f"{source.netlist}: paired BOM is required for file fixtures")
    bom = target / source.bom.name
    shutil.copy2(source.bom, bom)
    return SeededWorkspace(netlist=netlist, bom=bom)


def _write_base_bom(project: Path) -> Path:
    bom = project / "bom.csv"
    bom.write_text(_BASE_BOM, encoding="utf-8")
    return bom


def _apply_mutation(
    workspace: SeededWorkspace,
    *,
    target: MutationTarget,
    old: str,
    new: str,
) -> None:
    if target == "bom":
        path = workspace.bom
    elif target == "netlist":
        if workspace.netlist.is_dir():
            raise ValueError(f"{workspace.netlist}: expected a netlist file")
        path = workspace.netlist
    else:
        if not workspace.netlist.is_dir():
            raise ValueError(f"{workspace.netlist}: expected a PST fixture directory")
        path = workspace.netlist / target
    _replace_in_file(path, old, new)


def _replace_in_file(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError(f"{path}: expected mutation text not found: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
