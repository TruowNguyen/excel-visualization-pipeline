import pytest

from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.visualization import (
    build_bar_chart,
    build_line_chart,
    build_metric_combo_chart,
    build_project_total_chart,
    prepare_project_totals,
    prepare_project_totals_range,
)


def test_combo_chart_groups_counts_and_uses_secondary_axis(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"]

    figure = build_metric_combo_chart(item_data)

    assert [trace.type for trace in figure.data] == ["bar", "bar", "scatter"]
    assert [trace.name for trace in figure.data] == ["Tổng số", "Báo sai/Lỗi", "% báo sai"]
    assert figure.layout.barmode == "group"
    assert figure.data[2].yaxis == "y2"
    assert figure.layout.yaxis2.tickformat == ".1f"
    assert figure.layout.yaxis2.ticksuffix == "%"
    assert list(figure.data[0].text) == ["100", "120"]
    assert list(figure.data[1].text) == ["8", "6"]
    assert list(figure.data[2].text) == ["8.00%", "5.00%"]
    assert all(trace.hoverinfo == "skip" for trace in figure.data)


def test_combo_chart_rejects_multiple_entities(sample_workbook):
    data = run_pipeline(sample_workbook).data
    mixed_entities = data[data["chart_value"].notna()].copy()
    mixed_entities.loc[mixed_entities.index[0], "entity_id"] = "synthetic-other"

    with pytest.raises(ValueError, match="một entity"):
        build_metric_combo_chart(mixed_entities)


def test_all_demo_charts_render(sample_workbook):
    data = run_pipeline(sample_workbook).data
    data = data[(data["metric_normalized"] == "% báo sai") & (data["entity_level"] == "item")]
    line = build_line_chart(data)
    bar = build_bar_chart(data)
    assert len(line.data) > 0
    assert len(bar.data) > 0
    assert list(line.data[0].text) == ["8.00%", "5.00%"]
    assert list(bar.data[0].text) == ["5.00%"]
    assert "text" in line.data[0].mode
    assert line.data[0].hoverinfo == "skip"
    assert bar.data[0].hoverinfo == "skip"


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
    assert figure.data[0].hoverinfo == "skip"


def test_project_overview_supports_from_and_to_dates(sample_workbook):
    data = run_pipeline(sample_workbook).data
    overview = prepare_project_totals_range(data, "2026-09-12", "2026-09-13")
    assert len(overview) == 2
    assert set(overview["chart_value"]) == {100.0, 120.0}
    assert len(build_project_total_chart(data, "2026-09-12", "2026-09-13").data) > 0
