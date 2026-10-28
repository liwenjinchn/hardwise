"""Network identities use endpoint sets, not export ordering or inferred voltages."""

import hashlib
import json

from hardwise.revision.models import Observation, RevisionSnapshot


class ConnectionIndex:
    def __init__(self, snapshot: RevisionSnapshot):
        self.snapshot = snapshot
        self.networks = {net.name: net for net in snapshot.view.networks}
        # Hash each shared net once: avoid copying its full membership for every pin.
        self.signatures = {
            net.name: hashlib.sha256(
                json.dumps(
                    sorted((p.refdes, p.pin) for p in net.endpoints),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()
            for net in snapshot.view.networks
        }
        self._neighbor_cache: dict[str, set[str]] = {}

    def observation(self, ref: str, pin: str) -> tuple[Observation, str | None]:
        names = self.snapshot.pin_networks.get(ref, {}).get(pin, ())
        nets = [self.networks[name] for name in names]
        evidence = tuple(source for net in nets for source in net.evidence)
        if not names:
            return Observation(
                state="missing",
                evidence=self.snapshot.components[ref].evidence,
            ), None
        if len(names) != 1 or any(net.ambiguous for net in nets):
            return Observation(state="ambiguous", values=names, evidence=evidence), None
        return Observation(values=names, evidence=evidence), self.signatures[names[0]]

    def neighbors(self, ref: str) -> set[str]:
        if ref not in self._neighbor_cache:
            names = {
                name
                for values in self.snapshot.pin_networks.get(ref, {}).values()
                for name in values
            }
            self._neighbor_cache[ref] = {
                endpoint.refdes
                for name in names
                for endpoint in self.networks[name].endpoints
                if endpoint.refdes != ref and not self.networks[name].ambiguous
            }
        return self._neighbor_cache[ref]

    def ambiguous_refdes(self) -> set[str]:
        return {
            endpoint.refdes
            for net in self.networks.values()
            if net.ambiguous
            for endpoint in net.endpoints
        }
