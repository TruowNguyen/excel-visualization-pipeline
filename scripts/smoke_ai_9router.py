"""Opt-in 9Router smoke test using synthetic facts only.

This script deliberately does not read SQLite or workbook data. Run it only after
the privacy gate has been approved and the server-side environment is loaded.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

from excel_visualization_pipeline.ai import AIConfig, NineRouterLLMAdapter, OutputValidator, PromptRegistry


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
        max_retries=config.max_retries,
    )
    model_status = adapter.check_model()
    if not model_status.get("available"):
        print(f"FAIL: model {config.model} không xuất hiện trong /models.")
        return 1

    snapshot = {
        "analysisId": "ana_synthetic_smoke",
        "window": {"start": "2026-01-01", "end": "2026-01-02", "groupBy": "day", "comparisonBasis": "period_over_period_and_first_last"},
        "series": [
            {"periodStart": "2026-01-01", "periodEnd": "2026-01-01", "periodLabel": "01/01/2026", "value": 12, "change": None, "evidenceId": "ev-period-000"},
            {"periodStart": "2026-01-02", "periodEnd": "2026-01-02", "periodLabel": "02/01/2026", "value": 8, "change": {"absolute": -4, "relativePercent": -33.33, "direction": "decreasing"}, "evidenceId": "ev-period-001"},
        ],
        "facts": [
            {"factId": "fact-period-000", "kind": "period_value", "value": 12, "evidenceIds": ["ev-period-000"]},
            {"factId": "fact-period-001", "kind": "period_value", "value": 8, "evidenceIds": ["ev-period-001"]},
            {"factId": "fact-period-count", "kind": "period_count", "value": 2, "evidenceIds": ["ev-period-000", "ev-period-001"]},
            {"factId": "fact-change-001", "kind": "period_change", "value": -4, "evidenceIds": ["ev-period-000", "ev-period-001"]},
            {"factId": "fact-previous", "kind": "previous", "value": 12, "evidenceIds": ["ev-period-000"]},
            {"factId": "fact-current", "kind": "current", "value": 8, "evidenceIds": ["ev-period-001"]},
            {"factId": "fact-delta", "kind": "absolute_change", "value": -4, "evidenceIds": ["ev-period-000", "ev-period-001"]},
            {"factId": "fact-relative-change", "kind": "relative_change", "value": -33.33, "evidenceIds": ["ev-period-000", "ev-period-001"]},
            {"factId": "fact-direction", "kind": "direction", "value": "decreasing", "evidenceIds": ["ev-period-000", "ev-period-001"]},
            {"factId": "fact-trend-pattern", "kind": "trend_pattern", "value": "consistently_decreasing", "evidenceIds": ["ev-period-000", "ev-period-001"]},
        ],
        "evidence": [{"evidenceId": "ev-period-000"}, {"evidenceId": "ev-period-001"}],
    }
    provider_payload = {
        "schemaVersion": "ai-provider-input-v1",
        "analysisId": snapshot["analysisId"],
        "scope": {"projectToken": "synthetic", "entityToken": "synthetic", "metricCode": "error", "metricDisplayName": "Báo sai/Lỗi"},
        "window": snapshot["window"],
        "metric": {"unit": "ticket", "aggregationRule": "daily_value"},
        "facts": snapshot["facts"],
        "series": snapshot["series"],
        "quality": {"status": "valid", "validPeriodCount": 2, "expectedPeriodCount": 2, "coverageRatio": 1},
        "evidenceIds": ["ev-period-000", "ev-period-001"],
    }
    prompt = PromptRegistry().trend()
    result = adapter.generate(system_prompt=prompt, payload=provider_payload)
    validated = OutputValidator().validate(result.content, snapshot)
    if not validated.valid:
        print("FAIL: provider trả output không qua validator: " + ", ".join(validated.errors))
        print("SYNTHETIC_RESPONSE: " + result.content)
        return 1
    print(f"PASS: model={result.model}; schema=ai-narrative-v1; dữ liệu gửi=synthetic-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
