from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.pipeline import run_pipeline  # noqa: E402
from excel_visualization_pipeline.visualization import (  # noqa: E402
    build_bar_chart,
    build_line_chart,
    build_metric_average_chart,
    build_metric_box_plot,
    build_metric_combo_chart,
    build_multi_entity_metric_chart,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end smoke test on a real workbook.")
    parser.add_argument("excel", type=Path)
    args = parser.parse_args()
    result = run_pipeline(args.excel, PROJECT_ROOT / "config" / "parser.yaml")
    assert result.report.is_valid, result.report.as_dict()
    assert result.manifest["project_count"] > 0
    assert result.manifest["date_count"] > 0
    assert result.manifest["chartable_record_count"] > 0
    sample = result.data[result.data["chart_value"].notna()]
    metric = sample["metric_normalized"].iloc[0]
    level = sample["entity_level"].iloc[0]
    sample = sample[(sample["metric_normalized"] == metric) & (sample["entity_level"] == level)]
    build_line_chart(sample)
    build_bar_chart(sample)
    combo_metrics = ["Tổng số", "Báo sai/Lỗi", "% báo sai"]
    combo_source = result.data[result.data["metric_normalized"].isin(combo_metrics)]
    candidates = combo_source.groupby("entity_id")["metric_normalized"].nunique()
    assert not candidates.empty and candidates.max() == len(combo_metrics)
    combo_entity_id = candidates.idxmax()
    build_metric_combo_chart(combo_source[combo_source["entity_id"] == combo_entity_id])
    build_metric_average_chart(combo_source)
    build_metric_box_plot(combo_source, "Tổng số")
    build_metric_box_plot(combo_source, "Báo sai/Lỗi")
    eligible = result.data[
        (result.data["metric_normalized"] == "Báo sai/Lỗi")
        & result.data["effective_unit"].notna()
        & result.data["chart_value"].notna()
    ]
    compatible_groups = eligible[
        ["project_id", "effective_unit", "entity_id"]
    ].drop_duplicates().groupby(
        ["project_id", "effective_unit"]
    )["entity_id"].apply(list)
    comparison_ids = next((ids[:3] for ids in compatible_groups if len(ids) >= 2), None)
    assert comparison_ids is not None
    build_multi_entity_metric_chart(
        eligible[eligible["entity_id"].isin(comparison_ids)],
        "Báo sai/Lỗi",
    )
    print("SMOKE TEST PASSED")
    print(result.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
