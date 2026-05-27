"""Deterministic component validation reports."""

from hardwise.validation.component import (
    validate_component_against_profile,
)
from hardwise.validation.profile_candidates import (
    ProfileCandidate,
    ProfileCandidateError,
    ProfileCandidateReport,
    ProfileCandidateStatus,
    render_profile_candidate_manifest,
    suggest_profile_candidates,
)
from hardwise.validation.types import (
    ComponentValidation,
    PinValidation,
    PinValidationStatus,
    ValidationReport,
)
from hardwise.validation.targets import (
    ValidationTarget,
    ValidationTargetParseError,
    load_targets_manifest,
    parse_inline_targets,
)

__all__ = [
    "ComponentValidation",
    "PinValidation",
    "PinValidationStatus",
    "ProfileCandidate",
    "ProfileCandidateError",
    "ProfileCandidateReport",
    "ProfileCandidateStatus",
    "ValidationTarget",
    "ValidationTargetParseError",
    "ValidationReport",
    "load_targets_manifest",
    "parse_inline_targets",
    "render_profile_candidate_manifest",
    "suggest_profile_candidates",
    "validate_component_against_profile",
]
