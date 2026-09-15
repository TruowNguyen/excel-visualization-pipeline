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
