# Public Evidence Pack Pilot

## Outcome

The pilot pins three high-risk public manufacturer datasheets and materializes
their reviewed local filenames without committing the copyrighted PDF bytes.
It improves the mixed-controller sign-off evidence gate, but does not clear the
whole-project gate, so new power/reset/clock rule work remains deferred.

## Selected sources

| Part | Official document | Reviewed revision | SHA256 |
|---|---|---|---|
| XL1509-12E1 | `https://www.xlsemi.com/datasheet/XL1509-EN.pdf` | XL1509 Rev 2.6 | `d0226589787aa1ec629f0a1365aec4e017799ae79594891fa48f7733b4c1ebc2` |
| STM32G030C8T6 | `https://www.st.com/resource/en/datasheet/stm32g030c8.pdf` | DS12991 Rev 6 | `b86b1fa79171e8ed521745305bff03d43d75f07729c077e0c4e7badc896711d3` |
| EG2132 | `https://www.egmicro.com/static/doc/.../EG2132%20...pdf` | EG2132 V1.1 | `0142afa83dc1ca4b36000728a76f687647139a790fc0aeb1abc95a9ef8c14e00` |

The full percent-encoded EGmicro URL is kept in the CSV manifest. Its official
product landing page is `https://egmicro.com/products/detail/?name=EG2132`.
The site marks the document all-rights-reserved, so Hardwise records the URL,
revision, and hash while leaving the downloaded PDF in the gitignored local
cache.

## Reproduction

```bash
uv run hardwise fetch-approved-documents \
  data/document_indexes/high_risk_evidence_pilot.csv \
  --cache-dir data/datasheets/cache \
  --metadata data/datasheets/documents.jsonl
```

Measured on 2026-07-13: `fetched=3`, `skipped=0`; all three local aliases matched
their pinned hashes. The fetcher rejects a changed vendor file as
`sha256_mismatch`, removes a pre-existing alias when it fails the pinned hash,
and rejects absolute or parent-traversing `LocalPath` values.

## Sign-off gate delta

| State | Affected L1 tasks | Missing local evidence tokens | Gate |
|---|---:|---:|---|
| Isolated fresh checkout, before pilot fetch | 16 | 11 | blocked |
| Isolated checkout, after three-source pilot fetch | 11 | 7 | blocked |

The controlled comparison improves by five L1 tasks and four page-level tokens.
All three selected devices contribute to the gate delta. Electrical
PASS/WARN/ERROR remains unchanged.

## Rule-expansion decision

Defer new power/reset/clock validators. The acceptance gate was explicit:
evidence readiness must move to `ready` before adding another rule family. The
pilot proves the fetch/hash/local-source mechanism and reduces the backlog, but
seven cited tokens still block an isolated whole-project handoff. The smallest next step is
another bounded evidence pack for the exact remaining official sources, not a
new electrical rule.
