"""Tests for document-index candidate CSV generation."""

from __future__ import annotations

from hardwise.documents.candidates import _looks_like_passive_identity


def test_candidate_filter_recognizes_passive_values_with_ratings() -> None:
    assert _looks_like_passive_identity("470uF 2.5V 20%")
    assert _looks_like_passive_identity("6.8uH")
    assert _looks_like_passive_identity("10K")
    assert not _looks_like_passive_identity("PCA9617ADP")
    assert not _looks_like_passive_identity("MP5991")
