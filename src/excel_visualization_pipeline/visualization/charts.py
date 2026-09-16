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
    """Return a compact value while keeping source-state detail separate."""
    value_kind = getattr(row, "value_kind", None)
    if value_kind == "not_recorded":
        return "—"
    if value_kind == "source_marker":
        display_value = getattr(row, "display_value", None)
        marker = str(display_value).strip() if pd.notna(display_value) else "-"
        return marker or "-"
    if value_kind == "default_zero_rate":
        return "0%"
    display_value = getattr(row, "display_value", None)
    if pd.isna(display_value) or not str(display_value).strip():
        return "—"
    return str(display_value)


def _hover_data_note(row) -> str:
    """Return the business description associated with one metric value."""
    data_note = getattr(row, "data_note", None)
    if pd.isna(data_note) or not str(data_note).strip():
        value_kind = getattr(row, "value_kind", None)
        fallback_notes = {
            "not_recorded": "Không ghi nhận trong ngày",
            "source_marker": "Đánh dấu dữ liệu khác bản chất từ nguồn",
            "default_zero_rate": "Mặc định 0% vì Báo sai/Lỗi không ghi nhận hoặc bằng 0",
        }
        return fallback_notes.get(value_kind, "—")
    note = str(data_note)
    if "nhưng Báo sai/Lỗi" in note:
        return f"⚠ Không nhất quán — {note}"
    return note


def _metric_hover_lookup(
    data: pd.DataFrame,
    entity_id: str,
) -> dict[tuple[pd.Timestamp, str], tuple[str, str]]:
    lookup: dict[tuple[pd.Timestamp, str], tuple[str, str]] = {}
    entity_data = data[data["entity_id"] == entity_id]
    for row in entity_data.itertuples():
        if row.metric_normalized not in {"Tổng số", "Báo sai/Lỗi", "% báo sai"}:
            continue
        lookup[(pd.Timestamp(row.date), row.metric_normalized)] = (
            _hover_display_value(row),
            _hover_data_note(row),
        )
    return lookup


def _hover_row(
    lookup: dict[tuple[pd.Timestamp, str], tuple[str, str]],
    date,
    entity_label: str,
) -> list[str]:
    target_date = pd.Timestamp(date)
    total = lookup.get((target_date, "Tổng số"), ("—", "Không ghi nhận trong ngày"))
    error = lookup.get((target_date, "Báo sai/Lỗi"), ("—", "Không ghi nhận trong ngày"))
    rate = lookup.get((target_date, "% báo sai"), ("—", "Không ghi nhận trong ngày"))
    return [entity_label, total[0], error[0], rate[0], total[1], error[1], rate[1]]


ENTITY_HOVER_TEMPLATE = (
    "<b>%{customdata[0]}</b>"
    "<br><span style='color:#8ecae6'>■</span> Tổng số/Cảnh báo: %{customdata[1]}"
    "<br><i>Mô tả: %{customdata[4]}</i>"
    "<br><span style='color:#d1495b'>■</span> Báo sai/Lỗi: %{customdata[2]}"
    "<br><i>Mô tả: %{customdata[5]}</i>"
    "<br><span style='color:#ff9f1c'>━●━</span> % báo sai: %{customdata[3]}"
    "<br><i>Mô tả: %{customdata[6]}</i><extra></extra>"
)

COMBO_HOVER_TEMPLATE = (
    "<span style='color:#8ecae6'>■</span> Tổng số/Cảnh báo: %{customdata[1]}"
    "<br><i>Mô tả: %{customdata[4]}</i>"
    "<br><span style='color:#d1495b'>■</span> Báo sai/Lỗi: %{customdata[2]}"
    "<br><i>Mô tả: %{customdata[5]}</i>"
    "<br><span style='color:#ff9f1c'>━●━</span> % báo sai: %{customdata[3]}"
    "<br><i>Mô tả: %{customdata[6]}</i><extra></extra>"
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


def prepare_metric_averages(data: pd.DataFrame) -> pd.DataFrame:
    """Average count metrics per entity over dates that contain source data."""
    frame = chartable(data)
    frame = frame[frame["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi"])].copy()
    if frame.empty:
        return pd.DataFrame()

    frame["effective_unit"] = frame["effective_unit"].fillna("Chưa xác định từ Excel")
    grouped = (
        frame.groupby(
            ["entity_id", "entity_label", "entity_level", "effective_unit", "metric_normalized"],
            dropna=False,
            as_index=False,
        )
        .agg(
            average_value=("chart_value", "mean"),
            data_date_count=("date", "nunique"),
        )
    )
    grouped["display_value"] = grouped["average_value"].map(_formatted_number)
    grouped["calculation_method"] = grouped.apply(
        lambda row: f"Trung bình trên {row['data_date_count']} ngày có dữ liệu",
        axis=1,
    )
    grouped["entity_display"] = grouped.apply(
        lambda row: (
            f"[{ENTITY_LEVEL_LABELS.get(str(row['entity_level']), str(row['entity_level']).title())}] "
            f"{row['entity_label']}"
        ),
        axis=1,
    )
    return grouped


