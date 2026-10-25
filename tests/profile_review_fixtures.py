"""Explicit fictional review declarations for algorithm tests only. Never real approval.

No autouse hook, production source rewrite, API bypass, or monkeypatch is used.
Tests must choose this helper; product/migration tests use original DRAFT data.
"""

from hardwise.ir.profile_review import (
    FieldCondition,
    FieldDecision,
    FieldSource,
    ProfileReview,
    ReviewIdentity,
    ReviewedField,
    expected_subject,
    profile_values,
)
from hardwise.ir.profile_units import expected_unit


def approve_for_algorithm(profile, *, manufacturer, packages):
    identity = ReviewIdentity(
        manufacturer=manufacturer,
        part_numbers=[profile.part_number, *profile.part_number_aliases],
        packages=packages,
    )
    source = FieldSource(
        url="https://example.invalid/automated-synthetic-datasheet.pdf",
        document_revision="SYNTHETIC-TEST-ONLY",
        document_sha256="e" * 64,
        page=1,
        locator="Fictional test table",
        excerpt="Automated fictional fixture; not a vendor source or actual human approval.",
    )
    fields = []
    for pointer, value in profile_values(profile).items():
        key = pointer.rsplit("/", 1)[-1]
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        unit = (
            expected_unit(pointer) if numeric else "boolean" if isinstance(value, bool) else "text"
        )
        if numeric and unit is None:
            raise AssertionError(f"Test fixture requires an explicit implemented unit: {pointer}")
        role = (
            "maximum"
            if pointer.startswith("/abs_max/") or key in {"abs_max_voltage", "vb_vs_abs_max"}
            else "definition"
        )
        if key.endswith("_min") or key == "minimum_voltage":
            role = "minimum"
        if key.endswith("_max") or "_max_" in key:
            role = "maximum"
        if any(x in key for x in ("typical", "_typ", "nominal")):
            role = "typical"
        field = ReviewedField(
            pointer=pointer,
            value=value,
            unit=unit,
            subject=expected_subject(profile, pointer),
            role=role,
            nature="intrinsic",
            conditions=[FieldCondition(kind="unconditional", description="Fictional test premise")],
            source=source,
        )
        decision = FieldDecision(
            decision="approved",
            actor="human",
            reviewer="SIMULATED HUMAN RECORD FOR AUTOMATED TEST - NOT ACTUAL ACCEPTANCE",
            reviewed_at="2026-10-26T00:00:00Z",
            reason="Exercise algorithm under declared trusted test premises only",
            content_sha256=field.content_hash(identity),
        )
        fields.append(field.model_copy(update={"decisions": [decision]}))
    approved = profile.model_copy(
        update={"field_review": ProfileReview(identity=identity, status="READY", fields=fields)}
    )
    assert approved.approved_for_validation, f"Invalid synthetic contract for {profile.part_number}"
    return approved


def validate_with_synthetic_approval(component, profile, design):
    from hardwise.validation.component import validate_component_against_profile

    # Explicit fictional missing identity premises, confined to the copied unit-test design.
    component = component.model_copy(
        update={
            "manufacturer": component.manufacturer or "SYNTHETIC-TEST-MANUFACTURER",
            "package": component.package or "SYNTHETIC-TEST-PACKAGE",
        }
    )
    design = design.model_copy(
        update={"components": {**design.components, component.refdes: component}}
    )
    profile = approve_for_algorithm(
        profile, manufacturer=component.manufacturer, packages=[component.package]
    )
    return validate_component_against_profile(component, profile, design)


# Keep only explicitly requested test directories alive through import/rerun.
# This is resource ownership, not an autouse approval hook.
_review_directories = []


def reviewed_context_for_algorithm(**kwargs):
    """Real context/API with explicit fictional reviewed premises in an isolated copy.

    Only originally ready profiles that are actually bound in this test design
    receive simulated declarations. Legacy needs_review remains DRAFT.
    """
    from pathlib import Path
    import tempfile
    import shutil
    from hardwise.ir.profile import DatasheetProfile
    from hardwise.workbench.context import build_workbench_context, close_workbench_context

    original = build_workbench_context(**kwargs)
    directory = tempfile.TemporaryDirectory(prefix="hardwise-explicit-review-test-")
    _review_directories.append(directory)
    root = Path(directory.name)
    try:
        bound = {}
        for ref, profile in original.validation_targets.items():
            if profile.review_status != "ready":
                continue
            component = original.design.components[ref]
            bound.setdefault(profile.part_number, []).append(component)
        for path in Path(kwargs["profiles"]).glob("*.json"):
            profile = DatasheetProfile.load(path)
            components = bound.get(profile.part_number, [])
            if components:
                manufacturers = {c.manufacturer for c in components}
                packages = {c.package for c in components}
                assert len(manufacturers) == 1 and all(manufacturers) and all(packages), (
                    "Explicit manufacturer/package test premises required"
                )
                profile = approve_for_algorithm(
                    profile, manufacturer=next(iter(manufacturers)), packages=sorted(packages)
                )
                profile.save(root / path.name)
            else:
                shutil.copyfile(path, root / path.name)
    finally:
        close_workbench_context(original)
    kwargs = {**kwargs, "profiles": root}
    return build_workbench_context(**kwargs)
