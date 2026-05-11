"""Hardwise memory subsystem — Sleep Consolidator + candidate-rule pool.

Mechanism #3 of the five mechanisms (see CLAUDE.md). Slice 2 ships the
deterministic statistical aggregator: same-rule, same-severity findings
exceeding a threshold get distilled into a `STATUS: candidate` entry in
`memory/rules.md` for human review. The human gate is non-negotiable —
candidates never auto-promote to active rules.
"""
