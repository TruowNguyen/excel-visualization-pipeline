"""Gate 0 evidence for existing calculations, not the new Overview feature.

The project-source decision is blocked. These fixtures freeze the observed
semantics without adding an aggregation policy or modifying production code.
"""

import pandas as pd
import pytest

from excel_visualization_pipeline.visualization import prepare_period_metric_summary


def project_rows(total, error, error_kind, rate=0, rate_kind="default_zero_rate"):
    return pd.DataFrame([
        {
            "entity_id": "project", "parent_entity_id": None,
            "entity_label": "Dự án", "entity_level": "project",
            "effective_unit": "Lượt", "date": pd.Timestamp("2026-09-07"),
            "metric_normalized": metric, "chart_value": value, "value_kind": kind,
        }
        for metric, value, kind in [
            ("Tổng số", total, "numeric" if total is not None else "not_recorded"),
            ("Báo sai/Lỗi", error, error_kind),
            ("% báo sai", rate, rate_kind),
        ]
    ])


@pytest.mark.parametrize("grain", ["week", "month"])
@pytest.mark.parametrize(
    "total,error,error_kind,rate,rate_kind,expected,inferred",
    [
        (None, None, "not_recorded", 0, "default_zero_rate", None, False),
        (100, 0, "numeric", 0, "percentage", 0, False),
        (100, None, "not_recorded", 0, "default_zero_rate", 0, True),
        (100, None, "source_marker", 0, "default_zero_rate", None, False),
        (100, None, "not_recorded", 10, "percentage", None, False),
    ],
    ids=["all-missing", "physical-zero", "inferred-zero", "marker", "positive-rate"],
)
def test_gate_0_existing_grouped_error_semantics(
    grain, total, error, error_kind, rate, rate_kind, expected, inferred,
):
    data = project_rows(total, error, error_kind, rate, rate_kind)
    # Raw daily Overview uses the supplied chart_value, not grouped inference.
    raw_daily_error = data.loc[
        data.metric_normalized.eq("Báo sai/Lỗi"), "chart_value"
    ].iloc[0]
    if error is None:
        assert pd.isna(raw_daily_error)
    else:
        assert raw_daily_error == error

    result = prepare_period_metric_summary(
        data, "2026-09-01", "2026-09-30", grain,
    ).iloc[0]
    if expected is None:
        assert pd.isna(result.error_sum)
    else:
        assert result.error_sum == expected
    assert (result.rate_calculation_source == "inferred_zero") == inferred


@pytest.mark.parametrize("grain", ["week", "month"])
def test_gate_0_child_values_do_not_create_project_observations(grain):
    data = project_rows(100, 10, "numeric", 10, "percentage")
    data["entity_id"] = "child"
    data["parent_entity_id"] = "project"
    data["entity_level"] = "item"
    project_data = data[data.entity_id.eq("project")]
    result = prepare_period_metric_summary(
        project_data, "2026-09-01", "2026-09-30", grain, coverage_data=data,
    )
    assert result.empty


@pytest.mark.parametrize("grain", ["week", "month"])
def test_gate_0_valid_error_counts_sum_without_treating_missing_as_zero(grain):
    missing = project_rows(None, None, "not_recorded")
    numeric = project_rows(100, 7, "numeric", 7, "percentage")
    numeric["date"] = pd.Timestamp("2026-09-08")
    data = pd.concat([missing, numeric], ignore_index=True)
    result = prepare_period_metric_summary(
        data, "2026-09-01", "2026-09-30", grain,
    ).iloc[0]
    assert result.error_sum == 7
    assert result.total_sum == 100
    assert result.rate_calculation_source == "error_sum"
