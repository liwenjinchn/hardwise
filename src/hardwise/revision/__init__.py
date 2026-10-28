"""Standalone schematic revision comparison; legacy validation remains independent."""

from hardwise.revision.engine import compare_files, compare_revisions
from hardwise.revision.models import ComparisonResult

__all__ = ["ComparisonResult", "compare_files", "compare_revisions"]
