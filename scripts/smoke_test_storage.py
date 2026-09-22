from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.storage import (  # noqa: E402
    import_workbook,
    load_current_data,
    load_current_entities,
    verify_database,
)
from excel_visualization_pipeline.visualization import build_metric_combo_chart  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Excel → SQLite → chart.")
    parser.add_argument("excel", type=Path)
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "local" / "smoke.sqlite3",
    )
    parser.add_argument("--source-key", default="smoke_test_source")
    args = parser.parse_args()

    execution = import_workbook(
        args.database,
        args.excel,
        source_key=args.source_key,
        display_name="Storage smoke test",
        config_path=PROJECT_ROOT / "config" / "parser.yaml",
    )
    assert execution.outcome.status in {"committed", "duplicate"}
    data = load_current_data(args.database, args.source_key)
    entities = load_current_entities(args.database, args.source_key)
    assert not data.empty
    assert not entities.empty
    candidates = data.groupby("entity_id")["metric_normalized"].nunique()
    entity_id = candidates.idxmax()
    build_metric_combo_chart(data[data["entity_id"] == entity_id])
    report = verify_database(args.database)
    assert report["is_valid"], report
    print("STORAGE SMOKE TEST PASSED")
    print(f"status={execution.outcome.status} run={execution.outcome.run_id}")
    print(f"records={len(data)} entities={len(entities)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
