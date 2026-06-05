# Evidence Chain Audit

> First audit: 2026-05-31. Re-audited 2026-06-05 after the d3a/d3b validator
> migration merged to `main` (profile count grew from the C4 set to 25).
>
> Purpose: separate what is proven by live ingest/retrieve/agent citation from
> what is a reviewed structured profile token.

## Summary

Hardwise currently has one fully smoke-tested datasheet retrieval chain:

```text
data/datasheets/l78.pdf
  -> ingest/pdf.py
  -> store/vector.py (Chroma, 157 chunks)
  -> query-datasheet / search_datasheet
  -> agent answer citing l78.pdf p4
```

Most other `datasheet:<part>.pdf#pN` references in structured profiles are
reviewed profile tokens. They are useful L1 deterministic validator evidence,
but they should not be described as live Chroma retrieval unless the matching
public PDF has been staged and queried.

## Smoke Commands

```bash
rm -rf /tmp/hardwise-evidence-audit

uv run hardwise ingest-datasheet \
  data/datasheets/l78.pdf \
  --part-ref L7805 \
  --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise query-datasheet \
  "absolute maximum input voltage" \
  --top-k 3 \
  --persist-dir /tmp/hardwise-evidence-audit

uv run hardwise ask \
  data/projects/pic_programmer \
  "请先用 search_datasheet 查询 L7805 absolute maximum input voltage，再回答 U3 的 Vin absolute maximum 来自哪一页；如果没有检索证据就明确说没有。" \
  --vector \
  --persist-dir /tmp/hardwise-evidence-audit \
  --max-iterations 4 \
  --trace
```

## Observed Output

`ingest-datasheet` created 157 chunks for `part_ref=L7805`.

`query-datasheet` returned this top hit:

```text
1. [l78.pdf p4 part=L7805] L78 Maximum ratings ... Absolute maximum ratings ... 35...
```

`hardwise ask --vector` made two tool calls:

```text
1. search_datasheet({"part_ref": "L7805", "query": "L7805 absolute maximum input voltage", "top_k": 5}) -> hits=5
2. get_component({"refdes": "U3"}) -> status=found
```

The final answer cited `l78.pdf` page 4 and reported the 35 V absolute-maximum
input-voltage fact. This proves that the agent can cite retrieved datasheet
evidence when a vector collection is configured.

The trace also reported `unverified refdes wrapped: 4`, because part-number-like
strings such as `L78` and `L7805` match the conservative refdes regex. The board
object `U3` remained registry-verified; the wrap is a known display-layer
trade-off for part numbers, not a failure of datasheet retrieval.

## Evidence Classes

| Evidence class | Example | Current status | Narrative rule |
|---|---|---|---|
| Live retrieved evidence | `[l78.pdf p4 part=L7805]` from `search_datasheet` | Proven by the smoke above | Safe to describe as `ingest -> retrieve -> agent citation` |
| Reviewed profile token | `datasheet:l78.pdf#p4` in `l78.json` | Reviewed structured profile fact | Safe to describe as L1 profile evidence; mention Chroma retrieval only when separately smoked |
| Reviewed profile token without local PDF | `datasheet:mpq8626.pdf#p1`, `datasheet:bas316.pdf#p2`, `datasheet:stm32g030.pdf#p33` (full list in the profile ledger) | Profile evidence only in this repo state | Do not imply live retrieval; call it reviewed public profile evidence |
| Coverage/ranking artifact | C3/C4 `recommend-next-family` rows | Planning support | Use as supporting material, not the headline AI claim |

## Current Local PDF Inventory

Only `data/datasheets/l78.pdf` is staged locally (gitignored). No committed or
local Chroma store exists (`data/chroma/` is absent and gitignored); the L78
smoke ingests into a throwaway `--persist-dir`. Every other profile cites a
public datasheet token whose PDF is not present under `data/datasheets/` and has
not been ingested into a Chroma store.

## Full Profile Ledger (re-audited 2026-06-05, 25 profiles, all `review_status: ready`)

One profile is real-PDF-backed; the rest are reviewed public profile evidence.

| Class | Count | Profiles |
|---|---|---|
| **Real-PDF-backed** (PDF on disk + live retrieval smoked) | 1 | `l78.json` (`l78.pdf` p3/p4/p6) |
| **Reviewed token, no local PDF** (`datasheet:<file>.pdf#pN`, PDF absent) | 22 | `2n3904`, `74lv165`, `bas316`, `connector_2x5`, `eg2132`, `ina180a1`, `irf540n`, `l2n7002klt1g`, `lm393`, `lmv358`, `ln2312lt1g`, `mmbt3904`, `mpq8626`, `pca9548a`, `pca9617a`, `sd103aws_7_f`, `sm340af`, `smbj24ca`, `ss34`, `stm32g030c8t6`, `tlv9062`, `xl1509` |
| **Non-PDF scheme** (synthetic by construction) | 2 | `1_5smc15a` (`datasheet:..._product_page#...`), `ltst-c190kgkt` (`public_profile:...#...`) |

The 22 reviewed-token profiles use the **same** `datasheet:<file>#pN` string shape
that `ingest/pdf.py:evidence_token()` emits for live-retrieved chunks. That shared
shape is the over-claim hazard: a token shown without its evidence class can read
as live retrieval. Only L78 has been smoked end-to-end. The d3a/d3b families added
since the first audit (`mpq8626`, `pca9548a`, `pca9617a`, `ln2312lt1g`,
`l2n7002klt1g`, `sd103aws_7_f`, `sm340af`, `74lv165`, `1_5smc15a`, …) are reviewed
public profile evidence, not live retrieval — the same rule as the original C4 set.

## Implication for Narrative

Lead with the trust architecture:

```text
Refdes Guard + Evidence Ledger + L1 deterministic validators + structured tools
```

Then use the coverage loop as supporting proof:

```text
C3 ranking -> C4 family slices -> manual rows become deterministic rows
```

Do not lead with coverage counts alone, and do not say every profile token came
from live retrieval. The honest strongest claim is:

> L78 has a full ingest/retrieve/agent-citation smoke; the other 24 profiles
> (C4 families plus the d3a/d3b additions) are reviewed public profile evidence
> that feed deterministic validators.
