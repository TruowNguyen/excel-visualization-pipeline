from copy import deepcopy
import json
import re

import pytest

from excel_visualization_pipeline.ai import OutputValidator
from excel_visualization_pipeline.ai.synthesis import build_synthesis, provider_plan, synthesis_fallback
from test_ai_overview import overview


def snapshot(errors, totals=None, **kwargs):
    value = overview(totals or [100] * len(errors), errors, **kwargs)
    value["window"] = {"start": value["metrics"][0]["series"][0]["periodStart"] if value["metrics"][0]["series"] else "2026-09-01", "end": f"2026-09-{len(errors):02}", "groupBy": kwargs.get("group_by", "day")}
    value["synthesis"] = build_synthesis(value)
    value["facts"].extend(value["synthesis"]["facts"])
    return value


@pytest.mark.parametrize('errors,totals', [([20, 15], [100, 200]), ([20, 20], [100, 200]), ([20, 30], [200, 100]), ([20, 30], [100, 200])])
def test_two_metric_relation_keeps_independent_facts_and_rejects_wrong_direction(errors, totals):
    value = snapshot(errors, totals)
    value['metrics'] = [m for m in value['metrics'] if m['metricCode'] != 'error_rate']
    value['facts'] = [f for m in value['metrics'] for f in m['facts']]
    value['synthesis'] = build_synthesis(value)
    value['facts'].extend(value['synthesis']['facts'])
    pair = next(c for c in value['synthesis']['candidates'] if c['kind'] == 'metric_pair_movement')
    assert pair['metricCodes'] == ['total', 'error']
    assert all(row['metricCode'] != 'error_rate' for row in pair['quantitativeEvidence'])
    body = {'schemaVersion': 'ai-narrative-v4', 'analysisId': value['analysisId'], 'status': 'ready',
            'claims': [{'candidateId': pair['candidateId'], 'claimType': pair['kind'], 'text': pair['fallbackText'], 'factIds': pair['factIds']}]}
    checked = OutputValidator().validate(json.dumps(body, ensure_ascii=False), value)
    assert checked.valid, checked.errors
    if errors[0] == errors[1]:
        body['claims'][0]['text'] = 'Tổng số tăng. Số lỗi giữ nguyên ở mức 20. Lượng ghi nhận tăng nhưng lỗi không tăng cùng.'
        checked = OutputValidator().validate(json.dumps(body, ensure_ascii=False), value)
        assert checked.valid, checked.errors
    body['claims'][0]['text'] = 'Tổng số giảm. Số lỗi giảm.'
    assert not OutputValidator().validate(json.dumps(body, ensure_ascii=False), value).valid


def test_two_metric_relation_never_bridges_missing_period():
    value = snapshot([20, 25, 30], [100, 200, 300])
    value['metrics'] = [m for m in value['metrics'] if m['metricCode'] != 'error_rate']
    for m in value['metrics']:
        m['series'] = [m['series'][0], m['series'][2]]
        m['periodAnalytics']['temporalStructure']['stages'] = []
    value['facts'] = [f for m in value['metrics'] for f in m['facts']]
    assert not any(c['kind'] == 'metric_pair_movement' for c in build_synthesis(value)['candidates'])


def model_value(value):
    plan = value["synthesis"]
    return {"schemaVersion": "ai-narrative-v3", "analysisId": value["analysisId"], "status": "ready",
            "claims": [{"candidateId": cid, "text": c["fallbackText"], "factIds": c["factIds"]}
                       for cid in plan["selectedCandidateIds"] for c in plan["candidates"] if c["candidateId"] == cid]}


