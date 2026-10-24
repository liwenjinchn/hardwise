# Explicit DC voltage input

The passive capacitor voltage-margin and resistor-power checks require explicit
confirmed terminal envelopes. Names such as `VBUS_20V`, `USB3P0_D_P`, `GND` and
legacy `Net.voltage_hint` values do not confirm these inputs.

This input currently controls the generic passive stress checks. Existing
profile-family rules still use the legacy inference helper and have not been
re-certified by this change. Result/severity/evidence separation, BOM conflicts,
profile conditions and full project persistence remain open product work.

## Input and calculation

A `hardwise.voltage_facts.v1` JSON document contains an `active_mode` and a `facts`
list. Each record names an exact net and reference net, a mode, unit `V`, optional
minimum/typical/maximum, source, confirmation flag and confirmer name. An omitted
confirmation flag means unconfirmed. A typical-only record can be retained but
cannot establish a passing worst-case comparison.

Only records matching the active mode are used. Exactly two connected terminals,
both confirmed, both with finite minimum/maximum, and the same reference net are
required. Otherwise the affected stress check returns UNKNOWN with a reason.
Different reference nets are never equated by name or by two nominal zero values.

For different nets, maximum DC stress is
`max(abs(A.minimum - B.maximum), abs(A.maximum - B.minimum))`.
For the same net, differential is zero even when common-mode voltage varies.
Resistor worst-case DC power uses that maximum difference squared divided by the
parsed nonzero resistance. Missing power rating is UNKNOWN; a zero-ohm link never
uses that formula and cannot establish a passing current/power margin.

These are DC envelope checks only. No transient, ripple, polarity or thermal
suitability is established. Parsed BOM ratings are still subject to the existing
identity/conflict limitations; confirmation is a user assertion, not a physical
measurement or an independent engineering approval.

Unknown net/reference names, duplicate net/mode records, non-finite values,
reversed ranges, incompatible typical values, unsupported units, blank sources
and confirmations without a named confirmer reject the whole input. Failed
imports leave the previous active project intact.

## Reproducible public/synthetic example

The complete source is `tests/fixtures/allegro/bipolar_dc/`. It specifies +12 V
and -12 V relative to the same GND in DC mode, across a 16 V capacitor. This is a
synthetic engineering premise, not measured hardware. With the file, capacitor
stress is 24 V and ERROR; without it, stress is UNKNOWN.

```sh
PYTHONPATH=src uv run hardwise design-validator-ui \
  tests/fixtures/allegro/bipolar_dc/design.net \
  tests/fixtures/allegro/bipolar_dc/bom.csv \
  --voltage-facts tests/fixtures/allegro/bipolar_dc/voltage_facts.json \
  --ai-snapshot --output reports/bipolar-dc-white-workbench.html \
  --index-output reports/bipolar-dc.md --index-json reports/bipolar-dc.json
```

`--ai-snapshot` uses the current light React workbench with local audited chat
snapshots and makes no live model request. Without it, the legacy static report
renderer remains available. UI verification for the product should use the
React workbench or `serve-workbench`, rather than treating the legacy renderer
as the current frontend.

The same `--voltage-facts` option is supported by `serve-workbench`. The Import
page accepts the file in the optional “已确认电压事实” slot together with the
netlist and BOM. The current facts and source/confirmation records are readable
on that page and survive deterministic reruns. JSON state/index exports carry
the full document; Markdown includes a fact table and each computed stress
includes the facts it used. The offline React snapshot includes the same state.

Uploaded inputs still live in the existing process-owned temporary directory;
this is not cross-restart project persistence. Graphical per-net confirmation
and source locators for these new fact tokens remain further work.
