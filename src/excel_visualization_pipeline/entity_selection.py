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
        raise ValueError("Danh sách entity không được rỗng.")

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
