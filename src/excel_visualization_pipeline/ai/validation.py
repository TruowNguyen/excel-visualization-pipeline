from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
import re
from typing import Any

from .reading import plain_text
from .semantic import CLAIM_TYPES, POLICY as SEMANTIC_POLICY, validate_text
from .report import SECTIONS, report_output


NUMBER = re.compile(r"(?<![\w-])[-+]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)")
DATE_TOKEN = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b")
CAUSE = re.compile(r"\b(nguyên nhân|gây ra|do .{0,50}(?:nên|dẫn đến)|vì .{0,50}(?:nên|dẫn đến))\b", re.IGNORECASE)
INJECTION = re.compile(r"(ignore (?:all |the )?(?:previous|system)|system prompt|api[_ -]?key|tiết lộ.*bí mật)", re.IGNORECASE)


def _load_json(content: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise json.JSONDecodeError("Duplicate field", content, 0)
            result[key] = value
        return result
    def invalid_constant(raw: str) -> Any:
        raise json.JSONDecodeError("Non-finite value", content, 0)
    return json.loads(content, object_pairs_hook=pairs, parse_constant=invalid_constant)


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
    claim_results: tuple[dict[str, Any], ...] = ()


class OutputValidator:
    schema_version = "ai-narrative-v1"

    def normalize_fact_references(self, content: str, snapshot: dict[str, Any]) -> str:
        """Complete omitted citations only from deterministic facts already in scope."""
        if snapshot.get("synthesis") or snapshot.get("schemaVersion") == "ai-overview-v2":
            # V2 citations are exact candidate dependencies, not heuristically repaired.
            return content
        try:
            value = _load_json(self._strip_fence(content))
        except (json.JSONDecodeError, TypeError):
            return content
        if not isinstance(value, dict):
            return content
        facts = {item["factId"]: item for item in snapshot.get("facts", [])}
        support_groups: dict[str, set[str]] = {}

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                if value.get("policyVersion") == "chronological-stages-v1":
                    return
                refs = value.get("factIds")
                if isinstance(refs, list):
                    valid_refs = {ref for ref in refs if isinstance(ref, str) and ref in facts}
                    for ref in valid_refs:
                        support_groups.setdefault(ref, set()).update(valid_refs)
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        for metric in snapshot.get("metrics", []):
            collect(metric.get("periodAnalytics"))
            collect(metric.get("historicalContext"))
        collect(snapshot.get("periodAnalytics"))
        collect(snapshot.get("historicalContext"))

        blocks = [value.get("summary"), *value.get("insights", [])]
        for block in blocks:
            if not isinstance(block, dict) or not isinstance(block.get("factIds"), list):
                continue
            refs = [ref for ref in block["factIds"] if isinstance(ref, str)]
            completed = list(refs)
            for ref in refs:
                for supporting_ref in support_groups.get(ref, set()):
                    if supporting_ref not in completed:
                        completed.append(supporting_ref)

            text = block.get("text", "")
            if isinstance(text, str) and re.search(r"\d+(?:[.,]\d+)?\s+kỳ\b", text, re.IGNORECASE):
                prefixes = {ref.split(":", 1)[0] for ref in completed if ":" in ref}
                for raw in NUMBER.findall(text):
                    candidates = _numeric_candidates(raw)
                    for fact_id, fact in facts.items():
                        if prefixes and fact_id.split(":", 1)[0] not in prefixes:
                            continue
                        if fact.get("kind") not in {"period_count", "historical_period_count"}:
                            continue
                        fact_value = fact.get("value")
                        if isinstance(fact_value, (int, float)) and any(
                            math.isclose(float(fact_value), number, rel_tol=0.000001, abs_tol=0.011)
                            for number in candidates
                        ) and fact_id not in completed:
                            completed.append(fact_id)
            block["factIds"] = completed
        return json.dumps(value, ensure_ascii=False, allow_nan=False)

    def validate(self, content: str, snapshot: dict[str, Any]) -> ValidationResult:
        if snapshot.get("synthesis"):
            return self._validate_synthesis(content, snapshot)
        if snapshot.get("schemaVersion") == "ai-overview-v2":
            return self._validate_overview(content, snapshot)
        errors: list[str] = []
        try:
            value = _load_json(self._strip_fence(content))
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
        structure = snapshot.get("periodAnalytics", {}).get("temporalStructure")
        if isinstance(summary, dict):
            blocks.append(summary)
            if structure and (summary.get("text") != structure["summaryText"] or summary.get("factIds") != structure["summaryFactIds"]):
                errors.append("whole_series_priority")
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
            if block is summary and structure and text == structure["summaryText"] and refs == structure["summaryFactIds"]:
                # Exact deterministic story: chronology and meaning are engine-owned.
                continue
            numeric_text = self._strip_grounded_temporal_tokens(text, snapshot, errors)
            self._validate_numbers(numeric_text, referenced_facts, errors)
            self._validate_direction(text, referenced_facts, errors)
        if not isinstance(value.get("limitations", []), list) or not isinstance(value.get("suggestedChecks", []), list):
            errors.append("list_field")
        return ValidationResult(not errors, value if not errors else None, tuple(dict.fromkeys(errors)))

    def _validate_synthesis(self, content: str, snapshot: dict[str, Any]) -> ValidationResult:
        """Fail-closed relation grammar, not numeric membership or paragraph equality.

        Each expression is bound to a proved predicate, metric and temporal scope.
        Unsupported causal/quality/magnitude/date/value tails cannot full-match.
        Numeric evidence stays in engine-owned anchors, not free model arithmetic.
        """
        try:
            value = _load_json(self._strip_fence(content))
        except (json.JSONDecodeError, TypeError):
            return ValidationResult(False, None, ("invalid_json",))
        if isinstance(value, dict) and value.get("schemaVersion") in {"ai-narrative-v4", "ai-narrative-v5"}:
            return self._validate_semantic(value, snapshot)
        if not isinstance(value, dict) or set(value) != {"schemaVersion", "analysisId", "status", "claims"}:
            return ValidationResult(False, None, ("claim_schema",))
        errors: list[str] = []
        if value["schemaVersion"] != "ai-narrative-v3" or value["analysisId"] != snapshot["analysisId"] or value["status"] != "ready":
            errors.append("narrative_identity")
        claims = value["claims"]
        if not isinstance(claims, list) or not 1 <= len(claims) <= 2 or any(not isinstance(c, dict) for c in claims):
            return ValidationResult(False, None, ("claim_schema",))
        plan = snapshot["synthesis"]
        candidates = {c["candidateId"]: c for c in plan["candidates"]}
        ids = [c.get("candidateId") for c in claims]
        if ids != plan["selectedCandidateIds"]:
            errors.append("candidate_priority")
        facts = {f["factId"]: f for f in snapshot["facts"]}
        evidence = {e["evidenceId"] for e in snapshot["evidence"]}
        for claim in claims:
            if set(claim) != {"candidateId", "text", "factIds"}:
                errors.append("claim_schema")
            cid = claim.get("candidateId")
            if not isinstance(cid, str) or cid not in candidates:
                errors.append("candidate_reference")
                continue
            candidate = candidates[cid]
            refs = claim.get("factIds")
            if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs) or len(refs) != len(set(refs)) or set(refs) != set(candidate["factIds"]):
                errors.append("candidate_fact_mismatch")
            if any(ref not in facts or not set(facts[ref]["evidenceIds"]) <= evidence for ref in candidate["factIds"]):
                errors.append("unresolved_fact_evidence")
            relation = facts.get(candidate["factIds"][0], {})
            if relation.get("kind") != "insight_relation" or relation.get("value") != candidate["kind"] or relation.get("operandFactIds") != candidate["factIds"][1:]:
                errors.append("unresolved_relationship")
            text = claim.get("text")
            if not isinstance(text, str) or len(text) > 650:
                errors.append("claim_schema")
                continue
            if NUMBER.search(text):
                errors.append("unsupported_numeric_mention")
            if CAUSE.search(text) or re.search(r"\b(camera|nguyên nhân|gây ra|khiến|dự báo|sẽ|chất lượng|bất thường đáng kể|tốt hơn|xấu hơn|mạnh|nhẹ|nghiêm trọng)\b", text, re.I):
                errors.append("unsupported_meaning")
            if INJECTION.search(text):
                errors.append("prompt_injection_content")
            if not any(re.fullmatch(expression, text.strip(), re.I) for expression in candidate["expressions"]):
                errors.append("unsupported_relation_expression")
        if errors:
            return ValidationResult(False, None, tuple(dict.fromkeys(errors)))
        normalized = {"schemaVersion": "ai-narrative-v3", "analysisId": snapshot["analysisId"], "status": "ready",
                      "summary": {"text": " ".join(plain_text(c["text"].strip(), candidates[c["candidateId"]]["anchors"][0]["metricDisplayName"] if len(candidates[c["candidateId"]]["metricCodes"]) == 1 else "") for c in claims), "candidateIds": ids,
                                  "factIds": list(dict.fromkeys(ref for c in claims for ref in c["factIds"])), "claimType": "descriptive"},
                      "insights": [], "limitations": plan["limitations"], "suggestedChecks": []}
        return ValidationResult(True, normalized, ())

    def _validate_semantic(self, value: dict[str, Any], snapshot: dict[str, Any]) -> ValidationResult:
        """Strict envelope; independently ground every claim; preserve survivors."""
        if set(value) != {"schemaVersion", "analysisId", "status", "claims"}:
            return ValidationResult(False, None, ("claim_schema",))
        if value["analysisId"] != snapshot["analysisId"] or value["status"] != "ready":
            return ValidationResult(False, None, ("narrative_identity",))
        claims = value["claims"]
        report_mode = value["schemaVersion"] == "ai-narrative-v5"
        if not isinstance(claims, list) or not 1 <= len(claims) <= (sum(SECTIONS.values()) if report_mode else 2):
            return ValidationResult(False, None, ("claim_schema",))
        for claim in claims:
            expected_keys = {"candidateId", "claimType", "text", "factIds"} | ({"section"} if report_mode else set())
            if (not isinstance(claim, dict) or set(claim) != expected_keys
                    or not all(isinstance(claim.get(k), str) for k in ("candidateId", "claimType", "text"))
                    or claim["claimType"] not in CLAIM_TYPES
                    or not claim["text"].strip() or len(claim["text"]) > 650
                    or not isinstance(claim["factIds"], list) or not claim["factIds"]
                    or not all(isinstance(ref, str) for ref in claim["factIds"])
                    or len(set(claim["factIds"])) != len(claim["factIds"])):
                return ValidationResult(False, None, ("claim_schema",))
            if report_mode and (not isinstance(claim["section"], str) or claim["section"] not in SECTIONS):
                return ValidationResult(False, None, ("claim_schema",))
        if len({c["candidateId"] for c in claims}) != len(claims):
            return ValidationResult(False, None, ("duplicate_claim_id",))
        plan = snapshot["synthesis"]
        if report_mode and (not plan.get("reportPlan") or any(sum(c["section"] == section for c in claims) > maximum for section, maximum in SECTIONS.items())):
            return ValidationResult(False, None, ("claim_schema",))
        candidates = {c["candidateId"]: c for c in plan["candidates"]}
        facts = {f["factId"]: f for f in snapshot["facts"]}
        evidence = {e["evidenceId"]: e for e in snapshot["evidence"]}
        survivors: list[dict[str, Any]] = []
        diagnostics: list[dict[str, Any]] = []
        for index, claim in enumerate(claims):
            errors: list[str] = []
            warnings: list[str] = []
            candidate = candidates.get(claim["candidateId"])
            refs = claim["factIds"]
            if candidate is None:
                errors.append("candidate_reference")
            else:
                if report_mode and claim["candidateId"] not in plan["reportPlan"]["sections"][claim["section"]]:
                    errors.append("report_section_mismatch")
                if claim["claimType"] != candidate["kind"]:
                    errors.append("claim_type_mismatch")
                # A cited engine relation resolves its immutable dependency
                # closure. Do not force the model to repeat every operand ID.
                if candidate["factIds"][0] not in refs:
                    errors.append("candidate_fact_mismatch")
                if not set(refs) <= facts.keys():
                    errors.append("unknown_fact_id")
                relation = facts.get(candidate["factIds"][0], {})
                if (relation.get("kind") != "insight_relation" or relation.get("value") != candidate["kind"]
                        or relation.get("operandFactIds") != candidate["factIds"][1:]):
                    errors.append("unresolved_relationship")
                allowed_evidence = set(candidate["evidenceIds"])
                grounded_refs = list(dict.fromkeys([*refs, *candidate["factIds"]]))
                for ref in grounded_refs:
                    fact = facts.get(ref)
                    if fact is None:
                        continue
                    if not fact.get("evidenceIds") or not set(fact["evidenceIds"]) <= evidence.keys():
                        errors.append("unresolved_fact_evidence")
                    if ref not in candidate["factIds"] and not set(fact.get("evidenceIds", [])) <= allowed_evidence:
                        errors.append("fact_scope_mismatch")
                    if ref not in candidate["factIds"] and ":" in ref and ref.split(":", 1)[0] not in candidate["metricCodes"]:
                        errors.append("fact_scope_mismatch")
                # Evidence snapshot is scoped by service; validate aggregate
                # contexts as well (exact-cell targets carry no scope fields).
                for eid in allowed_evidence:
                    ev = evidence.get(eid)
                    if not ev:
                        continue
                    for key, expected in (("project", snapshot.get("scope", {}).get("project")),):
                        context = ev.get("target", {}).get("context", {})
                        if expected and key in context and context[key] != expected:
                            errors.append("evidence_scope_mismatch")
                    entity_ref = snapshot.get("scope", {}).get("entityRef")
                    if entity_ref and context.get("entity", {}).get("ref", entity_ref) != entity_ref:
                        errors.append("evidence_scope_mismatch")
                periods = {p["evidenceId"]: p for m in (snapshot.get("metrics") or [snapshot]) for p in m.get("series", [])}
                for anchor in candidate["anchors"]:
                    point = periods.get(anchor["evidenceId"])
                    if not point or point["factId"] != anchor["factId"]:
                        errors.append("unresolved_fact_evidence")
                if not errors:
                    if INJECTION.search(claim["text"]):
                        errors.append("prompt_injection_content")
                    text_errors, warnings = validate_text(claim["text"], candidate, snapshot, grounded_refs)
                    errors.extend(text_errors)
            errors = list(dict.fromkeys(errors))
            diagnostics.append({"index": index, "candidateId": claim["candidateId"],
                                "status": "rejected" if errors else "accepted", "errors": errors, "warnings": warnings})
            if not errors:
                survivors.append(claim)
        all_errors = tuple(dict.fromkeys(code for result in diagnostics for code in result["errors"]))
        if not survivors:
            return ValidationResult(False, None, all_errors, tuple(diagnostics))
        normalized = {"schemaVersion": value["schemaVersion"], "analysisId": snapshot["analysisId"], "status": "ready",
                      "validationPolicy": SEMANTIC_POLICY, "claims": survivors,
                      "summary": {"text": " ".join(c["text"].strip() for c in survivors),
                                  "candidateIds": [c["candidateId"] for c in survivors],
                                  "factIds": list(dict.fromkeys(ref for c in survivors for ref in c["factIds"])),
                                  "claimType": "descriptive"},
                      "insights": [], "limitations": plan["limitations"], "suggestedChecks": []}
        if report_mode:
            report = report_output(plan, survivors)
            normalized["report"] = report
            overview = report["overview"]
            if overview:
                normalized["summary"] = {"text": overview[0]["text"], "factIds": overview[0]["factIds"],
                                         "candidateIds": [overview[0]["candidateId"]], "claimType": "descriptive"}
        return ValidationResult(True, normalized, all_errors, tuple(diagnostics))

    def _validate_overview(self, content: str, snapshot: dict[str, Any]) -> ValidationResult:
        """Closed candidate grammar binds metric, date, unit and mathematical meaning.

        Free-form mathematical paraphrases cannot be proven with numeric membership checks.
        The model may select/connect approved sentences, never invent a relationship.
        """
        try:
            value = _load_json(self._strip_fence(content))
        except (json.JSONDecodeError, TypeError):
            return ValidationResult(False, None, ("invalid_json",))
        errors: list[str] = []
        if not isinstance(value, dict):
            return ValidationResult(False, None, ("root_must_be_object",))
        if set(value) != {"schemaVersion", "analysisId", "status", "summary", "insights", "limitations", "suggestedChecks"}:
            errors.append("unexpected_field")
        if value.get("schemaVersion") != "ai-narrative-v2" or value.get("analysisId") != snapshot["analysisId"] or value.get("status") != "ready":
            errors.append("narrative_identity")
        summary = value.get("summary")
        candidates = {item["candidateId"]: item for item in snapshot["insightCandidates"]}
        if not isinstance(summary, dict):
            return ValidationResult(False, None, ("summary",))
        refs = summary.get("candidateIds")
        if not isinstance(refs, list) or not 1 <= len(refs) <= 2 or not all(isinstance(ref, str) and ref in candidates for ref in refs):
            return ValidationResult(False, None, ("candidate_reference",))
        if len(set(refs)) != len(refs) or refs[0] != snapshot["insightCandidates"][0]["candidateId"]:
            errors.append("candidate_priority")
        if "whole-window" in candidates and refs != ["whole-window"]:
            errors.append("whole_series_priority")
        selected = [candidates[ref] for ref in refs]
        if summary.get("text") != " ".join(item["text"] for item in selected):
            errors.append("candidate_text_mismatch")
        if set(summary) != {"text", "candidateIds", "factIds", "claimType"} or summary.get("claimType") != "descriptive":
            errors.append("claim_schema")
        expected = {ref for item in selected for ref in item["factIds"]}
        fact_refs = summary.get("factIds")
        if not isinstance(fact_refs, list) or not all(isinstance(ref, str) for ref in fact_refs) or set(fact_refs) != expected:
            errors.append("candidate_fact_mismatch")
        facts = {item["factId"]: item for item in snapshot["facts"]}
        evidence = {item["evidenceId"] for item in snapshot["evidence"]}
        if not expected.issubset(facts) or any(not set(facts[ref]["evidenceIds"]).issubset(evidence) for ref in expected if ref in facts):
            errors.append("unresolved_fact_evidence")
        if any(value.get(key) != [] for key in ("insights", "limitations", "suggestedChecks")):
            errors.append("backend_owned_sections")
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
        series = list(snapshot.get("series", []))
        for metric in snapshot.get("metrics", []):
            series.extend(metric.get("series", []))
        for point in series:
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
        allowed.extend(
            float(value)
            for item in facts
            for value in item.get("supportingValues", [])
            if isinstance(value, (int, float))
        )
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
