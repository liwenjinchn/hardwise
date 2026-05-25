"""V2 component-centric intermediate representation.

Re-exports the four core types so callers can do
``from hardwise.ir import Pin, Component, Net, Design``.
"""

from hardwise.ir.types import Component, Design, Net, Pin

__all__ = ["Component", "Design", "Net", "Pin"]
