from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from .analytics import AnalyticsEngine, TrendComputation
from .config import AIConfig
from .evidence import EvidenceBuilder
from .llm import DisabledLLMAdapter, LLMAdapter, NineRouterLLMAdapter, ProviderError
from .repository import AnalysisSnapshotRepository
from .validation import OutputValidator


class PromptRegistry:
    version = "trend-summary-v2"
    resource_name = "trend-summary-v2.md"

    def __init__(self) -> None:
        source = (
            files("excel_visualization_pipeline.ai")
            .joinpath("prompts", self.resource_name)
            .read_text(encoding="utf-8")
        )
        self._trend = " ".join(line.strip() for line in source.splitlines() if line.strip())

    def trend(self) -> str:
        return self._trend


class AIApplicationService:
    schema_version = "ai-trend-v2"

    def __init__(
        self,
        *,
        config: AIConfig,
        adapter: LLMAdapter,
        repository: AnalysisSnapshotRepository,
        analytics: AnalyticsEngine | None = None,
        validator: OutputValidator | None = None,
        prompts: PromptRegistry | None = None,
    ):
        self.config = config
        self.adapter = adapter
        self.repository = repository
        self.analytics = analytics or AnalyticsEngine()
        self.validator = validator or OutputValidator()
        self.prompts = prompts or PromptRegistry()

    @classmethod
    def configured(cls, *, repository: AnalysisSnapshotRepository) -> "AIApplicationService":
        config = AIConfig.from_env()
        if config.can_call_external:
            adapter: LLMAdapter = NineRouterLLMAdapter(
                api_key=config.api_key or "", base_url=config.base_url, model=config.model,
                timeout_seconds=config.timeout_seconds, max_retries=config.max_retries,
            )
        else:
            reason = "feature_disabled" if not config.enabled else (
                "privacy_gate_closed" if not config.external_allowed else "provider_not_configured"
            )
            adapter = DisabledLLMAdapter(config.model, reason)
        return cls(config=config, adapter=adapter, repository=repository)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "configured": self.config.configured,
            "externalAllowed": self.config.external_allowed,
            "provider": "9router",
            "model": self.config.model,
            "availability": "not_checked" if self.config.can_call_external else "blocked",
            "privacyMode": "normalized_facts_only",
        }

    def check_provider(self) -> dict[str, Any]:
        if not self.config.can_call_external:
            return {**self.status(), "availability": "blocked"}
        try:
            return {**self.status(), "availability": "available" if self.adapter.check_model().get("available") else "model_missing"}
        except ProviderError as exc:
            return {**self.status(), "availability": "unavailable", "code": exc.code}

    def trend_summary(
        self,
        *,
        db_path: str | Path,
        source_key: str,
        project: str,
        entity_ref: str,
        metric_code: str,
        start: date,
        end: date,
        group_by: str = "day",
        data: pd.DataFrame,
        entities: pd.DataFrame,
    ) -> dict[str, Any]:
        if not self.config.enabled:
            raise PermissionError("Tính năng nhận định tự động đang bị tắt trong cấu hình hệ thống.")
        if entity_ref not in set(entities["entity_id"]):
            raise ValueError("Nội dung theo dõi không thuộc dự án đã chọn.")
        computation = self.analytics.trend(
            data, entity_ref=entity_ref, metric_code=metric_code, start=start, end=end,
            group_by=group_by,
        )
        evidence_builder = EvidenceBuilder(db_path, source_key)
        run_id, import_ref = evidence_builder.committed_version()
        entity_row = entities[entities["entity_id"].eq(entity_ref)].iloc[0].to_dict()
        analysis_id = f"ana_{uuid4().hex}"
        snapshot_id = f"as_{uuid4().hex}"
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        evidence = evidence_builder.build(
            computation, project=project, entity=entity_row, source_run_id=run_id
        )
        base = {
            "schemaVersion": self.schema_version,
            "analysisId": analysis_id,
            "kind": "trend",
            "status": computation.status,
            "scope": {
                "project": project,
                "entityRef": entity_ref,
                "entityLabel": entity_row["entity_label"],
                "mode": "node",
                "metricCode": metric_code,
                "metricDisplayName": computation.metric_display_name,
            },
            "window": {
                "start": start.isoformat(), "end": end.isoformat(),
                "groupBy": computation.group_by,
                "comparisonBasis": "period_over_period_and_first_last",
                "previousDate": computation.previous.period_start.isoformat() if computation.previous else None,
                "currentDate": computation.current.period_end.isoformat() if computation.current else None,
            },
            "dataAsOf": {
                "committedImportRef": import_ref, "snapshotId": snapshot_id,
                "generatedAt": generated_at, "stale": False,
            },
            "metric": {"unit": computation.unit, "aggregationRule": computation.aggregation_rule},
            "facts": list(computation.facts),
            "series": list(computation.series),
            "quality": computation.quality,
            "evidence": evidence,
            "provider": {
                "name": "9router", "model": self.config.model,
                "promptVersion": self.prompts.version,
            },
            "validation": {"status": "not_run", "errors": []},
        }
        checksum_payload = {key: base[key] for key in ("scope", "window", "dataAsOf", "metric", "facts", "series", "quality", "evidence")}
        checksum_payload["dataAsOf"] = {"committedImportRef": import_ref, "snapshotId": snapshot_id}
        base["dataAsOf"]["checksum"] = evidence_builder.checksum(checksum_payload)

        if computation.status == "insufficient_data":
            base["narrative"] = self._fallback(computation, "Không đủ dữ liệu để tạo so sánh.")
            self.repository.put(analysis_id, run_id, base)
            return base

        provider_payload = self._provider_payload(base)
        try:
            result = self.adapter.generate(system_prompt=self.prompts.trend(), payload=provider_payload)
            validated = self.validator.validate(result.content, base)
            if validated.valid:
                base["status"] = "ready"
                base["provider"]["model"] = result.model
                base["narrative"] = {"mode": "ai", **(validated.value or {})}
                base["validation"] = {"status": "accepted", "errors": []}
            else:
                base["status"] = "rejected_output"
                base["narrative"] = self._fallback(computation, "Phần diễn giải tự động không vượt qua bước kiểm chứng dữ liệu.")
                base["validation"] = {"status": "rejected", "errors": list(validated.errors)}
        except ProviderError as exc:
            base["status"] = "provider_unavailable"
            base["narrative"] = self._fallback(computation, "Không gọi được dịch vụ phân tích; các dữ kiện đã tính vẫn sử dụng được.")
            base["validation"] = {"status": "not_run", "errors": [exc.code]}
        self.repository.put(analysis_id, run_id, base)
        return base

    def get_analysis(self, analysis_id: str, *, db_path: str | Path, source_key: str) -> dict[str, Any] | None:
        stored = self.repository.get(analysis_id)
        if stored is None:
            return None
        source_run_id, payload = stored
        current_run_id, _ = EvidenceBuilder(db_path, source_key).committed_version()
        if current_run_id > source_run_id:
            payload["status"] = "stale"
            payload["dataAsOf"]["stale"] = True
        return payload

    @staticmethod
    def _provider_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
        token_seed = snapshot["dataAsOf"]["snapshotId"]
        token = lambda value: sha256(f"{token_seed}:{value}".encode()).hexdigest()[:16]
        return {
            "schemaVersion": "ai-provider-input-v1",
            "analysisId": snapshot["analysisId"],
            "scope": {
                "projectToken": token(snapshot["scope"]["project"]),
                "entityToken": token(snapshot["scope"]["entityRef"]),
                "metricCode": snapshot["scope"]["metricCode"],
                "metricDisplayName": snapshot["scope"]["metricDisplayName"],
            },
            "window": snapshot["window"],
            "metric": snapshot["metric"],
            "facts": snapshot["facts"],
            "series": snapshot["series"],
            "quality": snapshot["quality"],
            "evidenceIds": [item["evidenceId"] for item in snapshot["evidence"]],
        }

    @staticmethod
    def _fallback(computation: TrendComputation, reason: str) -> dict[str, Any]:
        if computation.previous is None or computation.current is None:
            summary = "Chưa có đủ hai kỳ dữ liệu hợp lệ để tính thay đổi và xu hướng."
            fact_ids = [item["factId"] for item in computation.facts if item["kind"] == "period_value"]
        else:
            direction = next(item["value"] for item in computation.facts if item["factId"] == "fact-direction")
            pattern = next(item["value"] for item in computation.facts if item["factId"] == "fact-trend-pattern")
            direction_labels = {"increasing": "tăng", "decreasing": "giảm", "unchanged": "không đổi"}
            pattern_labels = {
                "consistently_increasing": "tăng liên tục",
                "consistently_decreasing": "giảm liên tục",
                "unchanged": "không đổi qua các kỳ",
                "fluctuating": "dao động tăng giảm",
            }
            delta = next(item for item in computation.facts if item["factId"] == "fact-delta")
            relative = next((item for item in computation.facts if item["factId"] == "fact-relative-change"), None)
            delta_text = str(delta["displayValue"]).lstrip("+-")
            relative_text = f" ({str(relative['displayValue']).lstrip('+-')})" if relative else ""
            summary = (
                f"Qua {len(computation.points)} kỳ, giá trị kỳ cuối {direction_labels[direction]} "
                f"{delta_text}{relative_text} so với kỳ đầu; chuỗi {pattern_labels[pattern]}."
            )
            fact_ids = ["fact-previous", "fact-current", "fact-delta", "fact-direction", "fact-trend-pattern"]
            if relative:
                fact_ids.append("fact-relative-change")
        return {
            "mode": "deterministic",
            "schemaVersion": "ai-narrative-v1",
            "summary": {"text": summary, "factIds": fact_ids, "claimType": "descriptive"},
            "insights": [],
            "limitations": [reason, *computation.quality.get("limitations", [])],
            "suggestedChecks": ["Mở bằng chứng để đối chiếu observation hoặc aggregate nguồn."],
        }
