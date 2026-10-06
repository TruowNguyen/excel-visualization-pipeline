"""Provider-independent Overview summary. Never sums hierarchy nodes together."""
from __future__ import annotations

from datetime import timedelta
import math

import pandas as pd

from .visualization import display_entity_label, prepare_period_metric_summary, prepare_period_statistics

METRICS = {"Tổng số", "Báo sai/Lỗi", "% báo sai"}
SOURCE_KINDS = {"numeric", "percentage", "percentage_text"}


def _source_numeric(frame):
    values = pd.to_numeric(frame["chart_value"], errors="coerce")
    kinds = frame.get("value_kind", pd.Series("numeric", index=frame.index))
    status = frame.get("validation_status", pd.Series("valid", index=frame.index))
    return values.notna() & values.abs().lt(float("inf")) & kinds.isin(SOURCE_KINDS) & status.isin({"valid", "warning"})


def count_issues(data, entities):
    lookup = entities.set_index("entity_id").to_dict("index")

    def owner(entity_id):
        seen = set()
        while entity_id in lookup and entity_id not in seen:
            seen.add(entity_id)
            row = lookup[entity_id]
            if row["entity_level"] == "item":
                item_id = entity_id
                current = row.get("parent_entity_id")
                while current in lookup and current not in seen:
                    seen.add(current)
                    ancestor = lookup[current]
                    if ancestor["entity_level"] == "project" and pd.isna(ancestor.get("parent_entity_id")):
                        return item_id
                    current = ancestor.get("parent_entity_id")
                return None
            if row["entity_level"] != "subitem":
                return None
            entity_id = row["parent_entity_id"]
        return None

    rows = data[_source_numeric(data) & data["metric_normalized"].isin(METRICS)]
    issues = rows["entity_id"].map(owner)
    excluded = rows.loc[issues.isna() & rows["entity_level"].isin({"item", "subitem"}), "entity_id"].nunique()
    return {"status": "ready", "value": int(issues.dropna().nunique()), "excludedCount": int(excluded), "reason": None}


def _period_points(rows, start, end, grain, unit):
    totals = rows[rows["metric_normalized"].eq("Tổng số")].copy()
    totals.loc[~_source_numeric(totals), "chart_value"] = None
    if grain == "day":
        boundaries = pd.date_range(start, end, freq="D")
        prepared = None
    else:
        natural_start = start - timedelta(days=start.weekday()) if grain == "week" else start.replace(day=1)
        boundaries = pd.date_range(natural_start, end, freq="W-MON" if grain == "week" else "MS")
        prepared = prepare_period_metric_summary(totals, start, end, grain)
    points = []
    for natural in boundaries:
        natural_end = natural if grain == "day" else natural + (pd.Timedelta(days=6) if grain == "week" else pd.offsets.MonthEnd(0))
        first, last = max(natural, start), min(natural_end, end)
        daily = totals[totals["date"].between(first, last)]
        valid = daily[daily["chart_value"].notna()]
        value = None
        if grain == "day":
            if len(daily) == 1 and len(valid) == 1:
                value = float(valid.iloc[0]["chart_value"])
        elif prepared is not None and not prepared.empty:
            matched = prepared[prepared["period_start"].eq(first)]
            if len(matched) == 1 and pd.notna(matched.iloc[0]["total_sum"]):
                value = float(matched.iloc[0]["total_sum"])
        if value is not None and not math.isfinite(value):
            value = None
        label = first.strftime("%d/%m/%Y") if grain == "day" else (f"Tuần {natural.isocalendar().week:02d}/{natural.isocalendar().year}" if grain == "week" else f"Tháng {natural:%m/%Y}")
        points.append({"status": "ready" if value is not None else "no_data", "value": value, "unit": unit,
                       "inferredZero": False, "period": {"start": str(first.date()), "end": str(last.date()), "label": label,
                       "complete": first == natural and last == natural_end,
                       "observedDayCount": int(valid["date"].nunique()), "expectedDayCount": int((last - first).days + 1)}})
    return points


