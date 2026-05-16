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
