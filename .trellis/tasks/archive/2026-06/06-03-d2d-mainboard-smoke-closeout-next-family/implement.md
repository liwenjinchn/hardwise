# D2d Implementation Plan

## Checklist

1. Rerun the public-safe mainboard smoke with the D2b transistor document index.
2. Inspect the grouped JSON index:
   - board totals and PASS/WARN/ERROR/manual counts;
   - `L2N7002KLT1G` group evidence and profile status;
   - `LN2312LT1G` / `PE537BA` remain `profile_status=no_result`.
3. Generate the next-family advisory from the D2d JSON index.
4. Record measured D2b -> D2d movement and next recommended slice.
5. Update durable notes:
   - `docs/learning_log.md`;
   - `docs/interview_qa.md`;
   - `docs/rolling_log.md` only if the D2 split note needs closeout wording.
6. Run full gate:

```bash
uv run pytest -q
uv run ruff check .
git diff --check
```

7. Archive and commit D2d.

## Commands

```bash
uv run hardwise design-validator-ui \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/allegro" \
  --document-index data/document_indexes/mainboard_d2_transistor_docs.csv \
  --output /tmp/hardwise-mainboard-d2d-workbench.html \
  --index-output /tmp/hardwise-mainboard-d2d-index.md \
  --index-json /tmp/hardwise-mainboard-d2d-index.json

uv run hardwise recommend-next-family \
  /tmp/hardwise-mainboard-d2d-index.json \
  --output /tmp/hardwise-mainboard-d2d-next-family.md
```

## Stop And Ask

- The D2d smoke no longer reproduces D2c counts.
- Any next-family recommendation requires private or unreviewed evidence.
- Proving the D2c movement requires code changes.

## Execution Notes

Target mainboard smoke:

```text
uv run hardwise design-validator-ui \
  "/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/allegro" \
  --document-index data/document_indexes/mainboard_d2_transistor_docs.csv \
  --output /tmp/hardwise-mainboard-d2d-workbench.html \
  --index-output /tmp/hardwise-mainboard-d2d-index.md \
  --index-json /tmp/hardwise-mainboard-d2d-index.json

document-index: matched=3, no_result=189, ambiguous=0, manual_needed=0
8180 components, validated=6679, BOM matched=7248
PASS/WARN/ERROR=3868/2811/0, manual=1501
```

D2d reproduced D2c and moved exactly one matched profile group versus D2b:

- D2b baseline: validated 6573, manual 1607, PASS/WARN/ERROR 3867/2706/0.
- D2d closeout: validated 6679, manual 1501, PASS/WARN/ERROR 3868/2811/0.
- Per-row D2d `match_status`: `generic_passive=6573`, `matched=106`,
  `manual_needed=932`, `no_result=569`.
- `L2N7002KLT1G`: 106 refdes, `profile_status=matched`,
  `validation_status=WARN`,
  `document_source=doc:mainboard_d2_transistor_docs.csv#line2`.
- `LN2312LT1G`: 26 refdes, `profile_status=no_result`,
  `document_source=doc:mainboard_d2_transistor_docs.csv#line3`.
- `PE537BA`: 11 refdes, `profile_status=no_result`,
  `document_source=doc:mainboard_d2_transistor_docs.csv#line4`.

Next-family advisory:

```text
uv run hardwise recommend-next-family \
  /tmp/hardwise-mainboard-d2d-index.json \
  --output /tmp/hardwise-mainboard-d2d-next-family.md

families=6, try_existing=3, triage_new=3
covered refdes skipped=106
unknown=1118, ic=141, diode=81, transistor=37, inductor=41, ferrite=43
```

Generated an IC-scoped candidate CSV for the next evidence-backfill task:

```text
uv run hardwise build-document-index-candidates \
  /tmp/hardwise-mainboard-d2d-index.json \
  --family ic \
  --output /tmp/hardwise-mainboard-d2d-ic-document-candidates.csv

groups=195, candidates=37, families=ic
```

Largest IC candidates: `74LVC1G125GW` (24 refdes), `MP87000-MGMJTH` (22),
`MP5991GLU` (12), and `PCA9617ADP` (10). This is advisory evidence only; D2d
does not implement IC validation.

Quality gate:

```text
uv run pytest -q
491 passed, 7 deselected

uv run ruff check .
All checks passed!

git diff --check
clean
```
