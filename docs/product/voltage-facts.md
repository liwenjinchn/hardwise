# Explicit DC voltage input

The passive capacitor voltage-margin and resistor-power checks require explicit
confirmed terminal envelopes. Names such as `VBUS_20V`, `USB3P0_D_P`, `GND` and
legacy `Net.voltage_hint` values do not confirm these inputs.

Generic passive stress checks consume this document directly. Supported profile
pin/terminal-voltage, diode and control paths also consume explicit DC envelopes
through `dc_envelope.py`; their separate profile identity, approved-field and
condition guards still apply. Providing voltage facts does not approve a profile
or establish that every family rule is covered. See the current full-acceptance
ledger for outstanding product requirements.

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

An unsaved upload initially lives in a process-owned temporary directory. Saving
the project to the SQLite journal captures its voltage-facts file in the managed
input directory. Reopening the saved project can restore the complete document
without the original upload paths. Move the journal together with its managed
input directory, or use the project backup/restore workflow; copying the SQLite
file alone is insufficient. See [managed projects](managed-project-v1.md).

The graphical import surface currently uploads an entire JSON document and reads
back the records. It does not provide per-net editing, candidate selection, batch
confirmation or conflict resolution. Invalid/duplicate documents are rejected
atomically, retaining the previous active project; this does not satisfy the
PRD's full batch-confirmation workflow. The import page's legacy passive-only
help text understates the currently supported family consumers. Its wording and
the future editing workflow still need alignment; no family-wide certification
is implied. [Stage67 audit](fact-confirmation-audit-v1.md) records current evidence.


## Multi-source review input (stage72)

The same optional input accepts a `hardwise.voltage_review.v1` document with
source candidates and content/scope-bound declarations. Conflicts and stale
confirmations do not become executable confirmed facts. The complete ledger is
retained in the original captured input and in new run provenance; old runs and
v1 files are not rewritten. Managed save/open and project backup/restore retain
all candidates and declarations. Ordinary Design/index JSON and CSV carry
executable assessments/facts, not a complete ledger backup. Use the recorded run
manifest or complete project backup when preserving review history.

This enables file import/readback persistence only; the planned batch-edit and
conflict-resolution UI/API is still incomplete. See the selected
[multi-source implementation contract](fact-confirmation-plan-v1.md).


## White batch editor (stage74 development version)

The Import page now includes source candidates grouped by net/mode. Add or revise
explicit candidates, record source/locator/reference/envelope, choose sources or
leave unknown, and submit selected operations with a reviewer declaration and
reason. Changes save an independent managed source version and rerun checks.
Original inputs and recorded runs remain intact. Reverting candidate content does
not resurrect an earlier confirmation; an explicit new confirmation is needed.
A project/run/revision mismatch preserves the draft and requires an explicit
refresh and re-selection. Names alone never confirm a voltage.

New offline reports carry a read-only full candidate/history view. Old snapshots
without it retain their previous readback. Editing requires a local SQLite
journal; reviewer text is a local user assertion, not authenticated identity or
independent engineering approval. This stage is validated on public synthetic
inputs and still awaits unified delivery and actual target-environment review.
