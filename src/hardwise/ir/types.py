"""IR types: Pin / Component / Net / Design.

V2 architecture — Component is the first-class entity. Parse-level
records from ``adapters/`` get aggregated into Component objects via
``ir/build.py``. Compared to BoardRegistry (which is a bag of
parse-level records), a Design owns the per-component object graph
that reviews and reports work against.

Pydantic BaseModel is used here (not @dataclass) to stay consistent
with ``adapters/base.py`` and ``checklist/finding.py`` — both already
use BaseModel, and V2.4 will need JSON round-trip on DatasheetProfile,
so the IR layer commits to the same serialisation foundation.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from hardwise.checklist.finding import Finding


class Pin(BaseModel):
    """One pin of one Component instance.

    Schematic-side fields (``number``, ``name``, ``electrical_type``,
    ``is_nc``, ``net``) come from the KiCad / Allegro adapter at parse
    time. Datasheet-side ``datasheet_function`` is filled later by
    V2.4 datasheet-driven checks. ``findings`` accumulates pin-scoped
    review issues — the runner attaches them during V2.2.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    number: str
    name: str
    electrical_type: str
    is_nc: bool
    net: Optional[str] = None
    datasheet_function: Optional[str] = None
    findings: list[Finding] = Field(default_factory=list)
