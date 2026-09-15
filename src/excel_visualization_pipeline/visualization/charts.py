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


def _formatted_number(value: float) -> str:
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


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
    title = f"Tổng số — {scope} — {pd.Timestamp(start_date):%d/%m/%Y} đến {pd.Timestamp(end_date):%d/%m/%Y}"
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
        title=title,
        labels={"project": "Project", "chart_value": "Tổng số", "unit": "Đơn vị", "date": "Ngày"},
    )
    figure.update_traces(
        mode="lines+markers+text",
        textposition="top center",
        textfont_size=11,
        cliponaxis=False,
        hoverinfo="skip",
        hovertemplate=None,
    )
    figure.update_layout(margin={"t": 90})
    figure.for_each_yaxis(lambda axis: axis.update(matches=None))
    return figure


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


def prepare_descriptive_statistics(data: pd.DataFrame) -> pd.DataFrame:
    """Describe the distribution of count metrics without aggregating percentages."""
    frame = chartable(data)
    frame = frame[frame["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi"])].copy()
    if frame.empty:
        return pd.DataFrame()

    frame["effective_unit"] = frame["effective_unit"].fillna("Chưa xác định từ Excel")
    group_columns = [
        "entity_id",
        "entity_label",
        "entity_level",
        "effective_unit",
        "metric_normalized",
    ]
    grouped = (
        frame.groupby(group_columns, dropna=False)["chart_value"]
        .agg(
            data_point_count="count",
            mean="mean",
            median="median",
            minimum="min",
            q1=lambda values: values.quantile(0.25),
            q3=lambda values: values.quantile(0.75),
            maximum="max",
            standard_deviation="std",
        )
        .reset_index()
    )
    date_counts = (
        frame.groupby(group_columns, dropna=False)["date"]
        .nunique()
        .rename("data_date_count")
        .reset_index()
    )
    grouped = grouped.merge(date_counts, on=group_columns, how="left")
    grouped["entity_display"] = grouped.apply(
        lambda row: (
            f"[{ENTITY_LEVEL_LABELS.get(str(row['entity_level']), str(row['entity_level']).title())}] "
            f"{row['entity_label']}"
        ),
        axis=1,
    )
    for column in ["mean", "median", "minimum", "q1", "q3", "maximum", "standard_deviation"]:
        grouped[f"display_{column}"] = grouped[column].map(
            lambda value: _formatted_number(value) if pd.notna(value) else "N/A"
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
        title = f"Trung bình — {pd.Timestamp(start_date):%d/%m/%Y} đến {pd.Timestamp(end_date):%d/%m/%Y}"
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
        hoverinfo="skip",
        hovertemplate=None,
    )
    figure.update_layout(margin={"t": 100}, hovermode=False)
    figure.for_each_yaxis(lambda axis: axis.update(matches=None, rangemode="tozero"))
    return figure


def build_metric_box_plot(
    data: pd.DataFrame,
    metric: str,
    start_date=None,
    end_date=None,
) -> Figure:
    """Render one count metric as box plots, separated by unit."""
    if metric not in {"Tổng số", "Báo sai/Lỗi"}:
        raise ValueError("Box plot chỉ hỗ trợ Tổng số hoặc Báo sai/Lỗi.")
    frame = chartable(data)
    frame = frame[frame["metric_normalized"] == metric].copy()
    if start_date is not None and end_date is not None:
        title = f"Phân phối {metric} — {pd.Timestamp(start_date):%d/%m/%Y} đến {pd.Timestamp(end_date):%d/%m/%Y}"
    else:
        title = f"Phân phối {metric} trong khoảng đã chọn"
    if frame.empty:
        return px.box(title=title)

    frame["effective_unit"] = frame["effective_unit"].fillna("Chưa xác định từ Excel")
    frame["entity_display"] = frame.apply(
        lambda row: (
            f"[{ENTITY_LEVEL_LABELS.get(str(row['entity_level']), str(row['entity_level']).title())}] "
            f"{row['entity_label']}"
        ),
        axis=1,
    )
    metric_color = "#d1495b" if metric == "Báo sai/Lỗi" else "#8ecae6"
    figure = px.box(
        frame,
        x="entity_display",
        y="chart_value",
        color="entity_display",
        facet_col="effective_unit" if frame["effective_unit"].nunique() > 1 else None,
        points="all",
        title=title,
        labels={
            "entity_display": "Entity",
            "chart_value": metric,
            "effective_unit": "Effective Unit",
        },
        color_discrete_sequence=[metric_color],
    )
    figure.update_traces(hoverinfo="skip", hovertemplate=None)
    figure.update_layout(margin={"t": 100}, hovermode=False, showlegend=False)
    figure.for_each_yaxis(lambda axis: axis.update(matches=None, rangemode="tozero"))
    return figure


