from excel_visualization_pipeline.pipeline import run_pipeline


def test_extracts_traceable_long_format(sample_workbook):
    result = run_pipeline(sample_workbook)
    assert result.report.is_valid
    assert result.manifest["project_count"] == 1
    assert result.manifest["date_count"] == 2
    assert len(result.data) == 6
    rate = result.data[result.data["cell_address"] == "F7"].iloc[0]
    assert rate["raw_value"] == 0.08
    assert rate["value_numeric"] == 0.08
    assert rate["chart_value"] == 8.0
    assert rate["display_value"] == "8.00%"
    assert rate["project"] == "Alpha"
    assert rate["section"] == "1.1. Chất lượng cảnh báo"
    assert rate["item"] == "Camera"
    assert rate["entity_depth"] == 2
    assert rate["entity_path"] == "Alpha > 1.1. Chất lượng cảnh báo > Camera"
    assert rate["parent_entity_id"]
    assert rate["effective_unit"] == "Cảnh báo"
    assert rate["unit_source_level"] == "project"


def test_keeps_zero_distinct_from_blank(sample_workbook):
    from openpyxl import load_workbook

    workbook = load_workbook(sample_workbook)
    workbook.active["D7"] = 0
    workbook.active["E7"] = None
    workbook.save(sample_workbook)
    result = run_pipeline(sample_workbook)
    assert "D7" in set(result.data["cell_address"])
    assert "E7" not in set(result.data["cell_address"])
    assert result.data.set_index("cell_address").loc["D7", "chart_value"] == 0
