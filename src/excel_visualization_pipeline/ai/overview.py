"""Grounded cross-metric insight candidates; no LLM arithmetic or business judgement."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
import math
from typing import Any

from .analytics import TrendComputation, _display, _direction


POLICY = "aligned-overview-v1"


def build_overview(computations: dict[str, TrendComputation], metrics: list[dict[str, Any]]) -> dict[str, Any]:
    by_code = {metric["metricCode"]: metric for metric in metrics}
    facts: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    limitations: list[str] = []

    def candidate(key: str, layer: str, text: str, refs: list[str], evidence: list[str]) -> None:
        candidates.append({
            "candidateId": key, "layer": layer, "text": text,
            "factIds": list(dict.fromkeys(refs)), "evidenceIds": list(dict.fromkeys(evidence)),
        })

    rate = computations["error_rate"]
    periods = []
    for point, item in zip(rate.points, by_code["error_rate"]["series"]):
        rows = point.rows
        included = rows[rows["ai_included"].fillna(False).astype(bool)]
        numerator = float(included.loc[included["metric_code"].eq("error"), "chart_value"].sum())
        denominator = float(included.loc[included["metric_code"].eq("total"), "chart_value"].sum())
        dates = sorted({value.date().isoformat() for value in included["date"]})
        periods.append({
            "periodStart": item["periodStart"], "periodEnd": item["periodEnd"],
            "periodLabel": item["periodLabel"], "numerator": numerator, "denominator": denominator,
            "numeratorDisplay": _display(numerator, computations["error"].unit),
            "denominatorDisplay": _display(denominator, computations["total"].unit),
            "rateDisplay": item["displayValue"], "eligibleDays": dates,
            "eligibleDayCount": point.observed_day_count, "expectedDayCount": point.expected_day_count,
            "factIds": [item["factId"]], "evidenceIds": [item["evidenceId"]],
        })

    basis: dict[str, Any] = {
        "policyVersion": POLICY, "status": "unavailable", "reason": "Cần ít nhất hai kỳ có tỷ lệ hợp lệ để liên kết ba chỉ số.",
        "rule": "weighted_error_rate", "periods": periods,
        "baseline": periods[0] if periods else None, "current": periods[-1] if periods else None,
    }
    if len(periods) >= 2:
        basis["status"] = "comparable"
        basis["reason"] = "So sánh kỳ hợp lệ đầu và cuối, dùng cùng cặp tử số/mẫu số của tỷ lệ."
        for endpoint_index in (0, -1):
            endpoint = periods[endpoint_index]
            for code in ("total", "error", "error_rate"):
                series = by_code[code]["series"]
                if not series or any(series[endpoint_index][key] != endpoint[key] for key in ("periodStart", "periodEnd")):
                    basis.update(status="limited", reason="Các chỉ số không có cùng kỳ hợp lệ đầu và cuối; chưa liên kết mức thay đổi.")
                    break
                point = series[endpoint_index]
                if point["observedDayCount"] != point["expectedDayCount"]:
                    basis.update(status="limited", reason="Kỳ so sánh có ngày thiếu hoặc bị loại; chưa kết luận quan hệ tăng trưởng.")
                if code in {"total", "error"} and not math.isclose(
                    point["value"], endpoint["denominator" if code == "total" else "numerator"], abs_tol=1e-8,
                ):
                    basis.update(status="limited", reason="Số lượng độc lập khác tập số liệu tính tỷ lệ; chưa liên kết mức thay đổi.")
            start, end = date.fromisoformat(endpoint["periodStart"]), date.fromisoformat(endpoint["periodEnd"])
            full_period = rate.group_by == "day" or (
                rate.group_by == "week" and start.weekday() == 0 and end.weekday() == 6 and (end - start).days == 6
            ) or (rate.group_by == "month" and start.day == 1 and end.day == monthrange(end.year, end.month)[1])
            if not full_period:
                basis.update(status="limited", reason="Kỳ đầu hoặc cuối chưa đủ kỳ lịch; chỉ mô tả số ghi nhận, chưa liên kết tăng trưởng.")
            if endpoint["denominator"] <= 0:
                basis.update(status="unavailable", reason="Có kỳ không có lượng ghi nhận dương; không giải thích quan hệ tăng trưởng từ quy ước 0/0.")
            if endpoint["numerator"] < 0:
                basis.update(status="unavailable", reason="Có số Báo sai/Lỗi âm; chưa áp dụng quy tắc quan hệ tăng trưởng cho dữ liệu này.")

    if basis["status"] == "comparable":
        first, last = periods[0], periods[-1]
        refs = [f"{code}:fact-{name}" for code in ("total", "error", "error_rate") for name in ("previous", "current", "delta", "direction")]
        evidence = [f"{code}:{point.evidence_id}" for code, computation in computations.items() for point in (computation.points[0], computation.points[-1])]
        direction = _direction(rate.points[-1].value - rate.points[0].value)
        # Positive denominators permit ratio comparison; numerator zero does not permit growth percentages.
        relationship = {"decreasing": "error_share_decreased", "increasing": "error_share_increased", "unchanged": "error_share_unchanged"}[direction]
        fact = {
            "factId": "cross:rate-relationship", "kind": "numerator_denominator_relationship",
            "value": relationship, "displayValue": relationship, "unit": "enum",
            "operandFactIds": refs.copy(), "evidenceIds": evidence, "policyVersion": POLICY,
        }
        facts.append(fact)
        explanation = {"decreasing": "Tỷ trọng Báo sai/Lỗi trên Tổng số giảm", "increasing": "Tỷ trọng Báo sai/Lỗi trên Tổng số tăng", "unchanged": "Tỷ trọng Báo sai/Lỗi trên Tổng số không đổi"}[direction]
        if first["numerator"] > 0 and last["numerator"] > 0:
            total_growth = (last["denominator"] / first["denominator"] - 1) * 100
            error_growth = (last["numerator"] / first["numerator"] - 1) * 100
            growth_relation = "equal" if math.isclose(total_growth, error_growth, abs_tol=1e-8) else "total_higher" if total_growth > error_growth else "error_higher"
            facts.append({
                "factId": "cross:growth-relationship", "kind": "metric_growth_relationship",
                "value": growth_relation, "displayValue": growth_relation, "unit": "enum",
                "operandFactIds": refs.copy(), "evidenceIds": evidence, "policyVersion": POLICY,
            })
            refs.append("cross:growth-relationship")
            if math.isclose(total_growth, 0.0, abs_tol=1e-8) and growth_relation != "equal":
                lead = f"Tổng số không đổi, trong khi Báo sai/Lỗi {'tăng' if error_growth > 0 else 'giảm'}"
            elif math.isclose(error_growth, 0.0, abs_tol=1e-8) and growth_relation != "equal":
                lead = f"Báo sai/Lỗi không đổi, trong khi Tổng số {'tăng' if total_growth > 0 else 'giảm'}"
            elif total_growth >= 0 and error_growth >= 0 and growth_relation != "equal":
                lead = "Tổng số tăng nhanh hơn Báo sai/Lỗi" if growth_relation == "total_higher" else "Báo sai/Lỗi tăng nhanh hơn Tổng số"
            elif total_growth <= 0 and error_growth <= 0 and growth_relation != "equal":
                lead = "Tổng số giảm nhanh hơn Báo sai/Lỗi" if growth_relation == "error_higher" else "Báo sai/Lỗi giảm nhanh hơn Tổng số"
            elif growth_relation == "equal":
                lead = "Tổng số và Báo sai/Lỗi có cùng mức thay đổi tương đối"
            else:
                lead = "Tổng số và Báo sai/Lỗi thay đổi khác chiều"
            explanation = f"{lead}; {explanation[0].lower()}{explanation[1:]} trong phép tính tỷ lệ"
        text = (
            f"Từ {first['periodLabel']} đến {last['periodLabel']}, {explanation[0].lower()}{explanation[1:]} "
            f"({first['rateDisplay']} → {last['rateDisplay']}; chênh lệch "
            f"{_display(rate.points[-1].value - rate.points[0].value, 'percentage_point').replace(' pp', ' điểm phần trăm')}). "
            f"Lượng ghi nhận là {first['denominatorDisplay']} → {last['denominatorDisplay']}; Báo sai/Lỗi là "
            f"{first['numeratorDisplay']} → {last['numeratorDisplay']}."
        )
        candidate("relationship", "relational", text, [*refs, "cross:rate-relationship"], evidence)
        checks.append({"checkId": "check-relationship", "text": "Đối chiếu tử số và mẫu số của hai kỳ so sánh.", "factIds": refs, "evidenceIds": [first["evidenceIds"][0], last["evidenceIds"][0]]})
    else:
        limitations.append(basis["reason"])

    # Choose only one non-redundant temporal event, not a second metric table.
    for code in ("error_rate", "error", "total"):
        metric = by_code[code]
        events = [metric["periodAnalytics"][key] for key in ("largestIncrease", "largestDecrease") if metric["periodAnalytics"][key]]
        event = max(events, key=lambda item: (abs(item["absolute"]), item["toPeriodStart"]), default=None)
        if event is None or len(metric["series"]) < 3:
            continue
        movement = "tăng" if event["direction"] == "increasing" else "giảm"
        absolute = event["absoluteDisplay"].lstrip("+-").replace(" pp", " điểm phần trăm")
        text = f"{metric['metricDisplayName']} có mức {movement} lớn nhất trong khoảng đang xem từ {event['fromPeriodLabel']} đến {event['toPeriodLabel']}: {event['fromDisplayValue']} → {event['toDisplayValue']} ({movement} {absolute})."
        lookup = {fact["factId"]: fact for fact in metric["facts"]}
        evidence = list(dict.fromkeys(e for ref in event["factIds"] for e in lookup[ref]["evidenceIds"]))
        candidate("temporal-change", "temporal", text, event["factIds"], evidence)
        checks.append({"checkId": "check-change", "text": "Mở nguồn của hai kỳ có biến động lớn nhất để đối chiếu.", "factIds": event["factIds"], "evidenceIds": evidence})
        break

    if not candidates or candidates[0]["layer"] != "relational":
        for metric in metrics:
            if len(metric["series"]) < 2:
                continue
            first, last = metric["series"][0], metric["series"][-1]
            pattern = next(f for f in metric["facts"] if f["kind"] == "trend_pattern")
            wording = {"consistently_increasing": "không có lần giảm giữa các kỳ hợp lệ", "consistently_decreasing": "không có lần tăng giữa các kỳ hợp lệ", "unchanged": "không đổi qua các kỳ hợp lệ", "fluctuating": "tăng giảm qua các kỳ"}[pattern["value"]]
            candidate("description", "descriptive", f"{metric['metricDisplayName']} ghi nhận {first['displayValue']} tại {first['periodLabel']} và {last['displayValue']} tại {last['periodLabel']}; chuỗi {wording}.", [first["factId"], last["factId"], pattern["factId"]], pattern["evidenceIds"])
            candidates.insert(0, candidates.pop())
            break
    for metric in metrics:
        for limitation in metric["quality"]["limitations"]:
            limitations.append(f"{metric['metricDisplayName']}: {limitation}")
    if len(periods) >= 2 and basis["status"] != "comparable":
        checks.insert(0, {"checkId": "check-coverage", "text": "Kiểm tra các ngày đủ điều kiện và ngày bị loại khỏi phép tính tỷ lệ.", "factIds": [ref for period in (periods[0], periods[-1]) for ref in period["factIds"]], "evidenceIds": [period["evidenceIds"][0] for period in (periods[0], periods[-1])]})
    stories = [metric for metric in metrics if metric["periodAnalytics"].get("temporalStructure", {}).get("factIds")]
    if stories:
        structures = [metric["periodAnalytics"]["temporalStructure"] for metric in stories]
        candidate("whole-window", "whole_series", " ".join(
            f"{metric['metricDisplayName']}: {structure['overviewText']}"
            for metric, structure in zip(stories, structures)
        ), [ref for structure in structures for ref in structure["overviewFactIds"]],
            [ref for structure in structures for ref in structure["evidenceIds"]])
        candidates.insert(0, candidates.pop())
        candidates = [item for item in candidates if item["candidateId"] != "description"]
    return {"comparisonBasis": basis, "facts": facts, "insightCandidates": candidates[:3], "inspectionChecks": checks[:2], "limitations": list(dict.fromkeys(limitations))}


def overview_fallback(candidates: list[dict[str, Any]], limitations: list[str]) -> dict[str, Any]:
    first = candidates[0] if candidates else None
    return {
        "mode": "deterministic", "schemaVersion": "ai-narrative-v2",
        "summary": {"text": first["text"] if first else "Chưa đủ hai kỳ hợp lệ để phân tích; xem dữ liệu cần lưu ý.", "candidateIds": [first["candidateId"]] if first else [], "factIds": first["factIds"] if first else [], "claimType": "descriptive"},
        "insights": [], "limitations": limitations, "suggestedChecks": [],
    }