def build_line_chart(data: pd.DataFrame, title: str = "Xu hướng theo thời gian") -> Figure:
    frame = chartable(data).sort_values("date")
    figure = px.line(
        frame, x="date", y="chart_value", color="entity_label", markers=True, text="display_value",
        title=title, labels={"chart_value": "Giá trị", "date": "Ngày", "entity_label": "Đối tượng"},
    )
    figure.update_traces(
        mode="lines+markers+text",
        textposition="top center",
        textfont_size=10,
        cliponaxis=False,
        hoverinfo="skip",
        hovertemplate=None,
    )
    figure.update_layout(margin={"t": 90})
    return figure


def build_bar_chart(data: pd.DataFrame, selected_date=None, title: str = "So sánh tại một ngày") -> Figure:
    frame = chartable(data)
    if frame.empty:
        return px.bar(title=title)
    target_date = pd.Timestamp(selected_date) if selected_date is not None else frame["date"].max()
    frame = frame[frame["date"] == target_date].sort_values("chart_value", ascending=False)
    figure = px.bar(
        frame, x="entity_label", y="chart_value", color="entity_label", text="display_value",
        title=f"{title} — {target_date:%d/%m/%Y}",
        labels={"chart_value": "Giá trị", "entity_label": "Đối tượng"},
    )
    figure.update_traces(
        textposition="outside",
        cliponaxis=False,
        hoverinfo="skip",
        hovertemplate=None,
    )
    return figure


def build_metric_combo_chart(data: pd.DataFrame, title: str | None = None) -> Figure:
    """Render Total/Error as grouped bars and Error Rate on a secondary Y axis."""
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
    unit = str(units[0]) if len(units) else "Không xác định"
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    metric_specs = [
        ("Tổng số", "Tổng số", "#8ecae6", 0.85),
        ("Báo sai/Lỗi", "Báo sai/Lỗi", "#d1495b", 0.95),
    ]
    for metric, name, color, opacity in metric_specs:
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
                text=metric_data["display_value"],
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
                text=rate_data["display_value"],
                textposition="top center",
                cliponaxis=False,
                connectgaps=False,
                hoverinfo="skip",
            ),
            secondary_y=True,
        )

    figure.update_layout(
        title=title or f"{entity_label} — {unit}",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        hovermode=False,
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
    return figure


def build_multi_entity_metric_chart(
    data: pd.DataFrame,
    metric: str,
    title: str | None = None,
) -> Figure:
    """Compare one selected metric for up to three compatible entities."""
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
                    text=entity_data["display_value"],
                    textposition="top center",
                    cliponaxis=False,
                    connectgaps=False,
                    hoverinfo="skip",
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
                    text=entity_data["display_value"],
                    textposition="outside",
                    cliponaxis=False,
                    hoverinfo="skip",
                )
            )

    figure.update_layout(
        title=title or f"So sánh {metric} — {unit}",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        hovermode=False,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        margin={"t": 110},
        xaxis_title="Ngày",
        yaxis_title="% báo sai" if metric == "% báo sai" else f"{metric} ({unit})",
        yaxis={"rangemode": "tozero"},
    )
    if metric == "% báo sai":
        figure.update_yaxes(tickformat=".1f", ticksuffix="%")
    return figure
