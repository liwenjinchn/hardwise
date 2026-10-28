"""Read two lightweight source types without constructing an electrical workbench."""

from collections import defaultdict
from pathlib import Path
from typing import Literal

from hardwise.adapters.allegro_netlist import parse_allegro_netlist
from hardwise.bom.conflicts import group_bom_rows
from hardwise.bom.matcher import match_bom_to_design
from hardwise.bom.identity_fields import row_identity_conflicts
from hardwise.bom.parser import parse_bom
from hardwise.input_provenance import capture_input_reads, read_input_text
from hardwise.ir.build import build_design_from_netlist
from hardwise.ir.identity_sources import is_mpn_field
from hardwise.revision.bom_fields import bom_observations
from hardwise.revision.models import (
    ComparisonIssue,
    Endpoint,
    NetworkView,
    Observation,
    RevisionSnapshot,
    RevisionView,
    SnapshotComponent,
    SourceDigest,
    SourceEvidence,
)


def load_revision(
    netlist: Path,
    bom_path: Path,
    *,
    side: Literal["before", "after"],
) -> RevisionSnapshot:
    """The first slice accepts Telesis text plus CSV/TSV, never guessed PST/DSN inputs."""
    if netlist.suffix.lower() not in {".net", ".txt"} or not netlist.is_file():
        raise ValueError("改版对比首版仅接受 Telesis .net/.txt 文本网表；PST/DSN 尚未接入。")
    if bom_path.suffix.lower() not in {".csv", ".tsv"} or not bom_path.is_file():
        raise ValueError("改版对比首版仅接受 CSV/TSV BOM。")
    if netlist.resolve() == bom_path.resolve():
        raise ValueError("网表与 BOM 必须是两个独立文件。")
    with capture_input_reads() as collector:
        # Reject invalid encoding instead of silently comparing replacement characters.
        read_input_text(bom_path, role="bom", encoding="utf-8-sig", errors="strict")
        registry = parse_allegro_netlist(netlist, encoding="utf-8-sig")
        design = build_design_from_netlist(registry)
        bom = parse_bom(bom_path)
        match = match_bom_to_design(bom, design)
        manifest = collector.finish()
    digests = {item.resolved_path: item for item in manifest.files}
    net_digest, bom_digest = digests[str(netlist.resolve())], digests[str(bom_path.resolve())]
    issues = []

    def evidence(path, digest, locator):
        return SourceEvidence(file=path.name, sha256=digest.sha256, locator=locator)

    def issue(code, explanation, refdes=None, sources=()):
        issues.append(
            ComparisonIssue(
                side=side,
                code=code,
                refdes=refdes,
                explanation=explanation,
                evidence=sources,
            )
        )

    raw_properties = defaultdict(lambda: defaultdict(list))
    for prop in registry.properties:
        for ref in prop.targets:
            source = evidence(netlist, net_digest, f"$A_PROPERTIES; {prop.name}; refdes={ref}")
            if ref not in design.components:
                issue(
                    "unknown_property_target",
                    "网表属性指向未声明位号，未将其补造为器件。",
                    ref,
                    (source,),
                )
                continue
            raw_properties[ref][prop.name].append((prop.value, source))
    rows = group_bom_rows(bom.rows)
    components = {}
    for ref, component in sorted(design.components.items()):
        source = evidence(netlist, net_digest, f"$PACKAGES; refdes={ref}")
        attributes = {
            "netlist.device": Observation(values=(component.value,), evidence=(source,)),
            "netlist.package": Observation(
                state="known" if component.package else "missing",
                values=(component.package,) if component.package else (),
                evidence=(source,),
            ),
        }
        for name, entries in sorted(raw_properties[ref].items()):
            values = tuple(sorted({value.strip() for value, _ in entries if value.strip()}))
            attributes["netlist.property." + name] = Observation(
                state="ambiguous" if len(values) > 1 else "known" if values else "missing",
                values=values,
                evidence=tuple(item[1] for item in entries),
            )
        row = match.rows_by_refdes.get(ref)
        declared_rows = rows.get(ref, [])
        # Exact, unique BOM refdes remains a source observation even when its MPN
        # disagrees with the netlist. Do not reuse electrical-approval gating to
        # erase independently declared BOM changes.
        if row is None and len(declared_rows) == 1 and not row_identity_conflicts(declared_rows[0]):
            row = declared_rows[0]
            if ref in match.identity_conflicts:
                issue(
                    "cross_source_identity_conflict",
                    "网表与 BOM 的型号声明不一致；分别保留来源字段供改版比较，不认定任一来源为正确身份。",
                    ref,
                    (
                        *(
                            entry[1]
                            for name, entries in raw_properties[ref].items()
                            if is_mpn_field(name)
                            for entry in entries
                        ),
                        evidence(bom_path, bom_digest, f"line {row.source_line}; refdes={ref}"),
                    ),
                )
        join_ambiguous = row is None
        if row is not None:
            attributes.update(bom_observations(row, bom_digest.sha256))
        else:
            row_sources = tuple(
                evidence(bom_path, bom_digest, f"line {record.source_line}; refdes={ref}")
                for record in rows.get(ref, [])
            )
            if ref in match.identity_conflicts or ref in match.duplicate_bom_refdes:
                issue(
                    "bom_identity_ambiguous",
                    "BOM 位号/身份存在冲突或重复，相关 BOM 字段不做确定性比较。",
                    ref,
                    row_sources,
                )
            else:
                issue(
                    "bom_missing",
                    "网表中存在该位号，但 BOM 缺少对应记录；不把缺资料解释为属性删除。",
                    ref,
                    (source,),
                )
        for field, observation in attributes.items():
            if observation.state == "ambiguous":
                issue(
                    "attribute_ambiguous",
                    f"{field} 存在多条不同声明，未选择任意值。",
                    ref,
                    observation.evidence,
                )
        components[ref] = SnapshotComponent(
            refdes=ref,
            attributes=attributes,
            evidence=(source,),
            identity_ambiguous=join_ambiguous,
        )
    for ref in match.bom_only_refdes:
        sources = tuple(
            evidence(bom_path, bom_digest, f"line {r.source_line}; refdes={ref}") for r in rows[ref]
        )
        issue("bom_only", "BOM 位号未在网表声明，不认定为实际新增器件。", ref, sources)
    for record in (*match.quantity_mismatches, *match.quantity_column_conflicts):
        issue(
            "bom_quantity",
            "BOM 行数量声明与位号清单不一致或数量列冲突；数量不用于器件属性比较。",
            sources=(evidence(bom_path, bom_digest, f"line {record.source_line}"),),
        )
    for item in bom.non_refdes_items:
        issue(
            "bom_unmapped_row",
            "BOM 行未能映射到位号，未作为器件属性比较。",
            sources=(evidence(bom_path, bom_digest, f"line {item.source_line}"),),
        )

    declarations = defaultdict(list)
    projection = design.connectivity
    assert projection is not None
    for declaration in projection.declarations:
        declarations[declaration.net_name].append(declaration)
    networks, pin_networks = [], defaultdict(lambda: defaultdict(set))
    blocked = set(projection.ambiguous_net_names)
    for name, records in sorted(declarations.items()):
        endpoints = tuple(
            Endpoint(refdes=ref, pin=pin)
            for ref, pin in sorted({node for r in records for node in r.nodes})
        )
        sources = tuple(
            evidence(netlist, net_digest, f"line {r.line}; $NETS; {name}") for r in records
        )
        networks.append(
            NetworkView(name=name, endpoints=endpoints, ambiguous=name in blocked, evidence=sources)
        )
        for endpoint in endpoints:
            pin_networks[endpoint.refdes][endpoint.pin].add(name)
        if name in blocked:
            issue(
                "connectivity_ambiguous",
                f"网络 {name} 存在重复或冲突声明；不会把被隔离的连接当成断开。",
                sources=sources,
            )

    for ref, component in components.items():
        if ref not in pin_networks:
            issue(
                "component_connections_missing",
                "该器件在本版没有任何引脚连接声明，连接不可比较；不据此认定实际开路或没有变化。",
                ref,
                component.evidence,
            )

    return RevisionSnapshot(
        view=RevisionView(
            label="旧版" if side == "before" else "新版",
            component_count=len(components),
            net_count=len(networks),
            bom_row_count=len(bom.rows),
            sources=(
                SourceDigest(
                    file=netlist.name,
                    role="netlist",
                    sha256=net_digest.sha256,
                    size_bytes=net_digest.size_bytes,
                ),
                SourceDigest(
                    file=bom_path.name,
                    role="bom",
                    sha256=bom_digest.sha256,
                    size_bytes=bom_digest.size_bytes,
                ),
            ),
            networks=tuple(networks),
        ),
        components=components,
        issues=tuple(issues),
        pin_networks={
            ref: {pin: tuple(sorted(names)) for pin, names in pins.items()}
            for ref, pins in pin_networks.items()
        },
    )