@pytest.mark.parametrize("values,kind", [([8, 12], "period_comparison"), ([12, 8], "period_comparison"), ([8, 8], "period_comparison"), ([8, 12, 10], "short_sequence")])
def test_short_windows_cannot_claim_trend_or_extrema(values, kind):
    value = snapshot(values)
    selected = [c for c in value["synthesis"]["candidates"] if c["candidateId"] in value["synthesis"]["selectedCandidateIds"]]
    assert selected[0]["kind"] == kind
    assert all(c["kind"] != "peak_offset" for c in selected)
    text = synthesis_fallback(value["synthesis"])["summary"]["text"]
    assert "chưa" in text and "xu hướng" in text
    assert not any(word in text for word in ("qua các kỳ", "đỉnh", "đáy", "cao nhất", "thấp nhất"))
    assert OutputValidator().validate(json.dumps(model_value(value)), value).valid
    bad = model_value(value)
    bad["claims"][0]["text"] = "Báo sai/Lỗi: chỉ số đi lên qua các kỳ, không có nhịp giảm."
    assert not OutputValidator().validate(json.dumps(bad), value).valid


@pytest.mark.parametrize("errors,totals,kind", [
    ([20, 15], [100, 200], "errors_down_volume_up"),
    ([20, 15], [200, 100], "errors_down_share_up"),
    ([10, 30], [100, 200], "errors_outpace_volume"),
    ([30, 10], [200, 100], "errors_fall_faster"),
    ([10, 20], [200, 100], "errors_up_volume_down"),
    ([10, 10], [100, 200], "unchanged_errors_share_down"),
    ([10, 10], [200, 100], "unchanged_errors_share_up"),
    ([10, 20], [100, 200], "volume_up_same_share"),
    ([20, 10], [200, 100], "volume_down_same_share"),
])
def test_joint_kpi_relationships_are_grounded_not_statistical(errors, totals, kind):
    value = snapshot(errors, totals)
    plan = value["synthesis"]
    assert "correlations" not in plan and "minimumCorrelationPeriods" not in plan
    candidate = next(c for c in plan["candidates"] if c["kind"] == kind)
    assert candidate["metricCodes"] == ["total", "error", "error_rate"]
    assert candidate["relationshipDescription"]["comparisonContext"] == "giữa hai kỳ"
    assert len(candidate["anchors"]) == 6
    assert OutputValidator().validate(json.dumps(model_value(value)), value).valid
    payload = provider_plan(value)
    assert not any(f["kind"] == "pearson_change_correlation" for f in payload["facts"])
    assert all(c["kind"] != "joint_correlation" for c in plan["candidates"])
    output = model_value(value)
    output["claims"][0]["text"] += " Chất lượng đã cải thiện."
    assert not OutputValidator().validate(json.dumps(output), value).valid


def test_joint_phase_does_not_join_missing_periods():
    value = snapshot([20, 15, None, 12, 10], [100, 200, None, 300, 400])
    candidates = [c for c in value["synthesis"]["candidates"] if c.get("relationshipDescription")]
    assert candidates
    assert all(c["scope"] == "contiguous_block" for c in candidates)
    assert all(len(c["anchors"]) == 6 for c in candidates)


def test_short_contiguous_suffix_does_not_earn_trend_language_from_full_count():
    value = snapshot([4, 8, None, 10, 12])
    selected = [c for c in value["synthesis"]["candidates"] if c["candidateId"] in value["synthesis"]["selectedCandidateIds"]]
    assert selected[0]["kind"] == "period_comparison" and selected[0]["scope"] == "contiguous_block"


