"""Capture aggregate chart evidence without changing chart calculations."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from excel_visualization_pipeline.visualization.charts import (
    prepare_period_metric_summary,
    prepare_period_statistics,
)
from excel_visualization_pipeline.storage.aggregates import register_aggregate_snapshots


def _date(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def _members(rows: pd.DataFrame, role: str, note: str | None = None) -> list[dict[str, Any]] | None:
    result = []
    for row in rows.sort_values(["date", "entity_id", "metric_code"]).itertuples(index=False):
        lineage_ref = getattr(row, "lineage_ref", None)
        if lineage_ref is None or pd.isna(lineage_ref):
            return None
        value = getattr(row, "chart_value", None)
        included = value is not None and pd.notna(value)
        result.append({
            "date": _date(getattr(row, "date")),
            "lineageRef": str(lineage_ref),
            "role": role if included else "excluded_marker" if getattr(row, "value_kind", None) == "source_marker" else "missing",
            "included": included,
            "contributionValue": float(value) if included else None,
            "note": note if included else "Không có giá trị số được dùng trong phép tính.",
        })
    return result


def _range(data: pd.DataFrame, entity_id: str, start: str, end: str, metric: str) -> pd.DataFrame:
    dates = pd.to_datetime(data["date"]).dt.date
    return data[
        (data["entity_id"] == entity_id)
        & (data["metric_normalized"] == metric)
        & (dates >= date.fromisoformat(start))
        & (dates <= date.fromisoformat(end))
    ]


def _spec(
    project: str,
    entity,
    metric: str,
    series: str,
    start: str,
    end: str,
    result_value: float,
    display_value: str,
    rule_code: str,
    explanation: str,
    members: list[dict[str, Any]],
    source_run_id: int | None,
    observed_through: str | None,
    eligible_days: int | None = None,
    calendar_days: int | None = None,
    inferred_zero: bool = False,
) -> dict[str, Any]:
    context = {
        "project": project,
        "entity": {
            "ref": str(entity.name),
            "label": str(entity["entity_label"]),
            "hierarchyPath": [
                part.strip()
                for part in str(entity["entity_path"]).replace(" > ", "/").split("/")
                if part.strip()
            ],
            "effectiveUnit": entity["effective_unit"] if pd.notna(entity["effective_unit"]) else None,
        },
        "metric": metric,
        "series": series,
        "period": {"start": start, "end": end},
        "observedThrough": observed_through,
    }
    value_refs = {m["lineageRef"] for m in members if m["included"] and m["role"] in {"value", "numerator", "denominator"}}
    coverage_refs = {m["lineageRef"] for m in members if m["included"] and m["role"] == "coverage"}
    return {
        "context": context,
        "result": {"chartValue": result_value, "displayValue": display_value},
        "aggregation": {
            "ruleCode": rule_code,
            "explanation": explanation,
            "valueObservationCount": len(value_refs),
            "coverageObservationCount": len(coverage_refs),
            "eligibleDayCount": eligible_days,
            "calendarDayCount": calendar_days,
            "inferredZero": inferred_zero,
        },
        "members": members,
        "sourceRunId": source_run_id,
    }


def attach_aggregate_lineage(
    db_path,
    source_key: str,
    project: str,
    figure,
    data: pd.DataFrame,
    entities: pd.DataFrame,
    *,
    kind: str,
    group_by: str,
    start_date,
    end_date,
    comparison_metric: str | None = None,
    coverage_data: pd.DataFrame | None = None,
) -> None:
    """Add immutable refs to aggregate traces, using the already-rendered y values."""
    if not figure.data or data.empty:
        return
    summary = (
        prepare_period_statistics(
            data, start_date, end_date, group_by, coverage_data=coverage_data
        ) if kind == "statistics" else prepare_period_metric_summary(
            data, start_date, end_date, group_by
        )
    )
    if summary.empty:
        return
    entity_lookup = entities.set_index("entity_id") if "entity_id" in entities.columns else entities.set_index("db_entity_id")
    # Observation rows are the evidence snapshot; entity metadata can be read
    # from a later committed import while the workspace request is in flight.
    evidence_entities = data.drop_duplicates("entity_id").set_index("entity_id")
    observed_through = _date(pd.to_datetime(data["date"]).max())
    source_run_id = int(data["lineage_run_id"].max()) if "lineage_run_id" in data.columns else None
    specs: list[dict[str, Any]] = []
    locations: list[tuple[int, int]] = []
    per_trace: dict[int, list[str | None]] = {}

    for trace_index, trace in enumerate(figure.data):
        name = str(trace.name or "")
        if not name or trace.y is None:
            continue
        if kind == "statistics":
            if " · " not in name:
                continue
            aggregation_name, metric = name.split(" · ", 1)
            metric_column = "period_sum" if aggregation_name == "SUM" else "average_per_day"
            display_column = "display_sum" if aggregation_name == "SUM" else "display_average"
            entity_id = str(data["entity_id"].iloc[0])
        elif kind == "comparison":
            metric = str(comparison_metric)
            entity_id = str(trace.legendgroup)
            metric_column = {"Tổng số": "total_sum", "Báo sai/Lỗi": "error_sum", "% báo sai": "error_rate"}[metric]
            display_column = {"Tổng số": "display_total", "Báo sai/Lỗi": "display_error", "% báo sai": "display_rate"}[metric]
        else:
            metric = name
            entity_id = str(data["entity_id"].iloc[0])
            metric_column = {"Tổng số": "total_sum", "Báo sai/Lỗi": "error_sum", "% báo sai": "error_rate"}.get(metric)
            display_column = {"Tổng số": "display_total", "Báo sai/Lỗi": "display_error", "% báo sai": "display_rate"}.get(metric)
            if metric_column is None:
                continue
        if entity_id not in entity_lookup.index:
            continue
        summary_rows = summary[summary["entity_id"] == entity_id]
        if kind == "statistics":
            summary_rows = summary_rows[summary_rows["metric_normalized"] == metric]
        by_label = {str(row.period_label): row for row in summary_rows.itertuples(index=False)}
        per_trace[trace_index] = [None] * len(trace.x)
        for point_index, (label, chart_value) in enumerate(zip(trace.x, trace.y)):
            row = by_label.get(str(label))
            if row is None or chart_value is None or pd.isna(chart_value):
                continue
            start, end = _date(row.period_start), _date(row.period_end)
            members: list[dict[str, Any]] = []
            inferred_zero = False
            if kind == "statistics":
                value_rows = _range(data, entity_id, start, end, metric)
                value_members = _members(value_rows, "value")
                if value_members is None:
                    continue
                members.extend(value_members)
                rule_code = "period_sum" if metric_column == "period_sum" else "sum_divided_by_eligible_days"
                explanation = "Cộng các giá trị số trong kỳ." if metric_column == "period_sum" else "Tổng giá trị chia cho số ngày có dữ liệu hợp lệ."
                if metric_column == "average_per_day":
                    coverage_source = coverage_data if coverage_data is not None else data
                    coverage_rows = _range(coverage_source, str(row.coverage_source_entity_id), start, end, "Tổng số")
                    coverage_rows = coverage_rows[coverage_rows["chart_value"].notna()]
                    coverage_note = "Ngày có dữ liệu từ entity cha." if str(row.coverage_source_entity_id) != entity_id else "Ngày có dữ liệu Tổng số."
                    coverage_members = _members(coverage_rows, "coverage", coverage_note)
                    if coverage_members is None:
                        continue
                    marker_dates = set(pd.to_datetime(value_rows.loc[value_rows["value_kind"] == "source_marker", "date"]).dt.date)
                    for member, coverage_row in zip(coverage_members, coverage_rows.sort_values(["date", "entity_id", "metric_code"]).itertuples(index=False)):
                        if pd.Timestamp(coverage_row.date).date() in marker_dates:
                            member["included"] = False
                            member["note"] = "Ngày này có dấu nguồn ở metric đang xét nên bị loại khỏi mẫu số."
                    members.extend(coverage_members)
                eligible_days = int(row.eligible_day_count)
                calendar_days = int(row.calendar_day_count)
            else:
                metric_roles = [(metric, "value")]
                if metric == "% báo sai":
                    metric_roles = [("Báo sai/Lỗi", "numerator"), ("Tổng số", "denominator")]
                for source_metric, role in metric_roles:
                    source_rows = _range(data, entity_id, start, end, source_metric)
                    source_members = _members(source_rows, role)
                    if source_members is None:
                        members = []
                        break
                    members.extend(source_members)
                if not members:
                    continue
                if metric == "Báo sai/Lỗi" and not any(m["role"] == "value" for m in members):
                    total_rows = _range(data, entity_id, start, end, "Tổng số")
                    coverage_members = _members(total_rows[total_rows["chart_value"].notna()], "coverage", "Tổng số đã ghi nhận; lỗi trống được suy ra bằng 0.")
                    if coverage_members is None:
                        continue
                    members.extend(coverage_members)
                    inferred_zero = True
                rule_code = "weighted_error_rate" if metric == "% báo sai" else "period_sum"
                explanation = (
                    "Tổng Báo sai/Lỗi chia Tổng số rồi nhân 100; không lấy trung bình tỷ lệ từng ngày."
                    if metric == "% báo sai" else
                    "Cộng các giá trị số trong kỳ; ô trống không được coi là một ô nguồn bằng 0."
                )
                eligible_days = None
                calendar_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
            if not members:
                continue
            # A source marker can appear in two input roles; retain each role, never duplicate a pair.
            members = list({(m["role"], m["lineageRef"]): m for m in members}.values())
            role_order = {"value": 0, "numerator": 0, "denominator": 1, "coverage": 2}
            members.sort(key=lambda m: (m["date"], role_order.get(m["role"], 3), m["lineageRef"]))
            spec = _spec(
                project, evidence_entities.loc[entity_id], metric, name, start, end,
                float(chart_value), str(getattr(row, display_column)), rule_code,
                explanation, members, source_run_id, observed_through,
                eligible_days, calendar_days, inferred_zero,
            )
            specs.append(spec)
            locations.append((trace_index, point_index))

    refs = register_aggregate_snapshots(db_path, source_key, project, specs)
    for (trace_index, point_index), ref in zip(locations, refs):
        per_trace[trace_index][point_index] = ref
    for trace_index, refs_for_trace in per_trace.items():
        figure.data[trace_index].meta = {
            "lineage": {
                "contractVersion": 2,
                "kind": "aggregate",
                "selectable": any(refs_for_trace),
                "aggregateRefs": refs_for_trace,
            }
        }
