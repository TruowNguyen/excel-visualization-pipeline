from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any

import pandas as pd

from .temporal import temporal_structure


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
    historical_points: tuple[TrendPoint, ...]
    period_analytics: dict[str, Any]
    historical_context: dict[str, Any]
    quality: dict[str, Any]


class TrendStrategy:
    """Versioned deterministic period-over-period trend calculation."""

    policy_version = "period-series-v3"
    period_analytics_policy = "period-level-v1"
    historical_context_policy = "trailing-12-periods-v1"
    max_periods = 60
    history_period_limit = 12

    def from_points(self, points: list[TrendPoint], *, metric_code: str, unit: str,
                    group_by: str, start: date, end: date, expected_periods: int,
                    aggregation_rule: str, label: str) -> TrendComputation:
        """Describe canonical prepared statistics; never calculate chart values again."""
        quality = {"status": "valid" if len(points) >= 2 else "insufficient_data",
                   "validPeriodCount": len(points), "expectedPeriodCount": expected_periods,
                   "groupBy": group_by, "limitations": []}
        if len(points) < expected_periods:
            quality["limitations"].append("Có kỳ thiếu dữ liệu hợp lệ; không coi kỳ thiếu là 0.")
        if any(p.observed_day_count < p.expected_day_count for p in points):
            quality["limitations"].append("Các kỳ có số ngày được ghi nhận khác nhau; không kết luận hoạt động giảm chỉ từ tổng của kỳ ngắn hơn.")
        facts, series = self._series(points, metric_code, unit, quality)
        # Prepared statistics values are the chart's canonical floats, including
        # fractional averages. Preserve them exactly rather than serializing
        # the generic trend layer's eight-decimal representation.
        for point, item, fact in zip(points, series, [f for f in facts if f["kind"] == "period_value"]):
            item["value"] = point.value
            fact["value"] = point.value
        facts.append(self._fact("fact-period-count", "period_count", float(len(points)), "period", [p.evidence_id for p in points]))
        if len(points) >= 2:
            first, last = points[0], points[-1]
            delta = last.value - first.value
            refs = [first.evidence_id, last.evidence_id]
            facts.extend([self._fact("fact-previous", "previous", first.value, unit, refs[:1]),
                          self._fact("fact-current", "current", last.value, unit, refs[1:]),
                          self._fact("fact-delta", "absolute_change", delta, unit, refs),
                          self._enum_fact("fact-direction", "direction", _direction(delta), refs)])
            if first.value != 0:
                facts.append(self._fact("fact-relative-change", "relative_change", delta / abs(first.value) * 100, "percent", refs))
            facts.append(self._enum_fact("fact-trend-pattern", "trend_pattern", self._pattern([p["change"]["direction"] for p in series if p["change"]]), [p.evidence_id for p in points]))
        analytics = self._period_analytics(points, series, facts, metric_code, unit, incomplete=len(points) < expected_periods)
        history = self._historical_context([], points, facts, metric_code, unit)
        return TrendComputation("ready" if len(points) >= 2 else "insufficient_data", metric_code,
                                label, "count", unit, aggregation_rule, group_by, start, end,
                                tuple(points), points[0] if len(points) >= 2 else None,
                                points[-1] if points else None, tuple(facts), tuple(series), (), analytics, history, quality)

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

        entity_data = data[data["entity_id"].eq(entity_ref)].copy()
        if entity_data.empty:
            raise ValueError("Nội dung theo dõi không có dữ liệu đã ghi nhận trong dự án.")
        entity_data["date"] = pd.to_datetime(entity_data["date"]).dt.normalize()
        scoped = entity_data[
            entity_data["date"].ge(pd.Timestamp(start)) & entity_data["date"].le(pd.Timestamp(end))
        ]
        unit_values = scoped.get("effective_unit", pd.Series(dtype=object)).dropna().unique()
        count_unit = str(unit_values[0]) if len(unit_values) else "giá trị"
        metric = METRICS[metric_code]
        unit = "percent" if metric_code == "error_rate" else count_unit
        points = self._build_points(
            scoped, metric_code=metric_code, group_by=group_by,
            boundary_start=start, boundary_end=end, evidence_prefix="ev-period",
        )
        historical_candidates = self._build_points(
            entity_data[entity_data["date"].lt(pd.Timestamp(start))],
            metric_code=metric_code, group_by=group_by,
            evidence_prefix="ev-history",
        )
        historical_points = [
            point for point in historical_candidates if point.period_end < start
        ][-self.history_period_limit:]

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
            period_analytics = self._period_analytics(points, series, facts, metric_code, unit, incomplete=len(points) < expected_periods)
            historical_context = self._historical_context(
                historical_points, points, facts, metric_code, unit,
            )
            return TrendComputation(
                "insufficient_data", metric_code, metric["label"], metric["kind"], unit,
                self._aggregation_rule(metric_code, group_by), group_by, start, end,
                tuple(points), None, points[0] if points else None,
                tuple(facts), tuple(series), tuple(historical_points),
                period_analytics, historical_context, quality,
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
        period_analytics = self._period_analytics(points, series, facts, metric_code, unit, incomplete=len(points) < expected_periods)
        historical_context = self._historical_context(
            historical_points, points, facts, metric_code, unit,
        )
        return TrendComputation(
            "ready", metric_code, metric["label"], metric["kind"], unit,
            self._aggregation_rule(metric_code, group_by), group_by, start, end,
            tuple(points), previous, current, tuple(facts), tuple(series),
            tuple(historical_points), period_analytics, historical_context, quality,
        )

    def _build_points(
        self,
        scoped: pd.DataFrame,
        *,
        metric_code: str,
        group_by: str,
        evidence_prefix: str,
        boundary_start: date | None = None,
        boundary_end: date | None = None,
    ) -> list[TrendPoint]:
        if scoped.empty:
            return []
        grouped = scoped.copy()
        grouped["period_start"] = grouped["date"].map(lambda value: _period_start(value, group_by))
        points: list[TrendPoint] = []
        for index, (natural_start, rows) in enumerate(grouped.groupby("period_start", sort=True)):
            calculated = self._point(rows, metric_code)
            if calculated is None:
                continue
            value, evidence_rows, inferred_zero = calculated
            natural_start_date = natural_start.date()
            natural_end_date = _natural_period_end(natural_start, group_by).date()
            period_start = max(natural_start_date, boundary_start) if boundary_start else natural_start_date
            period_end = min(natural_end_date, boundary_end) if boundary_end else natural_end_date
            eligible = evidence_rows["chart_value"].notna()
            if "ai_included" in evidence_rows:
                eligible &= evidence_rows["ai_included"].fillna(False).astype(bool)
            observed_days = int(pd.to_datetime(
                evidence_rows.loc[eligible, "date"]
            ).dt.date.nunique())
            points.append(TrendPoint(
                period_start=period_start,
                period_end=period_end,
                period_label=_period_label(period_start, period_end, group_by),
                value=value,
                rows=evidence_rows.drop(columns=["period_start"], errors="ignore"),
                observed_day_count=observed_days,
                expected_day_count=(period_end - period_start).days + 1,
                evidence_id=f"{evidence_prefix}-{index:03d}",
                inferred_zero=inferred_zero,
            ))
        return points

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

    def _period_analytics(
        self,
        points: list[TrendPoint],
        series: list[dict[str, Any]],
        facts: list[dict[str, Any]],
        metric_code: str,
        unit: str,
        *, incomplete: bool = False,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "temporalStructure": temporal_structure(series, facts, incomplete=incomplete),
            "policyVersion": self.period_analytics_policy,
            "tieBreak": "latest_period",
            "peak": None,
            "lowest": None,
            "largestIncrease": None,
            "largestDecrease": None,
            "consecutiveIncrease": None,
            "consecutiveDecrease": None,
            "endingPlateau": None,
            "latestChange": None,
        }
        if not points:
            return result

        highest_index = max(range(len(points)), key=lambda index: (points[index].value, index))
        lowest_index = min(range(len(points)), key=lambda index: (points[index].value, -index))
        result["peak"] = self._ranked_period(
            "fact-period-highest", "period_highest_value", highest_index,
            points, facts, unit,
        )
        result["lowest"] = self._ranked_period(
            "fact-period-lowest", "period_lowest_value", lowest_index,
            points, facts, unit,
        )

        changes = [
            (index, item["change"])
            for index, item in enumerate(series)
            if item.get("change") is not None
        ]
        increases = [item for item in changes if item[1]["absolute"] > 0]
        decreases = [item for item in changes if item[1]["absolute"] < 0]
        if increases:
            selected = max(increases, key=lambda item: (item[1]["absolute"], item[0]))
            result["largestIncrease"] = self._ranked_change(
                "fact-period-largest-increase", "largest_period_increase",
                selected[0], selected[1], points, facts, metric_code, unit,
            )
        if decreases:
            selected = min(decreases, key=lambda item: (item[1]["absolute"], -item[0]))
            result["largestDecrease"] = self._ranked_change(
                "fact-period-largest-decrease", "largest_period_decrease",
                selected[0], selected[1], points, facts, metric_code, unit,
            )
        if changes:
            index, change = changes[-1]
            result["latestChange"] = self._ranked_change(
                "fact-period-latest-change", "latest_period_change",
                index, change, points, facts, metric_code, unit,
            )
        adjacent_changes = [item for item in changes if (
            points[item[0]].period_start - points[item[0] - 1].period_end
        ).days == 1]
        increase_run = self._longest_run(adjacent_changes, "increasing")
        decrease_run = self._longest_run(adjacent_changes, "decreasing")
        if len(increase_run) >= 2:
            result["consecutiveIncrease"] = self._sequence_analysis(
                "fact-consecutive-increase", "consecutive_increase_run",
                increase_run, points, series, facts, unit,
            )
        if len(decrease_run) >= 2:
            result["consecutiveDecrease"] = self._sequence_analysis(
                "fact-consecutive-decrease", "consecutive_decrease_run",
                decrease_run, points, series, facts, unit,
            )
        ending_plateau = self._ending_run(adjacent_changes, "unchanged") if adjacent_changes and adjacent_changes[-1][0] == len(points) - 1 else []
        if ending_plateau:
            result["endingPlateau"] = self._sequence_analysis(
                "fact-ending-plateau", "ending_plateau",
                ending_plateau, points, series, facts, unit,
            )
        return result

    @staticmethod
    def _longest_run(
        changes: list[tuple[int, dict[str, Any]]], direction: str,
    ) -> list[int]:
        best: list[int] = []
        current: list[int] = []
        for index, change in changes:
            if change["direction"] == direction:
                current = [*current, index] if current and index == current[-1] + 1 else [index]
                if len(current) >= len(best):
                    best = current.copy()
            else:
                current = []
        return best

    @staticmethod
    def _ending_run(
        changes: list[tuple[int, dict[str, Any]]], direction: str,
    ) -> list[int]:
        result: list[int] = []
        for index, change in reversed(changes):
            if change["direction"] != direction or (result and index != result[-1] - 1):
                break
            result.append(index)
        return list(reversed(result))

    def _sequence_analysis(
        self,
        fact_id: str,
        kind: str,
        change_indices: list[int],
        points: list[TrendPoint],
        series: list[dict[str, Any]],
        facts: list[dict[str, Any]],
        unit: str,
    ) -> dict[str, Any]:
        point_indices = [change_indices[0] - 1, *change_indices]
        selected_points = [points[index] for index in point_indices]
        evidence_ids = [point.evidence_id for point in selected_points]
        sequence_fact = self._fact(
            fact_id, kind, float(len(change_indices)), "transition", evidence_ids,
        )
        sequence_fact["supportingValues"] = [round(point.value, 8) for point in selected_points]
        facts.append(sequence_fact)
        supporting_fact_ids: list[str] = [fact_id]
        for index in point_indices:
            supporting_fact_ids.append(f"fact-period-{index:03d}")
        for index in change_indices:
            supporting_fact_ids.extend(series[index]["change"]["factIds"])
        return {
            "transitionCount": len(change_indices),
            "startPeriodLabel": selected_points[0].period_label,
            "endPeriodLabel": selected_points[-1].period_label,
            "values": [round(point.value, 8) for point in selected_points],
            "displayValues": [_display(point.value, unit) for point in selected_points],
            "periodLabels": [point.period_label for point in selected_points],
            "factIds": list(dict.fromkeys(supporting_fact_ids)),
        }

    def _ranked_period(
        self,
        fact_id: str,
        kind: str,
        index: int,
        points: list[TrendPoint],
        facts: list[dict[str, Any]],
        unit: str,
    ) -> dict[str, Any]:
        point = points[index]
        facts.append(self._fact(fact_id, kind, point.value, unit, [point.evidence_id]))
        return {
            "periodStart": point.period_start.isoformat(),
            "periodEnd": point.period_end.isoformat(),
            "periodLabel": point.period_label,
            "value": round(point.value, 8),
            "displayValue": _display(point.value, unit),
            "coverageRatio": round(point.observed_day_count / point.expected_day_count, 4),
            "factIds": [fact_id, f"fact-period-{index:03d}"],
        }

    def _ranked_change(
        self,
        fact_id: str,
        kind: str,
        index: int,
        change: dict[str, Any],
        points: list[TrendPoint],
        facts: list[dict[str, Any]],
        metric_code: str,
        unit: str,
    ) -> dict[str, Any]:
        prior, current = points[index - 1], points[index]
        delta_unit = "percentage_point" if metric_code == "error_rate" else unit
        facts.append(self._fact(
            fact_id, kind, change["absolute"], delta_unit,
            [prior.evidence_id, current.evidence_id],
        ))
        return {
            "fromPeriodStart": prior.period_start.isoformat(),
            "fromPeriodLabel": prior.period_label,
            "fromValue": round(prior.value, 8),
            "fromDisplayValue": _display(prior.value, unit),
            "toPeriodStart": current.period_start.isoformat(),
            "toPeriodLabel": current.period_label,
            "toValue": round(current.value, 8),
            "toDisplayValue": _display(current.value, unit),
            "absolute": change["absolute"],
            "absoluteDisplay": change["absoluteDisplay"],
            "relativePercent": change["relativePercent"],
            "relativeDisplay": change["relativeDisplay"],
            "direction": change["direction"],
            "factIds": [
                fact_id,
                f"fact-period-{index - 1:03d}",
                f"fact-period-{index:03d}",
                *change["factIds"],
            ],
        }

    def _historical_context(
        self,
        historical_points: list[TrendPoint],
        selected_points: list[TrendPoint],
        facts: list[dict[str, Any]],
        metric_code: str,
        unit: str,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": "available" if historical_points else "unavailable",
            "policyVersion": self.historical_context_policy,
            "lookbackPeriodLimit": self.history_period_limit,
            "observedPeriodCount": len(historical_points),
            "periods": [],
            "previousPeriod": None,
            "historicalRange": None,
            "boundaryComparison": None,
            "currentPosition": None,
            "limitations": [],
        }
        if not historical_points:
            result["limitations"].append(
                "Không có kỳ hợp lệ trước khoảng đang xem để tạo bối cảnh lịch sử."
            )
            return result

        history_fact_ids: list[str] = []
        for index, point in enumerate(historical_points):
            fact_id = f"fact-history-period-{index:03d}"
            history_fact_ids.append(fact_id)
            facts.append(self._fact(
                fact_id, "historical_period_value", point.value, unit, [point.evidence_id]
            ))
            result["periods"].append({
                "periodStart": point.period_start.isoformat(),
                "periodEnd": point.period_end.isoformat(),
                "periodLabel": point.period_label,
                "value": round(point.value, 8),
                "displayValue": _display(point.value, unit),
                "coverageRatio": round(point.observed_day_count / point.expected_day_count, 4),
                "factId": fact_id,
            })
        facts.append(self._fact(
            "fact-history-period-count", "historical_period_count",
            float(len(historical_points)), "period",
            [point.evidence_id for point in historical_points],
        ))

        previous_index = len(historical_points) - 1
        previous = historical_points[previous_index]
        previous_fact_id = history_fact_ids[previous_index]
        result["previousPeriod"] = {
            **result["periods"][previous_index],
            "factIds": [previous_fact_id],
        }

        highest_index = max(
            range(len(historical_points)),
            key=lambda index: (historical_points[index].value, index),
        )
        lowest_index = min(
            range(len(historical_points)),
            key=lambda index: (historical_points[index].value, -index),
        )
        highest, lowest = historical_points[highest_index], historical_points[lowest_index]
        facts.extend([
            self._fact(
                "fact-history-highest", "historical_highest_value", highest.value, unit,
                [highest.evidence_id],
            ),
            self._fact(
                "fact-history-lowest", "historical_lowest_value", lowest.value, unit,
                [lowest.evidence_id],
            ),
        ])
        result["historicalRange"] = {
            "start": historical_points[0].period_start.isoformat(),
            "end": historical_points[-1].period_end.isoformat(),
            "lowest": {
                "periodLabel": lowest.period_label,
                "value": round(lowest.value, 8),
                "displayValue": _display(lowest.value, unit),
                "factIds": ["fact-history-lowest", history_fact_ids[lowest_index]],
            },
            "highest": {
                "periodLabel": highest.period_label,
                "value": round(highest.value, 8),
                "displayValue": _display(highest.value, unit),
                "factIds": ["fact-history-highest", history_fact_ids[highest_index]],
            },
        }

        if not selected_points:
            return result

        first = selected_points[0]
        boundary_delta = first.value - previous.value
        boundary_relative = None if math.isclose(previous.value, 0.0, abs_tol=1e-12) else (
            boundary_delta / abs(previous.value) * 100
        )
        delta_unit = "percentage_point" if metric_code == "error_rate" else unit
        boundary_evidence = [previous.evidence_id, first.evidence_id]
        facts.extend([
            self._fact(
                "fact-history-boundary-change", "historical_boundary_change",
                boundary_delta, delta_unit, boundary_evidence,
            ),
            self._enum_fact(
                "fact-history-boundary-direction", "period_direction",
                _direction(boundary_delta), boundary_evidence,
            ),
        ])
        boundary_fact_ids = [
            previous_fact_id, "fact-period-000", "fact-history-boundary-change",
            "fact-history-boundary-direction",
        ]
        if boundary_relative is not None:
            facts.append(self._fact(
                "fact-history-boundary-relative", "historical_boundary_relative_change",
                boundary_relative, "percent", boundary_evidence,
            ))
            boundary_fact_ids.append("fact-history-boundary-relative")
        else:
            result["limitations"].append(
                "Kỳ lịch sử liền trước bằng 0 nên không tính phần trăm thay đổi tới kỳ đầu của khoảng đang xem."
            )
        result["boundaryComparison"] = {
            "fromPeriodLabel": previous.period_label,
            "toPeriodLabel": first.period_label,
            "absolute": round(boundary_delta, 8),
            "absoluteDisplay": _display(boundary_delta, delta_unit),
            "relativePercent": round(boundary_relative, 8) if boundary_relative is not None else None,
            "relativeDisplay": _display(boundary_relative, "percent"),
            "direction": _direction(boundary_delta),
            "factIds": boundary_fact_ids,
        }

        current = selected_points[-1]
        if current.value > highest.value:
            position = "above_historical_range"
        elif current.value < lowest.value:
            position = "below_historical_range"
        elif math.isclose(highest.value, lowest.value, abs_tol=1e-12) and math.isclose(
            current.value, highest.value, abs_tol=1e-12
        ):
            position = "matches_historical_range"
        else:
            position = "within_historical_range"
        position_evidence = [current.evidence_id, lowest.evidence_id, highest.evidence_id]
        facts.append(self._enum_fact(
            "fact-current-history-position", "historical_range_position",
            position, position_evidence,
        ))
        result["currentPosition"] = {
            "value": position,
            "currentPeriodLabel": current.period_label,
            "factIds": [
                f"fact-period-{len(selected_points) - 1:03d}",
                "fact-history-lowest", "fact-history-highest",
                "fact-current-history-position",
            ],
        }
        if any(point.observed_day_count < point.expected_day_count for point in historical_points):
            result["limitations"].append(
                "Một hoặc nhiều kỳ trong bối cảnh lịch sử chỉ có dữ liệu cho một phần số ngày."
            )
        return result

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