def _statistics_points(rows, data, start, end, grain, unit, periods, calculation):
    totals = rows[rows["metric_normalized"].eq("Tổng số")].copy()
    totals.loc[~_source_numeric(totals), "chart_value"] = None
    prepared = prepare_period_statistics(totals, start, end, grain, coverage_data=data, semantic_data=data)
    points = []
    column = "average_per_day" if calculation == "average_per_day" else "period_sum"
    for period in periods:
        first, last = max(pd.Timestamp(period.start), start), min(pd.Timestamp(period.end), end)
        matched = prepared[prepared["period_start"].eq(first)] if not prepared.empty else prepared
        row = matched.iloc[0] if len(matched) == 1 else None
        value = float(row[column]) if row is not None and pd.notna(row[column]) else None
        if value is not None and not math.isfinite(value):
            value = None
        points.append({"status": "ready" if value is not None else "no_data", "value": value,
                       "unit": f"{unit}/ngày" if calculation == "average_per_day" else unit,
                       "inferredZero": False, "period": {
                           "start": str(first.date()), "end": str(last.date()), "label": period.label,
                           "complete": period.is_complete and first.date() == period.start and last.date() == period.end,
                           "observedDayCount": int(row["observed_day_count"]) if row is not None else 0,
                           "expectedDayCount": int((last - first).days + 1),
                           "eligibleDayCount": int(row["eligible_day_count"]) if row is not None else 0,
                           "sourceMarkerDayCount": int(row["source_marker_day_count"]) if row is not None else 0,
                       }})
    return points


def build_statistics_summary(data, entities, project, start, end, grain, periods, mode, policy, source_ref=None):
    """Use the exact Statistics period selection and canonical SUM/AVG-day."""
    empty = not periods or start is None or end is None
    if empty:
        dates = pd.to_datetime(data["date"])
        start, end = dates.min(), dates.max()
    result = build_overview_summary(data, entities, project, start, end, grain, policy, source_ref,
                                    statistics_periods=periods, statistics_mode=mode)
    if empty:
        reason = "Không có kỳ thống kê phù hợp với bộ lọc đang chọn."
        result["window"] = None
        result["issueCount"] = {"status": "no_data", "value": None, "excludedCount": 0, "reason": reason}
        for name in ("peak", "lowest", "largestChange"):
            result[name] = {"status": "no_data", "value": None, "reason": reason}
        result["limitations"] = [reason]
    return result


