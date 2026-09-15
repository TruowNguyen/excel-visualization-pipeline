import pandas as pd
from openpyxl import load_workbook

from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.validation import validate_dataset


def test_duplicate_logical_key_fails_quality_gate(sample_workbook):
    result = run_pipeline(sample_workbook)
    duplicated = pd.concat([result.data, result.data.iloc[[0]]], ignore_index=True)
    report = validate_dataset(duplicated, entities=result.entities)
    assert not report.is_valid
    assert any(issue.code == "DUPLICATE_LOGICAL_KEY" for issue in report.errors)


def test_missing_marker_is_warning_not_zero(sample_workbook):
    workbook = load_workbook(sample_workbook)
    workbook.active["E7"] = "-"
    workbook.save(sample_workbook)
    result = run_pipeline(sample_workbook)
    row = result.data[result.data["cell_address"] == "E7"].iloc[0]
    assert row["value_kind"] == "missing_marker"
    assert row["chart_value"] != 0
    assert any(issue.cell_address == "E7" for issue in result.report.warnings)
