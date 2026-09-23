from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure
from plotly.subplots import make_subplots


ENTITY_COLORS = ["#0077b6", "#e76f51", "#2a9d8f"]
ENTITY_LEVEL_LABELS = {
    "project": "Project",
    "section": "Section",
    "item": "Item",
    "subitem": "Sub-item",
}


def _interactive_legend() -> dict:
    """Keep Plotly's native toggle behavior in a compact, production-style legend."""
    return {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "left",
        "x": 0,
        "bgcolor": "rgba(0, 0, 0, 0)",
        "borderwidth": 0,
        "font": {"color": "#334155", "size": 12},
        "itemsizing": "constant",
        "itemwidth": 34,
        "valign": "middle",
        "tracegroupgap": 8,
        "itemclick": "toggle",
        "itemdoubleclick": "toggleothers",
    }


def _format_date_axes(figure: Figure) -> Figure:
    """Use the Vietnamese day/month display without changing datetime values."""
    figure.for_each_xaxis(
        lambda axis: axis.update(tickformat="%d/%m", hoverformat="%d/%m")
    )
    return figure


def _enable_unified_date_hover(figure: Figure) -> Figure:
    """Show every trace for the nearest date without requiring point-level hover."""
    figure.update_layout(
        hovermode="x unified",
        hoverdistance=20,
        hoverlabel={"namelength": -1},
    )
    figure.for_each_xaxis(
        lambda axis: axis.update(
            unifiedhovertitle={"text": "<b>Ngày %{x|%d/%m/%Y}</b>"},
            showspikes=False,
        )
    )
    return figure


def _latest_labels(values) -> list[str]:
    """Keep only the last visible label while preserving every chart point."""
    value_list = list(values)
    labels = ["" for _ in value_list]
    if labels:
        labels[-1] = str(value_list[-1])
    return labels


def _exact_lineage_fields(frame: pd.DataFrame) -> dict:
    """Attach identity metadata only; chart values and ordering remain untouched."""
    if "observation_ref" not in frame.columns or "lineage_ref" not in frame.columns:
        return {
            "ids": [None] * len(frame),
            "meta": {
                "lineage": {
                    "contractVersion": 1,
                    "kind": "exact-observation",
                    "selectable": False,
                    "lineageRefs": [None] * len(frame),
                }
            },
        }
    observation_refs = [value if pd.notna(value) else None for value in frame["observation_ref"]]
    lineage_refs = [value if pd.notna(value) else None for value in frame["lineage_ref"]]
    return {
        "ids": observation_refs,
        "meta": {
            "lineage": {
                "contractVersion": 1,
                "kind": "exact-observation",
                "selectable": any(observation_refs) and any(lineage_refs),
                "lineageRefs": lineage_refs,
            }
        },
    }


def _keep_latest_trace_labels(figure: Figure) -> Figure:
    for trace in figure.data:
        if trace.text is None:
            continue
        text_values = list(trace.text)
        trace.text = _latest_labels(text_values)
    return figure


def _formatted_number(value: float) -> str:
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _hover_display_value(row) -> str:
    """Return a compact hover value and retain only essential warnings."""
    value_kind = getattr(row, "value_kind", None)
    if value_kind == "not_recorded":
        data_note = getattr(row, "data_note", None)
        return "— ⚠" if pd.notna(data_note) and "nhưng Báo sai/Lỗi" in str(data_note) else "—"
    if value_kind == "source_marker":
        display_value = getattr(row, "display_value", None)
        marker = str(display_value).strip() if pd.notna(display_value) else "-"
        return marker or "-"
    if value_kind == "default_zero_rate":
        return "0%"
    display_value = getattr(row, "display_value", None)
    if pd.isna(display_value) or not str(display_value).strip():
        return "—"
    result = str(display_value)
    data_note = getattr(row, "data_note", None)
    return f"{result} ⚠" if pd.notna(data_note) and "nhưng Báo sai/Lỗi" in str(data_note) else result


def _metric_hover_lookup(
    data: pd.DataFrame,
    entity_id: str,
) -> dict[tuple[pd.Timestamp, str], str]:
    lookup: dict[tuple[pd.Timestamp, str], str] = {}
    entity_data = data[data["entity_id"] == entity_id]
    for row in entity_data.itertuples():
        if row.metric_normalized not in {"Tổng số", "Báo sai/Lỗi", "% báo sai"}:
            continue
        lookup[(pd.Timestamp(row.date), row.metric_normalized)] = _hover_display_value(row)
    return lookup


def _hover_row(
    lookup: dict[tuple[pd.Timestamp, str], str],
    date,
    entity_label: str,
) -> list[str]:
    target_date = pd.Timestamp(date)
    return [
        entity_label,
        lookup.get((target_date, "Tổng số"), "—"),
        lookup.get((target_date, "Báo sai/Lỗi"), "—"),
        lookup.get((target_date, "% báo sai"), "—"),
    ]


