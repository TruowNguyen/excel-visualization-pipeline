from pathlib import Path

import pandas as pd
import pytest

from excel_visualization_pipeline.pipeline import run_pipeline


REAL_WORKBOOK = Path(__file__).resolve().parents[2] / "test data for CX report dashboard.xlsx"


@pytest.mark.skipif(not REAL_WORKBOOK.exists(), reason="Real demo workbook is not available")
def test_real_workbook_end_to_end():
    result = run_pipeline(REAL_WORKBOOK, Path(__file__).resolve().parents[1] / "config" / "parser.yaml")
    assert result.report.is_valid
    assert result.manifest["project_count"] == 6
    assert result.manifest["minimum_data_date"] == "2026-08-01"
    assert result.manifest["date_count"] == 41
    assert result.data["date"].min() >= pd.Timestamp("2026-08-01")
    assert result.manifest["record_count"] > 1000
    assert result.data["cell_address"].notna().all()
    assert result.data["source_hash"].nunique() == 1
    assert result.manifest["entity_count"] == 36
    assert result.manifest["max_entity_depth"] == 2

    vpet = result.entities[result.entities["project_label"] == "V-Pet"].set_index("entity_label")
    approved = vpet.loc["Phê duyệt định danh thú cưng"]
    assert approved["entity_level"] == "subitem"
    assert approved["entity_depth"] == 2
    assert approved["effective_unit"] == "Lượt (lũy kế)"
    assert approved["parent_entity_id"] == vpet.loc["Cư dân đăng ký thú cưng", "entity_id"]

    common_alert = vpet.loc["Cảnh báo chung"]
    assert common_alert["effective_unit"] == "Lượt (ngày)"
    assert common_alert["parent_entity_id"] == vpet.loc["Cảnh báo vi phạm", "entity_id"]
