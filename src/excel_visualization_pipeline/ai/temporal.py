"""Chronological stages backed by existing period and transition facts."""
from datetime import date, timedelta
from typing import Any


def temporal_structure(series: list[dict[str, Any]], facts: list[dict[str, Any]], *, incomplete: bool = False) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    words = {"increasing": "tăng", "decreasing": "giảm", "unchanged": "giữ nguyên"}
    lookup = {fact["factId"]: fact for fact in facts}
    for index in range(1, len(series)):
        previous, current = series[index - 1], series[index]
        change = current["change"]
        if date.fromisoformat(previous["periodEnd"]) + timedelta(days=1) != date.fromisoformat(current["periodStart"]):
            gaps.append({"startIndex": index - 1, "afterPeriodLabel": previous["periodLabel"], "beforePeriodLabel": current["periodLabel"],
                         "text": f"Thiếu kỳ giữa {previous['periodLabel']} và {current['periodLabel']}; không xác định diễn biến trong đoạn này.",
                         "factIds": [previous["factId"], current["factId"]],
                         "evidenceIds": [previous["evidenceId"], current["evidenceId"]]})
            continue
        direction = change["direction"]
        if stages and stages[-1]["endIndex"] == index - 1 and stages[-1]["direction"] == direction:
            stage = stages[-1]
            stage["endIndex"] = index
            stage["factIds"].extend([current["factId"], *change["factIds"]])
            stage["evidenceIds"].append(current["evidenceId"])
        else:
            stage = {"startIndex": index - 1, "endIndex": index, "direction": direction,
                     "factIds": [previous["factId"], current["factId"], *change["factIds"]],
                     "evidenceIds": [previous["evidenceId"], current["evidenceId"]]}
            stages.append(stage)
    for stage in stages:
        start, end = series[stage["startIndex"]], series[stage["endIndex"]]
        stage.update(startPeriodStart=start["periodStart"], endPeriodStart=end["periodStart"],
                     startPeriodLabel=start["periodLabel"], endPeriodLabel=end["periodLabel"],
                     transitionCount=stage["endIndex"] - stage["startIndex"],
                     displayValues=[item["displayValue"] for item in series[stage["startIndex"]:stage["endIndex"] + 1]])
        stage["factIds"] = list(dict.fromkeys(stage["factIds"]))
        run = " liên tiếp" if stage["transitionCount"] > 1 and stage["direction"] != "unchanged" else ""
        values = f"từ {start['displayValue']} lên {end['displayValue']}" if stage["direction"] == "increasing" else f"từ {start['displayValue']} xuống {end['displayValue']}"
        if stage["direction"] == "unchanged":
            values = f"ở {end['displayValue']}"
        stage["text"] = f"{start['periodLabel']}–{end['periodLabel']}: {words[stage['direction']]}{run} {values}."
        if stage["direction"] == "increasing" and end["value"] == max(item["value"] for item in series):
            stage["text"] = stage["text"].rstrip('.') + ", đạt mức cao nhất trong khoảng."
        if stage["direction"] == "decreasing" and end["value"] == min(item["value"] for item in series):
            stage["text"] = stage["text"].rstrip('.') + ", chạm mức thấp nhất trong khoảng."
    # A plateau is a stage in its own right, not an inferred immediate reversal.
    for left, right in zip(stages, stages[1:]):
        if left["endIndex"] != right["startIndex"] or {left["direction"], right["direction"]} != {"increasing", "decreasing"}:
            continue
        point = series[left["endIndex"]]
        turns.append({"periodLabel": point["periodLabel"], "displayValue": point["displayValue"],
                      "text": f"Tại {point['periodLabel']}, chỉ số chuyển từ {words[left['direction']]} sang {words[right['direction']]} ở mức {point['displayValue']}.",
                      "factIds": list(dict.fromkeys([*left["factIds"], *right["factIds"]])),
                      "evidenceIds": list(dict.fromkeys([*left["evidenceIds"], *right["evidenceIds"]]))})
    directions = {stage["direction"] for stage in stages}
    if gaps or incomplete:
        lead = "Chuỗi có kỳ thiếu; chỉ mô tả các đoạn có dữ liệu liền nhau."
    elif {"increasing", "decreasing"} <= directions:
        lead = "Chỉ số tăng giảm qua nhiều giai đoạn, không duy trì một chiều trong toàn khoảng."
    elif "increasing" in directions:
        lead = "Chỉ số đi lên trong toàn khoảng, không có nhịp giảm" + (" nhưng có kỳ giữ nguyên." if "unchanged" in directions else ".")
    elif "decreasing" in directions:
        lead = "Chỉ số đi xuống trong toàn khoảng, không có nhịp tăng" + (" nhưng có kỳ giữ nguyên." if "unchanged" in directions else ".")
    elif stages:
        lead = "Chỉ số giữ nguyên qua toàn bộ các kỳ."
    else:
        lead = "Chưa có hai kỳ liền nhau để mô tả diễn biến."
    # Detailed stages remain complete; complex windows get a bounded executive answer.
    selected = stages if len(stages) <= 6 else stages[-1:]
    detail = " ".join(item["text"] for item in sorted([*selected, *(gaps if len(stages) <= 6 else [])], key=lambda item: item.get("startIndex", 0)))
    if len(stages) > 6:
        detail = "Các giai đoạn được trình bày đầy đủ bên dưới. Đoạn liền nhau cuối được ghi nhận: " + detail
    refs = list(dict.fromkeys(ref for stage in stages for ref in stage["factIds"]))
    refs.extend(ref for gap in gaps for ref in gap["factIds"] if ref not in refs)
    evidence = list(dict.fromkeys(e for ref in refs for e in lookup[ref]["evidenceIds"]))
    overview_refs = []
    summary_refs = []
    summary_text = f"{lead} {detail}".strip()
    if refs:
        overview_refs = ["fact-temporal-structure"]
        facts.append({"factId": overview_refs[0], "kind": "temporal_structure", "value": lead,
                      "displayValue": lead, "unit": "enum", "evidenceIds": evidence,
                      "supportingFactIds": refs.copy(), "policyVersion": "chronological-stages-v1"})
        summary_refs = ["fact-temporal-story"]
        facts.append({"factId": summary_refs[0], "kind": "temporal_narrative", "value": summary_text,
                      "displayValue": summary_text, "unit": "text", "evidenceIds": evidence,
                      "supportingFactIds": refs.copy(), "policyVersion": "chronological-stages-v1"})
    return {"policyVersion": "chronological-stages-v1", "stages": stages, "turningPoints": turns,
            "gaps": gaps, "overviewText": lead, "overviewFactIds": overview_refs,
            "summaryText": summary_text, "summaryFactIds": summary_refs, "factIds": refs, "evidenceIds": evidence}