def build_overview_summary(data, entities, project, start, end, grain, policy, source_ref=None,
                           *, statistics_periods=None, statistics_mode=None):
    """Source selection is project-wide and independent of chart entity/scope."""
    entities = entities[entities["project_label"].eq(project)].copy()
    data = data[data["project_label"].eq(project)].copy()
    data["date"] = pd.to_datetime(data["date"]).dt.normalize()
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    window_data = data[data["date"].between(start, end)]
    if statistics_periods is not None:
        mask = pd.Series(False, index=window_data.index)
        for period in statistics_periods:
            mask |= window_data["date"].between(pd.Timestamp(period.start), pd.Timestamp(period.end))
        window_data = window_data[mask]
    totals = data[data["metric_normalized"].eq("Tổng số")]
    usable_ids = set(totals.loc[_source_numeric(totals), "entity_id"])
    roots = entities[entities["entity_level"].eq("project") & entities["parent_entity_id"].isna()]
    root_ids = roots.loc[roots["entity_id"].isin(usable_ids), "entity_id"].tolist()
    mapping = policy.get("projects", {}).get(project, {})
    allowed = root_ids if len(root_ids) == 1 else ([] if len(root_ids) > 1 else mapping.get("sources", []))
    choices = []
    hierarchy = entities.set_index("entity_id").to_dict("index")

    def has_project_ancestor(ref):
        seen = set()
        while ref in hierarchy and ref not in seen:
            seen.add(ref)
            node = hierarchy[ref]
            if node["entity_level"] == "project" and pd.isna(node.get("parent_entity_id")):
                return True
            ref = node.get("parent_entity_id")
        return False

    for ref in allowed:
        found = entities[entities["entity_id"].eq(ref)]
        if found.empty:
            continue
        row = found.iloc[0]
        unit = row.get("effective_unit")
        # Stock/cumulative values do not become period flow by summing snapshots.
        eligible = pd.notna(unit) and bool(str(unit).strip()) and "lũy kế" not in str(unit).lower() and has_project_ancestor(ref)
        choices.append({"entityRef": ref, "label": display_entity_label(row["entity_label"], row["entity_level"]),
                        "scope": "project" if ref in root_ids else "source", "effectiveUnit": str(unit) if pd.notna(unit) else None,
                        "eligible": eligible, "reason": None if eligible else "Nguồn có phân cấp/đơn vị không hợp lệ hoặc là số lũy kế chưa hỗ trợ."})
    eligible = [choice for choice in choices if choice["eligible"]]
    if source_ref and source_ref not in {choice["entityRef"] for choice in eligible}:
        raise ValueError("Nguồn phân tích không thuộc danh sách nguồn hợp lệ của dự án.")
    selected = next((choice for choice in eligible if choice["entityRef"] == (source_ref or mapping.get("default"))), None)
    # A missing configured default must not silently become another business source.
    if not selected and len(root_ids) == 1:
        selected = eligible[0] if eligible else None
    reason = "Chưa có nguồn Tổng số ghi nhận được xác nhận cho dự án." if not selected else None
    result = {
        "schemaVersion": 1, "policyVersion": policy["policyVersion"], "project": project,
        "metricKey": "Tổng số", "metricDisplayName": "Tổng số ghi nhận",
        "window": {"start": str(start.date()), "end": str(end.date())}, "grain": grain,
        "scope": selected["scope"] if selected else None, "source": selected, "sourceChoices": choices,
        "issueCount": count_issues(window_data, entities), "limitations": [],
        "peak": {"status": "unavailable", "value": None, "reason": reason},
        "lowest": {"status": "unavailable", "value": None, "reason": reason},
        "largestChange": {"status": "unavailable", "reason": reason},
        "validPeriodCount": 0, "expectedPeriodCount": 0,
    }
    calculation = "average_per_day" if statistics_mode == "average" else "sum"
    if statistics_mode is not None:
        result.update(calculation=calculation, requestedMode=statistics_mode)
    if selected:
        rows = window_data[window_data["entity_id"].eq(selected["entityRef"])]
        points = (_statistics_points(rows, data, start, end, grain, selected["effectiveUnit"], statistics_periods, calculation)
                  if statistics_periods is not None else _period_points(rows, start, end, grain, selected["effectiveUnit"]))
        valid = [point for point in points if point["value"] is not None]
        result.update(validPeriodCount=len(valid), expectedPeriodCount=len(points))
        for name, choose in [("peak", max), ("lowest", min)]:
            if not valid:
                result[name] = {"status": "no_data", "value": None, "reason": "Nguồn chưa có Tổng số ghi nhận trong khoảng đã chọn."}
                continue
            value = choose(point["value"] for point in valid)
            ties = [point for point in valid if point["value"] == value]
            result[name] = {**ties[-1], "tieCount": len(ties), "reason": None}
        if any(point["period"]["observedDayCount"] < point["period"]["expectedDayCount"] for point in points):
            result["limitations"].append("Có ngày thiếu dữ liệu; tổng theo kỳ chỉ gồm các giá trị ghi nhận hợp lệ.")
        if any(not point["period"]["complete"] for point in points):
            result["limitations"].append("Khoảng đang chọn có kỳ chưa đầy đủ.")
        pairs = []
        for previous, current in zip(points, points[1:]):
            if previous["value"] is None or current["value"] is None or not previous["period"]["complete"] or not current["period"]["complete"]:
                continue
            if pd.Timestamp(previous["period"]["end"]) + pd.Timedelta(days=1) != pd.Timestamp(current["period"]["start"]):
                continue
            delta = current["value"] - previous["value"]
            if math.isfinite(delta):
                pairs.append((previous, current, delta))
        if not pairs:
            result["largestChange"] = {"status": "insufficient_data", "reason": "Chưa đủ hai kỳ lịch liền nhau và đầy đủ để so sánh.", "eligiblePairCount": 0}
        else:
            previous, current, delta = max(pairs, key=lambda pair: (abs(pair[2]), pair[1]["period"]["start"]))
            zero = math.isclose(previous["value"], 0, abs_tol=1e-12)
            relative = None if zero else delta / abs(previous["value"]) * 100
            if relative is not None and not math.isfinite(relative):
                relative = None
            result["largestChange"] = {
                "status": "ready", "reason": None, "from": previous, "to": current,
                "absolute": round(delta, 8), "relativePercent": round(relative, 8) if relative is not None else None,
                "relativeReason": "Không tính được % vì kỳ trước bằng 0." if zero else "Phần trăm vượt phạm vi tính toán." if relative is None else None,
                "direction": "increasing" if delta > 0 else "decreasing" if delta < 0 else "unchanged",
                "unit": current["unit"], "eligiblePairCount": len(pairs),
                "tieCount": sum(abs(pair[2]) == abs(delta) for pair in pairs),
            }
    return result
