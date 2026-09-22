from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.storage import initialize_database, verify_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Khởi tạo/migrate SQLite analytics database.")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "local" / "analytics.sqlite3",
    )
    args = parser.parse_args()
    initialize_database(args.database)
    report = verify_database(args.database)
    print(f"database={args.database.resolve()}")
    print(report)
    return 0 if report["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
