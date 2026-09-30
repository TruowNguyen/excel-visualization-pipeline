from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.visualization import (
    build_multi_entity_statistics_chart,
    prepare_period_statistics,
)


REAL_WORKBOOK = Path(__file__).resolve().parents[2] / "test data for CX report dashboard.xlsx"


@pytest.mark.skipif(not REAL_WORKBOOK.exists(), reason="Real demo workbook is not available")
def test_real_workbook_end_to_end():
    result = run_pipeline(REAL_WORKBOOK, Path(__file__).resolve().parents[1] / "config" / "parser.yaml")
    assert result.report.is_valid
    assert result.manifest["project_count"] == 6
    assert result.manifest["minimum_data_date"] == "2026-08-01"
    assert result.manifest["date_count"] == 41
    assert result.manifest["metric_count"] == 3
    assert result.manifest["record_count"] == 4182
    assert result.manifest["chartable_record_count"] == 2343
    assert result.manifest["default_zero_rate_count"] == 646
    assert result.manifest["inconsistent_error_metric_count"] == 89
    assert result.manifest["metrics"] == ["% báo sai", "Báo sai/Lỗi", "Tổng số"]
    assert result.data["date"].min() >= pd.Timestamp("2026-08-01")
    assert result.data["cell_address"].notna().all()
    assert result.data["source_hash"].nunique() == 1
    assert result.manifest["entity_count"] == 36
    assert result.manifest["max_entity_depth"] == 2
    assert Counter(issue.code for issue in result.report.warnings) == {
        "INCONSISTENT_ERROR_METRICS": 89,
        "SOURCE_MARKER": 54,
        "NON_NUMERIC_METRIC": 48,
        "FALLBACK_ENTITY_CLASSIFICATION": 1,
        "UNKNOWN_UNIT": 1,
    }

    vpet = result.entities[result.entities["project_label"] == "V-Pet"].set_index("entity_label")
    approved = vpet.loc["Phê duyệt định danh thú cưng"]
    assert approved["entity_level"] == "subitem"
    assert approved["entity_depth"] == 2
    assert approved["effective_unit"] == "Lượt (lũy kế)"
    assert approved["parent_entity_id"] == vpet.loc["Cư dân đăng ký thú cưng", "entity_id"]

    common_alert = vpet.loc["Cảnh báo chung"]
    assert common_alert["effective_unit"] == "Lượt (ngày)"
    assert common_alert["parent_entity_id"] == vpet.loc["Cảnh báo vi phạm", "entity_id"]


@pytest.mark.skipif(not REAL_WORKBOOK.exists(), reason="Real demo workbook is not available")
def test_contextual_statistics_real_workbook_matrix_has_no_eligible_empty_chart():
    result = run_pipeline(
        REAL_WORKBOOK, Path(__file__).resolve().parents[1] / "config" / "parser.yaml"
    )
    checked = 0
    for project, project_entities in result.entities.groupby("project_label"):
        project_data = result.data[result.data["project_label"].eq(project)]
        start_date = pd.to_datetime(project_data["date"]).min()
        end_date = pd.to_datetime(project_data["date"]).max()
        for _, siblings in project_entities.dropna(subset=["parent_entity_id"]).groupby("parent_entity_id"):
            if len(siblings) < 2:
                continue
            for unit, compatible in siblings.dropna(subset=["effective_unit"]).groupby("effective_unit"):
                entity_ids = compatible["entity_id"].astype(str).tolist()
                if len(entity_ids) < 2:
                    continue
                for group_by in ["day", "week", "month", "quarter"]:
                    prepared = []
                    for entity_id in entity_ids:
                        rows = project_data[
                            project_data["entity_id"].eq(entity_id)
                            & project_data["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi"])
                        ]
                        summary = prepare_period_statistics(
                            rows, start_date, end_date, group_by,
                            coverage_data=project_data, semantic_data=project_data,
                        )
                        if not summary.empty:
                            prepared.append(summary)
                    if not prepared:
                        continue
                    frame = pd.concat(prepared, ignore_index=True)
                    for metric in ["Tổng số", "Báo sai/Lỗi"]:
                        for calculation, column in [
                            ("sum", "period_sum"),
                            ("average_per_day", "average_per_day"),
                        ]:
                            eligible = frame[
                                frame["metric_normalized"].eq(metric)
                                & frame[column].notna()
                            ]
                            if eligible["entity_id"].nunique() < 2:
                                continue
                            selected_ids = eligible["entity_id"].drop_duplicates().head(3)
                            selected = frame[frame["entity_id"].isin(selected_ids)]
                            figure = build_multi_entity_statistics_chart(
                                selected, calculation,
                                f"{project} · {unit}",
                            )
                            expected_trace_count = selected[
                                selected[column].notna()
                            ][["entity_id", "metric_normalized"]].drop_duplicates().shape[0]
                            assert len(figure.data) == expected_trace_count, (
                                project, unit, group_by, metric, calculation
                            )
                            assert all(len(trace.y) > 0 for trace in figure.data)
                            for trace in figure.data:
                                trace_metric = trace.meta["statisticsMetric"]
                                expected = selected[
                                    selected["entity_id"].eq(str(trace.legendgroup))
                                    & selected["metric_normalized"].eq(trace_metric)
                                    & selected[column].notna()
                                ].sort_values("period_start")[column].astype(float).tolist()
                                assert list(trace.y) == pytest.approx(expected)
                            checked += 1
    assert checked > 0
