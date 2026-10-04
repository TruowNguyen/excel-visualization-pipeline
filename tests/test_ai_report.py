from copy import deepcopy
import json

import pytest

from excel_visualization_pipeline.ai import OutputValidator
from excel_visualization_pipeline.ai.synthesis import provider_plan, synthesis_fallback
from test_ai_synthesis import snapshot


def current():
    return snapshot([16, 8, 10, 8, None, 19, 43, 32, 22, 22], [71, 454, 342, 251, None, 515, 214, 209, 657, 420],
                    dates=[f"2026-09-{day:02d}" for day in range(7, 17)])


def narrative(value):
    plan = value["synthesis"]
    candidates = {c["candidateId"]: c for c in plan["candidates"]}
    claims = []
    for section, ids in plan["reportPlan"]["sections"].items():
        for cid in ids:
            c = candidates[cid]
            text = c["fallbackText"]
            if section == "phases":
                text = f"Từ {c['startLabel']} đến {c['endLabel']}, " + text
            claims.append({"section": section, "candidateId": cid, "claimType": c["kind"], "text": text, "factIds": c["factIds"][:1]})
    return {"schemaVersion": "ai-narrative-v5", "analysisId": value["analysisId"], "status": "ready", "claims": claims}


def validate(value, body):
    return OutputValidator().validate(json.dumps(body, ensure_ascii=False), value)


def test_report_covers_both_blocks_extrema_and_joint_kpis():
    value = current()
    payload = provider_plan(value)
    assert payload["schemaVersion"] == "ai-insight-provider-input-v5"
    sections = payload["reportPlan"]["sections"]
    assert len(sections["phases"]) == 4
    assert "extrema" not in sections
    assert len(sections["relationships"]) > 1
    encoded = json.dumps(payload)
    assert "target" not in encoded and "fallbackText" not in encoded and "expressions" not in encoded
    result = validate(value, narrative(value))
    assert result.valid, result.errors
    assert not result.errors, result.claim_results
    report = result.value["report"]
    assert all(item["source"] == "ai" for section in ("overview", "phases", "relationships") for item in report[section])
    assert report["phases"][0]["start"] == "2026-09-07"
    assert report["phases"][-1]["end"] == "2026-09-16"
    highlights = [e for c in payload["insightCandidates"] for e in c["semanticSpec"].get("phaseExtrema", []) if e["metricCode"] == "error"]
    assert next(e for e in highlights if e["role"] == "lowest")["dates"] == ["2026-09-08", "2026-09-10"]
    assert next(e for e in highlights if e["role"] == "peak")["value"] == 43


@pytest.mark.parametrize("errors", [[22, 22], [16, 8, 10], [22, 22, 22, 22]])
def test_short_or_constant_metrics_do_not_get_meaningless_extrema(errors):
    value = snapshot(errors, [100] * len(errors))
    highlights = [e for c in value["synthesis"]["candidates"] for e in c.get("phaseExtrema", [])]
    if len(errors) < 4:
        assert not highlights
    assert not any(e["metricCode"] == "total" for e in highlights)


def test_rejected_or_missing_paragraph_keeps_engine_coverage_with_source_label():
    value = current()
    body = narrative(value)
    body["claims"][-1]["text"] = "Tỷ lệ báo sai cao nhất 999%."
    body["claims"] = [c for c in body["claims"] if c["candidateId"] != "report-phases-00"]
    result = validate(value, body)
    assert result.valid and "unsupported_numeric_mention" in result.errors
    report = result.value["report"]
    assert report["phases"][0]["source"] == "deterministic"
    assert len(report["phases"]) == 4
    assert "thấp nhất 8" in synthesis_fallback(value["synthesis"])["report"]["phases"][0]["text"]


@pytest.mark.parametrize("section", ["wrong", [], 42])
def test_invalid_section_is_structural_error(section):
    value = current()
    body = narrative(value)
    body["claims"][0]["section"] = section
    result = validate(value, body)
    assert not result.valid and "claim_schema" in result.errors


def test_correct_fact_cannot_be_rendered_in_wrong_section():
    value = current()
    body = narrative(value)
    body["claims"][0]["section"] = "phases"
    result = validate(value, body)
    assert result.valid and "report_section_mismatch" in result.errors
    assert result.value["report"]["overview"][0]["source"] == "deterministic"


def test_wrong_peak_value_or_date_is_still_rejected():
    value = current()
    base = narrative(value)
    for text in ("Báo sai/Lỗi cao nhất 22. Báo sai/Lỗi thấp nhất 8.",
                 "Báo sai/Lỗi cao nhất 43 vào 15/09/2026. Báo sai/Lỗi thấp nhất 8."):
        body = deepcopy(base)
        claim = next(c for c in body["claims"] if c["candidateId"] == "report-phases-01")
        claim["text"] = "Từ 12/09/2026 đến 13/09/2026, " + text
        result = validate(value, body)
        assert result.valid and set(result.errors) & {"numeric_role_mismatch", "numeric_period_mismatch"}
        assert result.value["report"]["phases"][1]["source"] == "deterministic"


def test_second_tied_trough_date_must_actually_have_the_minimum():
    value = current()
    body = narrative(value)
    claim = next(c for c in body["claims"] if c["candidateId"] == "report-phases-00")
    claim["text"] = "Từ 07/09/2026 đến 10/09/2026, số lỗi thấp nhất 8 vào 08/09/2026 và 09/09/2026."
    result = validate(value, body)
    assert result.valid and "numeric_period_mismatch" in result.errors
    assert result.value["report"]["phases"][0]["source"] == "deterministic"


def test_intermediate_movement_values_do_not_inherit_previous_peak_date():
    value = current()
    body = narrative(value)
    early = next(c for c in body["claims"] if c["candidateId"] == "report-phases-00")
    early["text"] = "Từ 07/09 đến 10/09, số lỗi giảm từ 16 xuống 8 rồi tăng lên 10 và về lại 8 vào 10/09."
    decline = next(c for c in body["claims"] if c["candidateId"] == "report-phases-02")
    decline["text"] = "Từ 13/09 đến 15/09, số lỗi giảm từ mức cao nhất 43 vào 13/09 xuống 32 rồi về 22."
    result = validate(value, body)
    assert result.valid and not result.errors, result.claim_results
    assert result.value["report"]["phases"][0]["source"] == "ai"
    assert result.value["report"]["phases"][2]["source"] == "ai"
