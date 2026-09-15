from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.pipeline import export_result, run_pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and validate an Excel report.")
    parser.add_argument("excel", type=Path)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed")
    args = parser.parse_args()
    result = run_pipeline(args.excel, PROJECT_ROOT / "config" / "parser.yaml")
    export_result(result, args.output)
    print(result.manifest)
    print(f"errors={len(result.report.errors)} warnings={len(result.report.warnings)}")
    return 0 if result.report.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

