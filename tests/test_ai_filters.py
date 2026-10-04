"""Different data and dates: daily, weekly, monthly, metric selectors and clipping."""
from datetime import date, timedelta
import json

import pandas as pd
import pytest

from scripts.evaluate_ai_filter_matrix import snapshot, audit
from test_ai_report import narrative
from excel_visualization_pipeline.ai import OutputValidator
from excel_visualization_pipeline.ai import AnalyticsEngine
from excel_visualization_pipeline.ai.evidence import EvidenceBuilder
from excel_visualization_pipeline.ai.synthesis import provider_plan, synthesis_fallback
from excel_visualization_pipeline.ai.semantic import validate_text
from test_ai_report import current


def data(dates, errors):
    return pd.DataFrame([{"entity_id": "example", "date": day, "metric_code": code, "metric_normalized": {"total": "Tổng số", "error": "Báo sai/Lỗi"}[code],
                          "chart_value": value, "value_kind": "numeric", "effective_unit": "lượt"}
                         for day, error in zip(dates, errors) for code, value in (("total", 100 + error * 2), ("error", error))])


@pytest.mark.parametrize("group,dates,end", [
    ("day", ["2025-12-29", "2025-12-30", "2025-12-31", "2026-01-01", "2026-01-02", "2026-01-03"], "2026-01-03"),
    ("week", ["2025-12-30", "2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26", "2026-02-02"], "2026-02-08"),
    ("month", ["2025-11-01", "2025-12-01", "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"], "2026-04-30"),
])
@pytest.mark.parametrize("metric", ["all", "total", "error", "error_rate"])
def test_all_groupings_and_selectors_cover_window_extrema_and_validate_labels(group, dates, end, metric):
    value, metrics = snapshot(data(dates, [8, 16, 4, 20, 12, 12]), "example", "sample", date.fromisoformat(dates[0]), date.fromisoformat(end), group, metric)
    result = audit(value, metrics)
    assert not result["errors"], result
    payload = narrative(value)
    # Engine period labels, including month/year and clipped cross-year weeks,
    # must work in prose, not just ISO daily endpoints.
    validated = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert validated.valid and not validated.errors, validated.claim_results
    report = validated.value["report"]
    assert report["phases"][0]["start"] == dates[0]
    assert report["phases"][-1]["end"] == end
    if metric != "all":
        assert not report["relationships"]
        assert all(c["metricCodes"] == [metric] for c in value["synthesis"]["candidates"])


def test_long_window_keeps_end_and_all_extrema_instead_of_first_eight_phases():
    dates = [(date(2026, 3, 1) + timedelta(days=i)).isoformat() for i in range(48)]
    errors = [12, 14, 16, 15, 14, 11, 8, 9] * 6
    errors[-5], errors[-2] = 50, 2
    value, metrics = snapshot(data(dates, errors), "example", "sample", date.fromisoformat(dates[0]), date.fromisoformat(dates[-1]), "day", "all")
    assert not audit(value, metrics)["missingExtrema"]
    phases = value["synthesis"]["reading"]["phases"]
    assert len(phases) <= 8 and phases[-1]["end"] == dates[-1]
    refs = {ref for p in phases for ref in p["factIds"]}
    assert all(p["factId"] in refs for m in metrics for p in m["series"])


def test_isolated_valid_period_is_not_dropped_and_gaps_are_not_bridged():
    dates = ["2026-04-01", "2026-04-04", "2026-04-05", "2026-04-06", "2026-04-07"]
    value, metrics = snapshot(data(dates, [99, 10, 8, 9, 12]), "example", "sample", date(2026, 4, 1), date(2026, 4, 7), "day", "all")
    assert not audit(value, metrics)["missingExtrema"]
    phases = value["synthesis"]["reading"]["phases"]
    assert phases[0]["start"] == phases[0]["end"] == "2026-04-01"
    assert not any(p["start"] < "2026-04-02" < p["end"] for p in phases)


