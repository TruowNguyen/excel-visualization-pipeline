from datetime import date
from copy import deepcopy
import json

import pandas as pd
import pytest

from excel_visualization_pipeline.ai import AnalyticsEngine, AIApplicationService, OutputValidator
from excel_visualization_pipeline.ai.overview import build_overview, overview_fallback


def overview(totals, errors, *, group_by="day", dates=None):
    dates = dates or [f"2026-09-{index + 1:02}" for index in range(len(totals))]
    rows = []
    for day, total, error in zip(dates, totals, errors):
        for code, label, value in (("total", "Tổng số", total), ("error", "Báo sai/Lỗi", error)):
            rows.append({"entity_id": "entity", "date": day, "metric_code": code,
                         "metric_normalized": label, "chart_value": value,
                         "value_kind": "source_marker" if value is None else "numeric", "effective_unit": "lượt"})
    data = pd.DataFrame(rows)
    computations, metrics = {}, []
    for code in ("total", "error", "error_rate"):
        c = AnalyticsEngine().trend(data, entity_ref="entity", metric_code=code,
                                   start=date.fromisoformat(dates[0]), end=date.fromisoformat(dates[-1]), group_by=group_by)
        computations[code] = c
        metrics.append(AIApplicationService._prefix_analysis_ids({
            "metricCode": code, "metricDisplayName": c.metric_display_name,
            "series": list(c.series), "facts": list(c.facts), "quality": c.quality,
            "periodAnalytics": c.period_analytics,
        }, code))
    result = build_overview(computations, metrics)
    result["facts"] = [f for m in metrics for f in m["facts"]] + result["facts"]
    result["evidence"] = [{"evidenceId": e} for e in sorted({e for f in result["facts"] for e in f["evidenceIds"]})]
    result.update(schemaVersion="ai-overview-v2", analysisId="test-overview")
    result["metrics"] = metrics
    return result


def test_whole_window_example_explains_all_stages_not_endpoint_delta():
    values = [16, 8, 10, 8, 19, 43, 32, 22, 22]
    result = overview([100] * len(values), values)
    metric = result["metrics"][1]
    structure = metric["periodAnalytics"]["temporalStructure"]
    assert [(s["startIndex"], s["endIndex"], s["direction"]) for s in structure["stages"]] == [
        (0, 1, "decreasing"), (1, 2, "increasing"), (2, 3, "decreasing"),
        (3, 5, "increasing"), (5, 7, "decreasing"), (7, 8, "unchanged")]
    assert "đạt mức cao nhất" in structure["stages"][3]["text"]
    assert "giảm liên tiếp từ 43 xuống 22" in structure["stages"][4]["text"]
    assert "giữ nguyên ở 22" in structure["stages"][-1]["text"]
    assert [t["periodLabel"] for t in structure["turningPoints"]] == ["02/09/2026", "03/09/2026", "04/09/2026", "06/09/2026"]
    assert not structure["gaps"]
    assert result["insightCandidates"][0]["candidateId"] == "whole-window"
    assert "tăng giảm qua nhiều giai đoạn" in result["insightCandidates"][0]["text"]
    assert "16" not in result["insightCandidates"][0]["text"]
    ids = {f["factId"] for f in metric["facts"]}
    evidence = {e["evidenceIds"][0] for e in metric["facts"] if e["kind"] == "period_value"}
    for block in [structure, *structure["stages"], *structure["turningPoints"]]:
        assert set(block["factIds"]) <= ids
        assert set(block["evidenceIds"]) <= evidence


@pytest.mark.parametrize("values,directions", [
    ([8, 8, 19, 43], ["unchanged", "increasing"]),
    ([43, 19, 19, 8], ["decreasing", "unchanged", "decreasing"]),
    ([22, 22, 22], ["unchanged"]),
    ([16, 8, 43, 16], ["decreasing", "increasing", "decreasing"]),
])
def test_temporal_stages_cover_every_adjacent_transition(values, directions):
    result = overview([100] * len(values), values)
    structure = result["metrics"][1]["periodAnalytics"]["temporalStructure"]
    assert [s["direction"] for s in structure["stages"]] == directions
    assert sum(s["transitionCount"] for s in structure["stages"]) == len(values) - 1


