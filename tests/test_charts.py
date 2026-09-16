import pytest
import pandas as pd

from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.visualization import (
    build_bar_chart,
    build_line_chart,
    build_metric_average_chart,
    build_metric_combo_chart,
    build_multi_entity_metric_chart,
    build_project_total_chart,
    prepare_project_totals,
    prepare_project_totals_range,
    prepare_metric_averages,
)


def test_combo_chart_overlays_counts_and_uses_secondary_axis(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"]

    figure = build_metric_combo_chart(item_data)

    assert [trace.type for trace in figure.data] == ["bar", "bar", "scatter"]
    assert [trace.name for trace in figure.data] == ["Tổng số", "Báo sai/Lỗi", "% báo sai"]
    assert figure.layout.barmode == "overlay"
    assert figure.data[0].width > figure.data[1].width
    assert figure.layout.xaxis.tickformat == "%d/%m"
    assert figure.data[2].yaxis == "y2"
    assert figure.layout.yaxis2.tickformat == ".1f"
    assert figure.layout.yaxis2.ticksuffix == "%"
    assert list(figure.data[0].text) == ["", "120"]
    assert list(figure.data[1].text) == ["", "6"]
    assert list(figure.data[2].text) == ["", "5.00%"]
    assert figure.layout.hovermode == "x unified"
    assert figure.layout.hoverdistance == -1
    assert figure.layout.xaxis.unifiedhovertitle.text == "<b>Ngày %{x|%d/%m/%Y}</b>"
    assert "Tổng số/Cảnh báo" in figure.data[0].hovertemplate
    assert "Báo sai/Lỗi" in figure.data[1].hovertemplate
    assert "% báo sai" in figure.data[2].hovertemplate


def test_combo_chart_rejects_multiple_entities(sample_workbook):
    data = run_pipeline(sample_workbook).data
    mixed_entities = data[data["chart_value"].notna()].copy()
    mixed_entities.loc[mixed_entities.index[0], "entity_id"] = "synthetic-other"

    with pytest.raises(ValueError, match="một entity"):
        build_metric_combo_chart(mixed_entities)


def test_metric_average_excludes_percentage_and_counts_data_dates(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"]

    averages = prepare_metric_averages(item_data).set_index("metric_normalized")
    figure = build_metric_average_chart(item_data, "2026-09-12", "2026-09-13")

    assert set(averages.index) == {"Tổng số", "Báo sai/Lỗi"}
    assert averages.loc["Tổng số", "average_value"] == 110
    assert averages.loc["Báo sai/Lỗi", "average_value"] == 7
    assert averages.loc["Tổng số", "data_date_count"] == 2
    assert len(figure.data) == 2
    assert all(trace.type == "bar" for trace in figure.data)
    assert {trace.name for trace in figure.data} == {"Tổng số", "Báo sai/Lỗi"}


def test_multi_entity_metric_chart_renders_three_bar_groups(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    frames = []
    for entity_id, label in [("camera-a", "Camera A"), ("camera-b", "Camera B"), ("camera-c", "Camera C")]:
        clone = item_data.copy()
        clone["entity_id"] = entity_id
        clone["entity_label"] = label
        frames.append(clone)

    figure = build_multi_entity_metric_chart(
        pd.concat(frames, ignore_index=True),
        "Báo sai/Lỗi",
    )

    assert len(figure.data) == 3
    assert figure.layout.barmode == "group"
    assert len({trace.legendgroup for trace in figure.data}) == 3
    assert figure.layout.hovermode == "x unified"
    assert all("Tổng số/Cảnh báo" in trace.hovertemplate for trace in figure.data)
    assert all("Báo sai/Lỗi" in trace.hovertemplate for trace in figure.data)
    assert all("% báo sai" in trace.hovertemplate for trace in figure.data)
    assert list(figure.data[0].customdata[0]) == ["Camera A", "100", "8", "8.00%"]
    assert all(trace.type == "bar" for trace in figure.data)
    assert all("% báo sai" not in trace.name and "Tổng số" not in trace.name for trace in figure.data)
    assert all(trace.name.startswith("[Item]") for trace in figure.data)


def test_multi_entity_metric_chart_enforces_limit_unit_and_project(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    frames = []
    for index in range(4):
        clone = item_data.copy()
        clone["entity_id"] = f"entity-{index}"
        clone["entity_label"] = f"Entity {index}"
        frames.append(clone)

    with pytest.raises(ValueError, match="tối đa 3"):
        build_multi_entity_metric_chart(pd.concat(frames, ignore_index=True), "Tổng số")

    mixed_unit = pd.concat(frames[:2], ignore_index=True)
    mixed_unit.loc[mixed_unit["entity_id"] == "entity-1", "effective_unit"] = "Unit khác"
    with pytest.raises(ValueError, match="cùng một effective unit"):
        build_multi_entity_metric_chart(mixed_unit, "Tổng số")

    mixed_project = pd.concat(frames[:2], ignore_index=True)
    mixed_project.loc[mixed_project["entity_id"] == "entity-1", "project_id"] = "project-khac"
    with pytest.raises(ValueError, match="cùng một Project"):
        build_multi_entity_metric_chart(mixed_project, "Tổng số")


def test_multi_entity_metric_chart_allows_mixed_hierarchy_levels(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    parent = item_data.copy()
    parent["entity_id"] = "parent"
    parent["entity_label"] = "Alpha"
    parent["entity_level"] = "project"
    parent["entity_depth"] = 0
    child = item_data.copy()
    child["entity_id"] = "child"
    child["entity_label"] = "Camera"

    figure = build_multi_entity_metric_chart(
        pd.concat([parent, child], ignore_index=True),
        "Báo sai/Lỗi",
    )

    assert len(figure.data) == 2
    assert any(trace.name.startswith("[Project] Alpha") for trace in figure.data)
    assert any(trace.name.startswith("[Item] Camera") for trace in figure.data)


def test_multi_entity_percentage_metric_uses_lines(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    second = item_data.copy()
    second["entity_id"] = "camera-b"
    second["entity_label"] = "Camera B"

    figure = build_multi_entity_metric_chart(
        pd.concat([item_data, second], ignore_index=True),
        "% báo sai",
    )

    assert len(figure.data) == 2
    assert all(trace.type == "scatter" for trace in figure.data)
    assert all("text" in trace.mode for trace in figure.data)
    assert figure.layout.yaxis.ticksuffix == "%"
    assert figure.layout.xaxis.tickformat == "%d/%m"


def test_multi_entity_unified_hover_preserves_missing_values(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    missing_error = (
        (item_data["metric_normalized"] == "Báo sai/Lỗi")
        & (pd.to_datetime(item_data["date"]) == pd.Timestamp("2026-09-12"))
    )
    item_data.loc[missing_error, "chart_value"] = None
    item_data.loc[missing_error, "display_value"] = ""

    figure = build_multi_entity_metric_chart(item_data, "Tổng số")

    assert list(figure.data[0].customdata[0]) == [
        "Camera",
        "100",
        "Không có dữ liệu",
        "8.00%",
    ]
    assert "0" not in figure.data[0].customdata[0][2]


def test_all_demo_charts_render(sample_workbook):
    data = run_pipeline(sample_workbook).data
    data = data[(data["metric_normalized"] == "% báo sai") & (data["entity_level"] == "item")]
    line = build_line_chart(data)
    bar = build_bar_chart(data)
    assert len(line.data) > 0
    assert len(bar.data) > 0
    assert list(line.data[0].text) == ["", "5.00%"]
    assert list(bar.data[0].text) == ["5.00%"]
    assert "text" in line.data[0].mode
    assert line.layout.xaxis.tickformat == "%d/%m"
    assert line.layout.hovermode == "x unified"
    assert "%{customdata[1]}" in line.data[0].hovertemplate
    assert "Giá trị" in bar.data[0].hovertemplate


def test_project_overview_uses_item_fallback_without_mixing_levels(sample_workbook):
    data = run_pipeline(sample_workbook).data
    overview = prepare_project_totals(data, "2026-09-12")
    assert len(overview) == 1
    assert overview.iloc[0]["project"] == "Alpha"
    assert overview.iloc[0]["chart_value"] == 100
    assert overview.iloc[0]["source_level"] == "item"
    assert overview.iloc[0]["source_count"] == 1
    figure = build_project_total_chart(data, "2026-09-12")
    assert len(figure.data) > 0
    assert list(figure.data[0].text) == ["100"]
    assert "text" in figure.data[0].mode
    assert figure.layout.hovermode == "x unified"
    assert "Tổng số" in figure.data[0].hovertemplate
    assert figure.layout.xaxis.tickformat == "%d/%m"


def test_project_overview_supports_from_and_to_dates(sample_workbook):
    data = run_pipeline(sample_workbook).data
    overview = prepare_project_totals_range(data, "2026-09-12", "2026-09-13")
    assert len(overview) == 2
    assert set(overview["chart_value"]) == {100.0, 120.0}
    assert len(build_project_total_chart(data, "2026-09-12", "2026-09-13").data) > 0
