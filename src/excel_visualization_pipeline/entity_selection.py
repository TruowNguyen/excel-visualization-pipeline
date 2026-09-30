from __future__ import annotations

import pandas as pd


def initial_entity_with_data(
    entities: pd.DataFrame,
    data: pd.DataFrame,
    start_date,
    end_date,
    metrics: list[str] | None = None,
) -> str:
    """Return the shallowest, earliest entity that has chartable data in range.

    If no entity has chartable data in the selected range, the top-level entity
    is returned so the dashboard can show an explicit empty-state message.
    """
    if entities.empty:
        raise ValueError("Danh sách nội dung theo dõi không được rỗng.")

    ordered = entities.sort_values(["entity_depth", "source_row"], kind="stable")
    frame = data[data["chart_value"].notna()].copy()
    dates = pd.to_datetime(frame["date"])
    frame = frame[
        (dates >= pd.Timestamp(start_date))
        & (dates <= pd.Timestamp(end_date))
    ]
    if metrics is not None:
        frame = frame[frame["metric_normalized"].isin(metrics)]

    entity_ids_with_data = set(frame["entity_id"].dropna())
    for entity_id in ordered["entity_id"]:
        if entity_id in entity_ids_with_data:
            return str(entity_id)
    return str(ordered.iloc[0]["entity_id"])


def same_parent_siblings(
    entities: pd.DataFrame,
    anchor_entity_id: str,
) -> pd.DataFrame:
    """Return true siblings for an anchor without treating roots as siblings.

    Sibling identity is structural: same project and the exact same non-null
    ``parent_entity_id``. Equal depth is not sufficient, and the anchor's own
    children are not siblings of the anchor.
    """
    required = {"entity_id", "parent_entity_id", "project_id"}
    missing = required.difference(entities.columns)
    if missing:
        raise ValueError(
            "Thiếu cột bắt buộc của cấu trúc theo dõi: " + ", ".join(sorted(missing))
        )

    anchor_rows = entities[entities["entity_id"] == anchor_entity_id]
    if len(anchor_rows) != 1:
        raise ValueError("Nội dung bắt đầu so sánh không tồn tại duy nhất trong cấu trúc theo dõi.")

    anchor = anchor_rows.iloc[0]
    parent_id = anchor["parent_entity_id"]
    if pd.isna(parent_id) or str(parent_id).strip() == "":
        return entities.iloc[0:0].copy()

    return entities[
        entities["project_id"].eq(anchor["project_id"])
        & entities["parent_entity_id"].eq(parent_id)
        & entities["entity_id"].ne(anchor_entity_id)
    ].copy()