@pytest.mark.parametrize("values,kind", [
    ([16, 8, 10, 8, 19, 43, 32, 22, 22], "peak_retreat"),
    ([20, 12, 8, 15, 25], "trough_recovery"),
    ([20, 12, 8, 15, 20], "endpoint_masks"),
    ([8, 12, 16, 20], "sustained_increase"),
    ([20, 16, 12, 8], "sustained_decrease"),
    ([10, 11, 10, 11], "descriptive_only"),
    ([22, 22, 22, 22], "unchanged"),
])
def test_golden_structural_synthesis_and_grounding(values, kind):
    value = snapshot(values)
    plan = value["synthesis"]
    primary = next(c for c in plan["candidates"] if c["candidateId"] == plan["selectedCandidateIds"][0])
    assert primary["kind"] == kind
    assert primary["metricCodes"] == ["error"] or kind in {"sustained_increase", "sustained_decrease"}
    result = OutputValidator().validate(json.dumps(model_value(value)), value)
    assert result.valid, result.errors
    text = result.value["summary"]["text"]
    assert not re.search(r"\d", text)
    assert len(text) < 650
    assert all(word not in text for word in ("mạnh", "nhẹ", "đáng kể", "chất lượng", "camera"))
    assert len(result.value["summary"]["candidateIds"]) <= 2
    ids = {f["factId"] for f in value["facts"]}
    for candidate in plan["candidates"]:
        assert set(candidate["factIds"]) <= ids
        assert all(a["factId"] in ids and a["evidenceId"] in candidate["evidenceIds"] for a in candidate["anchors"])


def test_noncanonical_synthesis_is_accepted_without_relaxing_relation():
    value = snapshot([16, 8, 10, 8, 19, 43, 32, 22, 22])
    output = model_value(value)
    output["claims"][0]["text"] = "Báo sai/Lỗi: đà tăng tới đỉnh đã đảo chiều; chỉ số giảm sau khi đạt đỉnh; cuối chuỗi đi ngang."
    assert output["claims"][0]["text"] != value["synthesis"]["candidates"][0]["fallbackText"]
    assert OutputValidator().validate(json.dumps(output), value).valid


@pytest.mark.parametrize("text", [
    "Báo sai/Lỗi: chỉ số tăng từ 16 lên 22.",
    "Tổng số: nhịp tăng lên đỉnh không được duy trì; sau đỉnh chỉ số giảm qua các kỳ; các kỳ cuối giữ nguyên.",
    "Báo sai/Lỗi: nhịp tăng lên đỉnh được duy trì; sau đỉnh chỉ số tăng qua các kỳ.",
    "Báo sai/Lỗi: nhịp tăng lên đỉnh không được duy trì; trước đỉnh chỉ số giảm qua các kỳ; các kỳ cuối giữ nguyên.",
    "Báo sai/Lỗi: nhịp tăng lên đỉnh không được duy trì; sau đỉnh chỉ số giảm qua các kỳ; các kỳ cuối giữ nguyên. Chất lượng đã cải thiện.",
    "Báo sai/Lỗi: tăng mạnh do camera hỏng ngày 13/09/2026.",
    "Báo sai/Lỗi: giảm 24 phần trăm.",
    "Báo sai/Lỗi: sẽ tiếp tục giảm.",
    "Báo sai/Lỗi: tăng giảm nhẹ giữa các kỳ.",
])
def test_rejects_unsupported_number_metric_direction_period_cause_unit_forecast(text):
    value = snapshot([16, 8, 10, 8, 19, 43, 32, 22, 22])
    output = model_value(value)
    output["claims"][0]["text"] = text
    assert not OutputValidator().validate(json.dumps(output), value).valid


def test_missing_period_does_not_join_reversal_or_cross_metric_alignment():
    value = snapshot([16, 43, None, 32, 22], [100, 200, None, 400, 500])
    plan = value["synthesis"]
    assert not any(c["kind"] == "peak_retreat" for c in plan["candidates"])
    assert not any(c["kind"] == "peak_offset" for c in plan["candidates"])
    assert len(plan["limitations"]) == 1
    assert "1/5 kỳ thiếu" in plan["limitations"][0]
    for c in plan["candidates"]:
        if c.get("section") in {"overview", "extrema"}:
            assert c["scope"] == "selected_window" and c.get("hasGaps")
        else:
            assert c["scope"] == "contiguous_block"
    assert OutputValidator().validate(json.dumps(model_value(value)), value).valid
    bad = model_value(value)
    bad["claims"][0]["text"] = bad["claims"][0]["text"].replace("Trong đoạn có dữ liệu liền nhau, ", "")
    assert not OutputValidator().validate(json.dumps(bad), value).valid


