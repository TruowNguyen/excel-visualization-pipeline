"""Opt-in 9Router smoke test using synthetic facts only.

This script deliberately does not read SQLite or workbook data. Run it only after
the privacy gate has been approved and the server-side environment is loaded.
"""

from __future__ import annotations

import json
from datetime import date
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
from dotenv import load_dotenv

from excel_visualization_pipeline.ai import AIConfig, AnalyticsEngine, NineRouterLLMAdapter, OutputValidator, PromptRegistry
from excel_visualization_pipeline.ai.synthesis import build_synthesis, provider_plan


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    load_dotenv(ROOT / ".env", override=False)
    config = AIConfig.from_env()
    if not config.enabled or not config.external_allowed:
        print("SKIP: cần EVP_AI_ENABLED=true và EVP_AI_EXTERNAL_ALLOWED=true.")
        return 2
    if not config.configured or not config.api_key:
        print("SKIP: cấu hình 9Router chưa đầy đủ.")
        return 2

    adapter = NineRouterLLMAdapter(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries, max_output_tokens=config.max_output_tokens,
    )
    model_status = adapter.check_model()
    if not model_status.get("available"):
        print(f"FAIL: model {config.model} không xuất hiện trong /models.")
        return 1

    rows = [{"entity_id": "synthetic", "date": day, "metric_code": code,
             "metric_normalized": label, "chart_value": value, "value_kind": "numeric",
             "effective_unit": "ticket"}
            for day, errors in (("2026-01-01", 12), ("2026-01-02", 8))
            for code, label, value in (("total", "Tổng số", 100), ("error", "Báo sai/Lỗi", errors))]
    computation = AnalyticsEngine().trend(pd.DataFrame(rows), entity_ref="synthetic",
                                         metric_code="error", start=date(2026, 1, 1), end=date(2026, 1, 2))
    snapshot = {
        "schemaVersion": "ai-trend-v3", "analysisId": "ana_synthetic_smoke",
        "scope": {"metricCode": "error", "metricDisplayName": computation.metric_display_name},
        "window": {"start": "2026-01-01", "end": "2026-01-02", "groupBy": "day"},
        "facts": list(computation.facts), "series": list(computation.series),
        "quality": computation.quality, "periodAnalytics": computation.period_analytics,
        "evidence": [{"evidenceId": p.evidence_id, "periodStart": p.period_start.isoformat(),
                      "periodEnd": p.period_end.isoformat()} for p in computation.points],
    }
    snapshot["synthesis"] = build_synthesis(snapshot)
    snapshot["facts"].extend(snapshot["synthesis"]["facts"])
    provider_payload = provider_plan(snapshot)
    prompt = PromptRegistry().trend()
    result = adapter.generate(system_prompt=prompt, payload=provider_payload)
    validated = OutputValidator().validate(result.content, snapshot)
    if not validated.valid:
        print("FAIL: provider trả output không qua validator: " + ", ".join(validated.errors))
        print("SYNTHETIC_RESPONSE: " + result.content)
        return 1
    print(
        f"PASS: model={result.model}; schema=ai-narrative-v4; "
        f"latency_ms={result.latency_ms}; attempts={result.attempt_count}; "
        "dữ liệu gửi=synthetic-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
