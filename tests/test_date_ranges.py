from datetime import date

import pytest

from excel_visualization_pipeline.date_ranges import (
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