def test_missing_period_breaks_runs_and_preserves_gap_position():
    result = overview([100] * 5, [8, 19, None, 32, 43])
    analytics = result["metrics"][1]["periodAnalytics"]
    structure = analytics["temporalStructure"]
    assert [(s["startIndex"], s["endIndex"]) for s in structure["stages"]] == [(0, 1), (2, 3)]
    assert structure["gaps"][0]["startIndex"] == 1
    assert not structure["turningPoints"]
    assert analytics["consecutiveIncrease"] is None
    assert "kỳ thiếu" in structure["summaryText"]


def test_missing_period_does_not_join_plateaus():
    result = overview([100] * 5, [22, 22, None, 22, 22])
    analytics = result["metrics"][1]["periodAnalytics"]
    assert analytics["endingPlateau"]["transitionCount"] == 1


def test_missing_boundary_period_does_not_claim_full_window_coverage():
    result = overview([100] * 3, [None, 8, 19])
    structure = result["metrics"][1]["periodAnalytics"]["temporalStructure"]
    assert "kỳ thiếu" in structure["overviewText"]
    assert not structure["gaps"]


def test_single_metric_rejects_endpoint_story_even_when_numbers_are_grounded():
    metric = overview([100] * 3, [16, 43, 22])["metrics"][1]
    structure = metric["periodAnalytics"]["temporalStructure"]
    snapshot = {**metric, "schemaVersion": "ai-trend-v3", "analysisId": "single",
                "window": {"start": "2026-09-01", "end": "2026-09-03"},
                "evidence": [{"evidenceId": e} for e in structure["evidenceIds"]]}
    value = {"schemaVersion": "ai-narrative-v1", "analysisId": "single", "status": "ready",
             "summary": {"text": structure["summaryText"], "factIds": structure["summaryFactIds"], "claimType": "descriptive"},
             "insights": [], "limitations": [], "suggestedChecks": []}
    validator = OutputValidator()
    assert validator.validate(json.dumps(value), snapshot).valid
    value["summary"].update(text="Chỉ số tăng từ 16 lên 22.", factIds=["error:fact-previous", "error:fact-current", "error:fact-direction"])
    assert "whole_series_priority" in validator.validate(json.dumps(value), snapshot).errors


def test_complex_series_retains_all_stages_with_bounded_summary():
    values = [8 if i % 2 else 22 for i in range(60)]
    result = overview([100] * 60, values, dates=[(date(2026, 7, 1) + pd.Timedelta(days=i)).isoformat() for i in range(60)])
    structure = result["metrics"][1]["periodAnalytics"]["temporalStructure"]
    assert len(structure["stages"]) == 59
    assert "đầy đủ bên dưới" in structure["summaryText"]
    assert len(structure["summaryFactIds"]) == 1
    assert len(result["insightCandidates"][0]["factIds"]) == 3


def test_endpoint_candidate_cannot_be_appended_to_executive_summary():
    snapshot = overview([100, 100, 100], [16, 43, 22])
    value = overview_fallback(snapshot["insightCandidates"], [])
    value.pop("mode")
    value.update(analysisId=snapshot["analysisId"], status="ready")
    relationship = next(c for c in snapshot["insightCandidates"] if c["layer"] == "relational")
    value["summary"]["candidateIds"].append(relationship["candidateId"])
    value["summary"]["text"] += " " + relationship["text"]
    value["summary"]["factIds"] = list(dict.fromkeys([*value["summary"]["factIds"], *relationship["factIds"]]))
    assert "whole_series_priority" in OutputValidator().validate(json.dumps(value), snapshot).errors


@pytest.mark.parametrize("totals,errors,expected,wording", [
    ([100, 200], [10, 15], "error_share_decreased", "Tổng số tăng nhanh hơn"),
    ([100, 60], [10, 8], "error_share_increased", "Tổng số giảm nhanh hơn"),
    ([100, 200], [10, 20], "error_share_unchanged", "cùng mức thay đổi tương đối"),
    ([100, 90], [10, 15], "error_share_increased", "khác chiều"),
    ([100, 200], [0, 10], "error_share_increased", "Tỷ trọng"),
])
def test_aligned_relationships(totals, errors, expected, wording):
    result = overview(totals, errors)
    assert result["comparisonBasis"]["status"] == "comparable"
    fact = next(f for f in result["facts"] if f["kind"] == "numerator_denominator_relationship")
    assert fact["value"] == expected
    assert result["insightCandidates"][0]["candidateId"] == "whole-window"
    relationship = next(c for c in result["insightCandidates"] if c["layer"] == "relational")
    assert wording.lower() in relationship["text"].lower()
    assert result["inspectionChecks"][0]["evidenceIds"]
    for item in result["facts"]:
        assert item["factId"] not in item.get("operandFactIds", [])