def test_wrong_month_still_rejected_as_source_error():
    dates = ["2026-02-01", "2026-03-01"]
    value, _ = snapshot(data(dates, [20, 10]), "example", "sample", date(2026, 2, 1), date(2026, 3, 15), "month", "all")
    payload = narrative(value)
    payload["claims"][0]["text"] = "Số lỗi giảm từ tháng 02/2030 đến tháng 03/2030."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert "unsupported_date_mention" in result.errors


def test_generation_budget_does_not_drop_late_isolated_extrema_from_report():
    dates = [(date(2026, 2, 1) + timedelta(days=i * 2)).isoformat() for i in range(12)]
    value, metrics = snapshot(data(dates, [5] * 11 + [50]), "example", "sample", date.fromisoformat(dates[0]), date.fromisoformat(dates[-1]), "day", "all")
    assert not audit(value, metrics)["missingExtrema"]
    payload = provider_plan(value)
    assert len(payload["reportPlan"]["sections"]["phases"]) <= 8
    report = synthesis_fallback(value["synthesis"])["report"]
    assert len(report["phases"]) == 12
    assert report["phases"][-1]["end"] == dates[-1]
    assert "cao nhất 50" in report["phases"][-1]["text"]
    assert report["omittedPhaseCount"] == 0


def test_sparse_secondary_metric_keeps_observed_points_without_joint_inference():
    dates = [(date(2026, 5, 1) + timedelta(days=i)).isoformat() for i in range(12)]
    rows = data(dates, [8, 9, 10, 11, 4, 5, 6, 20, 3, 5, 4, 9])
    rows = rows[rows.metric_code.eq("total") | rows.date.isin([dates[1], dates[4], dates[7], dates[-1]])]
    value, metrics = snapshot(rows, "example", "sample", date(2026, 5, 1), date(2026, 5, 12), "day", "all")
    assert not audit(value, metrics)["missingExtrema"]
    refs = {ref for p in value["synthesis"]["reading"]["phases"] for ref in p["factIds"]}
    assert all(p["factId"] in refs for m in metrics for p in m["series"])


def test_extremum_with_copula_still_requires_ranked_value():
    dates = ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]
    value, _ = snapshot(data(dates, [8, 10, 12, 11]), "example", "sample", date(2026, 6, 1), date(2026, 6, 4), "day", "error")
    payload = narrative(value)
    payload["claims"][0]["text"] = "Số lỗi cao nhất là 10."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert "numeric_role_mismatch" in result.errors


def test_number_of_cited_periods_is_grounded_but_wrong_count_is_rejected():
    dates = ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]
    value, _ = snapshot(data(dates, [8, 8, 8, 8]), "example", "sample", date(2026, 6, 1), date(2026, 6, 4), "day", "error")
    payload = narrative(value)
    payload["claims"][1]["text"] = "Từ ngày 01/06/2026 đến ngày 04/06/2026, số lỗi giữ nguyên ở 8 qua 4 kỳ."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results
    payload["claims"][1]["text"] = payload["claims"][1]["text"].replace("4 kỳ", "5 kỳ")
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert "unsupported_numeric_mention" in result.errors


def test_monthly_scope_resolves_actual_clipped_period_end():
    dates = ["2026-02-01", "2026-03-01"]
    value, _ = snapshot(data(dates, [20, 10]), "example", "sample", date(2026, 2, 1), date(2026, 3, 15), "month", "all")
    payload = narrative(value)
    payload["claims"][1]["text"] = "Từ kỳ 02/2026 đến kỳ 03/2026, Tổng số giảm. Số lỗi giảm. Tỷ lệ báo sai giảm."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results


def test_weekly_peak_reference_does_not_bind_later_decline_dates_to_peak():
    dates = ["2026-07-06", "2026-07-13", "2026-07-20", "2026-07-27"]
    value, _ = snapshot(data(dates, [50, 40, 30, 20]), "example", "sample", date(2026, 7, 6), date(2026, 8, 2), "week", "error")
    payload = narrative(value)
    payload["claims"][1]["text"] = "Từ kỳ 06/07–12/07/2026 đến kỳ 27/07–02/08/2026, số lỗi giảm từ mức cao nhất 50 xuống 40 ở kỳ 13/07–19/07/2026 và còn 20 ở kỳ 27/07–02/08/2026."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results


