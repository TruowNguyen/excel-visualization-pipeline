from openpyxl import load_workbook

from excel_visualization_pipeline.config import ParserConfig
from excel_visualization_pipeline.ingestion import load_excel
from excel_visualization_pipeline.parser import parse_workbook


def test_custom_parent_child_marker_is_config_driven(sample_workbook):
    workbook = load_workbook(sample_workbook)
    sheet = workbook.active
    sheet["B8"] = "> Lens phụ"
    sheet["D8"] = 1
    workbook.save(sample_workbook)

    default = ParserConfig()
    custom_rule = {
        "name": "greater_subitem",
        "pattern": r"^\s*>\s*",
        "entity_level": "component",
        "parent_strategy": "previous_item_or_project",
        "strip_marker": True,
        "confidence": "high",
    }
    config = ParserConfig(hierarchy_rules=(custom_rule, *default.hierarchy_rules))
    parsed = parse_workbook(load_excel(sample_workbook), config)

    entities = parsed.entities.set_index("entity_label")
    child = entities.loc["Lens phụ"]
    parent = entities.loc["Camera"]
    assert child["entity_level"] == "component"
    assert child["parent_entity_id"] == parent["entity_id"]
    assert child["entity_depth"] == parent["entity_depth"] + 1
    assert child["entity_path"].endswith("Camera > Lens phụ")
    assert child["effective_unit"] == "Cảnh báo"
