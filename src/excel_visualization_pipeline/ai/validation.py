from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
import re
from typing import Any


NUMBER = re.compile(r"(?<![\w-])[-+]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)")
DATE_TOKEN = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b")
CAUSE = re.compile(r"\b(nguyên nhân|gây ra|do .{0,50}(?:nên|dẫn đến)|vì .{0,50}(?:nên|dẫn đến))\b", re.IGNORECASE)
INJECTION = re.compile(r"(ignore (?:all |the )?(?:previous|system)|system prompt|api[_ -]?key|tiết lộ.*bí mật)", re.IGNORECASE)


def _numeric_candidates(raw: str) -> tuple[float, ...]:
    values: list[float] = []
    try:
        values.append(float(raw.replace(",", ".")))
    except ValueError:
        pass
    if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw):
        grouped = float(raw.replace(",", ""))
        if grouped not in values:
            values.append(grouped)
    return tuple(values)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    value: dict[str, Any] | None
    errors: tuple[str, ...]


class OutputValidator:
    schema_version = "ai-narrative-v1"

    def validate(self, content: str, snapshot: dict[str, Any]) -> ValidationResult:
        errors: list[str] = []
        try:
            value = json.loads(self._strip_fence(content))
        except (json.JSONDecodeError, TypeError):
            return ValidationResult(False, None, ("invalid_json",))
        if not isinstance(value, dict):
            return ValidationResult(False, None, ("root_must_be_object",))
        allowed_root = {"schemaVersion", "analysisId", "status", "summary", "insights", "limitations", "suggestedChecks"}
        if set(value) - allowed_root:
            errors.append("unexpected_field")
        if value.get("schemaVersion") != self.schema_version:
            errors.append("schema_version")
        if value.get("analysisId") != snapshot["analysisId"]:
            errors.append("analysis_id")
        if value.get("status") != "ready":
            errors.append("status")
        facts = {item["factId"]: item for item in snapshot.get("facts", [])}
        evidence_ids = {item["evidenceId"] for item in snapshot.get("evidence", [])}
        for fact in facts.values():
            if not set(fact.get("evidenceIds", [])).issubset(evidence_ids):
                errors.append("unresolved_fact_evidence")
        blocks: list[dict[str, Any]] = []
        summary = value.get("summary")
        if isinstance(summary, dict):
            blocks.append(summary)
        else:
            errors.append("summary")
        insights = value.get("insights", [])
        if not isinstance(insights, list) or not all(isinstance(item, dict) for item in insights):
            errors.append("insights")
        else:
            blocks.extend(insights)
        for block in blocks:
            text = block.get("text")
            refs = block.get("factIds")
            if block.get("claimType") != "descriptive" or not isinstance(text, str) or not isinstance(refs, list) or not refs:
                errors.append("claim_schema")
                continue
            if set(refs) - set(facts):
                errors.append("unknown_fact_id")
                continue
            if block is not summary and block.get("type") not in {"series_trend", "period_comparison", "data_quality"}:
                errors.append("insight_type")
            if CAUSE.search(text):
                errors.append("unsupported_cause")
            if INJECTION.search(text):
                errors.append("prompt_injection_content")
            referenced_facts = [facts[ref] for ref in refs]
            numeric_text = self._strip_grounded_temporal_tokens(text, snapshot, errors)
            self._validate_numbers(numeric_text, referenced_facts, errors)
            self._validate_direction(text, referenced_facts, errors)
        if not isinstance(value.get("limitations", []), list) or not isinstance(value.get("suggestedChecks", []), list):
            errors.append("list_field")
        return ValidationResult(not errors, value if not errors else None, tuple(dict.fromkeys(errors)))

    @staticmethod
    def _strip_fence(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        return text

    @staticmethod
    def _strip_grounded_temporal_tokens(
        text: str,
        snapshot: dict[str, Any],
        errors: list[str],
    ) -> str:
        allowed: set[str] = set()
        window = snapshot.get("window", {})
        raw_dates = [
            window.get("start"), window.get("end"),
            window.get("previousDate"), window.get("currentDate"),
        ]
        for point in snapshot.get("series", []):
            raw_dates.extend([point.get("periodStart"), point.get("periodEnd")])
            label = point.get("periodLabel")
            if isinstance(label, str) and label:
                allowed.add(label)
        for raw in raw_dates:
            if not isinstance(raw, str) or not raw:
                continue
            allowed.add(raw)
            try:
                allowed.add(date.fromisoformat(raw).strftime("%d/%m/%Y"))
            except ValueError:
                pass
        stripped = text
        for token in sorted(allowed, key=len, reverse=True):
            stripped = stripped.replace(token, " ")
        if DATE_TOKEN.search(stripped):
            errors.append("unsupported_date_mention")
        return DATE_TOKEN.sub(" ", stripped)

    @staticmethod
    def _validate_numbers(text: str, facts: list[dict[str, Any]], errors: list[str]) -> None:
        allowed = [float(item["value"]) for item in facts if isinstance(item.get("value"), (int, float))]
        for raw in NUMBER.findall(text):
            explicitly_signed = raw.startswith(("+", "-"))
            if not any(
                math.isclose(
                    number,
                    candidate if explicitly_signed else abs(candidate),
                    rel_tol=0.000001,
                    abs_tol=0.011,
                )
                for number in _numeric_candidates(raw)
                for candidate in allowed
            ):
                errors.append("unsupported_numeric_mention")
                return

    @staticmethod
    def _validate_direction(text: str, facts: list[dict[str, Any]], errors: list[str]) -> None:
        direction_values = {
            item.get("value")
            for item in facts
            if item.get("kind") in {"direction", "period_direction", "trend_pattern"}
        }
        mapped = {
            "consistently_increasing": "increasing",
            "consistently_decreasing": "decreasing",
            "fluctuating": "fluctuating",
        }
        directions = {mapped.get(str(value), value) for value in direction_values}
        if len(directions) != 1:
            return
        direction = next(iter(directions))
        lowered = text.lower()
        if direction == "increasing" and re.search(r"\b(giảm|thấp hơn)\b", lowered):
            errors.append("direction_conflict")
        elif direction == "decreasing" and re.search(r"\b(tăng|cao hơn)\b", lowered):
            errors.append("direction_conflict")
        elif direction == "unchanged" and re.search(r"\b(tăng|giảm|cao hơn|thấp hơn)\b", lowered):
            errors.append("direction_conflict")