ENTITY_HOVER_TEMPLATE = (
    "<b>%{customdata[0]}</b>"
    "<br><span style='color:#8ecae6'>■</span> Tổng số/Cảnh báo: %{customdata[1]}"
    "<br><span style='color:#d1495b'>■</span> Báo sai/Lỗi: %{customdata[2]}"
    "<br><span style='color:#ff9f1c'>━●━</span> % báo sai: %{customdata[3]}"
    "<extra></extra>"
)

COMBO_HOVER_TEMPLATE = (
    "<span style='color:#8ecae6'>■</span> Tổng số/Cảnh báo: %{customdata[1]}"
    "<br><span style='color:#d1495b'>■</span> Báo sai/Lỗi: %{customdata[2]}"
    "<br><span style='color:#ff9f1c'>━●━</span> % báo sai: %{customdata[3]}"
    "<extra></extra>"
)


def prepare_project_totals(data: pd.DataFrame, selected_date) -> pd.DataFrame:
    """Build one Total record per Project and Unit without mixing hierarchy levels.

    An explicit Project-level value is preferred. If it is absent, the function
    sums Section-level values, then Item-level values. Units are never mixed.
    """
    target_date = pd.Timestamp(selected_date)
    frame = chartable(data)
    frame = frame[
        (frame["date"] == target_date)
        & (frame["metric_normalized"] == "Tổng số")
    ]
    rows: list[dict] = []
    for project, project_data in frame.groupby("project", dropna=False):
        for unit, unit_data in project_data.groupby("unit", dropna=False):
            source_depth = int(unit_data["entity_depth"].min())
            selected = unit_data[unit_data["entity_depth"] == source_depth]
            source_levels = sorted(selected["entity_level"].unique())
            source_level = ", ".join(source_levels)
            is_direct = source_depth == 0 and len(selected) == 1
            total_value = float(selected["chart_value"].sum())
            rows.append(
                {
                    "project": project,
                    "unit": unit or "Không xác định",
                    "date": target_date,
                    "chart_value": total_value,
                    "display_value": _formatted_number(total_value),
                    "source_level": source_level,
                    "source_depth": source_depth,
                    "source_count": len(selected),
                    "calculation_method": "Giá trị cấp Project" if is_direct else f"Cộng {len(selected)} dòng cấp {source_level}",
                    "source_cells": ", ".join(selected["cell_address"].astype(str)),
                }
            )
    return pd.DataFrame(rows)


