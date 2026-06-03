# D2a Mainboard Family Selection

## Recommendation

Select **transistor** as the D2 family, with **`L2N7002KLT1G` N-MOS** as the
first D2c implementation target.

This is the smallest high-impact deterministic slice from D1:

- 143 uncovered transistor refdes across only 3 BOM groups.
- 106 of those refdes are one repeated `L2N7002KLT1G` group.
- The representative `PQ10` topology matches the current MOSFET validator shape:
  pin `1=GATE`, `2=SOURCE`, `3=DRAIN`.
- D2b needs only 3 public document-index rows for the whole transistor family.

D2a does not change validation truth. This report only chooses the next slice.

## D1 Inputs Used

```text
/tmp/hardwise-mainboard-d1-next-family.md
/tmp/hardwise-mainboard-d1-document-candidates.csv
/tmp/hardwise-mainboard-d1-auto-index.json
```

## Family Comparison

| Family | Uncovered refdes | Groups | D2b rows | Existing validator fit | D2c risk | D2a decision |
|---|---:|---:|---:|---|---|---|
| `transistor` | 143 | 3 | 3 | `mosfet`, `bjt`; current board groups are MOSFET-like | Low for `L2N7002KLT1G`; medium for other groups | **Select** |
| `diode` | 81 | 10 | 10 | `diode`; several ready profiles already exist | Medium: mixed TVS, LED, small-signal, Schottky roles | Defer |
| `ic` | 150 | 37 | 37 | `buck`, `i2c_mux`, `i2c_level_shift_repeater`, `mcu_basic` | High: broad family mix and many part-specific pinouts | Defer |

The large `unknown` bucket is intentionally deferred. It has more refdes, but
the D1 advisory marks it `triage_for_new_validator`, and most rows are not a
clean existing-validator fit.

## Selected Transistor Groups

| Rank | BOM identity | Refdes | Representative topology | D2a classification |
|---:|---|---:|---|---|
| 1 | `N-MOS管 L2N7002KLT1G SOT23 1.5 LRC` | 106 | `PQ10`: `1/GATE -> N146259293`, `2/SOURCE -> GND`, `3/DRAIN -> PWRGD_R_P12V_GPU0` | Best first target |
| 2 | `N-MOS管 LN2312LT1G 5A SOT– 23 LRC` | 26 | `PQ9`: `D -> N146259293`, `G -> N146259223`, `S -> GND` | Same electrical family, but pin-id contract differs |
| 3 | `P-MOS管 PE537BA PDFN -33 NIKO-SEM` | 11 | `Q13`: parallel source pins `1/2/3`, gate `4`, drain pins `5/6/7/8` | Defer; multi-pin P-MOS package needs care |

## Why `L2N7002KLT1G` First

`L2N7002KLT1G` gives the best ratio of impact to implementation risk:

1. It covers 106 refdes, the largest single non-passive D1 profile gap.
2. It looks like a standard 3-pin N-channel MOSFET in the parsed topology.
3. The existing MOSFET validator already checks gate/drain/source connectivity,
   Vgs, and Vds without assuming source is ground.
4. D2c should be able to add one reviewed public profile and reuse the existing
   `mosfet` validator.

`LN2312LT1G` is not the first target even though a ready profile already exists:
the mainboard symbol uses pin ids `D/G/S`, while the existing profile uses
datasheet package numbers `1/2/3`. Current validator dispatch looks up pins by
profile pin number, so directly applying that profile would miss the local pins.

`PE537BA` is also not first because the representative package exposes multiple
source and drain pins. A correct D2c result would need either a reviewed
multi-pin profile strategy or a careful local-symbol mapping; it is a good
follow-up, not the first slice.

## D2b Input Rows

D2b should backfill public document-index rows for all three transistor groups,
but prioritize `L2N7002KLT1G`.

| Priority | Exact BOM value for current matcher | Public part number to verify | Refdes count | Refdes sample | Suggested search |
|---:|---|---|---:|---|---|
| 1 | `N-MOS管 L2N7002KLT1G SOT23 1.5 LRC` | `L2N7002KLT1G` | 106 | `PQ10, PQ17, PQ27, PQ38, PQ39, PQ40, PQ41, PQ43` | `L2N7002KLT1G LRC datasheet` |
| 2 | `N-MOS管 LN2312LT1G 5A SOT– 23 LRC` | `LN2312LT1G` | 26 | `PQ9, PQ13, PQ14, PQ16, PQ18, PQ19, PQ20, PQ21` | `LN2312LT1G LRC datasheet` |
| 3 | `P-MOS管 PE537BA PDFN -33 NIKO-SEM` | `PE537BA` | 11 | `Q13, Q27, Q57, Q60, Q65, Q66, Q67, Q83` | `PE537BA NIKO-SEM datasheet` |

Current document/profile matching treats the Chinese BOM `名称` as a part-like
value. To match these rows without changing code, D2b document-index entries
should include the exact BOM value in the `Value` field as well as the public
part number in `PartNumber`. Do not use the Chinese BOM `编号` as MPN.

## D2c Boundaries

D2c may:

- add a reviewed public `L2N7002KLT1G` profile if D2b/public evidence supports
  pinout and limits;
- reuse the existing `mosfet` validator;
- add focused profile-candidate or explicit-target tests only if needed to
  prove the selected group can be assigned without fabricating MPNs.

D2c must not:

- validate all transistor rows in one pass;
- add a new MOSFET validator when the existing `mosfet` family is sufficient;
- add Chinese BOM description strings as public profile aliases;
- promote `LN2312LT1G` on this mainboard until the local `D/G/S` pin-id issue is
  handled deliberately;
- infer layout, current, thermal, PLM, supplier, lifecycle, price, or stock.

## Stop Conditions

- Public evidence for `L2N7002KLT1G` cannot verify pinout and absolute limits.
- The selected mainboard symbols do not preserve the expected pin mapping across
  sampled refdes.
- Moving coverage would require treating `编号` as an MPN.
- D2c would need new validator semantics instead of a profile plus current
  `mosfet` checks.