def test_named_month_alone_is_enough_scope_for_one_month_observation():
    dates = ["2026-02-01", "2026-03-01"]
    rows = data(dates, [20, 10])
    rows.loc[rows.metric_code.eq("error") & rows.date.eq(dates[1]), "chart_value"] = None
    rows.loc[rows.metric_code.eq("error") & rows.date.eq(dates[1]), "value_kind"] = "source_marker"
    value, _ = snapshot(rows, "example", "sample", date(2026, 2, 1), date(2026, 3, 15), "month", "all")
    payload = narrative(value)
    candidates = {c["candidateId"]: c for c in value["synthesis"]["candidates"]}
    claim = next(c for c in payload["claims"] if c["section"] == "phases" and candidates[c["candidateId"]]["metricCodes"] == ["error"])
    claim["text"] = "Trong tháng 02/2026, số lỗi ghi nhận 20."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results


def test_extra_ranked_fact_dependencies_do_not_make_two_periods_a_trend():
    value = current()
    candidate = next(c for c in value["synthesis"]["candidates"] if c["candidateId"] == "report-phases-01")
    refs = list(candidate["factIds"]) + [p["factId"] for m in value["metrics"] for p in m["series"]]
    errors, _ = validate_text("Từ 12/09/2026 đến 13/09/2026, số lỗi có xu hướng tăng.", candidate, value, refs)
    assert "insufficient_trend_periods" in errors


def test_missing_unit_in_evidence_is_null_not_nan(monkeypatch, tmp_path):
    rows = data(["2026-07-01", "2026-07-02"], [10, 20])
    rows["lineage_ref"] = [f"lin_test_{i}" for i in range(len(rows))]
    computation = AnalyticsEngine().trend(rows, entity_ref="example", metric_code="error_rate", start=date(2026, 7, 1), end=date(2026, 7, 2), group_by="day")
    captured = []
    def register(_db, _source, _project, specs):
        json.dumps(specs, allow_nan=False)
        captured.extend(specs)
        return ["agg_test"]
    monkeypatch.setattr("excel_visualization_pipeline.ai.evidence.register_aggregate_snapshots", register)
    builder = EvidenceBuilder(tmp_path / "unused.sqlite", "source")
    builder.build(computation, project="sample", entity={"entity_id": "example", "entity_label": "sample", "entity_path": "sample", "effective_unit": float("nan")}, source_run_id=1)
    assert captured and all(spec["context"]["entity"]["effectiveUnit"] is None for spec in captured)


def test_source_coverage_fraction_is_not_a_date_and_wrong_fraction_rejected():
    value = current()
    payload = narrative(value)
    payload["claims"][0]["text"] = "Dữ liệu có 1/10 kỳ thiếu dữ liệu hợp lệ. Số lỗi tăng rồi giảm."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results
    payload["claims"][0]["text"] = payload["claims"][0]["text"].replace("1/10", "2/10")
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert "unsupported_date_mention" in result.errors


def test_gap_explanation_uses_quality_not_kpi_business_causality():
    value = current()
    payload = narrative(value)
    payload["claims"][0]["text"] = "Số lỗi tăng rồi giảm. Dữ liệu có khoảng trống do thiếu kỳ."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results
    payload["claims"][0]["text"] = "Số lỗi tăng do thiếu kỳ."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert "unsupported_meaning" in result.errors


def test_peak_reference_then_decrease_value_does_not_inherit_extremum_role():
    value = current()
    payload = narrative(value)
    claim = next(c for c in payload["claims"] if c["candidateId"] == "report-phases-02")
    claim["text"] = "Từ 13/09/2026 đến 15/09/2026, số lỗi là 43 vào 13/09/2026, mức cao nhất trong các kỳ có dữ liệu, trước khi giảm xuống 22 vào 15/09/2026."
    result = OutputValidator().validate(json.dumps(payload, ensure_ascii=False), value)
    assert result.valid and not result.errors, result.claim_results
