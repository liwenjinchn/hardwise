"""V2 component-centric intermediate representation.

Re-exports the four core types so callers can do
``from hardwise.ir import Pin, Component, Net, Design``.
"""

from hardwise.ir.profile import DatasheetProfile
from hardwise.ir.types import Component, Design, Net, Pin

__all__ = ["Component", "DatasheetProfile", "Design", "Net", "Pin"]
