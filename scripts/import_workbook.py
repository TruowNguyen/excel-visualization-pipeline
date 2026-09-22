from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.storage import import_workbook  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse, validate và lưu workbook vào SQLite.")
    parser.add_argument("excel", type=Path)
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "data" / "local" / "analytics.sqlite3",
    )
    parser.add_argument("--source-key", default="cx_report_master")
    parser.add_argument("--display-name", default="CX Report Master")
    parser.add_argument(
        "--mode",
        choices=["full_snapshot", "incremental"],
        default="full_snapshot",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "parser.yaml",
    )
    parser.add_argument(
        "--allow-replay",
        action="store_true",
        help="Cho phép áp dụng lại artifact cũ; chỉ dùng để phục hồi/correction có chủ đích.",
    )
    args = parser.parse_args()
    execution = import_workbook(
        args.database,
        args.excel,
        source_key=args.source_key,
        display_name=args.display_name,
        config_path=args.config,
        mode=args.mode,
        allow_replay=args.allow_replay,
    )
    outcome = execution.outcome
    print(
        f"status={outcome.status} attempt_id={outcome.attempt_id} "
        f"run_id={outcome.run_id} duplicate_of={outcome.duplicate_of_run_id}"
    )
    print(
        f"inserted={outcome.inserted_count} updated={outcome.updated_count} "
        f"unchanged={outcome.unchanged_count} restored={outcome.restored_count} "
        f"deleted={outcome.deleted_count} lineage_changed={outcome.lineage_changed_count}"
    )
    return 0 if outcome.status in {"committed", "duplicate"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
