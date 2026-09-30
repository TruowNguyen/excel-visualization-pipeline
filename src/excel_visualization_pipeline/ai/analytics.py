from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any

import pandas as pd


METRICS = {
    "total": {"label": "Tổng số", "kind": "count"},
    "error": {"label": "Báo sai/Lỗi", "kind": "count"},
    "error_rate": {"label": "% báo sai", "kind": "percentage"},
}
GROUPS = {"day", "week", "month"}


def _display(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    if unit in {"percent", "percentage_point"}:
        suffix = "%" if unit == "percent" else " pp"
        return f"{value:.2f}".rstrip("0").rstrip(".") + suffix
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _direction(delta: float) -> str:
    if math.isclose(delta, 0.0, abs_tol=1e-12):
        return "unchanged"
    return "increasing" if delta > 0 else "decreasing"


def _period_start(value: pd.Timestamp, group_by: str) -> pd.Timestamp:
    value = value.normalize()
    if group_by == "day":
        return value
    if group_by == "week":
        return value - pd.Timedelta(days=value.weekday())
    return value.replace(day=1)


def _natural_period_end(value: pd.Timestamp, group_by: str) -> pd.Timestamp:
    if group_by == "day":
        return value
    if group_by == "week":
        return value + pd.Timedelta(days=6)
    return value + pd.offsets.MonthEnd(0)


def _period_label(start: date, end: date, group_by: str) -> str:
    if group_by == "day":
        return start.strftime("%d/%m/%Y")
    if group_by == "month" and start.day == 1:
        return start.strftime("%m/%Y")
    return f"{start:%d/%m}–{end:%d/%m/%Y}"


@dataclass(frozen=True)
class TrendPoint:
    period_start: date
    period_end: date
    period_label: str
    value: float
    rows: pd.DataFrame
    observed_day_count: int
    expected_day_count: int
    evidence_id: str
    inferred_zero: bool = False

    @property
    def observed_date(self) -> date:
        """Compatibility alias for callers that previously handled daily points only."""
        return self.period_start


@dataclass(frozen=True)
class TrendComputation:
    status: str
    metric_code: str
    metric_display_name: str
    metric_kind: str
    unit: str
    aggregation_rule: str
    group_by: str
    window_start: date
    window_end: date
    points: tuple[TrendPoint, ...]
    previous: TrendPoint | None
    current: TrendPoint | None
    facts: tuple[dict[str, Any], ...]
    series: tuple[dict[str, Any], ...]
    quality: dict[str, Any]


class TrendStrategy:
    """Versioned deterministic period-over-period trend calculation."""

    policy_version = "period-series-v2"
    max_periods = 60

    def compute(
        self,
        data: pd.DataFrame,
        *,
        entity_ref: str,
        metric_code: str,
        start: date,
        end: date,
        group_by: str = "day",
    ) -> TrendComputation:
        if metric_code not in METRICS:
            raise ValueError("Chỉ số chỉ hỗ trợ Tổng số, Báo sai/Lỗi hoặc % báo sai.")
        if group_by not in GROUPS:
            raise ValueError("Cách nhóm dữ liệu chỉ hỗ trợ theo ngày, tuần hoặc tháng.")
        if start > end:
            raise ValueError("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
        calendar = pd.date_range(start, end, freq="D")
        expected_periods = len({_period_start(value, group_by) for value in calendar})
        if expected_periods > self.max_periods:
            raise ValueError(
                f"Khoảng đã chọn tạo {expected_periods} kỳ; tối đa {self.max_periods}. Hãy chọn mức thời gian lớn hơn hoặc thu hẹp khoảng."
            )

        scoped = data[data["entity_id"].eq(entity_ref)].copy()
        if scoped.empty:
            raise ValueError("Nội dung theo dõi không có dữ liệu đã ghi nhận trong dự án.")
        scoped["date"] = pd.to_datetime(scoped["date"]).dt.normalize()
        scoped = scoped[
            scoped["date"].ge(pd.Timestamp(start)) & scoped["date"].le(pd.Timestamp(end))
        ]
        unit_values = scoped.get("effective_unit", pd.Series(dtype=object)).dropna().unique()
        count_unit = str(unit_values[0]) if len(unit_values) else "giá trị"
        metric = METRICS[metric_code]
        unit = "percent" if metric_code == "error_rate" else count_unit
        scoped["period_start"] = scoped["date"].map(lambda value: _period_start(value, group_by))
        points: list[TrendPoint] = []
        for index, (natural_start, rows) in enumerate(scoped.groupby("period_start", sort=True)):
            calculated = self._point(rows, metric_code)
            if calculated is None:
                continue
            value, evidence_rows, inferred_zero = calculated
            period_start = max(natural_start.date(), start)
            period_end = min(_natural_period_end(natural_start, group_by).date(), end)
            eligible = evidence_rows["chart_value"].notna()
            if "ai_included" in evidence_rows:
                eligible &= evidence_rows["ai_included"].fillna(False).astype(bool)
            observed_days = int(pd.to_datetime(
                evidence_rows.loc[eligible, "date"]
            ).dt.date.nunique())
            expected_days = (period_end - period_start).days + 1
            points.append(TrendPoint(
                period_start=period_start,
                period_end=period_end,
                period_label=_period_label(period_start, period_end, group_by),
                value=value,
                rows=evidence_rows.drop(columns=["period_start"], errors="ignore"),
                observed_day_count=observed_days,
                expected_day_count=expected_days,
                evidence_id=f"ev-period-{index:03d}",
                inferred_zero=inferred_zero,
            ))

        total_days = (end - start).days + 1
        observed_days = len({
            observed
            for point in points
            for observed in pd.to_datetime(point.rows.loc[point.rows["chart_value"].notna(), "date"]).dt.date
        })
        quality: dict[str, Any] = {
            "status": "valid" if len(points) >= 2 else "insufficient_data",
            "validPointCount": len(points),
            "validPeriodCount": len(points),
            "expectedPeriodCount": expected_periods,
            "observedInputDayCount": observed_days,
            "expectedCalendarDayCount": total_days,
            "coverageRatio": round(len(points) / expected_periods, 4) if expected_periods else 0,
            "dayCoverageRatio": round(observed_days / total_days, 4) if total_days else 0,
            "comparisonBasis": "period_over_period_and_first_last",
            "groupBy": group_by,
            "policyVersion": self.policy_version,
            "limitations": [],
        }
        if len(points) < expected_periods:
            quality["limitations"].append(
                "Có kỳ không tạo được giá trị hợp lệ; thay đổi chỉ so với kỳ dữ liệu hợp lệ trước đó và kỳ thiếu không được coi là 0."
            )
        if any(point.observed_day_count < point.expected_day_count for point in points):
            quality["limitations"].append(
                "Một hoặc nhiều kỳ chỉ có dữ liệu hợp lệ cho một phần số ngày; độ bao phủ từng kỳ được hiển thị cùng kết quả."
            )

        facts, series = self._series(points, metric_code, unit, quality)
        facts.append(self._fact(
            "fact-period-count", "period_count", float(len(points)), "period",
            [point.evidence_id for point in points],
        ))
        if len(points) < 2:
            quality["limitations"].append(
                "Cần ít nhất hai kỳ hợp lệ để tính thay đổi và xu hướng."
            )
            return TrendComputation(
                "insufficient_data", metric_code, metric["label"], metric["kind"], unit,
                self._aggregation_rule(metric_code, group_by), group_by, start, end,
                tuple(points), None, points[0] if points else None,
                tuple(facts), tuple(series), quality,
            )

        previous, current = points[0], points[-1]
        overall_delta = current.value - previous.value
        overall_direction = _direction(overall_delta)
        overall_relative = None if math.isclose(previous.value, 0.0, abs_tol=1e-12) else (
            overall_delta / abs(previous.value) * 100
        )
        delta_unit = "percentage_point" if metric_code == "error_rate" else unit
        overall_evidence = [previous.evidence_id, current.evidence_id]
        facts.extend([
            self._fact("fact-previous", "previous", previous.value, unit, [previous.evidence_id]),
            self._fact("fact-current", "current", current.value, unit, [current.evidence_id]),
            self._fact("fact-delta", "absolute_change", overall_delta, delta_unit, overall_evidence),
            self._enum_fact("fact-direction", "direction", overall_direction, overall_evidence),
        ])
        if overall_relative is not None:
            facts.append(self._fact(
                "fact-relative-change", "relative_change", overall_relative, "percent", overall_evidence,
            ))
        else:
            quality["limitations"].append(
                "Kỳ đầu bằng 0 nên không tính phần trăm thay đổi toàn khoảng."
            )
        pattern = self._pattern([item["change"]["direction"] for item in series if item["change"]])
        facts.append(self._enum_fact(
            "fact-trend-pattern", "trend_pattern", pattern,
            [point.evidence_id for point in points],
        ))
        return TrendComputation(
            "ready", metric_code, metric["label"], metric["kind"], unit,
            self._aggregation_rule(metric_code, group_by), group_by, start, end,
            tuple(points), previous, current, tuple(facts), tuple(series), quality,
        )

    def _series(
        self,
        points: list[TrendPoint],
        metric_code: str,
        unit: str,
        quality: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        facts: list[dict[str, Any]] = []
        series: list[dict[str, Any]] = []
        delta_unit = "percentage_point" if metric_code == "error_rate" else unit
        for index, point in enumerate(points):
            period_fact_id = f"fact-period-{index:03d}"
            facts.append(self._fact(
                period_fact_id, "period_value", point.value, unit, [point.evidence_id]
            ))
            change = None
            if index:
                prior = points[index - 1]
                delta = point.value - prior.value
                relative = None if math.isclose(prior.value, 0.0, abs_tol=1e-12) else (
                    delta / abs(prior.value) * 100
                )
                direction = _direction(delta)
                evidence_ids = [prior.evidence_id, point.evidence_id]
                absolute_fact_id = f"fact-change-{index:03d}"
                direction_fact_id = f"fact-change-direction-{index:03d}"
                facts.extend([
                    self._fact(absolute_fact_id, "period_change", delta, delta_unit, evidence_ids),
                    self._enum_fact(direction_fact_id, "period_direction", direction, evidence_ids),
                ])
                relative_fact_id = None
                if relative is not None:
                    relative_fact_id = f"fact-change-relative-{index:03d}"
                    facts.append(self._fact(
                        relative_fact_id, "period_relative_change", relative, "percent", evidence_ids
                    ))
                else:
                    quality["limitations"].append(
                        f"Kỳ {prior.period_label} bằng 0 nên không tính phần trăm thay đổi sang kỳ {point.period_label}."
                    )
                change = {
                    "fromPeriodStart": prior.period_start.isoformat(),
                    "absolute": round(delta, 8),
                    "absoluteDisplay": _display(delta, delta_unit),
                    "relativePercent": round(relative, 8) if relative is not None else None,
                    "relativeDisplay": _display(relative, "percent"),
                    "direction": direction,
                    "factIds": [
                        absolute_fact_id,
                        *([relative_fact_id] if relative_fact_id else []),
                        direction_fact_id,
                    ],
                }
            series.append({
                "periodStart": point.period_start.isoformat(),
                "periodEnd": point.period_end.isoformat(),
                "periodLabel": point.period_label,
                "value": round(point.value, 8),
                "displayValue": _display(point.value, unit),
                "observedDayCount": point.observed_day_count,
                "expectedDayCount": point.expected_day_count,
                "coverageRatio": round(point.observed_day_count / point.expected_day_count, 4),
                "evidenceId": point.evidence_id,
                "factId": period_fact_id,
                "change": change,
            })
        return facts, series

    @staticmethod
    def _pattern(directions: list[str]) -> str:
        if directions and all(value == "unchanged" for value in directions):
            return "unchanged"
        active = {value for value in directions if value != "unchanged"}
        if active == {"increasing"}:
            return "consistently_increasing"
        if active == {"decreasing"}:
            return "consistently_decreasing"
        return "fluctuating"

    @staticmethod
    def _aggregation_rule(metric_code: str, group_by: str) -> str:
        if metric_code == "error_rate":
            return "weighted_error_rate"
        return "daily_value" if group_by == "day" else "period_sum"

    @staticmethod
    def _fact(fact_id: str, kind: str, value: float, unit: str, evidence_ids: list[str]) -> dict[str, Any]:
        return {
            "factId": fact_id, "kind": kind, "value": round(float(value), 8),
            "unit": unit, "displayValue": _display(float(value), unit),
            "evidenceIds": evidence_ids,
        }

    @staticmethod
    def _enum_fact(fact_id: str, kind: str, value: str, evidence_ids: list[str]) -> dict[str, Any]:
        return {
            "factId": fact_id, "kind": kind, "value": value,
            "unit": "enum", "displayValue": value, "evidenceIds": evidence_ids,
        }

    @staticmethod
    def _point(rows: pd.DataFrame, metric_code: str) -> tuple[float, pd.DataFrame, bool] | None:
        def metric_rows(label: str) -> pd.DataFrame:
            return rows[rows["metric_normalized"].eq(label)].copy()

        if metric_code == "total":
            selected = metric_rows("Tổng số")
            value = pd.to_numeric(selected["chart_value"], errors="coerce").sum(min_count=1)
            return None if pd.isna(value) else (float(value), selected, False)
        if metric_code == "error":
            selected = metric_rows("Báo sai/Lỗi")
            value = pd.to_numeric(selected["chart_value"], errors="coerce").sum(min_count=1)
            if pd.notna(value):
                return float(value), selected, False
            total_rows = metric_rows("Tổng số")
            total = pd.to_numeric(total_rows["chart_value"], errors="coerce").sum(min_count=1)
            kinds = set(selected.get("value_kind", pd.Series(dtype=str)).dropna())
            if pd.notna(total) and "source_marker" not in kinds:
                return 0.0, pd.concat([selected, total_rows]), True
            return None
        evidence_chunks: list[pd.DataFrame] = []
        eligible_totals: list[float] = []
        eligible_errors: list[float] = []
        inferred_zero = False
        for _, day_rows in rows.groupby("date", sort=True):
            total_rows = day_rows[day_rows["metric_normalized"].eq("Tổng số")].copy()
            error_rows = day_rows[day_rows["metric_normalized"].eq("Báo sai/Lỗi")].copy()
            total = pd.to_numeric(total_rows["chart_value"], errors="coerce").sum(min_count=1)
            error = pd.to_numeric(error_rows["chart_value"], errors="coerce").sum(min_count=1)
            error_kinds = set(error_rows.get("value_kind", pd.Series(dtype=str)).dropna())
            inferred_for_day = False
            if pd.isna(error) and pd.notna(total) and "source_marker" not in error_kinds:
                error = 0.0
                inferred_for_day = True
            eligible_day = bool(
                pd.notna(total)
                and pd.notna(error)
                and (float(total) > 0 or (float(total) == 0 and float(error) == 0))
            )
            day_evidence = pd.concat([error_rows, total_rows])
            day_evidence["ai_included"] = eligible_day & day_evidence["chart_value"].notna()
            evidence_chunks.append(day_evidence)
            if eligible_day:
                eligible_totals.append(float(total))
                eligible_errors.append(float(error))
                inferred_zero = inferred_zero or inferred_for_day
        if not eligible_totals:
            return None
        total_sum = sum(eligible_totals)
        error_sum = sum(eligible_errors)
        value = error_sum / total_sum * 100 if total_sum > 0 else 0.0
        return value, pd.concat(evidence_chunks), inferred_zero


class AnalyticsEngine:
    def __init__(self, trend_strategy: TrendStrategy | None = None):
        self.trend_strategy = trend_strategy or TrendStrategy()

    def trend(self, data: pd.DataFrame, **request: Any) -> TrendComputation:
        return self.trend_strategy.compute(data, **request)
