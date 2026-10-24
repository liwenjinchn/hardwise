"""Connected resistor observations, never proof of LED current regulation."""

from hardwise.ir.types import Component, Design
from hardwise.validation.topology import components_on_net


def led_current_limit_summary(
    component: Component, design: Design, anode_net: str, cathode_net: str
) -> str | None:
    """Expose actual neighboring resistors as candidates; infer no rail voltage.

    The netlist omits external supplies/drivers and operating states. A nearby
    resistor is not necessarily in series with LED current, so this helper
    cannot authorize a current-limit PASS or a missing-resistor defect.
    """
    candidates = []
    for branch, net in (("anode", anode_net), ("cathode", cathode_net)):
        neighbors = components_on_net(design, net, exclude_refdes=component.refdes)
        shared = any(n.refdes.startswith("D") for n in neighbors)
        for resistor in neighbors:
            if resistor.refdes.startswith("R"):
                candidates.append(
                    f"{resistor.refdes}（连接 {branch} 网络 {net}"
                    + ("，存在其他二极管共网" if shared else "")
                    + "）"
                )
    return "限流候选电阻：" + "；".join(candidates) + "。" if candidates else None