def prepare_project_totals_range(data: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    dates = sorted(
        pd.to_datetime(
            data.loc[
                (data["metric_normalized"] == "Tổng số")
                & data["chart_value"].notna()
                & (pd.to_datetime(data["date"]) >= start)
                & (pd.to_datetime(data["date"]) <= end),
                "date",
            ]
        ).unique()
    )
    frames = [prepare_project_totals(data, date) for date in dates]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_project_total_chart(data: pd.DataFrame, start_date, end_date=None) -> Figure:
    end_date = start_date if end_date is None else end_date
    frame = prepare_project_totals_range(data, start_date, end_date)
    projects = sorted(data["project"].dropna().unique())
    scope = projects[0] if len(projects) == 1 else "các Project"
    title = f"Tổng số — {scope} — {pd.Timestamp(start_date):%d/%m} đến {pd.Timestamp(end_date):%d/%m}"
    if frame.empty:
        return px.line(title=title)
    figure = px.line(
        frame,
        x="date",
        y="chart_value",
        color="project",
        facet_col="unit" if frame["unit"].nunique() > 1 else None,
        markers=True,
        text="display_value",
        custom_data=["display_value"],
        title=title,
        labels={"project": "Project", "chart_value": "Tổng số", "unit": "Đơn vị", "date": "Ngày"},
    )
    figure.update_traces(
        mode="lines+markers+text",
        textposition="top center",
        textfont_size=11,
        cliponaxis=False,
        hovertemplate="Tổng số: %{customdata[0]}<extra></extra>",
    )
    figure.update_layout(margin={"t": 90})
    figure.for_each_yaxis(lambda axis: axis.update(matches=None))
    return _enable_unified_date_hover(_format_date_axes(_keep_latest_trace_labels(figure)))


def chartable(data: pd.DataFrame) -> pd.DataFrame:
    result = data[data["chart_value"].notna()].copy()
    result["date"] = pd.to_datetime(result["date"])
    return result


def _period_start(values: pd.Series, group_by: str) -> pd.Series:
    dates = pd.to_datetime(values).dt.normalize()
    if group_by == "day":
        return dates
    if group_by == "week":
        return dates - pd.to_timedelta(dates.dt.weekday, unit="D")
    if group_by == "month":
        return dates.dt.to_period("M").dt.start_time
    if group_by == "quarter":
        return dates.dt.to_period("Q").dt.start_time
    raise ValueError("Nhóm thời gian chỉ hỗ trợ day, week, month hoặc quarter.")


def _natural_period_end(period_start: pd.Timestamp, group_by: str) -> pd.Timestamp:
    if group_by == "day":
        return period_start
    if group_by == "week":
        return period_start + pd.Timedelta(days=6)
    if group_by == "month":
        return period_start + pd.offsets.MonthEnd(0)
    return period_start + pd.offsets.QuarterEnd(startingMonth=12)


def _period_label(start: pd.Timestamp, end: pd.Timestamp, group_by: str) -> str:
    if group_by == "day":
        return f"{start:%d/%m}"
    if group_by == "week":
        iso = start.isocalendar()
        return f"Tuần {iso.week:02d}/{iso.year}"
    if group_by == "month":
        return f"{start:%m/%Y}"
    return f"Q{start.quarter}/{start.year}"


def prepare_period_metric_summary(
    data: pd.DataFrame,
    start_date,
    end_date,
    group_by: str,
) -> pd.DataFrame:
    """Aggregate the overview metrics into independent calendar periods.

    Count metrics are summed inside each period.  The period error rate is a
    weighted rate (SUM errors / SUM total), never an average of daily rates.
    This keeps a weekly view as a comparison of calendar weeks instead of a
    seven-point daily chart.
    """
    if group_by not in {"week", "month"}:
        raise ValueError("So sánh kỳ chỉ hỗ trợ week hoặc month.")

    frame = data[
        data["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi", "% báo sai"])
    ].copy()
    if frame.empty:
        return pd.DataFrame()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    if frame.empty:
        return pd.DataFrame()

    frame["period_start"] = _period_start(frame["date"], group_by)
    rows: list[dict] = []
    for (entity_id, period_start), period_data in frame.groupby(
        ["entity_id", "period_start"], dropna=False, sort=True
    ):
        period_start = pd.Timestamp(period_start)
        period_end = min(_natural_period_end(period_start, group_by), end)
        scoped_start = max(period_start, start)
        total_rows = period_data[period_data["metric_normalized"] == "Tổng số"]
        error_rows = period_data[period_data["metric_normalized"] == "Báo sai/Lỗi"]
        total_values = pd.to_numeric(total_rows["chart_value"], errors="coerce")
        error_values = pd.to_numeric(error_rows["chart_value"], errors="coerce")
        total_sum = total_values.sum(min_count=1)
        error_sum = error_values.sum(min_count=1)

        # A blank error cell means no error was recorded for a day whose total
        # was observed. A source marker ("-", N/A, ...) remains missing.
        if pd.isna(error_sum) and pd.notna(total_sum):
            error_kinds = set(error_rows.get("value_kind", pd.Series(dtype=str)).dropna())
            if "source_marker" not in error_kinds:
                error_sum = 0.0

        if pd.notna(total_sum) and float(total_sum) > 0 and pd.notna(error_sum):
            error_rate = float(error_sum) / float(total_sum) * 100
        elif pd.notna(total_sum) and float(total_sum) == 0 and error_sum == 0:
            error_rate = 0.0
        else:
            error_rate = None

        first = period_data.iloc[0]
        unit_values = period_data["effective_unit"].dropna().unique()
        unit = str(unit_values[0]) if len(unit_values) else "Chưa xác định từ Excel"
        rows.append(
            {
                "entity_id": entity_id,
                "entity_label": first["entity_label"],
                "entity_level": first["entity_level"],
                "effective_unit": unit,
                "period_start": scoped_start,
                "period_end": period_end,
                "period_label": _period_label(period_start, period_end, group_by),
                "total_sum": float(total_sum) if pd.notna(total_sum) else None,
                "error_sum": float(error_sum) if pd.notna(error_sum) else None,
                "error_rate": error_rate,
                "display_total": _formatted_number(total_sum) if pd.notna(total_sum) else "—",
                "display_error": _formatted_number(error_sum) if pd.notna(error_sum) else "—",
                "display_rate": f"{error_rate:.2f}%" if error_rate is not None else "—",
                "period_range": f"{scoped_start:%d/%m}–{period_end:%d/%m}",
            }
        )
    return pd.DataFrame(rows)


