"""Registered schematic-review checks."""

from hardwise.checklist.checks.ds001_vin_abs_max import DS001_SPEC
from hardwise.checklist.checks.r001_new_component_candidate import R001_SPEC
from hardwise.checklist.checks.r002_cap_voltage_derating import R002_SPEC
from hardwise.checklist.checks.r003_nc_pin_handling import R003_SPEC

CHECK_SPECS = [R001_SPEC, R002_SPEC, R003_SPEC, DS001_SPEC]

__all__ = ["CHECK_SPECS", "DS001_SPEC", "R001_SPEC", "R002_SPEC", "R003_SPEC"]
