from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable


@dataclass(frozen=True)
class DateRange:
    label: str
    start: date
    end: date
    data_date_count: int
    is_complete: bool = True


def _normalized_dates(values: Iterable[date]) -> list[date]:
    return sorted({value for value in values})


def recent_data_range(values: Iterable[date], count: int = 10) -> DateRange:
    dates = _normalized_dates(values)
    if not dates:
        raise ValueError("Cần ít nhất một ngày dữ liệu.")
    if count < 1:
        raise ValueError("Số ngày gần nhất phải lớn hơn 0.")
    selected = dates[-count:]
    return DateRange(
        label=f"{len(selected)} ngày dữ liệu gần nhất",
        start=selected[0],
        end=selected[-1],
        data_date_count=len(selected),
    )


def week_ranges(values: Iterable[date]) -> list[DateRange]:
    dates = _normalized_dates(values)
    grouped: dict[tuple[int, int], list[date]] = {}
    for value in dates:
        iso = value.isocalendar()
        grouped.setdefault((iso.year, iso.week), []).append(value)

    ranges: list[DateRange] = []
    for (year, week), data_dates in grouped.items():
        start = date.fromisocalendar(year, week, 1)
        end = start + timedelta(days=6)
        ranges.append(
            DateRange(
                label=f"Tuần {week:02d}/{year} ({start:%d/%m}–{end:%d/%m})",
                start=start,
                end=end,
                data_date_count=len(data_dates),
            )
        )
    return sorted(ranges, key=lambda value: value.start, reverse=True)


def month_ranges(values: Iterable[date]) -> list[DateRange]:
    dates = _normalized_dates(values)
    grouped: dict[tuple[int, int], list[date]] = {}
    for value in dates:
        grouped.setdefault((value.year, value.month), []).append(value)

    ranges: list[DateRange] = []
    for (year, month), data_dates in grouped.items():
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        ranges.append(
            DateRange(
                label=f"Tháng {month:02d}/{year}",
                start=start,
                end=end,
                data_date_count=len(data_dates),
            )
        )
    return sorted(ranges, key=lambda value: value.start, reverse=True)


def aggregation_period_ranges(values: Iterable[date], group_by: str) -> list[DateRange]:
    """Return available calendar periods in chronological order.

    A period is complete only when its natural calendar boundaries are contained
    in the available data window. This describes coverage, not whether every day
    has a numeric value; blank cells are still valid daily observations.
    """
    dates = _normalized_dates(values)
    if not dates:
        return []
    if group_by not in {"day", "week", "month", "quarter"}:
        raise ValueError(f"Unsupported aggregation period: {group_by}")

    grouped: dict[date, list[date]] = {}
    for value in dates:
        if group_by == "day":
            start = value
        elif group_by == "week":
            start = value - timedelta(days=value.weekday())
        elif group_by == "month":
            start = date(value.year, value.month, 1)
        else:
            quarter_month = ((value.month - 1) // 3) * 3 + 1
            start = date(value.year, quarter_month, 1)
        grouped.setdefault(start, []).append(value)

    data_start, data_end = dates[0], dates[-1]
    ranges: list[DateRange] = []
    for start, data_dates in grouped.items():
        if group_by == "day":
            end = start
            label = f"{start:%d/%m/%Y}"
        elif group_by == "week":
            end = start + timedelta(days=6)
            iso = start.isocalendar()
            label = f"Tuần {iso.week:02d}/{iso.year} ({start:%d/%m}–{end:%d/%m})"
        elif group_by == "month":
            end = date(start.year, start.month, monthrange(start.year, start.month)[1])
            label = f"Tháng {start:%m/%Y}"
        else:
            quarter = (start.month - 1) // 3 + 1
            end_month = start.month + 2
            end = date(start.year, end_month, monthrange(start.year, end_month)[1])
            label = f"Quý {quarter}/{start.year}"

        ranges.append(
            DateRange(
                label=label,
                start=start,
                end=end,
                data_date_count=len(data_dates),
                is_complete=start >= data_start and end <= data_end,
            )
        )
    return sorted(ranges, key=lambda value: value.start)
