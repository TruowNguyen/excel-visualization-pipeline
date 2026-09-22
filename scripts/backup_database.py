from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.storage import backup_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup SQLite bằng Online Backup API.")
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "local" / "analytics.sqlite3",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or (
        PROJECT_ROOT
        / "data"
        / "backups"
        / f"analytics_{datetime.now():%Y%m%d_%H%M%S}.sqlite3"
    )
    backup_database(args.database, output)
    print(f"backup={output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
