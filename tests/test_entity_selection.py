from datetime import date

import pandas as pd
import pytest

from excel_visualization_pipeline.entity_selection import initial_entity_with_data


def _entities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"entity_id": "root", "entity_depth": 0, "source_row": 1},
            {"entity_id": "child-a", "entity_depth": 1, "source_row": 2},
            {"entity_id": "child-b", "entity_depth": 1, "source_row": 3},
            {"entity_id": "grandchild", "entity_depth": 2, "source_row": 4},
        ]
    )


def _record(entity_id: str, record_date: str, value=1) -> dict:
    return {
        "entity_id": entity_id,
        "date": record_date,
        "metric_normalized": "Tổng số",
        "chart_value": value,
    }


def test_uses_top_entity_when_it_has_data():
    data = pd.DataFrame([_record("root", "2026-09-10"), _record("child-a", "2026-09-10")])

    selected = initial_entity_with_data(_entities(), data, date(2026, 9, 1), date(2026, 9, 30))

    assert selected == "root"


def test_falls_back_to_first_secondary_entity_with_data():
    data = pd.DataFrame([_record("child-b", "2026-09-10")])

    selected = initial_entity_with_data(_entities(), data, date(2026, 9, 1), date(2026, 9, 30))

    assert selected == "child-b"


def test_searches_deeper_and_respects_date_and_metric_filters():
    data = pd.DataFrame(
        [
            _record("root", "2026-08-31"),
            {
                **_record("child-a", "2026-09-10"),
                "metric_normalized": "Ghi chú",
            },
            _record("grandchild", "2026-09-12"),
        ]
    )

    selected = initial_entity_with_data(
        _entities(),
        data,
        date(2026, 9, 1),
        date(2026, 9, 30),
        ["Tổng số", "Báo sai/Lỗi", "% báo sai"],
    )

    assert selected == "grandchild"


def test_returns_root_for_empty_range_and_rejects_empty_entities():
    empty_data = pd.DataFrame(columns=["entity_id", "date", "metric_normalized", "chart_value"])
    assert initial_entity_with_data(_entities(), empty_data, "2026-09-01", "2026-09-30") == "root"

    with pytest.raises(ValueError, match="không được rỗng"):
        initial_entity_with_data(_entities().iloc[0:0], empty_data, "2026-09-01", "2026-09-30")
