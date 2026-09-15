from __future__ import annotations

import pandas as pd

from ..models import ValidationIssue, ValidationReport


LOGICAL_KEY = ["sheet_name", "project_id", "entity_id", "date", "metric_normalized", "unit_normalized"]


def validate_dataset(
    data: pd.DataFrame,
    parser_issues: list[ValidationIssue] | None = None,
    entities: pd.DataFrame | None = None,
) -> ValidationReport:
    issues = list(parser_issues or [])
    if data.empty:
        issues.append(ValidationIssue("error", "EMPTY_DATASET", "Không trích xuất được record nào."))
        return ValidationReport(issues)

    missing_context = data[data["project"].isna() | data["date"].isna() | data["metric_normalized"].eq("")]
    for row in missing_context.itertuples():
        issues.append(ValidationIssue(
            "error", "MISSING_CONTEXT", "Record thiếu Project, Date hoặc Metric.", row.sheet_name, row.cell_address
        ))

    duplicates = data[data.duplicated(LOGICAL_KEY, keep=False)]
    for row in duplicates.itertuples():
        issues.append(ValidationIssue(
            "error", "DUPLICATE_LOGICAL_KEY", "Trùng khóa Project/Section/Item/Date/Metric.", row.sheet_name, row.cell_address
        ))

    if entities is not None and not entities.empty:
        entity_ids = set(entities["entity_id"])
        invalid_parents = entities[
            entities["parent_entity_id"].notna()
            & ~entities["parent_entity_id"].isin(entity_ids)
        ]
        for row in invalid_parents.itertuples():
            issues.append(ValidationIssue(
                "error", "MISSING_PARENT_ENTITY", "parent_entity_id không tồn tại trong entity tree.",
                row.sheet_name,
            ))

        parents = dict(zip(entities["entity_id"], entities["parent_entity_id"]))
        for entity_id in entity_ids:
            visited: set[str] = set()
            current = entity_id
            while current in parents and pd.notna(parents[current]):
                if current in visited:
                    node = entities[entities["entity_id"] == entity_id].iloc[0]
                    issues.append(ValidationIssue(
                        "error", "HIERARCHY_CYCLE", "Phát hiện cycle trong entity tree.", node["sheet_name"]
                    ))
                    break
                visited.add(current)
                current = parents[current]

    percent_rows = data[(data["metric_normalized"] == "% báo sai") & data["chart_value"].notna()]
    suspicious = percent_rows[(percent_rows["chart_value"] < 0) | (percent_rows["chart_value"] > 100)]
    for row in suspicious.itertuples():
        issues.append(ValidationIssue(
            "warning", "PERCENT_OUT_OF_RANGE", f"Tỷ lệ nằm ngoài 0–100%: {row.display_value}", row.sheet_name, row.cell_address
        ))

    return ValidationReport(issues)