def prepare_period_statistics(
    data: pd.DataFrame,
    start_date,
    end_date,
    group_by: str,
    coverage_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calculate period SUM and AVG/day, inheriting observation days when needed."""
    frame = data[data["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi"])].copy()
    if frame.empty:
        return pd.DataFrame()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    if frame.empty:
        return pd.DataFrame()
    coverage_frame = (
        coverage_data if coverage_data is not None else data
    )
    coverage_frame = coverage_frame[
        coverage_frame["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi"])
    ].copy()
    coverage_frame["date"] = pd.to_datetime(coverage_frame["date"]).dt.normalize()
    parent_lookup = (
        coverage_frame[["entity_id", "parent_entity_id"]]
        .drop_duplicates("entity_id")
        .set_index("entity_id")["parent_entity_id"]
        .to_dict()
        if "parent_entity_id" in coverage_frame.columns
        else {}
    )
    entities_with_total = set(
        coverage_frame.loc[
            coverage_frame["metric_normalized"].eq("Tổng số")
            & coverage_frame["chart_value"].notna(),
            "entity_id",
        ]
    )

    def coverage_source_for(entity_id):
        current = entity_id
        visited = set()
        while pd.notna(current) and current not in visited:
            if current in entities_with_total:
                return current
            visited.add(current)
            current = parent_lookup.get(current)
        return entity_id

    coverage_source_by_entity = {
        entity_id: coverage_source_for(entity_id)
        for entity_id in frame["entity_id"].dropna().unique()
    }
    coverage_frame = coverage_frame[
        (coverage_frame["date"] >= start) & (coverage_frame["date"] <= end)
    ]
    coverage_frame["period_start"] = _period_start(coverage_frame["date"], group_by)
    frame["effective_unit"] = frame["effective_unit"].fillna("Chưa xác định từ Excel")
    frame["period_start"] = _period_start(frame["date"], group_by)
    group_columns = [
        "entity_id", "entity_label", "entity_level", "effective_unit",
        "metric_normalized", "period_start",
    ]
    observed_dates_by_period = {
        keys: set(group["date"])
        for keys, group in coverage_frame[
            coverage_frame["metric_normalized"].eq("Tổng số")
            & coverage_frame["chart_value"].notna()
        ].groupby(["entity_id", "period_start"], dropna=False, sort=True)
    }
    rows: list[dict] = []
    for keys, group in frame.groupby(group_columns, dropna=False, sort=True):
        entity_id, entity_label, entity_level, unit, metric, period_start = keys
        natural_end = _natural_period_end(pd.Timestamp(period_start), group_by)
        scoped_start = max(pd.Timestamp(period_start), start)
        scoped_end = min(natural_end, end)
        calendar_days = (scoped_end - scoped_start).days + 1
        coverage_source_entity_id = coverage_source_by_entity.get(entity_id, entity_id)
        coverage_key = (coverage_source_entity_id, period_start)
        observed_dates = observed_dates_by_period.get(coverage_key, set())
        source_marker_dates = set(group.loc[group["value_kind"] == "source_marker", "date"])
        source_marker_days = len(observed_dates & source_marker_dates)
        eligible_days = max(len(observed_dates) - source_marker_days, 0)
        period_sum = float(group["chart_value"].fillna(0).sum())
        inherits_coverage = coverage_source_entity_id != entity_id
        average_per_day = (
            period_sum / eligible_days
            if eligible_days and not (metric == "Tổng số" and inherits_coverage)
            else None
        )
        rows.append({
            "entity_id": entity_id,
            "entity_label": entity_label,
            "entity_level": entity_level,
            "effective_unit": unit,
            "metric_normalized": metric,
            "period_start": scoped_start,
            "period_end": scoped_end,
            "period_label": _period_label(scoped_start, scoped_end, group_by),
            "period_sum": period_sum,
            "average_per_day": average_per_day,
            "eligible_day_count": eligible_days,
            "observed_day_count": len(observed_dates),
            "calendar_day_count": calendar_days,
            "source_marker_day_count": source_marker_days,
            "coverage_source_entity_id": coverage_source_entity_id,
            "display_sum": _formatted_number(period_sum),
            "display_average": (
                _formatted_number(average_per_day) if average_per_day is not None else "—"
            ),
        })
    return pd.DataFrame(rows)


def build_period_statistics_chart(
    data: pd.DataFrame,
    start_date,
    end_date,
    group_by: str,
    modes: list[str] | tuple[str, ...],
    title: str | None = None,
    coverage_data: pd.DataFrame | None = None,
    prepared_frame: pd.DataFrame | None = None,
) -> Figure:
    """Render nested SUM bars and AVG/day lines on a secondary axis."""
    frame = prepared_frame if prepared_frame is not None else prepare_period_statistics(
        data, start_date, end_date, group_by, coverage_data=coverage_data,
    )
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    if frame.empty or not modes:
        return figure
    entity_ids = frame["entity_id"].dropna().unique()
    if len(entity_ids) != 1:
        raise ValueError("Biểu đồ thống kê theo kỳ chỉ nhận dữ liệu của đúng một entity.")
    colors = {
        "Tổng số": ("#8ecae6", "#0077b6"),
        "Báo sai/Lỗi": ("#d1495b", "#9d0208"),
    }
    metric_frames: dict[str, tuple[pd.DataFrame, object]] = {}
    for metric in ["Tổng số", "Báo sai/Lỗi"]:
        metric_data = frame[frame["metric_normalized"] == metric].sort_values("period_start")
        if metric_data.empty:
            continue
        customdata = metric_data[
            [
                "display_sum", "display_average", "eligible_day_count",
                "period_start", "period_end", "observed_day_count", "calendar_day_count",
            ]
        ].to_numpy()
        metric_frames[metric] = (metric_data, customdata)

    if "SUM" in modes:
        for metric in ["Tổng số", "Báo sai/Lỗi"]:
            if metric not in metric_frames:
                continue
            metric_data, customdata = metric_frames[metric]
            bar_color, _ = colors[metric]
            figure.add_trace(
                go.Bar(
                    x=metric_data["period_label"],
                    y=metric_data["period_sum"],
                    name=f"SUM · {metric}",
                    marker_color=bar_color,
                    width=0.72,
                    opacity=0.72 if metric == "Tổng số" else 0.95,
                    customdata=customdata,
                    hoverinfo="skip",
                ),
                secondary_y=False,
            )

    if "AVG/ngày" in modes:
        for metric in ["Tổng số", "Báo sai/Lỗi"]:
            if metric not in metric_frames:
                continue
            metric_data, customdata = metric_frames[metric]
            _, line_color = colors[metric]
            figure.add_trace(
                go.Scatter(
                    x=metric_data["period_label"],
                    y=metric_data["average_per_day"],
                    name=f"AVG/ngày · {metric}",
                    mode="lines+markers",
                    line={"color": line_color, "width": 3},
                    marker={"size": 8},
                    connectgaps=False,
                    customdata=customdata,
                    hoverinfo="skip",
                ),
                secondary_y=True,
            )

    period_rows = (
        frame[["period_start", "period_end", "period_label"]]
        .drop_duplicates()
        .sort_values("period_start")
    )
    period_lookup = {
        (row.period_label, row.metric_normalized): (row.display_sum, row.display_average)
        for row in frame.itertuples()
    }
    hover_rows = [
        [
            period_lookup.get((row.period_label, "Tổng số"), ("—", "—"))[0],
            period_lookup.get((row.period_label, "Báo sai/Lỗi"), ("—", "—"))[0],
            period_lookup.get((row.period_label, "Tổng số"), ("—", "—"))[1],
            period_lookup.get((row.period_label, "Báo sai/Lỗi"), ("—", "—"))[1],
            next(
                (
                    f"{period_row.observed_day_count}/{period_row.calendar_day_count}"
                    for period_row in frame.itertuples()
                    if period_row.period_label == row.period_label
                ),
                "—",
            ),
            f"{row.period_start:%d/%m}–{row.period_end:%d/%m}",
        ]
        for row in period_rows.itertuples()
    ]
    hover_lines: list[str] = ["Số ngày có dữ liệu: %{customdata[4]}"]
    if group_by == "week":
        hover_lines.insert(0, "Khoảng tuần: %{customdata[5]}")
    if "SUM" in modes:
        hover_lines.extend([
            "<span style='color:#8ecae6'>■</span> Tổng số/Cảnh báo · SUM: %{customdata[0]}",
            "<span style='color:#d1495b'>■</span> Báo sai/Lỗi · SUM: %{customdata[1]}",
        ])
    if "AVG/ngày" in modes:
        hover_lines.extend([
            "<span style='color:#0077b6'>━●━</span> Tổng số/Cảnh báo · AVG/ngày: %{customdata[2]}",
            "<span style='color:#9d0208'>━●━</span> Báo sai/Lỗi · AVG/ngày: %{customdata[3]}",
        ])
    hover_by_period = dict(zip(period_rows["period_label"], hover_rows))
    hovertemplate = "<b>%{x}</b><br>" + "<br>".join(hover_lines) + "<extra></extra>"
    for trace in figure.data:
        trace.customdata = [hover_by_period[str(label)] for label in trace.x]
        trace.hoverinfo = None
        trace.hovertemplate = hovertemplate
    entity_label = str(frame["entity_label"].iloc[0])
    unit = str(frame["effective_unit"].iloc[0])
    figure.update_layout(
        title=title or f"Thống kê theo kỳ — {entity_label}",
        barmode="overlay",
        bargap=0.25,
        bargroupgap=0.08,
        hovermode="closest",
        hoverdistance=5,
        hoverlabel={"namelength": -1},
        legend=_interactive_legend(),
        margin={"t": 100},
        xaxis_title="Kỳ",
    )
    figure.update_xaxes(showspikes=False)
    figure.update_yaxes(title_text=f"SUM ({unit})", rangemode="tozero", secondary_y=False)
    figure.update_yaxes(title_text=f"AVG/ngày ({unit})", rangemode="tozero", secondary_y=True)
    return figure


def build_line_chart(data: pd.DataFrame, title: str = "Xu hướng theo thời gian") -> Figure:
    frame = chartable(data).sort_values("date")
    figure = px.line(
        frame, x="date", y="chart_value", color="entity_label", markers=True, text="display_value",
        custom_data=["display_value", "metric_normalized", "effective_unit"],
        title=title, labels={"chart_value": "Giá trị", "date": "Ngày", "entity_label": "Đối tượng"},
    )
    figure.update_traces(
        mode="lines+markers+text",
        textposition="top center",
        textfont_size=10,
        cliponaxis=False,
        hovertemplate=(
            "<b>%{fullData.name}</b><br>%{customdata[1]}: %{customdata[0]}"
            "<br>Unit: %{customdata[2]}<extra></extra>"
        ),
    )
    figure.update_layout(margin={"t": 90})
    return _enable_unified_date_hover(_format_date_axes(_keep_latest_trace_labels(figure)))


def build_bar_chart(data: pd.DataFrame, selected_date=None, title: str = "So sánh tại một ngày") -> Figure:
    frame = chartable(data)
    if frame.empty:
        return px.bar(title=title)
    target_date = pd.Timestamp(selected_date) if selected_date is not None else frame["date"].max()
    frame = frame[frame["date"] == target_date].sort_values("chart_value", ascending=False)
    figure = px.bar(
        frame, x="entity_label", y="chart_value", color="entity_label", text="display_value",
        custom_data=["display_value", "metric_normalized", "effective_unit"],
        title=f"{title} — {target_date:%d/%m}",
        labels={"chart_value": "Giá trị", "entity_label": "Đối tượng"},
    )
    figure.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Entity: %{x}<br>Metric: %{customdata[1]}"
            "<br>Giá trị: %{customdata[0]}<br>Unit: %{customdata[2]}<extra></extra>"
        ),
    )
    return _format_date_axes(figure)


def build_period_metric_combo_chart(
    data: pd.DataFrame,
    start_date,
    end_date,
    group_by: str,
    title: str | None = None,
    prepared_frame: pd.DataFrame | None = None,
) -> Figure:
    """Compare overview metrics across calendar weeks or calendar months."""
    frame = prepared_frame if prepared_frame is not None else prepare_period_metric_summary(
        data, start_date, end_date, group_by
    )
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    if frame.empty:
        return figure

    entity_ids = frame["entity_id"].dropna().unique()
    units = frame["effective_unit"].dropna().unique()
    if len(entity_ids) != 1:
        raise ValueError("Combo chart theo kỳ chỉ nhận dữ liệu của đúng một entity.")
    if len(units) > 1:
        raise ValueError("Combo chart theo kỳ không được trộn nhiều effective unit.")

    frame = frame.sort_values("period_start")
    entity_label = str(frame["entity_label"].iloc[0])
    unit = str(units[0]) if len(units) else "Không xác định"
    x_values = frame["period_label"]
    hover_rows = frame[
        ["entity_label", "display_total", "display_error", "display_rate", "period_range"]
    ].to_numpy()
    hovertemplate = (
        "<b>%{x}</b><br>Khoảng: %{customdata[4]}"
        "<br><span style='color:#8ecae6'>■</span> Tổng số/Cảnh báo: %{customdata[1]}"
        "<br><span style='color:#d1495b'>■</span> Báo sai/Lỗi: %{customdata[2]}"
        "<br><span style='color:#ff9f1c'>━●━</span> % báo sai: %{customdata[3]}"
        "<extra></extra>"
    )
    for column, name, color, opacity, position in [
        ("total_sum", "Tổng số", "#8ecae6", 0.72, "inside"),
        ("error_sum", "Báo sai/Lỗi", "#d1495b", 0.95, "outside"),
    ]:
        figure.add_trace(
            go.Bar(
                x=x_values,
                y=frame[column],
                name=name,
                marker_color=color,
                opacity=opacity,
                width=0.72,
                text=_latest_labels(
                    frame["display_total" if column == "total_sum" else "display_error"]
                ),
                textposition=position,
                cliponaxis=False,
                customdata=hover_rows,
                hovertemplate=hovertemplate,
            ),
            secondary_y=False,
        )

    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=frame["error_rate"],
            name="% báo sai",
            mode="lines+markers+text",
            line={"color": "#ff9f1c", "width": 3},
            marker={"size": 8},
            text=_latest_labels(frame["display_rate"]),
            textposition="top center",
            cliponaxis=False,
            connectgaps=False,
            customdata=hover_rows,
            hovertemplate=hovertemplate,
        ),
        secondary_y=True,
    )
    figure.update_layout(
        title=title or f"{entity_label} — {unit}",
        barmode="overlay",
        bargap=0.25,
        bargroupgap=0.08,
        hovermode="closest",
        hoverdistance=5,
        hoverlabel={"namelength": -1},
        legend=_interactive_legend(),
        margin={"t": 100},
        xaxis_title="Tuần" if group_by == "week" else "Tháng",
    )
    figure.update_xaxes(showspikes=False)
    figure.update_yaxes(title_text=f"Số lượng ({unit})", rangemode="tozero", secondary_y=False)
    figure.update_yaxes(
        title_text="% báo sai",
        rangemode="tozero",
        tickformat=".1f",
        ticksuffix="%",
        secondary_y=True,
    )
    return figure


def build_metric_combo_chart(data: pd.DataFrame, title: str | None = None) -> Figure:
    """Render Error inside Total bars and Error Rate on a secondary Y axis."""
    frame = chartable(data)
    if frame.empty:
        return make_subplots(specs=[[{"secondary_y": True}]])

    entity_ids = frame["entity_id"].dropna().unique()
    units = frame["effective_unit"].dropna().unique()
    if len(entity_ids) != 1:
        raise ValueError("Combo chart chỉ nhận dữ liệu của đúng một entity.")
    if len(units) > 1:
        raise ValueError("Combo chart không được trộn nhiều effective unit.")

    entity_label = str(frame["entity_label"].iloc[0])
    entity_id = str(entity_ids[0])
    unit = str(units[0]) if len(units) else "Không xác định"
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    hover_lookup = _metric_hover_lookup(data, entity_id)
    hovertemplate = "<b>Ngày %{x|%d/%m/%Y}</b><br>" + COMBO_HOVER_TEMPLATE
    metric_specs = [
        ("Tổng số", "Tổng số", "#8ecae6", 0.72, 18 * 60 * 60 * 1000),
        ("Báo sai/Lỗi", "Báo sai/Lỗi", "#d1495b", 0.95, 18 * 60 * 60 * 1000),
    ]
    for metric, name, color, opacity, width in metric_specs:
        metric_data = frame[frame["metric_normalized"] == metric].sort_values("date")
        if metric_data.empty:
            continue
        hover_rows = [
            _hover_row(hover_lookup, date, entity_label)
            for date in metric_data["date"]
        ]
        figure.add_trace(
            go.Bar(
                x=metric_data["date"],
                y=metric_data["chart_value"],
                name=name,
                marker_color=color,
                opacity=opacity,
                width=width,
                text=_latest_labels(metric_data["display_value"]),
                textposition="outside" if metric == "Báo sai/Lỗi" else "inside",
                cliponaxis=False,
                customdata=hover_rows,
                hovertemplate=hovertemplate,
                **_exact_lineage_fields(metric_data),
            ),
            secondary_y=False,
        )

    rate_data = frame[frame["metric_normalized"] == "% báo sai"].sort_values("date")
    if not rate_data.empty:
        hover_rows = [
            _hover_row(hover_lookup, date, entity_label)
            for date in rate_data["date"]
        ]
        figure.add_trace(
            go.Scatter(
                x=rate_data["date"],
                y=rate_data["chart_value"],
                name="% báo sai",
                mode="lines+markers+text",
                line={"color": "#ff9f1c", "width": 3},
                marker={"size": 8},
                text=_latest_labels(rate_data["display_value"]),
                textposition="top center",
                cliponaxis=False,
                connectgaps=False,
                customdata=hover_rows,
                hovertemplate=hovertemplate,
                **_exact_lineage_fields(rate_data),
            ),
            secondary_y=True,
        )

    figure.update_layout(
        title=title or f"{entity_label} — {unit}",
        barmode="overlay",
        bargap=0.25,
        bargroupgap=0.08,
        legend=_interactive_legend(),
        margin={"t": 100},
        xaxis_title="Ngày",
        hovermode="closest",
        hoverdistance=5,
        hoverlabel={"namelength": -1},
    )
    figure.update_yaxes(title_text=f"Số lượng ({unit})", rangemode="tozero", secondary_y=False)
    figure.update_yaxes(
        title_text="% báo sai",
        rangemode="tozero",
        tickformat=".1f",
        ticksuffix="%",
        secondary_y=True,
    )
    figure.update_xaxes(showspikes=False)
    return _format_date_axes(figure)


def build_multi_entity_metric_chart(
    data: pd.DataFrame,
    metric: str,
    title: str | None = None,
    group_by: str | None = None,
    start_date=None,
    end_date=None,
) -> Figure:
    """Compare one selected metric for up to three compatible entities."""
    if group_by is not None:
        if data.empty:
            return go.Figure()
        if "project_id" in data.columns and data["project_id"].nunique() != 1:
            raise ValueError("Các entity so sánh phải thuộc cùng một Project.")
        date_values = pd.to_datetime(data["date"])
        period_frame = prepare_period_metric_summary(
            data,
            start_date if start_date is not None else date_values.min(),
            end_date if end_date is not None else date_values.max(),
            group_by,
        )
        value_columns = {
            "Tổng số": ("total_sum", "display_total"),
            "Báo sai/Lỗi": ("error_sum", "display_error"),
            "% báo sai": ("error_rate", "display_rate"),
        }
        if metric not in value_columns:
            raise ValueError(f"Metric không được hỗ trợ: {metric}")
        value_column, display_column = value_columns[metric]
        frame = period_frame[period_frame[value_column].notna()].copy()
        if frame.empty:
            return go.Figure()

        entity_ids = list(frame["entity_id"].dropna().unique())
        if len(entity_ids) > 3:
            raise ValueError("Chỉ được so sánh tối đa 3 entity.")
        units = frame["effective_unit"].dropna().unique()
        if frame["effective_unit"].isna().any() or len(units) != 1:
            raise ValueError("Các entity so sánh phải có cùng một effective unit đã xác định.")

        unit = str(units[0])
        figure = go.Figure()
        for color_index, entity_id in enumerate(entity_ids):
            entity_data = frame[frame["entity_id"] == entity_id].sort_values("period_start")
            entity_label = str(entity_data["entity_label"].iloc[0])
            entity_level = str(entity_data["entity_level"].iloc[0])
            level_label = ENTITY_LEVEL_LABELS.get(entity_level, entity_level.title())
            legend_label = f"[{level_label}] {entity_label}"
            color = ENTITY_COLORS[color_index]
            hover_rows = entity_data[
                ["entity_label", "display_total", "display_error", "display_rate"]
            ].to_numpy()
            common = {
                "x": entity_data["period_label"],
                "y": entity_data[value_column],
                "name": legend_label,
                "legendgroup": entity_id,
                "customdata": hover_rows,
                "hovertemplate": ENTITY_HOVER_TEMPLATE,
            }
            if metric == "% báo sai":
                figure.add_trace(
                    go.Scatter(
                        **common,
                        mode="lines+markers+text",
                        line={"color": color, "width": 3},
                        marker={"size": 8},
                        text=_latest_labels(entity_data[display_column]),
                        textposition="top center",
                        cliponaxis=False,
                        connectgaps=False,
                    )
                )
            else:
                figure.add_trace(
                    go.Bar(
                        **common,
                        marker_color=color,
                        text=_latest_labels(entity_data[display_column]),
                        textposition="outside",
                        cliponaxis=False,
                    )
                )

        figure.update_layout(
            title=title or f"So sánh {metric} — {unit}",
            barmode="group",
            bargap=0.25,
            bargroupgap=0.08,
            hovermode="x unified",
            hoverdistance=20,
            hoverlabel={"namelength": -1},
            legend=_interactive_legend(),
            margin={"t": 100},
            xaxis_title="Tuần" if group_by == "week" else "Tháng",
            yaxis_title="% báo sai" if metric == "% báo sai" else f"{metric} ({unit})",
            yaxis={"rangemode": "tozero"},
        )
        figure.update_xaxes(showspikes=False, unifiedhovertitle={"text": "<b>%{x}</b>"})
        if metric == "% báo sai":
            figure.update_yaxes(tickformat=".1f", ticksuffix="%")
        return figure

    hover_source = data.copy()
    hover_source["date"] = pd.to_datetime(hover_source["date"])
    frame = chartable(data)
    frame = frame[frame["metric_normalized"] == metric]
    if frame.empty:
        return go.Figure()

    entity_ids = list(frame["entity_id"].dropna().unique())
    if len(entity_ids) > 3:
        raise ValueError("Chỉ được so sánh tối đa 3 entity.")

    units = frame["effective_unit"].dropna().unique()
    if frame["effective_unit"].isna().any() or len(units) != 1:
        raise ValueError("Các entity so sánh phải có cùng một effective unit đã xác định.")

    if "project_id" in frame.columns and frame["project_id"].nunique() != 1:
        raise ValueError("Các entity so sánh phải thuộc cùng một Project.")

    unit = str(units[0])
    figure = go.Figure()
    for color_index, entity_id in enumerate(entity_ids):
        entity_data = frame[frame["entity_id"] == entity_id].sort_values("date")
        entity_label = str(entity_data["entity_label"].iloc[0])
        entity_level = str(entity_data["entity_level"].iloc[0])
        level_label = ENTITY_LEVEL_LABELS.get(entity_level, entity_level.title())
        legend_label = f"[{level_label}] {entity_label}"
        color = ENTITY_COLORS[color_index]
        hover_lookup = _metric_hover_lookup(hover_source, entity_id)
        hover_rows = [
            _hover_row(hover_lookup, date, entity_label)
            for date in entity_data["date"]
        ]
        if metric == "% báo sai":
            figure.add_trace(
                go.Scatter(
                    x=entity_data["date"],
                    y=entity_data["chart_value"],
                    name=legend_label,
                    legendgroup=entity_id,
                    mode="lines+markers+text",
                    line={"color": color, "width": 3},
                    marker={"size": 8},
                    text=_latest_labels(entity_data["display_value"]),
                    textposition="top center",
                    cliponaxis=False,
                    connectgaps=False,
                    customdata=hover_rows,
                    hovertemplate=ENTITY_HOVER_TEMPLATE,
                    **_exact_lineage_fields(entity_data),
                )
            )
        else:
            figure.add_trace(
                go.Bar(
                    x=entity_data["date"],
                    y=entity_data["chart_value"],
                    name=legend_label,
                    legendgroup=entity_id,
                    marker_color=color,
                    text=_latest_labels(entity_data["display_value"]),
                    textposition="outside",
                    cliponaxis=False,
                    customdata=hover_rows,
                    hovertemplate=ENTITY_HOVER_TEMPLATE,
                    **_exact_lineage_fields(entity_data),
                )
            )

    figure.update_layout(
        title=title or f"So sánh {metric} — {unit}",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        legend=_interactive_legend(),
        margin={"t": 100},
        xaxis_title="Ngày",
        yaxis_title="% báo sai" if metric == "% báo sai" else f"{metric} ({unit})",
        yaxis={"rangemode": "tozero"},
    )
    if metric == "% báo sai":
        figure.update_yaxes(tickformat=".1f", ticksuffix="%")
    return _enable_unified_date_hover(_format_date_axes(figure))
