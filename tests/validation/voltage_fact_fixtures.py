"""Explicit synthetic premises for rating regression tests; never name parsing."""

from hardwise.ir.types import Net
from hardwise.ir.voltage import VoltageFact, VoltageFactsDocument


def confirm_dc_values(design, values):
    reference = "TEST_REFERENCE"
    design.nets.setdefault(reference, Net(name=reference, nodes=[]))
    facts = {fact.net: fact for fact in design.voltage_facts.facts}
    facts.update(
        {
            net: VoltageFact(
                net=net,
                reference_net=reference,
                minimum=value,
                maximum=value,
                source="synthetic regression premise; not a physical measurement",
                confirmed=True,
                confirmed_by="test author",
            )
            for net, value in values.items()
        }
    )
    design.voltage_facts = VoltageFactsDocument(facts=list(facts.values()))
