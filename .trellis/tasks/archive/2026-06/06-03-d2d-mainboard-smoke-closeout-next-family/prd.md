# D2d mainboard smoke closeout and next-family advisory

## Goal

Rerun the public mainboard smoke after D2c, record measured manual/validated coverage movement without changing unrelated verdicts, and generate the next-family advisory for the next deterministic slice.

The product value is to close the D2 loop with auditable evidence: D2b provided
public document coverage, D2c promoted one reviewed profile, and D2d proves the
large-board coverage queue moved by exactly the intended group before any next
profile work starts.

## Confirmed Facts

- D2b mainboard baseline was 8180 components, BOM matched 7248, validated
  6573, manual 1607, PASS/WARN/ERROR 3867/2706/0.
- D2c added only the reviewed `L2N7002KLT1G` MOSFET profile plus the reviewed
  document-MPN profile bridge needed for that public MPN.
- D2c mainboard smoke measured validated 6679 and manual 1501, a movement of
  +106 validated / -106 manual versus D2b.
- The D2c target group is 106 `L2N7002KLT1G` refdes with
  `profile_status=matched`, `validation_status=WARN`, and
  `document_source=doc:mainboard_d2_transistor_docs.csv#line2`.
- `LN2312LT1G` and `PE537BA` remained `profile_status=no_result` in D2c.
- The public-safe Allegro input folder is:
  `/Users/liwenjin/Library/Containers/com.comisys.lanxin.hgo/Data/Library/Application Support/lanxin_macgoh/custom/files/lanxindownload/allegro`.

## Requirements

1. Rerun the real public-safe mainboard smoke with
   `data/document_indexes/mainboard_d2_transistor_docs.csv`.
2. Record the D2d smoke artifact paths for the workbench HTML, grouped Markdown
   index, grouped JSON index, and next-family advisory.
3. Compare D2d measured counts to the D2b baseline and D2c result.
4. Confirm the intended `L2N7002KLT1G` group is still promoted and that
   `LN2312LT1G` / `PE537BA` remain unpromoted.
5. Generate the next-family advisory from the D2d validation index.
6. Update durable notes with the measured closeout and the recommended next
   deterministic slice.
7. Do not add or modify datasheet profiles, validators, document-index rows, or
   workbench behavior as part of D2d.

## Acceptance Criteria

- [x] `design-validator-ui` reruns successfully on the public-safe mainboard
      folder and writes D2d artifacts under `/tmp/`.
- [x] D2d records the D2b-to-D2d movement as validated 6573 -> 6679 and manual
      1607 -> 1501, with no ERROR rows introduced.
- [x] D2d records that `L2N7002KLT1G` accounts for the 106 newly validated rows.
- [x] D2d records that `LN2312LT1G` and `PE537BA` remain outside the D2c/D2d
      promotion.
- [x] `recommend-next-family` emits a D2d next-family advisory from the D2d
      index.
- [x] `docs/learning_log.md` and `docs/interview_qa.md` are updated with
      durable, measured facts.
- [x] `uv run pytest -q`, `uv run ruff check .`, and `git diff --check` pass
      before completion.

## Out Of Scope

- Adding the next datasheet profile or validator slice.
- Promoting `LN2312LT1G`, `PE537BA`, or any other group.
- Changing document matching, profile candidate logic, validator dispatch, or
  verdict semantics.
- Supplier lookup, lifecycle, pricing, availability, PLM, PCB/layout, thermal,
  or simulation claims.

## Stop Conditions

- The mainboard smoke no longer reproduces the D2c measured counts.
- The D2d advisory contradicts the validation index or depends on private
  documents.
- Proving the movement requires changing production behavior.

## Notes

- D2d is a closeout/advisory slice. The next implementation slice should be a
  separate task.