@pytest.mark.parametrize("totals,errors", [([100, None, 200], [10, 20, 30]), ([0, 100], [0, 10]), ([100, 200], [None, 10])])
def test_zero_exposure_and_misaligned_endpoints_do_not_claim_growth(totals, errors):
    result = overview(totals, errors)
    if result["comparisonBasis"]["status"] == "comparable":
        # Missing interior days do not make complete daily endpoints invalid;
        # the relationship is explicitly endpoint-only, never a whole-series claim.
        assert "Từ" in next(c for c in result["insightCandidates"] if c["layer"] == "relational")["text"]
        assert result["limitations"]
    else:
        assert not any(c["layer"] == "relational" for c in result["insightCandidates"])
        assert result["limitations"]


def test_partial_week_blocks_growth_and_retains_description():
    result = overview([100] * 9, [10] * 9, group_by="week")
    assert result["comparisonBasis"]["status"] == "limited"
    assert not any(c["layer"] == "relational" for c in result["insightCandidates"])


def test_full_week_with_excluded_pairs_does_not_link_independent_counts():
    dates = [f"2026-09-{day:02}" for day in range(7, 21)]
    errors = [10] * 14
    errors[2] = None
    result = overview([100] * 14, errors, group_by="week", dates=dates)
    assert result["comparisonBasis"]["status"] == "limited"
    assert result["comparisonBasis"]["baseline"]["denominator"] == 600
    assert result["comparisonBasis"]["baseline"]["eligibleDayCount"] == 6
    assert not any(c["layer"] == "relational" for c in result["insightCandidates"])
    assert result["inspectionChecks"][0]["checkId"] == "check-coverage"


def test_zero_numerator_has_rate_fact_but_no_relative_growth_fact():
    result = overview([100, 200], [0, 10])
    assert any(f["kind"] == "numerator_denominator_relationship" for f in result["facts"])
    assert not any(f["kind"] == "metric_growth_relationship" for f in result["facts"])
    assert result == overview([100, 200], [0, 10])


def test_temporal_fact_and_fallback_have_grounding():
    result = overview([100, 100, 100], [10, 50, 5])
    temporal = next(c for c in result["insightCandidates"] if c["layer"] == "temporal")
    assert "50% → 5%" in temporal["text"]
    assert "45 điểm phần trăm" in temporal["text"]
    assert temporal["evidenceIds"] and temporal["factIds"]
    fallback = overview_fallback(result["insightCandidates"], result["limitations"])
    assert fallback["summary"]["text"] == result["insightCandidates"][0]["text"]


def test_v2_rejects_wrong_metric_date_cause_and_suggested_action():
    snapshot = overview([100, 200], [10, 15])
    value = overview_fallback(snapshot["insightCandidates"], [])
    value.pop("mode")
    value.update(analysisId=snapshot["analysisId"], status="ready")
    validator = OutputValidator()
    assert validator.validate(json.dumps(value), snapshot).valid
    for replacement in ("camera đã được tối ưu", "01/01/2020", "% báo sai tăng", "Chất lượng đã cải thiện"):
        broken = deepcopy(value)
        broken["summary"]["text"] = replacement
        assert not validator.validate(json.dumps(broken), snapshot).valid
    broken = deepcopy(value)
    broken["suggestedChecks"] = ["Sửa camera"]
    assert not validator.validate(json.dumps(broken), snapshot).valid


def test_limited_comparison_uses_exact_description_citations_without_repair():
    snapshot = overview([100] * 9, [10] * 9, group_by="week")
    value = overview_fallback(snapshot["insightCandidates"], [])
    value.pop("mode")
    value.update(analysisId=snapshot["analysisId"], status="ready")
    content = json.dumps(value)
    validator = OutputValidator()
    assert validator.normalize_fact_references(content, snapshot) == content
    assert validator.validate(content, snapshot).valid
