"""Unknown and inapplicable work must remain distinct from evaluated passes."""

import pytest

from hardwise.validation.types import ComponentValidation, ValidationReport, VALIDATION_STATUSES


def _report(*statuses):
    return ValidationReport(
        refdes="U1",
        component_value="Fixture",
        profile_part_number="Fixture",
        component_checks=[
            ComponentValidation(
                check=f"check_{i}", status=status, summary="Public synthetic fixture"
            )
            for i, status in enumerate(statuses)
        ],
    )


@pytest.mark.parametrize(
    "statuses,expected",
    [
        ((), "UNKNOWN"),
        (("PASS", "UNKNOWN"), "UNKNOWN"),
        (("NOT_APPLICABLE",), "NOT_APPLICABLE"),
        (("PASS", "NOT_APPLICABLE"), "PASS"),
        (("WARN", "UNKNOWN"), "WARN"),
        (("ERROR", "UNKNOWN"), "ERROR"),
    ],
)
def test_report_rollup_never_turns_missing_work_into_pass(statuses, expected):
    report = _report(*statuses)
    assert report.status == expected
    assert sum(report.component_counts_by_status.values()) == len(statuses)
    assert set(report.component_counts_by_status) == set(VALIDATION_STATUSES)


def test_unknown_roundtrip_keeps_check_and_count():
    report = _report("PASS", "UNKNOWN", "NOT_APPLICABLE")
    restored = ValidationReport.model_validate_json(report.model_dump_json())
    assert restored.status == "UNKNOWN"
    assert restored.component_counts_by_status["PASS"] == 1
    assert restored.component_counts_by_status["UNKNOWN"] == 1
    assert restored.component_counts_by_status["NOT_APPLICABLE"] == 1


def test_legacy_warn_is_not_reinterpreted_as_unknown_or_fail():
    report = _report("WARN")
    restored = ValidationReport.model_validate_json(report.model_dump_json())
    assert restored.status == "WARN"
    assert restored.component_counts_by_status["UNKNOWN"] == 0
