from datetime import date

import pytest

from excel_visualization_pipeline.date_ranges import (
    aggregation_period_ranges,
    month_ranges,
    recent_data_range,
    week_ranges,
)


def test_recent_range_uses_last_ten_distinct_data_dates():
    dates = [date(2026, 1, day) for day in range(1, 16)] + [date(2026, 1, 15)]

    selected = recent_data_range(dates)

    assert selected.start == date(2026, 1, 6)
    assert selected.end == date(2026, 1, 15)
    assert selected.data_date_count == 10


def test_week_ranges_use_iso_week_boundaries_and_latest_first():
    ranges = week_ranges([date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 7)])

    assert ranges[0].start == date(2026, 1, 5)
    assert ranges[0].end == date(2026, 1, 11)
    assert ranges[0].data_date_count == 2
    assert ranges[1].start == date(2025, 12, 29)


def test_month_ranges_use_full_calendar_month_and_latest_first():
    ranges = month_ranges([date(2026, 1, 31), date(2026, 2, 1), date(2026, 2, 20)])

    assert ranges[0].label == "Tháng 02/2026"
    assert ranges[0].start == date(2026, 2, 1)
    assert ranges[0].end == date(2026, 2, 28)
    assert ranges[0].data_date_count == 2


def test_recent_range_rejects_empty_dates():
    with pytest.raises(ValueError, match="ít nhất một ngày"):
        recent_data_range([])


def test_aggregation_period_ranges_marks_boundary_months_incomplete():
    ranges = aggregation_period_ranges(
        [date(2026, 8, 1), date(2026, 8, 31), date(2026, 9, 10)],
        "month",
    )

    assert [value.label for value in ranges] == ["Tháng 08/2026", "Tháng 09/2026"]
    assert ranges[0].is_complete is True
    assert ranges[1].is_complete is False


def test_aggregation_period_ranges_supports_quarters():
    ranges = aggregation_period_ranges(
        [date(2026, 7, 1), date(2026, 9, 30), date(2026, 10, 1)],
        "quarter",
    )

    assert ranges[0].label == "Quý 3/2026"
    assert ranges[0].start == date(2026, 7, 1)
    assert ranges[0].end == date(2026, 9, 30)
    assert ranges[0].is_complete is True
    assert ranges[1].is_complete is False


def test_aggregation_period_ranges_rejects_unknown_group():
    with pytest.raises(ValueError, match="Unsupported aggregation period"):
        aggregation_period_ranges([date(2026, 8, 1)], "year")
