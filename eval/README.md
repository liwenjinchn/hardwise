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
