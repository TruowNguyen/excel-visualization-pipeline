from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.storage import load_import_history  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Xem lịch sử attempt/run trong SQLite.")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "local" / "analytics.sqlite3",
    )
    parser.add_argument("--source-key", default="cx_report_master")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    history = load_import_history(args.database, args.source_key).head(max(args.limit, 0))
    if history.empty:
        print("Chưa có import attempt.")
    else:
        print(history.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
