"""Trace connection reads for one topology family, without changing source objects.

The scope is a family invocation, not a claim of minimal per-check dependencies.
Only families that actually inspect ambiguous connectivity are suspended. Local
pin/value checks and invocations on unrelated branches retain their own results.
"""

from collections.abc import Mapping
from functools import wraps

from hardwise.ir.connectivity_queries import ambiguous_net_names, declaration_token


class _ReadScope:
    def __init__(self, design):
        self.design = design
        self.blocked = ambiguous_net_names(design)
        self.touched = set()

    def note(self, names):
        self.touched.update(name for name in names if name in self.blocked)


class _View:
    def __init__(self, source, scope):
        self._source, self._scope = source, scope

    def __getattr__(self, name):
        if name in {"model_copy", "model_dump", "model_dump_json", "copy", "dict"}:
            raise TypeError(
                "Topology validation must read explicit fields, not unwrap traced objects"
            )
        return getattr(self._source, name)


class _Pin(_View):
    @property
    def net(self):
        self._scope.note(self._source.connection_ambiguity)
        if self._source.net:
            self._scope.note([self._source.net])
        return self._source.net

    @property
    def connection_ambiguity(self):
        self._scope.note(self._source.connection_ambiguity)
        return self._source.connection_ambiguity


class _Component(_View):
    @property
    def pins(self):
        return [_Pin(pin, self._scope) for pin in self._source.pins]

    def pin_by_number(self, number):
        pin = self._source.pin_by_number(number)
        return _Pin(pin, self._scope) if pin is not None else None

    def pin_by_name(self, name):
        pin = self._source.pin_by_name(name)
        return _Pin(pin, self._scope) if pin is not None else None


class _Components(Mapping):
    def __init__(self, source, scope):
        self.source, self.scope = source, scope

    def __getitem__(self, key):
        return _Component(self.source[key], self.scope)

    def __iter__(self):
        return iter(self.source)

    def __len__(self):
        return len(self.source)


class _Nets(Mapping):
    def __init__(self, source, scope):
        self.source, self.scope = source, scope

    def __getitem__(self, key):
        self.scope.note([key])
        return self.source[key]

    def __iter__(self):
        # Enumeration/absence over the whole graph needs the complete graph.
        self.scope.note(self.scope.blocked)
        return iter(self.source)

    def __len__(self):
        self.scope.note(self.scope.blocked)
        return len(self.source)


class _Design(_View):
    @property
    def components(self):
        return _Components(self._source.components, self._scope)

    @property
    def nets(self):
        return _Nets(self._source.nets, self._scope)


def isolate_topology(function):
    @wraps(function)
    def guarded(component, profile, design):
        if not ambiguous_net_names(design):
            return function(component, profile, design)
        scope = _ReadScope(design)
        results = function(_Component(component, scope), profile, _Design(design, scope))
        if not scope.touched:
            return results
        names = sorted(scope.touched)
        tokens = [
            declaration_token(d, i)
            for i, d in enumerate(design.connectivity.declarations)
            if d.net_name in scope.touched
        ]
        return [
            item.model_copy(
                update={
                    "result": "UNKNOWN",
                    "severity": "WARNING",
                    "needs_review": True,
                    "evidence_kind": "SOURCE_FACT",
                    "rule_version": f"{item.rule_version}.connection-isolation1",
                    "summary": "本次拓扑规则组读取了歧义连接（"
                    + ", ".join(names)
                    + "）；该规则组暂停判定。未声称开路、短路或器件缺失；原始声明保留待核对。",
                    "evidence": list(dict.fromkeys([*item.evidence, *tokens])),
                }
            )
            for item in results
        ]

    return guarded
