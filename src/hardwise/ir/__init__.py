"""V2/V3 component-centric intermediate representation.

Re-exports the core design and profile types.
"""

from hardwise.ir.profile import DatasheetProfile, PinProfile
from hardwise.ir.types import Component, Design, Net, Pin

__all__ = ["Component", "DatasheetProfile", "Design", "Net", "Pin", "PinProfile"]
