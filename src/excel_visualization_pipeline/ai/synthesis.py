"""Evidence-backed relations and bounded, compositional narrative synthesis.

KPI values are never recomputed here. Predicates join existing analytical facts;
the language grammar is bound to each predicate, not to a canonical paragraph.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
import re
from typing import Any

from .reading import plain_text, reading_report
from .semantic import semantic_spec
from .report import attach_report, report_output

POLICY = "grounded-synthesis-v4"
MIN_TREND_PERIODS = 4
def metrics_of(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return snapshot.get("metrics") or [{
        "metricCode": snapshot["scope"]["metricCode"],
        "metricDisplayName": snapshot["scope"]["metricDisplayName"],
        **{key: snapshot[key] for key in ("facts", "series", "periodAnalytics", "quality")},
    }]


def build_synthesis(snapshot: dict[str, Any]) -> dict[str, Any]:
    metrics = metrics_of(snapshot)
    facts = {f["factId"]: f for f in snapshot["facts"]}
    candidates: list[dict[str, Any]] = []
    relation_facts: list[dict[str, Any]] = []

    def add(kind: str, codes: list[str], refs: list[str], anchors: list[dict[str, Any]],
            text: str, expressions: list[str], priority: int, partial: bool = False) -> None:
        refs = list(dict.fromkeys(refs))
        if not refs or not set(refs) <= facts.keys():
            return
        cid = f"insight-{len(candidates):02d}-{kind}"
        evidence = list(dict.fromkeys(e for ref in refs for e in facts[ref]["evidenceIds"]))
        fid = f"relation:{cid}"
        relation_facts.append({"factId": fid, "kind": "insight_relation", "value": kind,
                               "displayValue": kind, "unit": "enum", "policyVersion": POLICY,
                               "operandFactIds": refs, "evidenceIds": evidence})
        prefix = "Trong đoạn có dữ liệu liền nhau, " if partial else ""
        label = next((m["metricDisplayName"] for m in metrics if m["metricCode"] == codes[0]), "") if len(codes) == 1 else ""
        readable = plain_text(text, label)
        readable_expressions = [plain_text(expression, re.escape(label)).replace(". ", r"\. ") for expression in expressions]
        expressions = [*expressions, *readable_expressions, re.escape(readable)]
        text = readable
        # Every expression must express the supported relation. Arbitrary tails,
        # causal adjectives, dates, values or changing the metric cannot match.
        candidates.append({"candidateId": cid, "kind": kind, "metricCodes": codes,
                           "factIds": [fid, *refs], "evidenceIds": evidence,
                           "anchors": anchors, "scope": "contiguous_block" if partial else "selected_window",
                           "priority": priority, "fallbackText": prefix + text,
                           "expressions": [re.escape(prefix) + expression for expression in expressions]})

    def anchor(metric: dict[str, Any], point: dict[str, Any]) -> dict[str, Any]:
        return {"metricCode": metric["metricCode"], "metricDisplayName": metric["metricDisplayName"],
                **{key: point[key] for key in ("periodLabel", "displayValue", "factId", "evidenceId")}}

    for metric in metrics:
        series = metric["series"]
        stages = metric["periodAnalytics"].get("temporalStructure", {}).get("stages", [])
        if len(series) < 2 or not stages:
            continue
        code, label = metric["metricCode"], metric["metricDisplayName"]
        subject = re.escape(label) + r": "
        partial = metric["quality"]["validPeriodCount"] < metric["quality"]["expectedPeriodCount"]
        # Count the latest CONTIGUOUS block; separated observations cannot earn
        # trend language merely by contributing to the selected-window count.
        latest = [stages[-1]]
        for stage in reversed(stages[:-1]):
            if stage["endIndex"] != latest[0]["startIndex"]:
                break
            latest.insert(0, stage)
        start_index, end_index = latest[0]["startIndex"], latest[-1]["endIndex"]
        short = end_index - start_index + 1 < MIN_TREND_PERIODS
        if short:
            points = series[start_index:end_index + 1]
            if len(points) == 2:
                word = "tăng" if points[1]["value"] > points[0]["value"] else "giảm" if points[1]["value"] < points[0]["value"] else "giữ nguyên"
                text = f"{label}: kỳ sau {word} so với kỳ trước; đây là so sánh hai kỳ, chưa đủ để xác định xu hướng."
                kind = "period_comparison"
            else:
                words = [{"increasing": "tăng", "decreasing": "giảm", "unchanged": "giữ nguyên"}[s["direction"]] for s in latest]
                text = f"{label}: diễn biến quan sát được là {' rồi '.join(words)}; số kỳ còn ít, chưa xác định xu hướng."
                kind = "short_sequence"
            add(kind, [code], [p["factId"] for p in points],
                [anchor(metric, p) for p in points], text, [re.escape(text)], 10, partial)
            candidates[-1]["observedDirections"] = [word] if len(points) == 2 else words
            continue
        local: list[tuple[str, int, list[dict[str, Any]], str, list[str], list[int]]] = []
        for left, right in zip(stages, stages[1:]):
            if left["endIndex"] != right["startIndex"]:
                continue
            pivot = left["endIndex"]
            if left["direction"] == "increasing" and right["direction"] == "decreasing" and series[pivot]["value"] == max(p["value"] for p in series):
                plateau = next((s for s in stages if s["startIndex"] == right["endIndex"] and s["direction"] == "unchanged" and s["endIndex"] == len(series) - 1), None)
                if right["endIndex"] != len(series) - 1 and plateau is None:
                    continue
                ending = bool(plateau)
                tail = "; các kỳ cuối giữ nguyên" if ending else ""
                tail_pattern = r"; (?:các kỳ cuối giữ nguyên|cuối chuỗi đi ngang)" if ending else ""
                text = f"{label}: nhịp tăng lên đỉnh không được duy trì; sau đỉnh chỉ số giảm qua các kỳ{tail}."
                expressions = [subject + r"(?:nhịp tăng lên đỉnh không được duy trì|đà tăng tới đỉnh đã đảo chiều); (?:sau đỉnh chỉ số giảm qua các kỳ|chỉ số giảm sau khi đạt đỉnh)" + tail_pattern + r"\."]
                local.append(("peak_retreat", 90, [left, right, *([plateau] if plateau else [])], text, expressions, [left["startIndex"], pivot, (plateau or right)["endIndex"]]))
            if left["direction"] == "decreasing" and right["direction"] == "increasing" and series[pivot]["value"] == min(p["value"] for p in series):
                same_ends = series[0]["value"] == series[-1]["value"] and not partial and left["startIndex"] == 0 and right["endIndex"] == len(series) - 1
                kind = "endpoint_masks" if same_ends else "trough_recovery"
                tail = "; đầu và cuối bằng nhau không có nghĩa chuỗi đi ngang" if same_ends else ""
                pattern_tail = r"; (?:đầu và cuối bằng nhau không có nghĩa chuỗi đi ngang|endpoint bằng nhau che khuất hai giai đoạn trái chiều)" if same_ends else ""
                text = f"{label}: chuỗi giảm xuống đáy rồi tăng trở lại{tail}."
                expressions = [subject + r"(?:chuỗi giảm xuống đáy rồi tăng trở lại|nhịp giảm tới đáy được tiếp nối bằng một đoạn hồi phục)" + pattern_tail + r"\."]
                if right["endIndex"] == len(series) - 1:
                    local.append((kind, 100 if same_ends else 80, [left, right], text, expressions, [left["startIndex"], pivot, right["endIndex"]]))
        binary_cycle = not partial and len(series) >= 4 and len({p["value"] for p in series}) == 2 and all(s["transitionCount"] == 1 and s["direction"] != "unchanged" for s in stages)
        if binary_cycle:
            # Recurring two-level alternation does not establish a lasting
            # retreat/recovery. This is structural abstention, not magnitude.
            local = []
        if local:
            kind, priority, selected, text, expressions, indices = max(local, key=lambda item: (item[1], item[2][-1]["endIndex"]))
            ranked = metric["periodAnalytics"]["peak" if kind == "peak_retreat" else "lowest"]["factIds"]
            endpoint_refs = [f["factId"] for f in metric["facts"] if f["kind"] in {"previous", "current"}] if kind == "endpoint_masks" else []
            add(kind, [code], [*ranked, *endpoint_refs, *[ref for stage in selected for ref in stage["factIds"]]],
                [anchor(metric, series[i]) for i in dict.fromkeys(indices)], text, expressions, priority, partial)
        else:
            dirs = {s["direction"] for s in stages}
            selected = stages[-1:] if partial else stages
            if not partial and "decreasing" not in dirs and "increasing" in dirs:
                kind, text, pattern = "sustained_increase", "chỉ số đi lên qua các kỳ, không có nhịp giảm", r"(?:chỉ số đi lên qua các kỳ, không có nhịp giảm|các kỳ đi theo chiều tăng hoặc giữ nguyên, không có lần giảm)"
            elif not partial and "increasing" not in dirs and "decreasing" in dirs:
                kind, text, pattern = "sustained_decrease", "chỉ số đi xuống qua các kỳ, không có nhịp tăng", r"(?:chỉ số đi xuống qua các kỳ, không có nhịp tăng|các kỳ đi theo chiều giảm hoặc giữ nguyên, không có lần tăng)"
            elif dirs == {"unchanged"}:
                kind, text, pattern = "unchanged", "các kỳ liền nhau giữ nguyên cùng một mức", r"(?:các kỳ liền nhau giữ nguyên cùng một mức|không ghi nhận thay đổi giữa các kỳ liền nhau)"
            else:
                kind, text, pattern = "descriptive_only", "các kỳ được cung cấp có tăng và giảm; chưa có căn cứ về mức độ bất thường", r"(?:các kỳ được cung cấp có tăng và giảm|chỉ số tăng giảm giữa các kỳ được cung cấp); (?:chưa có căn cứ về mức độ bất thường|facts chưa hỗ trợ kết luận về mức độ bất thường)"
            # A missing window with no complete reversal gets a modest local description.
            if partial and dirs != {"unchanged"}:
                direction = selected[0]["direction"]
                word = {"increasing": "tăng", "decreasing": "giảm", "unchanged": "giữ nguyên"}[direction]
                kind, text, pattern = "local_description", f"đoạn cuối được quan sát có chiều {word}; không nối xu hướng qua kỳ thiếu", re.escape(f"đoạn cuối được quan sát có chiều {word}; không nối xu hướng qua kỳ thiếu")
            add(kind, [code], [ref for s in selected for ref in s["factIds"]],
                [anchor(metric, series[selected[0]["startIndex"]]), anchor(metric, series[selected[-1]["endIndex"]])],
                f"{label}: {text}.", [subject + pattern + r"\."], 40 if kind.startswith("sustained") else 10, partial)

    # Cross-metric claims use shared, full natural periods and the SAME eligible
    # numerator/denominator contributors, never independent endpoint direction.
    by_code = {m["metricCode"]: m for m in metrics}
    if set(by_code) == {"total", "error", "error_rate"}:
        maps = {code: {p["periodStart"]: p for p in m["series"]} for code, m in by_code.items()}
        blocks: list[list[dict[str, dict[str, Any]]]] = []
        grain = snapshot["window"]["groupBy"]
        for period in snapshot.get("comparisonBasis", {}).get("periods", []):
            start, end = date.fromisoformat(period["periodStart"]), date.fromisoformat(period["periodEnd"])
            full = grain == "day" or (grain == "week" and start.weekday() == 0 and (end-start).days == 6) or (grain == "month" and start.day == 1 and end.day == monthrange(end.year, end.month)[1])
            points = {code: mapping.get(period["periodStart"]) for code, mapping in maps.items()}
            eligible = full and all(p and p["periodEnd"] == period["periodEnd"] and p["observedDayCount"] == p["expectedDayCount"] for p in points.values())
            eligible = eligible and period["denominator"] > 0 and period["numerator"] >= 0
            eligible = eligible and points["total"]["value"] == period["denominator"] and points["error"]["value"] == period["numerator"]
            if not eligible:
                continue
            if not blocks or date.fromisoformat(blocks[-1][-1]["total"]["periodEnd"]) + timedelta(days=1) != start:
                blocks.append([])
            blocks[-1].append(points)
        for block in blocks:
            if len(block) < 2:
                continue
            total_peak = max(block, key=lambda p: (p["total"]["value"], p["total"]["periodStart"]))
            error_peak = max(block, key=lambda p: (p["error"]["value"], p["error"]["periodStart"]))
            # Extrema must match the engine's selected whole-window peak, including ties.
            unique_peaks = all(sum(p["value"] == by_code[code]["periodAnalytics"]["peak"]["value"] for p in by_code[code]["series"]) == 1 for code in ("total", "error"))
            if (len(block) >= MIN_TREND_PERIODS and unique_peaks and total_peak["total"]["periodStart"] == by_code["total"]["periodAnalytics"]["peak"]["periodStart"] and error_peak["error"]["periodStart"] == by_code["error"]["periodAnalytics"]["peak"]["periodStart"] and total_peak["total"]["periodStart"] != error_peak["error"]["periodStart"]):
                later = total_peak["total"]["periodStart"] > error_peak["error"]["periodStart"]
                relation = "muộn hơn" if later else "sớm hơn"
                text = f"Tổng số đạt đỉnh {relation} Báo sai/Lỗi; hai chỉ số không đạt mức cao nhất cùng kỳ."
                refs = [ref for code in ("total", "error") for ref in by_code[code]["periodAnalytics"]["peak"]["factIds"]]
                add("peak_offset", ["total", "error"], refs,
                    [anchor(by_code["total"], total_peak["total"]), anchor(by_code["error"], error_peak["error"])], text,
                    [rf"Tổng số (?:đạt đỉnh|đạt mức cao nhất) {relation} Báo sai/Lỗi; (?:hai chỉ số không đạt mức cao nhất cùng kỳ|thời điểm đạt đỉnh của hai chỉ số khác nhau)\."], 85, len(block) < len(by_code["total"]["series"]))
            run: list[dict[str, dict[str, Any]]] = []
            best: list[dict[str, dict[str, Any]]] = []
            for left, right in zip(block, block[1:]):
                qualifies = all(p["error"]["value"] > 0 for p in (left, right)) and right["total"]["value"] > left["total"]["value"] and right["error"]["value"] > left["error"]["value"] and right["error_rate"]["value"] < left["error_rate"]["value"]
                run = [*(run or [left]), right] if qualifies else []
                if len(run) > len(best):
                    best = run.copy()
            if best:
                refs = [p[code]["factId"] for p in best for code in by_code]
                context = "giữa hai kỳ" if len(best) == 2 else "trong cùng giai đoạn"
                text = f"Báo sai/Lỗi tăng về số lượng nhưng tỷ lệ báo sai giảm {context}; Tổng số tăng nhanh hơn Báo sai/Lỗi trong phép tính tỷ lệ."
                add("count_rate_contrast", list(by_code), refs,
                    [anchor(by_code[code], p[code]) for p in (best[0], best[-1]) for code in by_code], text,
                    [rf"(?:Báo sai/Lỗi tăng về số lượng nhưng tỷ lệ báo sai giảm|Số Báo sai/Lỗi tăng nhưng tỷ trọng trên Tổng số giảm) {context}; (?:Tổng số tăng nhanh hơn Báo sai/Lỗi trong phép tính tỷ lệ|chỉ nhìn số lỗi tuyệt đối chưa phản ánh đầy đủ diễn biến)\."], 95, len(best) < len(by_code["total"]["series"]))
                candidates[-1]["comparisonContext"] = context
            # Link numerator, denominator and rate by verified aligned movement,
            # not statistical correlation or endpoints across different phases.
            recipes = [
                ((0, 1, 1), "errors_up_same_volume", "Báo sai/Lỗi tăng khi Tổng số giữ nguyên; tỷ lệ báo sai cũng tăng", "với Tổng số không đổi, tỷ lệ báo sai tăng cùng số lỗi", 90),
                ((0, -1, -1), "errors_down_same_volume", "Báo sai/Lỗi giảm khi Tổng số giữ nguyên; tỷ lệ báo sai cũng giảm", "với Tổng số không đổi, tỷ lệ báo sai giảm cùng số lỗi", 90),
                ((1, -1, -1), "errors_down_volume_up", "Báo sai/Lỗi giảm trong khi Tổng số tăng; tỷ lệ báo sai cũng giảm", "số lỗi tuyệt đối và tỷ trọng đều giảm, không chỉ riêng tỷ lệ", 95),
                ((-1, -1, 1), "errors_down_share_up", "Báo sai/Lỗi giảm nhưng tỷ lệ báo sai tăng khi Tổng số giảm", "chỉ nhìn số lỗi giảm chưa phản ánh tỷ trọng lỗi tăng", 95),
                ((1, 1, 1), "errors_outpace_volume", "Báo sai/Lỗi và Tổng số cùng tăng, đồng thời tỷ lệ báo sai tăng", "số lỗi tăng nhanh hơn Tổng số trong phép tính tỷ lệ", 90),
                ((-1, -1, -1), "errors_fall_faster", "Báo sai/Lỗi và Tổng số cùng giảm, đồng thời tỷ lệ báo sai giảm", "số lỗi giảm nhanh hơn Tổng số trong phép tính tỷ lệ", 90),
                ((-1, 1, 1), "errors_up_volume_down", "Báo sai/Lỗi tăng trong khi Tổng số giảm; tỷ lệ báo sai cũng tăng", "số lỗi tuyệt đối và tỷ trọng đều tăng", 95),
                ((1, 0, -1), "unchanged_errors_share_down", "Báo sai/Lỗi giữ nguyên nhưng tỷ lệ báo sai giảm khi Tổng số tăng", "tỷ trọng thấp hơn không có nghĩa số lỗi đã giảm", 95),
                ((-1, 0, 1), "unchanged_errors_share_up", "Báo sai/Lỗi giữ nguyên nhưng tỷ lệ báo sai tăng khi Tổng số giảm", "tỷ trọng cao hơn không có nghĩa số lỗi đã tăng", 95),
                ((1, 1, 0), "volume_up_same_share", "Báo sai/Lỗi và Tổng số cùng tăng nhưng tỷ lệ báo sai giữ nguyên", "số lỗi tăng không đồng nghĩa tỷ trọng lỗi tăng", 70),
                ((-1, -1, 0), "volume_down_same_share", "Báo sai/Lỗi và Tổng số cùng giảm nhưng tỷ lệ báo sai giữ nguyên", "số lỗi giảm không đồng nghĩa tỷ trọng lỗi giảm", 70),
            ]
            for signature, kind, observation, interpretation, priority in recipes:
                run, best = [], []
                for left, right in zip(block, block[1:]):
                    directions = tuple((right[code]["value"] > left[code]["value"]) - (right[code]["value"] < left[code]["value"]) for code in ("total", "error", "error_rate"))
                    qualifies = directions == signature and all(p["error"]["value"] > 0 for p in (left, right))
                    run = [*(run or [left]), right] if qualifies else []
                    if len(run) > len(best):
                        best = run.copy()
                if not best:
                    continue
                context = "giữa hai kỳ" if len(best) == 2 else "trong cùng giai đoạn"
                text = f"{observation} {context}; {interpretation}."
                add(kind, list(by_code), [p[code]["factId"] for p in best for code in by_code],
                    [anchor(by_code[code], p[code]) for p in (best[0], best[-1]) for code in by_code],
                    text, [re.escape(text)], min(priority, 75) if len(best) == 2 and len(by_code["total"]["series"]) >= MIN_TREND_PERIODS else priority, len(best) < len(by_code["total"]["series"]))
                candidates[-1]["relationshipDescription"] = {"observation": observation, "interpretation": interpretation, "comparisonContext": context}
    candidates.sort(key=lambda c: (-c["priority"], {"error": 0, "error_rate": 1, "total": 2}.get(c["metricCodes"][0], 3)))
    primary = next((c for c in candidates if len(c["metricCodes"]) == 1), None)
    # A linked count/volume/rate explanation is more useful than merely
    # reporting that peaks occurred on different dates. This is selection
    # guidance only; no KPI calculation or source fact changes.
    cross = next((c for c in candidates if c.get("relationshipDescription")
                  and c["kind"] not in {"errors_up_same_volume", "errors_down_same_volume"}), None)
    cross = cross or next((c for c in candidates if len(c["metricCodes"]) > 1 and c["kind"] not in {"errors_up_same_volume", "errors_down_same_volume"}), None)
    # A joint relation replaces a weak single-metric template, rather than
    # repeating the same operands before the actual insight.
    weak_primary = primary and primary["kind"] in {"period_comparison", "short_sequence", "descriptive_only", "local_description"}
    selected = [cross] if cross and weak_primary else [c for c in (primary, cross) if c]
    if not selected and candidates:
        selected = candidates[:1]
    checks = [{"checkId": f"check-{c['candidateId']}", "candidateId": c["candidateId"],
               "text": ("Đối chiếu hai thời điểm đạt đỉnh để kiểm tra sự lệch kỳ giữa Tổng số và Báo sai/Lỗi." if c["kind"] == "peak_offset" else "Đối chiếu số lượng và tỷ lệ trong cùng giai đoạn để kiểm tra hai cách đọc dữ liệu." if c["kind"] == "count_rate_contrast" else "Đối chiếu đoạn lên đỉnh và đoạn giảm sau đỉnh để kiểm tra nhịp tăng không được duy trì." if c["kind"] == "peak_retreat" else "Đối chiếu đoạn xuống đáy và đoạn tăng trở lại để kiểm tra sự đảo chiều." if c["kind"] in {"trough_recovery", "endpoint_masks"} else "Đối chiếu các kỳ của đoạn được nêu trước khi tìm thêm bối cảnh nghiệp vụ."),
               "factIds": c["factIds"], "evidenceIds": list(dict.fromkeys(a["evidenceId"] for a in c["anchors"]))} for c in selected]
    for check, c in zip(checks, selected):
        if c["kind"] == "peak_offset":
            check["text"] = f"Đối chiếu Tổng số tại {c['anchors'][0]['periodLabel']} và Báo sai/Lỗi tại {c['anchors'][1]['periodLabel']} để kiểm tra sự lệch kỳ đạt đỉnh."
        elif c["kind"] == "peak_retreat":
            check["text"] = f"Kiểm tra đoạn {c['anchors'][0]['periodLabel']}–{c['anchors'][-1]['periodLabel']}, quanh đỉnh {c['anchors'][1]['periodLabel']}: đối chiếu nhịp tăng và diễn biến giảm sau đỉnh."
        elif c["kind"] == "count_rate_contrast":
            check["text"] = f"Đối chiếu số lượng và tỷ lệ từ {c['anchors'][0]['periodLabel']} đến {c['anchors'][-1]['periodLabel']} để kiểm tra hai cách đọc dữ liệu."
        elif c.get("relationshipDescription"):
            check["text"] = f"Đối chiếu cả Tổng số, Báo sai/Lỗi và tỷ lệ báo sai từ {c['anchors'][0]['periodLabel']} đến {c['anchors'][-1]['periodLabel']}; kiểm tra số lỗi và lượng ghi nhận trong cùng phạm vi trước khi diễn giải tỷ trọng."
    plan = {"policyVersion": POLICY, "minimumTrendPeriods": MIN_TREND_PERIODS,
            "candidates": candidates, "selectedCandidateIds": [c["candidateId"] for c in selected],
            "facts": relation_facts, "inspectionChecks": checks,
            "limitations": grouped_limitations(metrics),
            "reading": reading_report(metrics, candidates, selected)}
    attach_report(plan, metrics)
    return plan


def grouped_limitations(metrics: list[dict[str, Any]]) -> list[str]:
    groups: dict[str, list[str]] = {}
    for metric in metrics:
        for text in metric["quality"].get("limitations", []):
            groups.setdefault(text, []).append(metric["metricDisplayName"])
    result = [text if len(labels) == len(metrics) else f"{' / '.join(labels)}: {text}" for text, labels in groups.items()]
    keys = [{p["periodStart"] for p in metric["series"]} for metric in metrics]
    expected = {metric["quality"]["expectedPeriodCount"] for metric in metrics}
    if keys and all(key == keys[0] for key in keys) and len(expected) == 1:
        total = next(iter(expected))
        missing = total - len(keys[0])
        if missing > 0:
            result = [text for text in result if "Có kỳ không tạo được giá trị hợp lệ" not in text]
            result.insert(0, f"Có {missing}/{total} kỳ thiếu dữ liệu hợp lệ. Không nối xu hướng qua khoảng trống và không coi kỳ thiếu là 0.")
    return result


def synthesis_fallback(plan: dict[str, Any], reason: str | None = None) -> dict[str, Any]:
    selected = [c for cid in plan["selectedCandidateIds"] for c in plan["candidates"] if c["candidateId"] == cid]
    return {"mode": "deterministic", "schemaVersion": "ai-narrative-v3",
            **({"report": report_output(plan, [])} if plan.get("reportPlan") else {}),
            "summary": {"text": " ".join(c["fallbackText"] for c in selected) or "Chưa đủ các kỳ liền nhau để tạo insight có căn cứ.",
                        "candidateIds": [c["candidateId"] for c in selected], "factIds": list(dict.fromkeys(f for c in selected for f in c["factIds"])), "claimType": "descriptive"},
            "insights": [], "limitations": [*([reason] if reason else []), *plan["limitations"]], "suggestedChecks": []}


def provider_plan(snapshot: dict[str, Any]) -> dict[str, Any]:
    plan = snapshot["synthesis"]
    # Ranking is guidance, not a required selection/order. Bound input size.
    ids_by_section = plan["reportPlan"]["sections"]
    # Bound generation, not report coverage. Extra gap-isolated phases remain
    # visible with Engine source labels. Include first/last and extrema phases
    # before filling the budget; never silently take only the window beginning.
    ids_by_section = {key: list(ids) for key, ids in ids_by_section.items()}
    phase_ids = ids_by_section["phases"]
    if len(phase_ids) > 8:
        lookup = {c["candidateId"]: c for c in plan["candidates"]}
        chosen = {phase_ids[0], phase_ids[-1]}
        covered = set()
        for cid in phase_ids:
            highlights = {(h["metricCode"], h["role"]) for h in lookup[cid].get("phaseExtrema", [])}
            if highlights - covered and len(chosen) < 8:
                chosen.add(cid)
                covered.update(highlights)
        for cid in reversed(phase_ids):
            if len(chosen) >= 8:
                break
            chosen.add(cid)
        ids_by_section["phases"] = [cid for cid in phase_ids if cid in chosen]
    report_ids = [cid for ids in ids_by_section.values() for cid in ids]
    candidates = [c for cid in report_ids for c in plan["candidates"] if c["candidateId"] == cid]
    ids = {ref for c in candidates for ref in c["factIds"]}
    return {"schemaVersion": "ai-insight-provider-input-v5", "analysisId": snapshot["analysisId"],
            "window": {key: snapshot["window"][key] for key in ("start", "end", "groupBy")},
            "reportPlan": {**plan["reportPlan"], "sections": ids_by_section,
                           "generatedPhaseCount": len(ids_by_section["phases"]),
                           "engineOnlyPhaseCount": len(phase_ids) - len(ids_by_section["phases"])},
            "selectedCandidateIds": plan["selectedCandidateIds"],
            "insightCandidates": [{**{key: value for key, value in c.items() if key not in {"fallbackText", "expressions", "priority", "factIds"}},
                                   "factIds": c["factIds"][:1], "supportingFactIds": c["factIds"][1:],
                                   "semanticSpec": semantic_spec(c, snapshot)} for c in candidates],
            "facts": [f for f in snapshot["facts"] if f["factId"] in ids], "limitations": plan["limitations"]}
