import pytest
import pandas as pd

from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.visualization import (
    build_bar_chart,
    build_line_chart,
    build_metric_combo_chart,
    build_multi_entity_metric_chart,
    build_period_metric_combo_chart,
    build_period_statistics_chart,
    build_project_total_chart,
    prepare_project_totals,
    prepare_project_totals_range,
    prepare_period_statistics,
    prepare_period_metric_summary,
)


def test_combo_chart_overlays_counts_and_uses_secondary_axis(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"]

    figure = build_metric_combo_chart(item_data)

    assert [trace.type for trace in figure.data] == ["bar", "bar", "scatter"]
    assert [trace.name for trace in figure.data] == [
        "Tổng số",
        "Báo sai/Lỗi",
        "% báo sai",
    ]
    assert figure.layout.barmode == "overlay"
    assert figure.data[0].width == figure.data[1].width
    assert figure.layout.legend.title.text is None
    assert figure.layout.legend.x == 0
    assert figure.layout.legend.xanchor == "left"
    assert figure.layout.legend.yanchor == "bottom"
    assert figure.layout.legend.itemclick == "toggle"
    assert figure.layout.legend.itemdoubleclick == "toggleothers"
    assert figure.layout.legend.bgcolor == "rgba(0, 0, 0, 0)"
    assert figure.layout.legend.borderwidth == 0
    assert figure.layout.legend.itemwidth == 34
    assert figure.layout.legend.valign == "middle"
    assert figure.layout.legend.tracegroupgap == 8
    assert figure.layout.xaxis.tickformat == "%d/%m"
    assert figure.data[2].yaxis == "y2"
    assert figure.layout.yaxis2.tickformat == ".1f"
    assert figure.layout.yaxis2.ticksuffix == "%"
    assert list(figure.data[0].text) == ["", "120"]
    assert list(figure.data[1].text) == ["", "6"]
    assert list(figure.data[2].text) == ["", "5.00%"]
    assert figure.layout.hovermode == "closest"
    assert figure.layout.hoverdistance == 5
    assert figure.layout.xaxis.showspikes is False
    assert all(trace.name for trace in figure.data)
    assert all("Ngày %{x|%d/%m/%Y}" in trace.hovertemplate for trace in figure.data)
    assert all("Tổng số/Cảnh báo" in trace.hovertemplate for trace in figure.data)
    assert all("Báo sai/Lỗi" in trace.hovertemplate for trace in figure.data)
    assert all("% báo sai" in trace.hovertemplate for trace in figure.data)
    assert all("color:#8ecae6'>■" in trace.hovertemplate for trace in figure.data)
    assert all("color:#d1495b'>■" in trace.hovertemplate for trace in figure.data)
    assert all("color:#ff9f1c'>━●━" in trace.hovertemplate for trace in figure.data)
    assert all("Mô tả" not in trace.hovertemplate for trace in figure.data)
    assert list(figure.data[0].customdata[0]) == [
        "Camera", "100", "8", "8.00%",
    ]


def test_combo_chart_rejects_multiple_entities(sample_workbook):
    data = run_pipeline(sample_workbook).data
    mixed_entities = data[data["chart_value"].notna()].copy()
    mixed_entities.loc[mixed_entities.index[0], "entity_id"] = "synthetic-other"

    with pytest.raises(ValueError, match="một entity"):
        build_metric_combo_chart(mixed_entities)


def test_period_combo_compares_calendar_weeks_instead_of_daily_points():
    rows = []
    daily_values = [
        ("2026-09-07", 100, 10),
        ("2026-09-08", 200, 20),
        ("2026-09-14", 50, 5),
        ("2026-09-15", 50, 0),
    ]
    for value_date, total, error in daily_values:
        for metric, value, display in [
            ("Tổng số", total, str(total)),
            ("Báo sai/Lỗi", error, str(error)),
            # The period rate must be derived from period sums, not averaged
            # from this deliberately unrelated daily source percentage.
            ("% báo sai", 99, "99.00%"),
        ]:
            rows.append(
                {
                    "entity_id": "camera-a",
                    "entity_label": "Camera A",
                    "entity_level": "item",
                    "effective_unit": "lượt",
                    "metric_normalized": metric,
                    "date": value_date,
                    "chart_value": value,
                    "display_value": display,
                    "value_kind": "number",
                }
            )
    data = pd.DataFrame(rows)

    summary = prepare_period_metric_summary(
        data, "2026-09-07", "2026-09-20", "week"
    )
    figure = build_period_metric_combo_chart(
        data, "2026-09-07", "2026-09-20", "week"
    )

    assert list(summary["period_label"]) == ["Tuần 37/2026", "Tuần 38/2026"]
    assert list(summary["total_sum"]) == [300, 100]
    assert list(summary["error_sum"]) == [30, 5]
    assert list(summary["error_rate"]) == [10, 5]
    assert [len(trace.x) for trace in figure.data] == [2, 2, 2]
    assert list(figure.data[0].x) == ["Tuần 37/2026", "Tuần 38/2026"]
    assert figure.layout.xaxis.title.text == "Tuần"
    assert figure.layout.barmode == "overlay"
    assert figure.data[0].width == figure.data[1].width
    assert figure.layout.hovermode == "closest"
    assert all("Khoảng: %{customdata[4]}" in trace.hovertemplate for trace in figure.data)


def test_combo_hover_labels_inconsistent_positive_rate(sample_workbook):
    from openpyxl import load_workbook

    workbook = load_workbook(sample_workbook)
    workbook.active["E7"] = None
    workbook.save(sample_workbook)
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"]

    figure = build_metric_combo_chart(item_data)

    assert figure.data[-1].customdata[0][2] == "— ⚠"
    assert figure.data[-1].customdata[0][3] == "8.00% ⚠"


def test_combo_hover_distinguishes_not_recorded_and_source_marker(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    target_date = pd.to_datetime(item_data["date"]) == pd.Timestamp("2026-09-12")
    not_recorded = target_date & (item_data["metric_normalized"] == "Báo sai/Lỗi")
    source_marker = target_date & (item_data["metric_normalized"] == "% báo sai")
    item_data.loc[not_recorded, ["chart_value", "display_value", "value_kind"]] = [
        None,
        "",
        "not_recorded",
    ]
    item_data.loc[source_marker, ["chart_value", "display_value", "value_kind"]] = [
        None,
        "-",
        "source_marker",
    ]

    figure = build_metric_combo_chart(item_data)

    # The non-null Total point remains hoverable and carries the full tooltip
    # row, while the null Error/Rate observations do not become click targets.
    assert list(figure.data[0].customdata[0]) == [
        "Camera",
        "100",
        "—",
        "-",
    ]


def test_period_statistics_calculates_sum_and_average_per_observed_day(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"]

    statistics = prepare_period_statistics(
        item_data,
        "2026-09-12",
        "2026-09-13",
        "week",
    ).set_index("metric_normalized")
    figure = build_period_statistics_chart(
        item_data,
        "2026-09-12",
        "2026-09-13",
        "week",
        ["SUM", "AVG/ngày"],
    )

    assert set(statistics.index) == {"Tổng số", "Báo sai/Lỗi"}
    assert statistics.loc["Tổng số", "period_sum"] == 220
    assert statistics.loc["Báo sai/Lỗi", "period_sum"] == 14
    assert statistics.loc["Tổng số", "average_per_day"] == 110
    assert statistics.loc["Báo sai/Lỗi", "average_per_day"] == 7
    assert statistics.loc["Tổng số", "eligible_day_count"] == 2
    assert statistics.loc["Tổng số", "period_label"] == "Tuần 37/2026"
    assert [trace.type for trace in figure.data] == ["bar", "bar", "scatter", "scatter"]
    assert {trace.name for trace in figure.data} == {
        "SUM · Tổng số",
        "AVG/ngày · Tổng số",
        "SUM · Báo sai/Lỗi",
        "AVG/ngày · Báo sai/Lỗi",
    }
    assert figure.layout.barmode == "overlay"
    assert figure.data[0].width == figure.data[1].width
    assert figure.layout.legend.itemclick == "toggle"
    assert figure.layout.legend.itemdoubleclick == "toggleothers"
    assert figure.data[0].yaxis == "y"
    assert figure.data[1].yaxis == "y"
    assert figure.data[2].yaxis == "y2"
    assert figure.layout.hovermode == "closest"
    assert all(trace.name for trace in figure.data)
    assert all("Mô tả" not in trace.hovertemplate for trace in figure.data)
    assert all("color:#8ecae6'>■" in trace.hovertemplate for trace in figure.data)
    assert all("color:#d1495b'>■" in trace.hovertemplate for trace in figure.data)
    assert all("color:#0077b6'>━●━" in trace.hovertemplate for trace in figure.data)
    assert all("color:#9d0208'>━●━" in trace.hovertemplate for trace in figure.data)
    assert list(figure.data[0].customdata[0]) == [
        "220", "14", "110", "7", "2/2", "12/09–13/09",
    ]
    assert all("Khoảng tuần: %{customdata[5]}" in trace.hovertemplate for trace in figure.data)


def test_period_statistics_mode_selection_and_source_marker_denominator(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    marker = (
        item_data["metric_normalized"].eq("Báo sai/Lỗi")
        & pd.to_datetime(item_data["date"]).eq(pd.Timestamp("2026-09-12"))
    )
    item_data.loc[marker, ["chart_value", "value_kind"]] = [None, "source_marker"]

    statistics = prepare_period_statistics(
        item_data,
        "2026-09-12",
        "2026-09-13",
        "week",
    ).set_index("metric_normalized")
    sum_only = build_period_statistics_chart(
        item_data,
        "2026-09-12",
        "2026-09-13",
        "week",
        ["SUM"],
    )

    assert statistics.loc["Báo sai/Lỗi", "period_sum"] == 6
    assert statistics.loc["Báo sai/Lỗi", "eligible_day_count"] == 1
    assert statistics.loc["Báo sai/Lỗi", "average_per_day"] == 6
    assert len(sum_only.data) == 2
    assert all(trace.type == "bar" for trace in sum_only.data)
    assert all("AVG/ngày" not in trace.hovertemplate for trace in sum_only.data)


def test_period_statistics_excludes_days_without_total_observation():
    dates = pd.date_range("2026-09-07", "2026-09-13", freq="D")
    rows = []
    for index, value_date in enumerate(dates):
        total_value = [10, 20, 0, 30, None, None, None][index]
        error_value = [1, 2, None, 3, None, None, None][index]
        for metric, value in [("Tổng số", total_value), ("Báo sai/Lỗi", error_value)]:
            rows.append({
                "entity_id": "camera-a",
                "entity_label": "Camera A",
                "entity_level": "item",
                "effective_unit": "lượt",
                "metric_normalized": metric,
                "date": value_date,
                "chart_value": value,
                "value_kind": "number" if value is not None else "not_recorded",
            })
    data = pd.DataFrame(rows)

    statistics = prepare_period_statistics(
        data,
        "2026-09-07",
        "2026-09-13",
        "week",
    ).set_index("metric_normalized")
    figure = build_period_statistics_chart(
        data,
        "2026-09-07",
        "2026-09-13",
        "week",
        ["SUM", "AVG/ngày"],
    )

    assert statistics.loc["Tổng số", "period_sum"] == 60
    assert statistics.loc["Tổng số", "eligible_day_count"] == 4
    assert statistics.loc["Tổng số", "average_per_day"] == 15
    assert statistics.loc["Báo sai/Lỗi", "period_sum"] == 6
    assert statistics.loc["Báo sai/Lỗi", "eligible_day_count"] == 4
    assert statistics.loc["Báo sai/Lỗi", "average_per_day"] == 1.5
    assert statistics.loc["Tổng số", "observed_day_count"] == 4
    assert statistics.loc["Tổng số", "calendar_day_count"] == 7
    assert statistics.loc["Tổng số", "period_label"] == "Tuần 37/2026"
    assert "Số ngày có dữ liệu" in figure.data[-1].hovertemplate
    assert figure.data[-1].customdata[0][4] == "4/7"
    assert figure.data[-1].customdata[0][5] == "07/09–13/09"


def test_period_statistics_inherits_parent_observation_days_for_error_only_child():
    dates = pd.date_range("2026-09-07", "2026-09-13", freq="D")
    rows = []
    for index, value_date in enumerate(dates):
        parent_total = [10, 20, 0, 30, None, None, None][index]
        child_error = [1, 2, None, 3, None, None, None][index]
        rows.append({
            "entity_id": "parent",
            "parent_entity_id": None,
            "entity_label": "Section",
            "entity_level": "section",
            "effective_unit": "lượt",
            "metric_normalized": "Tổng số",
            "date": value_date,
            "chart_value": parent_total,
            "value_kind": "numeric" if parent_total is not None else "not_recorded",
        })
        for metric, value in [("Tổng số", None), ("Báo sai/Lỗi", child_error)]:
            rows.append({
                "entity_id": "child",
                "parent_entity_id": "parent",
                "entity_label": "Camera",
                "entity_level": "item",
                "effective_unit": "lượt",
                "metric_normalized": metric,
                "date": value_date,
                "chart_value": value,
                "value_kind": "numeric" if value is not None else "not_recorded",
            })
    coverage_data = pd.DataFrame(rows)
    child_data = coverage_data[coverage_data["entity_id"] == "child"]

    statistics = prepare_period_statistics(
        child_data,
        "2026-09-07",
        "2026-09-13",
        "week",
        coverage_data=coverage_data,
    ).set_index("metric_normalized")

    assert statistics.loc["Báo sai/Lỗi", "period_sum"] == 6
    assert statistics.loc["Báo sai/Lỗi", "eligible_day_count"] == 4
    assert statistics.loc["Báo sai/Lỗi", "average_per_day"] == 1.5
    assert statistics.loc["Báo sai/Lỗi", "coverage_source_entity_id"] == "parent"
    assert pd.isna(statistics.loc["Tổng số", "average_per_day"])


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
    assert figure.layout.legend.title.text is None
    assert figure.layout.legend.xanchor == "left"
    assert figure.layout.legend.itemclick == "toggle"
    assert figure.layout.legend.itemdoubleclick == "toggleothers"
    assert all("Tổng số/Cảnh báo" in trace.hovertemplate for trace in figure.data)
    assert all("Báo sai/Lỗi" in trace.hovertemplate for trace in figure.data)
    assert all("% báo sai" in trace.hovertemplate for trace in figure.data)
    assert all("Mô tả" not in trace.hovertemplate for trace in figure.data)
    assert list(figure.data[0].customdata[0]) == [
        "Camera A", "100", "8", "8.00%",
    ]
    assert all(trace.type == "bar" for trace in figure.data)
    assert all("% báo sai" not in trace.name and "Tổng số" not in trace.name for trace in figure.data)
    assert all(trace.name.startswith("[Item]") for trace in figure.data)


def test_multi_entity_week_view_has_one_value_per_calendar_week(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    second_week = item_data.copy()
    second_week["date"] = pd.to_datetime(second_week["date"]) + pd.Timedelta(days=7)
    two_weeks = pd.concat([item_data, second_week], ignore_index=True)
    second_entity = two_weeks.copy()
    second_entity["entity_id"] = "camera-b"
    second_entity["entity_label"] = "Camera B"
    comparison = pd.concat([two_weeks, second_entity], ignore_index=True)

    figure = build_multi_entity_metric_chart(
        comparison,
        "Báo sai/Lỗi",
        group_by="week",
        start_date="2026-09-07",
        end_date="2026-09-20",
    )

    assert len(figure.data) == 2
    assert all(len(trace.x) == 2 for trace in figure.data)
    assert all(
        list(trace.x) == ["Tuần 37/2026", "Tuần 38/2026"]
        for trace in figure.data
    )
    assert figure.layout.xaxis.title.text == "Tuần"


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
    item_data.loc[missing_error, "value_kind"] = "not_recorded"

    figure = build_multi_entity_metric_chart(item_data, "Tổng số")

    assert list(figure.data[0].customdata[0]) == [
        "Camera",
        "100",
        "—",
        "8.00%",
    ]
    assert "0" not in figure.data[0].customdata[0][2]


def test_multi_entity_unified_hover_distinguishes_source_marker(sample_workbook):
    data = run_pipeline(sample_workbook).data
    item_data = data[data["entity_level"] == "item"].copy()
    missing_error = (
        (item_data["metric_normalized"] == "Báo sai/Lỗi")
        & (pd.to_datetime(item_data["date"]) == pd.Timestamp("2026-09-12"))
    )
    item_data.loc[missing_error, "chart_value"] = None
    item_data.loc[missing_error, "display_value"] = "-"
    item_data.loc[missing_error, "value_kind"] = "source_marker"

    figure = build_multi_entity_metric_chart(item_data, "Tổng số")

    assert figure.data[0].customdata[0][2] == "-"


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
