from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.storage import verify_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra integrity và foreign key SQLite.")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "local" / "analytics.sqlite3",
    )
    args = parser.parse_args()
    report = verify_database(args.database)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
