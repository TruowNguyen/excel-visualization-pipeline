"""Replay recorded real model responses against fresh committed-data engine facts.

No model call, source write, or relaxed grounding. This is a parsing regression
audit, NOT a fresh live-provider result. Stdout is machine-readable evidence.
"""
from datetime import date
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from app import api
from scripts.evaluate_ai_filter_matrix import snapshot
from excel_visualization_pipeline.ai import OutputValidator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    records = json.loads(args.evidence.read_text(encoding="utf-8"))["records"]
    results = []
    for r in records:
        if not r.get("rawNarrative"):
            continue
        c = r["request"]
        data, _ = api._project(c["project"])
        value, _ = snapshot(data, c["entity"], c["project"], date.fromisoformat(r["window"]["start"]),
                            date.fromisoformat(r["window"]["end"]), c["group"], c["metric"])
        value["analysisId"] = r["narrative"]["analysisId"]
        validator = OutputValidator()
        validated = validator.validate(validator.normalize_fact_references(r["rawNarrative"], value), value)
        results.append({"caseIndex": r["caseIndex"], "valid": validated.valid, "errors": list(validated.errors),
                        "claimResults": list(validated.claim_results)})
    print(json.dumps({"mode": "replay_not_live", "records": results}))


if __name__ == "__main__":
    main()
