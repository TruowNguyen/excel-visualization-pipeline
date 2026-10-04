"""Explicitly opt-in live narrative evaluation on a chosen committed scope.

Prints selected normalized KPI points and model prose for local review, never
credentials, raw Excel values, lineage targets or the complete provider input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient
from app import api
from excel_visualization_pipeline.ai import AIApplicationService, AnalysisSnapshotRepository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize one live generation on normalized committed data")
    parser.add_argument("--project", required=True)
    parser.add_argument("--entity", required=True, help="Exact entity reference from /entities")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--group-by", choices=("day", "week", "month"), default="day")
    parser.add_argument("--metric", choices=("all", "total", "error", "error_rate"), default="all")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; no provider call was made")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    configured = AIApplicationService.configured(repository=AnalysisSnapshotRepository(limit=10))
    if not configured.config.can_call_external:
        print(json.dumps({"status": "blocked", "reason": "feature_config_or_privacy_gate"}))
        return 2

    class Capture:
        def __init__(self, delegate):
            self.delegate = delegate
            self.model, self.provider_name = delegate.model, delegate.provider_name
            self.content = None
            self.input_bytes = 0

        def generate(self, *, system_prompt, payload):
            self.input_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            result = self.delegate.generate(system_prompt=system_prompt, payload=payload)
            self.content = result.content
            return result

        def check_model(self):
            return self.delegate.check_model()

    adapter = Capture(configured.adapter)
    service = AIApplicationService(config=configured.config, adapter=adapter, repository=AnalysisSnapshotRepository(limit=10))
    api._ai_service = lambda: service
    client = TestClient(api.app)
    request = {"entityRef": args.entity, "metricCode": args.metric, "start": args.start, "end": args.end,
               "groupBy": args.group_by, "scope": "node"}
    started = time.monotonic()
    response = client.post(f"/api/projects/{quote(args.project, safe='')}/ai/trend-summary", json=request)
    if response.status_code != 200:
        print(json.dumps({"httpStatus": response.status_code, "detail": response.json().get("detail")}, ensure_ascii=False))
        return 1
    body = response.json()
    print(json.dumps({"scope": body["scope"], "window": body["window"], "status": body["status"],
                      "provider": body["provider"], "validation": body["validation"], "rawNarrative": adapter.content,
                      "requestLatencyMs": round((time.monotonic()-started)*1000), "providerInputBytes": adapter.input_bytes,
                      "narrative": body["narrative"], "reading": body["synthesis"].get("reading"),
                      "series": [{"metric": m.get("metricCode", body["scope"]["metricCode"]), "points": [{"period": p["periodStart"], "end": p["periodEnd"], "label": p["periodLabel"], "value": p["value"]} for p in m["series"]]} for m in (body.get("metrics") or [body])]},
                     ensure_ascii=False))
    return 0 if body["validation"]["status"] in {"accepted", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
