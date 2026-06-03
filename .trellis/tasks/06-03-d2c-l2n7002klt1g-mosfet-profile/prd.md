# D2c L2N7002KLT1G MOSFET profile

## Goal

Add one reviewed, public-source-backed datasheet profile for `L2N7002KLT1G`
so the existing `mosfet` validator can validate the D2a-selected mainboard
transistor group without adding a new validator or broadening document matching.

The product value is to move the largest low-risk D1 profile gap from manual
coverage to deterministic L1 schematic validation while preserving the
distinction between document coverage and electrical validation.

## Confirmed Facts

- D2a selected `transistor` as the next family and `L2N7002KLT1G` as the first
  D2c target.
- D2a counted 106 refdes in the selected group, represented by `PQ10`, with
  expected local pin mapping `1=Gate`, `2=Source`, `3=Drain`.
- D2b added reusable document coverage for the same group in
  `data/document_indexes/mainboard_d2_transistor_docs.csv`.
- The D2b index row matches the mainboard group by reviewed document identity,
  not by family alone:
  `doc:mainboard_d2_transistor_docs.csv#line2`.
- The official public LRC PDF at
  `https://www.lrc.cn/Upload/PDF/Product/MOS/L2N7002KLT1G.pdf` states:
  `L2N7002KLT1G`, 380 mA, 60 V N-channel SOT-23; pinout
  `1 Gate`, `2 Source`, `3 Drain`; maximum ratings include `VDSS 60 V`,
  `VGS +/-20 V`, steady-state `ID 320 mA` at 25 C, and pulsed `IDM 1.5 A`.
- Existing `src/hardwise/validation/mosfet.py` already validates MOSFET
  gate/drain/source connectivity plus Vgs/Vds through
  `recommended.topology_family = "mosfet"`.
- Existing profile matching ignores `needs_review` drafts and matches only
  ready profiles by `part_number` or `part_number_aliases`.

## Requirements

1. Add a ready `L2N7002KLT1G` profile under `data/datasheet_profiles/`.
2. The profile must use `recommended.topology_family = "mosfet"` and the
   reviewed package pin mapping `1=Gate`, `2=Source`, `3=Drain`.
3. The profile must carry public source tokens for pinout and limits using the
   existing profile evidence style, e.g. `datasheet:l2n7002klt1g.pdf#p1`.
4. The profile must be reusable across projects by public MPN and safe aliases
   such as reel/order variants from the same datasheet. It must not use the
   Chinese BOM `名称`, `编号`, source line, or refdes as profile aliases.
5. Existing MOSFET validator dispatch must remain family-based. Do not add an
   `L2N7002KLT1G` part-number branch.
6. D2c must prove that the profile matches the D2b/mainboard identity and that
   `LN2312LT1G` / `PE537BA` remain outside this promotion.
7. D2c must not introduce live supplier lookup, lifecycle, price, availability,
   PLM, layout, current-flow, thermal, or PCB geometry claims.

## Acceptance Criteria

- [ ] `data/datasheet_profiles/l2n7002klt1g.json` loads as a valid
      `DatasheetProfile` with `review_status = "ready"`.
- [ ] A focused MOSFET profile test verifies the public pinout, abs-max Vds/Vgs,
      and family dispatch for `L2N7002KLT1G`.
- [ ] A profile-candidate test proves a BOM MPN of `L2N7002KLT1G` matches the
      new profile.
- [ ] A mainboard smoke with `design-validator-ui <mainboard-folder>
      --document-index data/document_indexes/mainboard_d2_transistor_docs.csv`
      shows the selected `L2N7002KLT1G` group matched to the new profile and no
      longer present as a profile gap.
- [ ] The same smoke does not promote `LN2312LT1G` or `PE537BA` as part of D2c.
- [ ] Validation artifacts keep raw profile/document evidence visible; document
      source remains `doc:mainboard_d2_transistor_docs.csv#line2`.
- [ ] Focused tests, `uv run pytest -q`, `uv run ruff check .`, and
      `git diff --check` pass before completion.

## Out Of Scope

- Adding a new MOSFET validator or changing existing MOSFET validation
  semantics.
- Promoting `LN2312LT1G`, because the mainboard local symbol uses `D/G/S`
  pin IDs while the ready profile uses package numbers `1/2/3`.
- Promoting `PE537BA`, because its multi-pin P-MOS package needs a separate
  reviewed strategy.
- Treating same-family membership as datasheet/profile evidence.
- Treating Chinese BOM `编号` as MPN.
- Supplier, lifecycle, pricing, stock, PLM, PCB layout, or thermal analysis.

## Stop Conditions

- Public evidence cannot support pinout or the Vds/Vgs limits.
- Sampled mainboard components in the selected group do not consistently use
  package pins `1/2/3` for gate/source/drain.
- Moving coverage would require adding the BOM value text as a profile alias.
- Implementation discovers that the existing `mosfet` validator is insufficient
  for this part.

## Notes

- Public PDF checked during planning:
  `https://www.lrc.cn/Upload/PDF/Product/MOS/L2N7002KLT1G.pdf`.