def build_metric_average_chart(
    data: pd.DataFrame,
    start_date=None,
    end_date=None,
) -> Figure:
    """Render average Total and Error values, separating incompatible units."""
    frame = prepare_metric_averages(data)
    if start_date is not None and end_date is not None:
        title = f"Trung bình — {pd.Timestamp(start_date):%d/%m} đến {pd.Timestamp(end_date):%d/%m}"
    else:
        title = "Trung bình trong khoảng đã chọn"
    if frame.empty:
        return px.bar(title=title)

    figure = px.bar(
        frame,
        x="entity_display",
        y="average_value",
        color="metric_normalized",
        barmode="group",
        facet_col="effective_unit" if frame["effective_unit"].nunique() > 1 else None,
        text="display_value",
        custom_data=["display_value", "data_date_count"],
        title=title,
        labels={
            "entity_display": "Entity",
            "average_value": "Giá trị trung bình",
            "metric_normalized": "Metric",
            "effective_unit": "Effective Unit",
        },
        color_discrete_map={"Tổng số": "#8ecae6", "Báo sai/Lỗi": "#d1495b"},
    )
    figure.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "Entity: %{x}<br>Trung bình: %{customdata[0]}"
            "<br>Số ngày dữ liệu: %{customdata[1]}<extra></extra>"
        ),
    )
    figure.update_layout(margin={"t": 100}, hovermode="closest")
    figure.for_each_yaxis(lambda axis: axis.update(matches=None, rangemode="tozero"))
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
    metric_specs = [
        ("Tổng số", "Tổng số", "#8ecae6", 0.72, 18 * 60 * 60 * 1000),
        ("Báo sai/Lỗi", "Báo sai/Lỗi", "#d1495b", 0.95, 9 * 60 * 60 * 1000),
    ]
    for metric, name, color, opacity, width in metric_specs:
        metric_data = frame[frame["metric_normalized"] == metric].sort_values("date")
        if metric_data.empty:
            continue
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
                hoverinfo="skip",
            ),
            secondary_y=False,
        )

    rate_data = frame[frame["metric_normalized"] == "% báo sai"].sort_values("date")
    if not rate_data.empty:
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
                hoverinfo="skip",
            ),
            secondary_y=True,
        )

    hover_lookup = _metric_hover_lookup(data, entity_id)
    hover_dates = sorted(
        pd.to_datetime(
            data.loc[
                (data["entity_id"] == entity_id)
                & data["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi", "% báo sai"]),
                "date",
            ]
        ).unique()
    )
    figure.add_trace(
        go.Scatter(
            x=hover_dates,
            y=[0] * len(hover_dates),
            name="",
            mode="markers",
            marker={"size": 1, "opacity": 0},
            showlegend=False,
            customdata=[_hover_row(hover_lookup, date, entity_label) for date in hover_dates],
            hovertemplate=COMBO_HOVER_TEMPLATE,
        ),
        secondary_y=False,
    )

    figure.update_layout(
        title=title or f"{entity_label} — {unit}",
        barmode="overlay",
        bargap=0.25,
        bargroupgap=0.08,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"t": 110},
        xaxis_title="Ngày",
    )
    figure.update_yaxes(title_text=f"Số lượng ({unit})", rangemode="tozero", secondary_y=False)
    figure.update_yaxes(
        title_text="% báo sai",
        rangemode="tozero",
        tickformat=".1f",
        ticksuffix="%",
        secondary_y=True,
    )
    return _enable_unified_date_hover(_format_date_axes(figure))


def build_multi_entity_metric_chart(
    data: pd.DataFrame,
    metric: str,
    title: str | None = None,
) -> Figure:
    """Compare one selected metric for up to three compatible entities."""
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
                )
            )

    figure.update_layout(
        title=title or f"So sánh {metric} — {unit}",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"t": 110},
        xaxis_title="Ngày",
        yaxis_title="% báo sai" if metric == "% báo sai" else f"{metric} ({unit})",
        yaxis={"rangemode": "tozero"},
    )
    if metric == "% báo sai":
        figure.update_yaxes(tickformat=".1f", ticksuffix="%")
    return _enable_unified_date_hover(_format_date_axes(figure))
