from __future__ import annotations

from datetime import date, datetime, timezone
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

import pandas as pd

from .analytics import AnalyticsEngine, TrendComputation
from .config import AIConfig
from .evidence import EvidenceBuilder
from .llm import DisabledLLMAdapter, LLMAdapter, NineRouterLLMAdapter, ProviderError
from .repository import AnalysisSnapshotRepository
from .validation import OutputValidator
from .overview import build_overview, overview_fallback
from .synthesis import build_synthesis, provider_plan, synthesis_fallback


class PromptRegistry:
    version = "trend-summary-v15"
    overview_version = "metric-overview-v11"
    resource_name = "grounded-insight-v5.md"

    def __init__(self) -> None:
        source = (
            files("excel_visualization_pipeline.ai")
            .joinpath("prompts", self.resource_name)
            .read_text(encoding="utf-8")
        )
        self._trend = " ".join(line.strip() for line in source.splitlines() if line.strip())
        self._overview = files("excel_visualization_pipeline.ai").joinpath(
            "prompts", self.resource_name
        ).read_text(encoding="utf-8")

    def trend(self) -> str:
        return self._trend

    def overview(self) -> str:
        return self._overview


class AIApplicationService:
    schema_version = "ai-trend-v3"

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
                max_output_tokens=config.max_output_tokens,
                report_max_output_tokens=config.report_max_output_tokens,
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

    @staticmethod
    def _validation_receipt(result: Any) -> dict[str, Any]:
        structural = {"invalid_json", "claim_schema", "narrative_identity", "duplicate_claim_id"}
        numerical = {"unsupported_numeric_mention", "unsupported_date_mention", "numeric_period_mismatch", "numeric_role_mismatch"}
        grounding = {"candidate_reference", "candidate_fact_mismatch", "unknown_fact_id", "unresolved_fact_evidence",
                     "unresolved_relationship", "fact_scope_mismatch", "metric_scope_mismatch", "evidence_scope_mismatch"}
        def category(code: str) -> str:
            return "structure" if code in structural else "numerical_temporal" if code in numerical else "grounding" if code in grounding else "safety" if code == "prompt_injection_content" else "semantic"
        return {"status": "partial" if result.valid and result.errors else "accepted" if result.valid else "rejected",
                "errors": list(result.errors), "categories": list(dict.fromkeys(category(code) for code in result.errors)),
                "warnings": list(dict.fromkeys(code for item in result.claim_results for code in item.get("warnings", []))),
                "claimResults": [{**item, "categories": list(dict.fromkeys(category(code) for code in item["errors"]))} for item in result.claim_results]}

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
        if metric_code == "all":
            return self.overview_summary(
                db_path=db_path, source_key=source_key, project=project,
                entity_ref=entity_ref, start=start, end=end, group_by=group_by,
                data=data, entities=entities,
            )
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
            "periodAnalytics": computation.period_analytics,
            "historicalContext": computation.historical_context,
            "quality": computation.quality,
            "evidence": evidence,
            "provider": {
                "name": "9router", "model": self.config.model,
                "promptVersion": self.prompts.version,
            },
            "validation": {"status": "not_run", "errors": []},
        }
        base["synthesis"] = build_synthesis(base)
        base["facts"].extend(base["synthesis"]["facts"])
        base["inspectionChecks"] = base["synthesis"]["inspectionChecks"]
        base["quality"]["limitations"] = base["synthesis"]["limitations"]
        checksum_payload = {key: base[key] for key in (
            "scope", "window", "dataAsOf", "metric", "facts", "series",
            "periodAnalytics", "historicalContext", "quality", "evidence", "synthesis", "inspectionChecks",
        )}
        checksum_payload["dataAsOf"] = {"committedImportRef": import_ref, "snapshotId": snapshot_id}
        base["dataAsOf"]["checksum"] = evidence_builder.checksum(checksum_payload)

        if computation.status == "insufficient_data" or not base["synthesis"]["selectedCandidateIds"]:
            base["status"] = "insufficient_data"
            base["narrative"] = synthesis_fallback(base["synthesis"], "Không đủ dữ liệu để tạo so sánh.")
            self.repository.put(analysis_id, run_id, base)
            return base

        provider_payload = self._provider_payload(base)
        provider_started_at = time.monotonic()
        try:
            result = self.adapter.generate(system_prompt=self.prompts.trend(), payload=provider_payload)
            base["provider"]["latencyMs"] = result.latency_ms
            base["provider"]["attemptCount"] = result.attempt_count
            normalized_content = self.validator.normalize_fact_references(result.content, base)
            validated = self.validator.validate(normalized_content, base)
            if validated.valid:
                base["status"] = "ready"
                base["provider"]["model"] = result.model
                base["narrative"] = {"mode": "ai", **(validated.value or {})}
                base["validation"] = self._validation_receipt(validated)
            else:
                base["status"] = "rejected_output"
                base["narrative"] = synthesis_fallback(base["synthesis"], "Phần diễn giải tự động không vượt qua bước kiểm chứng dữ liệu.")
                base["validation"] = self._validation_receipt(validated)
        except ProviderError as exc:
            base["status"] = "provider_unavailable"
            base["provider"]["latencyMs"] = exc.latency_ms or round(
                (time.monotonic() - provider_started_at) * 1000
            )
            base["provider"]["attemptCount"] = exc.attempt_count
            base["narrative"] = synthesis_fallback(base["synthesis"], "Không gọi được dịch vụ phân tích; các dữ kiện đã tính vẫn sử dụng được.")
            base["validation"] = {"status": "not_run", "errors": [exc.code]}
        self.repository.put(analysis_id, run_id, base)
        return base

    def overview_summary(
        self,
        *,
        db_path: str | Path,
        source_key: str,
        project: str,
        entity_ref: str,
        start: date,
        end: date,
        group_by: str,
        data: pd.DataFrame,
        entities: pd.DataFrame,
    ) -> dict[str, Any]:
        if not self.config.enabled:
            raise PermissionError("Tính năng nhận định tự động đang bị tắt trong cấu hình hệ thống.")
        if entity_ref not in set(entities["entity_id"]):
            raise ValueError("Nội dung theo dõi không thuộc dự án đã chọn.")

        analysis_id = f"ana_{uuid4().hex}"
        snapshot_id = f"as_{uuid4().hex}"
        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        evidence_builder = EvidenceBuilder(db_path, source_key)
        run_id, import_ref = evidence_builder.committed_version()
        entity_row = entities[entities["entity_id"].eq(entity_ref)].iloc[0].to_dict()
        metrics: list[dict[str, Any]] = []
        computations: dict[str, TrendComputation] = {}

        for metric_code in ("total", "error", "error_rate"):
            computation = self.analytics.trend(
                data, entity_ref=entity_ref, metric_code=metric_code,
                start=start, end=end, group_by=group_by,
            )
            computations[metric_code] = computation
            evidence = evidence_builder.build(
                computation, project=project, entity=entity_row, source_run_id=run_id,
            )
            metric_payload = {
                "metricCode": metric_code,
                "metricDisplayName": computation.metric_display_name,
                "status": computation.status,
                "unit": computation.unit,
                "aggregationRule": computation.aggregation_rule,
                "facts": list(computation.facts),
                "series": list(computation.series),
                "periodAnalytics": computation.period_analytics,
                "historicalContext": computation.historical_context,
                "quality": computation.quality,
                "evidence": evidence,
            }
            metrics.append(self._prefix_analysis_ids(metric_payload, metric_code))

        overview = build_overview(computations, metrics)
        facts = [fact for metric in metrics for fact in metric["facts"]] + overview["facts"]
        evidence = [item for metric in metrics for item in metric["evidence"]]
        limitations = overview["limitations"]
        available_count = sum(metric["status"] != "insufficient_data" for metric in metrics)
        base = {
            "schemaVersion": "ai-overview-v2",
            "analysisId": analysis_id,
            "kind": "metric_overview",
            "status": "ready" if available_count else "insufficient_data",
            "scope": {
                "project": project, "entityRef": entity_ref,
                "entityLabel": entity_row["entity_label"], "mode": "node",
                "metricCode": "all", "metricDisplayName": "Tất cả chỉ số",
            },
            "window": {
                "start": start.isoformat(), "end": end.isoformat(), "groupBy": group_by,
                "comparisonBasis": "per_metric_period_over_period_and_first_last",
                "previousDate": start.isoformat(), "currentDate": end.isoformat(),
            },
            "dataAsOf": {
                "committedImportRef": import_ref, "snapshotId": snapshot_id,
                "generatedAt": generated_at, "stale": False,
            },
            "metrics": metrics,
            "comparisonBasis": overview["comparisonBasis"],
            "insightCandidates": overview["insightCandidates"],
            "inspectionChecks": overview["inspectionChecks"],
            "facts": facts,
            "evidence": evidence,
            "quality": {
                "status": "valid" if available_count == 3 else "partial" if available_count else "insufficient_data",
                "availableMetricCount": available_count,
                "expectedMetricCount": 3,
                "validPeriodCount": max(
                    (metric["quality"].get("validPeriodCount", 0) for metric in metrics),
                    default=0,
                ),
                "expectedPeriodCount": max(
                    (metric["quality"].get("expectedPeriodCount", 0) for metric in metrics),
                    default=0,
                ),
                "limitations": limitations,
            },
            "provider": {
                "name": "9router", "model": self.config.model,
                "promptVersion": self.prompts.overview_version,
            },
            "validation": {"status": "not_run", "errors": []},
        }
        base["synthesis"] = build_synthesis(base)
        base["facts"].extend(base["synthesis"]["facts"])
        base["inspectionChecks"] = base["synthesis"]["inspectionChecks"]
        base["quality"]["limitations"] = base["synthesis"]["limitations"]
        checksum_payload = {
            key: base[key] for key in ("scope", "window", "metrics", "facts", "evidence", "quality", "comparisonBasis", "insightCandidates", "inspectionChecks", "synthesis")
        }
        checksum_payload["dataAsOf"] = {
            "committedImportRef": import_ref, "snapshotId": snapshot_id,
        }
        base["dataAsOf"]["checksum"] = evidence_builder.checksum(checksum_payload)

        fallback = synthesis_fallback(base["synthesis"])
        if not available_count or not base["synthesis"]["selectedCandidateIds"]:
            base["status"] = "insufficient_data"
            base["narrative"] = fallback
            self.repository.put(analysis_id, run_id, base)
            return base

        provider_payload = self._overview_provider_payload(base)
        provider_started_at = time.monotonic()
        try:
            result = self.adapter.generate(
                system_prompt=self.prompts.overview(), payload=provider_payload,
            )
            base["provider"]["latencyMs"] = result.latency_ms
            base["provider"]["attemptCount"] = result.attempt_count
            normalized_content = self.validator.normalize_fact_references(result.content, base)
            validated = self.validator.validate(normalized_content, base)
            if validated.valid:
                base["status"] = "ready"
                base["provider"]["model"] = result.model
                base["narrative"] = {"mode": "ai", **(validated.value or {})}
                base["validation"] = self._validation_receipt(validated)
            else:
                base["status"] = "rejected_output"
                base["narrative"] = fallback
                base["validation"] = self._validation_receipt(validated)
        except ProviderError as exc:
            base["status"] = "provider_unavailable"
            base["provider"]["latencyMs"] = exc.latency_ms or round(
                (time.monotonic() - provider_started_at) * 1000
            )
            base["provider"]["attemptCount"] = exc.attempt_count
            base["narrative"] = fallback
            base["validation"] = {"status": "not_run", "errors": [exc.code]}
        self.repository.put(analysis_id, run_id, base)
        return base

    @staticmethod
    def _prefix_analysis_ids(value: Any, prefix: str) -> Any:
        result = deepcopy(value)

        def visit(item: Any, key: str | None = None) -> Any:
            if isinstance(item, dict):
                return {child_key: visit(child, child_key) for child_key, child in item.items()}
            if isinstance(item, list):
                return [visit(child, key) for child in item]
            if isinstance(item, str) and key in {"factId", "evidenceId"}:
                return f"{prefix}:{item}"
            if isinstance(item, str) and key in {"factIds", "evidenceIds", "overviewFactIds", "summaryFactIds", "supportingFactIds"}:
                return f"{prefix}:{item}"
            return item

        return visit(result)

    @classmethod
    def _overview_provider_payload(cls, snapshot: dict[str, Any]) -> dict[str, Any]:
        if snapshot.get("synthesis"):
            return provider_plan(snapshot)
        if snapshot["schemaVersion"] == "ai-overview-v2":
            candidates = snapshot["insightCandidates"]
            selected_ids = {ref for item in candidates for ref in item["factIds"]}
            facts = [item for item in snapshot["facts"] if item["factId"] in selected_ids]
            # Only normalized candidates/facts and logical IDs cross the existing privacy boundary.
            return {
                "schemaVersion": "ai-overview-provider-input-v2", "analysisId": snapshot["analysisId"],
                "insightCandidates": candidates, "facts": facts,
                "evidenceIds": sorted({ref for item in facts for ref in item["evidenceIds"]}),
            }
        token_seed = snapshot["dataAsOf"]["snapshotId"]
        token = lambda value: sha256(f"{token_seed}:{value}".encode()).hexdigest()[:16]
        provider_metrics = []
        selected_facts: list[dict[str, Any]] = []
        evidence_ids: set[str] = set()
        for metric in snapshot["metrics"]:
            metric_snapshot = {
                "analysisId": snapshot["analysisId"],
                "scope": {
                    **snapshot["scope"],
                    "metricCode": metric["metricCode"],
                    "metricDisplayName": metric["metricDisplayName"],
                },
                "window": snapshot["window"],
                "metric": {
                    "unit": metric["unit"],
                    "aggregationRule": metric["aggregationRule"],
                },
                "facts": metric["facts"], "series": metric["series"],
                "periodAnalytics": {
                    key: value for key, value in metric["periodAnalytics"].items()
                    if key in {"policyVersion", "peak", "lowest", "latestChange"}
                },
                "historicalContext": {
                    key: value for key, value in metric["historicalContext"].items()
                    if key in {
                        "status", "observedPeriodCount", "currentPosition",
                        "historicalRange", "limitations",
                    }
                },
                "quality": metric["quality"], "evidence": metric["evidence"],
                "dataAsOf": snapshot["dataAsOf"],
            }
            compact = cls._provider_payload(metric_snapshot)
            selected_facts.extend(compact["facts"])
            evidence_ids.update(compact["evidenceIds"])
            provider_metrics.append({
                "metricCode": metric["metricCode"],
                "metricDisplayName": metric["metricDisplayName"],
                "status": metric["status"], "metric": compact["metric"],
                "periodAnalytics": compact["periodAnalytics"],
                "historicalContext": compact["historicalContext"],
                "quality": compact["quality"],
            })
        return {
            "schemaVersion": "ai-overview-provider-input-v1",
            "analysisId": snapshot["analysisId"],
            "scope": {
                "projectToken": token(snapshot["scope"]["project"]),
                "entityToken": token(snapshot["scope"]["entityRef"]),
            },
            "window": snapshot["window"], "metrics": provider_metrics,
            "facts": selected_facts, "evidenceIds": sorted(evidence_ids),
            "quality": snapshot["quality"],
        }

    @staticmethod
    def _overview_fallback(metrics: list[dict[str, Any]]) -> dict[str, Any]:
        clauses: list[str] = []
        fact_ids: list[str] = []
        for metric in metrics:
            current = next((fact for fact in metric["facts"] if fact["kind"] == "current"), None)
            direction = next((fact for fact in metric["facts"] if fact["kind"] == "direction"), None)
            if current is None:
                continue
            direction_text = {
                "increasing": "tăng", "decreasing": "giảm", "unchanged": "không đổi",
            }.get(direction["value"] if direction else "", "chưa đủ dữ liệu so sánh")
            clauses.append(
                f"{metric['metricDisplayName']} kết thúc ở {current['displayValue']} và {direction_text} so với kỳ đầu"
            )
            fact_ids.append(current["factId"])
            if direction:
                fact_ids.append(direction["factId"])
        summary = "; ".join(clauses) + "." if clauses else "Chưa đủ dữ liệu hợp lệ để tổng quan các chỉ số."
        limitations = list(dict.fromkeys(
            limitation
            for metric in metrics
            for limitation in metric["quality"].get("limitations", [])
        ))
        return {
            "mode": "deterministic", "schemaVersion": "ai-narrative-v1",
            "summary": {"text": summary, "factIds": fact_ids, "claimType": "descriptive"},
            "insights": [], "limitations": limitations,
            "suggestedChecks": ["Mở bằng chứng của từng chỉ số để đối chiếu dữ liệu nguồn."],
        }

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
        if snapshot.get("synthesis"):
            return provider_plan(snapshot)
        token_seed = snapshot["dataAsOf"]["snapshotId"]
        token = lambda value: sha256(f"{token_seed}:{value}".encode()).hexdigest()[:16]
        fact_ids = {
            "fact-period-count", "fact-previous", "fact-current", "fact-delta",
            "fact-relative-change", "fact-direction", "fact-trend-pattern",
            "fact-history-period-count",
        }
        # Overview IDs are namespaced; preserve the same endpoint facts as a
        # single-metric request rather than silently omitting them.
        prefix = snapshot["scope"]["metricCode"] + ":"
        if any(item["factId"].startswith(prefix) for item in snapshot["facts"]):
            fact_ids = {prefix + fact_id for fact_id in fact_ids}

        def collect_fact_ids(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"factIds", "summaryFactIds", "overviewFactIds"} and isinstance(child, list):
                        fact_ids.update(item for item in child if isinstance(item, str))
                    else:
                        collect_fact_ids(child)
            elif isinstance(value, list):
                for child in value:
                    collect_fact_ids(child)

        compact_history = {
            key: value
            for key, value in snapshot["historicalContext"].items()
            if key != "periods"
        }
        compact_analytics = deepcopy(snapshot["periodAnalytics"])
        if compact_analytics.get("temporalStructure"):
            compact_analytics["temporalStructure"] = {
                key: value for key, value in compact_analytics["temporalStructure"].items()
                if key in {"policyVersion", "summaryText", "summaryFactIds", "overviewText", "overviewFactIds"}
            }
        collect_fact_ids(compact_analytics)
        collect_fact_ids(compact_history)
        selected_facts = [item for item in snapshot["facts"] if item["factId"] in fact_ids]
        evidence_ids = sorted({
            evidence_id
            for fact in selected_facts
            for evidence_id in fact.get("evidenceIds", [])
        })
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
            "facts": selected_facts,
            "periodAnalytics": compact_analytics,
            "historicalContext": compact_history,
            "quality": snapshot["quality"],
            "evidenceIds": evidence_ids,
        }

    @staticmethod
    def _fallback(computation: TrendComputation, reason: str) -> dict[str, Any]:
        if computation.previous is None or computation.current is None:
            summary = "Chưa có đủ hai kỳ dữ liệu hợp lệ để tính thay đổi và xu hướng."
            fact_ids = [item["factId"] for item in computation.facts if item["kind"] == "period_value"]
        elif computation.period_analytics.get("temporalStructure"):
            structure = computation.period_analytics["temporalStructure"]
            summary = structure["summaryText"]
            fact_ids = structure["summaryFactIds"]
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