def test_absolute_count_increase_rate_decrease_requires_complete_paired_phase():
    value = snapshot([10, 15, 20], [100, 200, 400])
    plan = value["synthesis"]
    relation = next(c for c in plan["candidates"] if c["kind"] == "count_rate_contrast")
    assert relation["candidateId"] in plan["selectedCandidateIds"]
    assert len(relation["anchors"]) == 6
    assert OutputValidator().validate(json.dumps(model_value(value)), value).valid
    partial = snapshot([10] * 9, [100] * 9, group_by="week")
    assert not any(c["kind"] == "count_rate_contrast" for c in partial["synthesis"]["candidates"])


def test_peak_timing_relationship_and_investigation_are_aligned():
    value = snapshot([8, 43, 32, 22], [100, 200, 657, 420])
    plan = value["synthesis"]
    cross = next(c for c in plan["candidates"] if c["kind"] == "peak_offset")
    assert [(a["metricCode"], a["periodLabel"]) for a in cross["anchors"]] == [("total", "03/09/2026"), ("error", "02/09/2026")]
    assert cross["candidateId"] not in plan["selectedCandidateIds"]
    selected_cross = next(c for c in plan["candidates"] if c["candidateId"] == plan["selectedCandidateIds"][-1])
    assert selected_cross.get("relationshipDescription")
    assert any(c["candidateId"] == selected_cross["candidateId"] for c in plan["inspectionChecks"])
    # Peak timing remains available to v4 providers; it is not the default
    # takeaway when a linked count/volume/rate explanation exists.
    output = {"schemaVersion": "ai-narrative-v4", "analysisId": value["analysisId"], "status": "ready", "claims": [
        {"candidateId": cross["candidateId"], "claimType": cross["kind"], "text": cross["fallbackText"], "factIds": cross["factIds"]}]}
    assert OutputValidator().validate(json.dumps(output), value).valid
    output["claims"][-1]["text"] = output["claims"][-1]["text"].replace("muộn hơn", "sớm hơn")
    assert not OutputValidator().validate(json.dumps(output), value).valid


def test_insufficient_data_abstains_and_empty_fallback_is_honest():
    value = snapshot([8])
    assert not value["synthesis"]["selectedCandidateIds"]
    assert "Chưa đủ" in synthesis_fallback(value["synthesis"])["summary"]["text"]


def test_peak_ties_do_not_invent_later_peak_for_constant_series():
    value = snapshot([8, 43, 32, 22])
    assert not any(c["kind"] == "peak_offset" for c in value["synthesis"]["candidates"])


def test_schema_citations_evidence_and_predicate_cannot_be_swapped():
    value = snapshot([8, 43, 32, 22])
    for mutation in ("missing_ref", "unknown_id", "wrong_schema", "wrong_analysis", "missing_source", "wrong_relation"):
        changed = deepcopy(value)
        output = model_value(changed)
        if mutation == "missing_ref": output["claims"][0]["factIds"] = output["claims"][0]["factIds"][:-1]
        if mutation == "unknown_id": output["claims"][0]["candidateId"] = "made-up"
        if mutation == "wrong_schema": output["schemaVersion"] = "ai-narrative-v1"
        if mutation == "wrong_analysis": output["analysisId"] = "other"
        if mutation == "missing_source": changed["evidence"] = []
        if mutation == "wrong_relation": next(f for f in changed["facts"] if f["factId"] == output["claims"][0]["factIds"][0])["value"] = "unsupported"
        assert not OutputValidator().validate(json.dumps(output), changed).valid, mutation


def test_provider_payload_excludes_paragraphs_patterns_and_core_provenance():
    value = snapshot([8, 43, 32, 22])
    payload = provider_plan(value)
    serialized = json.dumps(payload)
    assert not any(key in serialized for key in ("fallbackText", "expressions", "temporal_narrative", "raw_value", "observationRef", "lineageRef", "comparisonBasis"))
    assert len(payload["selectedCandidateIds"]) <= 2
