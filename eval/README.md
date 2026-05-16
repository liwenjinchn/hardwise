# Hardwise Eval Pack v0

This is the MVP evaluation path for Hardwise. It uses public KiCad repositories
selected from the `kicad-happy-testharness` smoke/corpus lists, then runs
Hardwise's deterministic R001/R002/R003 checks over local checkouts.

Trust boundary: this is a public regression oracle / pseudo-gold corpus, not a
human expert gold-label dataset. The purpose is to prove reproducibility,
parser/rule stability, and noise controls across more than one public project.

Run:

```bash
uv run hardwise eval --download
```

Outputs:

- `reports/eval/eval-summary.json`
- `reports/eval/eval-summary.html`

Use `--limit-projects N` while iterating.

Harness loop:

```bash
# 1. Run a small slice while debugging parser/rule behavior.
uv run hardwise eval --download --limit-projects 1

# 2. Accept a known-good run as the local baseline after inspection.
uv run hardwise eval --limit-projects 1 \
  --baseline eval/baselines/local-smoke.json \
  --accept-baseline

# 3. Compare future runs against that baseline.
uv run hardwise eval --limit-projects 1 \
  --baseline eval/baselines/local-smoke.json
```

The comparison gate is intentionally narrow for MVP. It fails on parser/project
failures, new unverified refdes wrapping, or newly dropped unsupported findings.
Finding-count changes are reported as observations because a useful rule change
can legitimately add or remove findings.

Current public smoke result:

- 5 public repos from `eval/manifest.yaml`
- 16 discovered KiCad project directories
- 1707 parsed components
- 437 deterministic findings
- decision split: 298 likely_issue / 99 reviewer_to_confirm / 40 likely_ok / 0 undecided
- 0 project failures
- 0 unverified refdes wrapped
- 0 findings dropped for missing evidence

Treat these as harness health and attention-allocation metrics, not expert
correctness scores. Public-corpus connector/header/module density can make
`likely_ok` look high; that is a corpus feature to inspect, not automatic proof
that the rule is too optimistic.

## Synthetic Must-Catch Cases

The public corpus is paired with a small synthetic must-catch harness in
`tests/harness/test_must_catch.py`. These tests use minimal schematic records
rather than full KiCad fixtures and lock known review safety cases:

- new real component without a footprint must be reported as `reviewer_to_confirm`
- capacitor value missing a rated-voltage suffix must be `likely_issue`
- capacitor value with a rated-voltage suffix must not produce a low-value finding
- IC/module NC pin without datasheet evidence must be `reviewer_to_confirm`
- connector-like batch NC pins must be grouped as one low-priority `likely_ok` finding

This is not an expert gold-label accuracy benchmark. It is the MVP
false-negative guardrail for known critical scenarios; a human-labeled
calibration set can be added later to measure precision/recall.
