"""Block ambiguous BOM/netlist bindings before profiles become executable targets."""

from typing import TYPE_CHECKING
from hardwise.bom.conflicts import CONFLICT_PROPERTY, conflict_reason, group_bom_rows
from hardwise.bom.types import Bom
from hardwise.bom.identity_fields import row_identity_conflicts
from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Design
from hardwise.validation.identity_scope import profile_identity_conflict_report

if TYPE_CHECKING:
    from hardwise.validation.profile_candidates import ProfileCandidate


def block_identity_candidates(
    candidates: list["ProfileCandidate"], bom: Bom, design: Design | None
):
    grouped = group_bom_rows(bom.rows)
    conflicts = {}
    for ref, rows in grouped.items():
        reason = conflict_reason(ref, rows) if len(rows) > 1 else row_identity_conflicts(rows[0])
        if reason:
            conflicts[ref] = reason
    if design is not None:
        conflicts.update(
            {
                ref: component.properties[CONFLICT_PROPERTY]
                for ref, component in design.components.items()
                if component.properties.get(CONFLICT_PROPERTY)
            }
        )
    loaded_profiles = {}
    for candidate in candidates:
        if (
            candidate.refdes not in conflicts
            and design is not None
            and candidate.profile is not None
            and candidate.refdes in design.components
        ):
            if candidate.profile not in loaded_profiles:
                loaded_profiles[candidate.profile] = DatasheetProfile.load(candidate.profile)
            blocked = profile_identity_conflict_report(
                design.components[candidate.refdes], loaded_profiles[candidate.profile]
            )
            if blocked is not None:
                conflicts[candidate.refdes] = blocked.component_checks[0].summary
        if candidate.refdes in conflicts:
            # All later topology/agent consumers must see the unresolved binding too.
            if design is not None and candidate.refdes in design.components:
                component = design.components[candidate.refdes]
                design.components[candidate.refdes] = component.model_copy(
                    update={
                        "properties": {
                            **component.properties,
                            CONFLICT_PROPERTY: conflicts[candidate.refdes],
                        }
                    }
                )
            candidate.match_status = "ambiguous"
            candidate.profile = None
            candidate.candidates = []
            candidate.identity = "-"
            candidate.identity_kind = "missing"
            candidate.reason = conflicts[candidate.refdes]
