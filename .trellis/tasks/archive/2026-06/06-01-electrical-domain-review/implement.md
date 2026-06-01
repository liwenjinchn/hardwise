# Electrical Domain Review Execution Plan

## Checklist

1. Inspect project specs and scope docs for stated validation boundaries.
2. Inventory all validation modules and tests that encode electrical semantics.
3. Review generic helpers for voltage inference, ground recognition, pin
   category handling, and status severity.
4. Review each family validator for professional correctness and overclaiming.
5. Review report/UI wording for unsupported implications.
6. Run targeted validation tests if code behavior needs confirmation.
7. Produce a findings-first audit; do not edit production code unless a
   follow-up remediation task is approved.

## Validation Commands

- `uv run pytest tests/validation -q`
- `uv run pytest tests/report/test_component_validation_markdown.py tests/report/test_validator_ui.py -q`
- `uv run ruff check src/hardwise/validation src/hardwise/report`

## Stop-and-Ask Conditions

- A potential finding depends on non-public/private hardware material.
- A fix would require expanding Hardwise beyond pre-layout schematic review.
- The audit discovers a broad architectural rewrite rather than a bounded
  correctness fix.

