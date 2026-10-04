"""Plain-language reading order over verified period facts; no new KPI arithmetic."""
from datetime import date, timedelta
from typing import Any

def plain_text(text: str, label: str = "") -> str:
    for old, new in (
        ("toàn khoảng", "thời gian đã chọn"),
        ("endpoint", "đầu và cuối giai đoạn"),
        ("tỷ trọng lỗi", "tỷ lệ báo sai"),
        ("tỷ trọng trên Tổng số", "tỷ lệ báo sai"),
        ("tỷ trọng", "tỷ lệ báo sai"),
        ("trong phép tính tỷ lệ", "khi tính tỷ lệ báo sai"),
        ("chuỗi đi ngang", "các kỳ giữ nguyên"),
        ("cuối chuỗi đi ngang", "các kỳ cuối giữ nguyên"),
        ("facts chưa hỗ trợ", "dữ liệu chưa hỗ trợ"),
    ):
        text = text.replace(old, new)
    if label:
        text = text.replace("chỉ số", label)
    text = text.replace("; ", ". ")
    return ". ".join(sentence[:1].upper() + sentence[1:] for sentence in text.split(". "))


def reading_report(metrics: list[dict[str, Any]], candidates: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any]:
    """One shared chronology. Merge short alternating transitions, never cross gaps.

    Phase boundaries follow the count-of-errors metric where available. Other
    metrics describe their actual movements INSIDE that phase, not endpoints.
    All statements retain period fact IDs and evidence IDs.
    """
    coverage = max((len(m["series"]) for m in metrics), default=0)
    focus = next((m for m in metrics if m["metricCode"] == "error" and len(m["series"]) == coverage and coverage >= 2), None)
    focus = focus or next((m for m in metrics if len(m["series"]) == coverage and coverage >= 2), None)
    if not focus:
        return {"policyVersion": "analytical-reading-v1", "overview": None, "phases": [], "takeaways": []}
    series = focus["series"]
    stages = focus["periodAnalytics"].get("temporalStructure", {}).get("stages", [])
    groups: list[tuple[int, int]] = []
    pending: tuple[int, int] | None = None
    for stage in stages:
        start, end = stage["startIndex"], stage["endIndex"]
        if pending and pending[1] != start:
            groups.append(pending)
            pending = None
        if stage["transitionCount"] == 1 and stage["direction"] != "unchanged":
            pending = (pending[0] if pending else start, end)
        else:
            if pending:
                groups.append(pending)
                pending = None
            groups.append((start, end))
    if pending:
        groups.append(pending)
    covered = {i for first, last in groups for i in range(first, last + 1)}
    groups.extend((i, i) for i in range(len(series)) if i not in covered)
    groups.sort()
    # Keep the whole window, not just its first eight stages. Condense adjacent
    # short phases without crossing missing periods or dropping their points.
    while len(groups) > 8:
        adjacent = [(b[1] - a[0], i) for i, (a, b) in enumerate(zip(groups, groups[1:])) if a[1] == b[0]]
        if not adjacent:
            break
        _, index = min(adjacent)
        groups[index:index + 2] = [(groups[index][0], groups[index + 1][1])]
    constant_metrics = [m for m in metrics if m is not focus and len(m["series"]) >= 4 and m["quality"]["validPeriodCount"] == m["quality"]["expectedPeriodCount"] and len({p["value"] for p in m["series"]}) == 1]
    phases = []
    focus_movements = []
    for start, end in groups:
        first, last = series[start], series[end]
        sentences, refs, evidence = [], [], []
        for metric in metrics:
            points = [p for p in metric["series"] if first["periodStart"] <= p["periodStart"] <= last["periodStart"]]
            if not points:
                continue
            if points[0]["periodStart"] != first["periodStart"] or points[-1]["periodEnd"] != last["periodEnd"]:
                continue
            if any(date.fromisoformat(a["periodEnd"]) + timedelta(days=1) != date.fromisoformat(b["periodStart"]) for a, b in zip(points, points[1:])):
                continue
            if len(points) == 1:
                sentences.append(f"{metric['metricDisplayName']} ghi nhận {points[0]['displayValue']} ở kỳ này; không đủ để mô tả diễn biến trong đoạn.")
                refs.append(points[0]["factId"])
                evidence.append(points[0]["evidenceId"])
                if metric is focus:
                    focus_movements.append("chỉ có một kỳ hợp lệ ở đoạn này")
                continue
            directions = []
            for left, right in zip(points, points[1:]):
                direction = "tăng" if right["value"] > left["value"] else "giảm" if right["value"] < left["value"] else "giữ nguyên"
                if not directions or directions[-1] != direction:
                    directions.append(direction)
            label = metric["metricDisplayName"]
            if len(directions) > 2:
                movement = "có cả lần tăng và giảm" if {"tăng", "giảm"} <= set(directions) else " ".join(directions)
            else:
                movement = " rồi ".join(directions)
            if metric is focus:
                focus_movements.append(movement)
            # Show a numeric anchor only for the phase-setting metric.
            anchor = ""
            if metric is focus and len(directions) == 1:
                anchor = f" từ {points[0]['displayValue']} lên {points[-1]['displayValue']}" if directions[0] == "tăng" else f" từ {points[0]['displayValue']} xuống {points[-1]['displayValue']}" if directions[0] == "giảm" else f" ở {points[-1]['displayValue']}"
                movement = "" if directions[0] == "giữ nguyên" else movement
                if not movement:
                    movement = "giữ nguyên"
            if metric not in constant_metrics:
                sentences.append(f"{label} {movement}{anchor}.")
            refs.extend(p["factId"] for p in points)
            evidence.extend(p["evidenceId"] for p in points)
        if not sentences:
            continue
        relationship = next((c for c in candidates if len(c["metricCodes"]) > 1 and set(c["factIds"][1:]) <= set(refs) and c["anchors"][0]["periodLabel"] == first["periodLabel"] and c["anchors"][-1]["periodLabel"] == last["periodLabel"]), None)
        explanation = ""
        if relationship:
            refs.extend(relationship["factIds"])
            description = relationship.get("relationshipDescription")
            if description:
                explanation = plain_text(description["interpretation"] + ".")
            elif relationship["kind"] == "count_rate_contrast":
                explanation = "Tổng số tăng nhanh hơn số lỗi khi tính tỷ lệ báo sai."
        phases.append({"start": first["periodStart"], "end": last["periodEnd"],
                       "startLabel": first["periodLabel"], "endLabel": last["periodLabel"],
                       "text": " ".join(sentences), "explanation": explanation,
                       "factIds": list(dict.fromkeys(refs)),
                       "evidenceIds": list(dict.fromkeys(evidence))})
    # Sparse secondary metrics cannot describe a shared phase continuously.
    # Keep their observed points in separate, explicit source-backed phases
    # rather than dropping extrema or pretending the gaps are zero.
    used = {ref for phase in phases for ref in phase["factIds"]}
    for metric in metrics:
        for point in metric["series"]:
            if point["factId"] in used:
                continue
            phases.append({"start": point["periodStart"], "end": point["periodEnd"],
                           "startLabel": point["periodLabel"], "endLabel": point["periodLabel"],
                           "text": f"{metric['metricDisplayName']} ghi nhận {point['displayValue']} ở kỳ này. Không đủ các kỳ liền nhau để mô tả diễn biến của chỉ số này trong giai đoạn chung.",
                           "explanation": "", "factIds": [point["factId"]], "evidenceIds": [point["evidenceId"]]})
    phases.sort(key=lambda phase: (phase["start"], phase["end"]))
    label = focus["metricDisplayName"]
    partial = focus["quality"]["validPeriodCount"] < focus["quality"]["expectedPeriodCount"]
    if partial:
        directions = {s["direction"] for s in stages}
        movement = "có cả lần tăng và giảm" if {"increasing", "decreasing"} <= directions else "tăng hoặc giữ nguyên" if "increasing" in directions else "giảm hoặc giữ nguyên" if "decreasing" in directions else "giữ nguyên"
        overview = f"Trong các đoạn có dữ liệu, {label} {movement}. Ở các kỳ cuối, {label} {focus_movements[-1]}."
    elif len(series) < 4:
        movement = " rồi ".join(focus_movements) if focus_movements else "chưa có hai kỳ liền nhau để so sánh"
        overview = f"{label} {movement}" + (" giữa hai kỳ." if len(series) == 2 else ".") + (" Hai kỳ chỉ cho biết mức thay đổi, chưa xác định xu hướng." if len(series) == 2 else " Số kỳ còn ít, chưa xác định xu hướng.")
    elif len(focus_movements) <= 4 and focus_movements:
        overview = f"{label} {focus_movements[0]}."
        if len(focus_movements) > 1:
            overview = f"{label} {focus_movements[0]} ở đầu giai đoạn. Sau đó, {label} " + ", rồi ".join(focus_movements[1:]) + "."
    else:
        overview = f"{label} có nhiều lần thay đổi chiều. Các giai đoạn bên dưới cho biết thời điểm tăng, giảm và giữ nguyên."
    if not partial and any(m["quality"]["validPeriodCount"] < m["quality"]["expectedPeriodCount"] for m in metrics):
        overview += " Một số chỉ số có kỳ thiếu dữ liệu. Chỉ mô tả các đoạn có dữ liệu của từng chỉ số."
    overview_refs = [p["factId"] for p in series]
    for metric in constant_metrics:
        overview += f" {metric['metricDisplayName']} giữ nguyên trong thời gian đã chọn."
        overview_refs.extend(p["factId"] for p in metric["series"])
    takeaways = []
    messages = {
        "count_rate_contrast": "Số lỗi tăng không đồng nghĩa tỷ lệ báo sai tăng.",
        "errors_down_share_up": "Số lỗi giảm chưa có nghĩa tỷ lệ báo sai giảm.",
        "unchanged_errors_share_down": "Tỷ lệ báo sai giảm chưa có nghĩa số lỗi đã giảm.",
        "unchanged_errors_share_up": "Tỷ lệ báo sai tăng chưa có nghĩa số lỗi đã tăng.",
        "volume_up_same_share": "Số lỗi tăng cùng lượng ghi nhận. Dữ liệu chưa cho thấy tỷ lệ báo sai tăng.",
        "volume_down_same_share": "Số lỗi giảm cùng lượng ghi nhận. Dữ liệu chưa cho thấy tỷ lệ báo sai giảm.",
        "endpoint_masks": "Giá trị đầu và cuối bằng nhau không có nghĩa các kỳ ở giữa giữ nguyên.",
    }
    # Only distinct, supported interpretations; no forced takeaway per metric.
    for candidate in selected:
        label = candidate["anchors"][0]["metricDisplayName"]
        structural = {
            "peak_retreat": f"{label} không duy trì đà tăng sau khi đạt mức cao nhất.",
            "trough_recovery": f"{label} đã chuyển từ giảm sang tăng.",
            "peak_offset": "Tổng số và Báo sai/Lỗi không đạt mức cao nhất cùng kỳ.",
        }
        message = messages.get(candidate["kind"]) or structural.get(candidate["kind"])
        if message:
            prefix = "Trong đoạn có dữ liệu liền nhau, " if candidate["scope"] == "contiguous_block" else ""
            takeaways.append({"text": prefix + message, "candidateId": candidate["candidateId"],
                              "factIds": candidate["factIds"], "evidenceIds": candidate["evidenceIds"]})
    return {"policyVersion": "analytical-reading-v1",
            "overview": {"text": overview, "factIds": overview_refs},
            "phases": phases, "takeaways": takeaways[:2]}
