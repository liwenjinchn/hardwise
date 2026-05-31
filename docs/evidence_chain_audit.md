# Evidence Chain Audit

> Date: 2026-05-31
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
| Reviewed profile token without local PDF | `datasheet:bas316.pdf#p2`, `datasheet:smbj24ca...#pN`, `datasheet:mmbt3904...#p1` | Profile evidence only in this repo state | Do not imply live retrieval; call it reviewed public profile evidence |
| Coverage/ranking artifact | C3/C4 `recommend-next-family` rows | Planning support | Use as supporting material, not the headline AI claim |

## Current Local PDF Inventory

Only `data/datasheets/l78.pdf` is staged locally. The C4 family profiles cite
public datasheet tokens, but their PDFs are not currently present under
`data/datasheets/` or ingested into a committed/local Chroma store.

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

> L78 has a full ingest/retrieve/agent-citation smoke; C4 profiles are reviewed
> public profile evidence that feed deterministic validators.
