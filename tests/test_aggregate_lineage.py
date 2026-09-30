from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from app.aggregate_lineage import attach_aggregate_lineage


def test_statistics_lineage_fails_closed_for_multi_entity_input(storage_workspace):
    figure = go.Figure(go.Scatter(x=["Tuần 37/2026"], y=[1], name="SUM · Tổng số"))
    data = pd.DataFrame([
        {"entity_id": "entity-a"},
        {"entity_id": "entity-b"},
    ])

    with pytest.raises(ValueError, match="cơ chế ánh xạ riêng"):
        attach_aggregate_lineage(
            storage_workspace / "unused.sqlite3",
            "sample",
            "Alpha",
            figure,
            data,
            pd.DataFrame(),
            kind="statistics",
            group_by="week",
            start_date="2026-09-07",
            end_date="2026-09-13",
        )


def test_statistics_comparison_lineage_does_not_guess_missing_source_ref(storage_workspace):
    figure = go.Figure(go.Bar(
        x=["Tuần 37/2026"], y=[3], name="[Vấn đề] Camera A · Báo sai/Lỗi",
        legendgroup="entity-a", meta={"statisticsMetric": "Báo sai/Lỗi"},
    ))
    data = pd.DataFrame([{
        "entity_id": "entity-a", "entity_label": "Camera A", "entity_path": "Alpha / Camera A",
        "entity_level": "item", "effective_unit": "lượt", "metric_normalized": "Báo sai/Lỗi",
        "metric_code": "error", "date": "2026-09-07", "chart_value": 3,
        "display_value": "3", "value_kind": "numeric", "lineage_ref": None,
        "lineage_run_id": 1,
    }])
    entities = pd.DataFrame([{
        "entity_id": "entity-a", "entity_label": "Camera A", "entity_path": "Alpha / Camera A",
        "effective_unit": "lượt",
    }])
    prepared = pd.DataFrame([{
        "entity_id": "entity-a", "metric_normalized": "Báo sai/Lỗi",
        "period_start": pd.Timestamp("2026-09-07"), "period_end": pd.Timestamp("2026-09-13"),
        "period_label": "Tuần 37/2026", "period_sum": 3.0, "average_per_day": 3.0,
        "display_sum": "3", "display_average": "3", "inferred_zero": False,
        "eligible_day_count": 1, "calendar_day_count": 7,
        "coverage_source_entity_id": "entity-a",
    }])

    attach_aggregate_lineage(
        storage_workspace / "lineage.sqlite3", "sample", "Alpha", figure, data, entities,
        kind="statistics_comparison", group_by="week",
        start_date="2026-09-07", end_date="2026-09-13",
        comparison_metric="Báo sai/Lỗi", comparison_calculation="sum",
        prepared_summary=prepared,
    )

    lineage = figure.data[0].meta["lineage"]
    assert lineage["selectable"] is False
    assert lineage["aggregateRefs"] == [None]
