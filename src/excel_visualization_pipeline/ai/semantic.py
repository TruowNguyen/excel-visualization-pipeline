"""Bounded Vietnamese semantic grounding, independent of canonical sentences.

This is NOT a general natural-language entailment model. Reject source errors
and recognized contradictions; incomplete language parsing is a quality warning,
not proof of fabrication. No second provider call or model arithmetic.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any

POLICY = "semantic-grounding-v9"
DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{4}|\d{1,2}/\d{1,2})\b")
PERIOD_TOKEN = r"(?:" + DATE.pattern.replace(r"\b", "") + r"\s*[–—]\s*" + DATE.pattern.replace(r"\b", "") + r"|" + DATE.pattern.replace(r"\b", "") + r")"
SCOPE_RANGE = re.compile(r"(?:từ|đến)\s+(?:(?:ngày|kỳ|tuần|tháng|quý)\s+)?(?P<start>" + PERIOD_TOKEN + r")\s+(?:đến|sang|tới)\s+(?:(?:ngày|kỳ|tuần|tháng|quý)\s+)?(?P<end>" + PERIOD_TOKEN + r")")
COVERAGE = re.compile(r"\b\d+/\d+\s+kỳ\b")
NUMBER = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)*(?!\w)")
LIMITATION = re.compile(r"^(?:chưa đủ|không đủ|chưa có|không có) (?:dữ liệu|căn cứ|thông tin|số kỳ)(?: .*)? (?:để |cho |về )?(?:đánh giá|kết luận|xác định)(?: về)? (?:chất lượng|nguyên nhân|xu hướng|mức độ bất thường)[.!]?$", re.I)
ALIASES = {"total": ["tổng số", "lượng ghi nhận", "trung bình số lượng"], "error": ["báo sai/lỗi", "số báo sai/lỗi", "số lỗi", "lỗi"],
           "error_rate": ["% báo sai", "tỷ lệ báo sai", "tỷ lệ", "tỷ trọng trên tổng số", "tỷ trọng lỗi", "tỷ trọng"]}
SIGNATURES = {
    "count_rate_contrast": (1, 1, -1), "errors_down_volume_up": (1, -1, -1),
    "errors_down_share_up": (-1, -1, 1), "errors_outpace_volume": (1, 1, 1),
    "errors_fall_faster": (-1, -1, -1), "errors_up_volume_down": (-1, 1, 1),
    "unchanged_errors_share_down": (1, 0, -1), "unchanged_errors_share_up": (-1, 0, 1),
    "volume_up_same_share": (1, 1, 0), "volume_down_same_share": (-1, -1, 0),
    "errors_up_same_volume": (0, 1, 1), "errors_down_same_volume": (0, -1, -1),
}
REPORT_TYPES = {"window_overview", "phase_description", "window_extrema", "metric_pair_movement"}
CLAIM_TYPES = frozenset(SIGNATURES) | {"peak_retreat", "trough_recovery", "endpoint_masks", "sustained_increase", "sustained_decrease", "unchanged", "period_comparison", "short_sequence", "descriptive_only", "local_description", "peak_offset"} | REPORT_TYPES
MOTION = re.compile(r"giữ nguyên|giữ (?:ở mức|tại|mức)|không đổi|không có (?:lần|nhịp) (?:tăng|giảm)|không (?:tăng|giảm)|đi ngang|tăng|giảm|đi lên|đi xuống|hồi phục", re.I)
# Only incomplete wording checks are soft. Never downgrade contradictory
# directions, source scope, units, dates or numerical roles to warnings.
WORDING_WARNINGS = frozenset({"relation_not_expressed", "ambiguous_metric_subject", "unquantified_magnitude"})
UNSUPPORTED_BUSINESS = re.compile(r"\b(doanh thu|lợi nhuận|chi phí|khách hàng|nhân sự|quy trình|năng suất)\b", re.I)


def _denominator_explanation(sentence: str, candidate: dict[str, Any]) -> bool:
    """Allow a narrowly grounded ratio explanation, not business causality."""
    sentence = re.sub(r'\s+trong phép tính tỷ lệ[.!]?$', '', sentence)
    if candidate["kind"] not in SIGNATURES or UNSUPPORTED_BUSINESS.search(sentence):
        return False
    # With the numerator held constant, the engine's aligned ratio relation
    # proves the denominator effect. Direction checks below still apply.
    markers = list(re.finditer(r"\b(?:do|vì|khiến|gây ra|dẫn đến)\b", sentence))
    if len(markers) != 1 or "nguyên nhân" in sentence:
        return False
    marker = markers[0]
    left = {code for _, _, code in _subjects(sentence[:marker.start()], candidate)}
    right = {code for _, _, code in _subjects(sentence[marker.end():], candidate)}
    # The cause clause must name the denominator, and the result the rate.
    # The fixed numerator is established by the engine relation; it need not
    # be repeated in this particular sentence.
    if marker.group() in {"do", "vì"}:
        cause, effect = right, left
    else:
        cause, effect = left, right
    constant_restatement = (candidate['kind'] in {'unchanged_errors_share_up', 'unchanged_errors_share_down'}
                            and marker.group() in {'khiến', 'dẫn đến'}
                            and bool(re.search(r'cùng số lỗi chiếm (?:tỷ lệ|tỷ trọng) (?:cao|thấp) hơn', sentence[:marker.start()])))
    if not constant_restatement and (not ({'total', 'error'} & cause) or "error_rate" not in effect or "error_rate" in cause):
        return False
    expected = dict(zip(("total", "error", "error_rate"), SIGNATURES[candidate["kind"]]))
    observed: dict[str, set[int]] = {}
    for motion in MOTION.finditer(sentence):
        if re.search(r'không (?:có nghĩa|đồng nghĩa).*$', sentence[max(0, motion.start()-60):motion.start()]):
            continue
        for code in _motion_subjects(sentence, motion.start(), candidate):
            observed.setdefault(code, set()).add(_direction(motion.group()))
    relative_comparison = ({'total', 'error'} <= cause and bool(re.search(r'(?:tăng|giảm) (?:nhanh|chậm) hơn', sentence)))
    required = {'error_rate'} if constant_restatement else {'error_rate', 'error'} if relative_comparison else {'error_rate', *cause}
    return (required <= observed.keys()
            and all(values == {expected[code]} for code, values in observed.items()))


def semantic_spec(candidate: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Expose engine truth, not a required sentence or regex."""
    metrics = snapshot.get("metrics") or [{"metricCode": snapshot["scope"]["metricCode"], "series": snapshot.get("series", [])}]
    evidence = {p["evidenceId"]: p for m in metrics for p in m["series"]}
    periods = [{"metricCode": a["metricCode"], "factId": a["factId"],
                "periodStart": evidence[a["evidenceId"]]["periodStart"],
                "periodEnd": evidence[a["evidenceId"]]["periodEnd"],
                "displayValue": a["displayValue"]} for a in candidate["anchors"] if a["evidenceId"] in evidence]
    return {"claimType": candidate["kind"], "metricCodes": candidate["metricCodes"],
            "scope": candidate["scope"], "groupBy": snapshot["window"]["groupBy"],
            "anchors": periods, "directionSignature": SIGNATURES.get(candidate["kind"]),
            "observedDirections": candidate.get("observedDirections", []),
            **{key: candidate[key] for key in ("allowedDirections", "extrema", "phaseExtrema", "hasGaps") if key in candidate}}


def _decimal(raw: str) -> Decimal | None:
    try:
        # Canonical engine formatting uses comma grouping, dot decimal.
        if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw):
            return Decimal(raw.replace(",", ""))
        return Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None


def _matches_value(fact: dict[str, Any], value: Decimal | None) -> bool:
    """Accept engine-authored representations, never a fuzzy tolerance."""
    if value is None or not isinstance(fact.get("value"), (int, float)) or isinstance(fact["value"], bool):
        return False
    if value == Decimal(str(fact["value"])):
        return True
    display = str(fact.get("displayValue", "")).strip()
    match = re.fullmatch(r"(" + NUMBER.pattern + r")\s*(?:%|pp|điểm phần trăm)?", display)
    return bool(match and _decimal(match.group(1)) == value)


def _sentence_start(text: str, position: int) -> int:
    boundaries = list(re.finditer(r"\.(?!\d)|;|\n", text[:position]))
    return boundaries[-1].end() if boundaries else 0


def _subject_at(text: str, position: int, candidate: dict[str, Any]) -> str | None:
    # Resolve explicit names within this sentence. Never inherit the subject
    # from a different sentence and silently turn uncertainty into a conflict.
    start = _sentence_start(text, position)
    subjects = [code for left, _, code in _subjects(text, candidate) if start <= left < position]
    return subjects[-1] if subjects else candidate["metricCodes"][0] if len(candidate["metricCodes"]) == 1 else None


def _motion_subjects(text: str, position: int, candidate: dict[str, Any]) -> list[str]:
    """Bind a motion to its named subject or coordinated subject phrase."""
    start = _sentence_start(text, position)
    subjects = [item for item in _subjects(text, candidate) if start <= item[0] < position]
    if not subjects:
        subject = _subject_at(text, position, candidate)
        return [subject] if subject else []
    codes = [subjects[-1][2]]
    if re.fullmatch(r"\s*(?:(?:cùng|đều|cũng)\s*)?", text[subjects[-1][1]:position]):
        for left, right in zip(reversed(subjects[:-1]), reversed(subjects[1:])):
            if not re.fullmatch(r"\s*(?:và|,)\s*", text[left[1]:right[0]]):
                break
            codes.append(left[2])
    return list(dict.fromkeys(codes))


def _motion_clause(text: str, position: int) -> str:
    boundaries = list(re.finditer(r"[,;:]|\b(?:và|rồi|sau đó|nhưng)\b", text))
    start = max((m.end() for m in boundaries if m.end() <= position), default=0)
    end = min((m.start() for m in boundaries if m.start() > position), default=len(text))
    return text[start:end]


def _subjects(text: str, candidate: dict[str, Any]) -> list[tuple[int, int, str]]:
    labels = {code: list(ALIASES.get(code, [])) for code in ("total", "error", "error_rate")}
    for anchor in candidate["anchors"]:
        labels[anchor["metricCode"]].append(anchor["metricDisplayName"].lower())
    found: list[tuple[int, int, str]] = []
    for code, aliases in labels.items():
        for alias in aliases:
            for match in re.finditer(re.escape(alias), text.lower()):
                found.append((match.start(), match.end(), code))
    chosen: list[tuple[int, int, str]] = []
    for item in sorted(found, key=lambda x: (x[0], -(x[1] - x[0]))):
        if not any(item[0] < end and item[1] > start for start, end, _ in chosen):
            chosen.append(item)
    return chosen


def _direction(word: str) -> int:
    if word.startswith("không có") or word == "không tăng":
        return -1 if "tăng" in word else 1
    if word == "không giảm":
        return 1
    if word.startswith("giữ ") or word in {"không đổi", "đi ngang"}:
        return 0
    return -1 if word in {"giảm", "đi xuống"} else 1


def validate_numbers_and_dates(text: str, candidate: dict[str, Any], snapshot: dict[str, Any], refs: list[str]) -> tuple[list[str], dict[str, set[str]]]:
    """Layer 3: typed engine values/display values and explicit period bindings."""
    errors: list[str] = []
    facts = {f["factId"]: f for f in snapshot["facts"]}
    evidence = {e["evidenceId"]: e for e in snapshot["evidence"]}
    metrics = snapshot.get("metrics") or [{"metricCode": snapshot["scope"]["metricCode"], "series": snapshot.get("series", [])}]
    # Periods come from engine points, independently of source target shape.
    evidence = {**evidence, **{p["evidenceId"]: p for m in metrics for p in m["series"]}}
    supporting = [facts[ref] for ref in refs if ref in facts]
    evs = [evidence[eid] for f in supporting for eid in f.get("evidenceIds", []) if eid in evidence]
    # A yearless day is allowed only when unambiguous within cited evidence.
    dates: dict[str, set[str]] = {}
    for ev in evs:
        for key in ("periodStart", "periodEnd"):
            raw = ev.get(key)
            if not raw:
                continue
            parsed = date.fromisoformat(raw)
            for spelling in (raw, parsed.strftime("%d/%m/%Y"), parsed.strftime("%d/%m")):
                dates.setdefault(spelling, set()).add(raw)
        if re.fullmatch(r"\d{1,2}/\d{4}", str(ev.get("periodLabel", ""))):
            dates.setdefault(ev["periodLabel"], set()).add(ev["periodStart"])
        named_period = re.search(r"(?:tuần|tháng|quý|q)\s*(\d{1,2}/\d{4})", str(ev.get("periodLabel", "")), re.I)
        if named_period:
            dates.setdefault(named_period.group(1), set()).add(ev["periodStart"])
    body = text.lower()
    for fraction in reversed(list(COVERAGE.finditer(body))):
        # Engine-authored coverage text is a fraction, never a calendar date.
        # No arbitrary fraction is excused by this representation rule.
        if (re.match(r"\s+thiếu\b", body[fraction.end():])
                and any(fraction.group() + " thiếu" in limitation.lower() for limitation in snapshot.get("synthesis", {}).get("limitations", []))):
            body = body[:fraction.start()] + " " * (fraction.end() - fraction.start()) + body[fraction.end():]
    for match in DATE.finditer(body):
        if len(dates.get(match.group(), set())) != 1:
            errors.append("unsupported_date_mention")
    numerical_body = DATE.sub(lambda m: " " * len(m.group()), body)
    subjects = _subjects(body, candidate)
    if any(code not in candidate["metricCodes"] for _, _, code in subjects):
        errors.append("metric_scope_mismatch")
    def metric_at(position: int) -> str | None:
        named = _subject_at(body, position, candidate)
        if named:
            return named
        # A value mentioned before this date can resolve an omitted subject
        # only when its typed cited facts belong to exactly one KPI.
        numbers = list(NUMBER.finditer(numerical_body[_sentence_start(body, position):position]))
        if not numbers:
            return None
        number = numbers[-1]
        offset = _sentence_start(body, position) + number.end()
        wanted_percent = numerical_body[offset:].lstrip().startswith("%")
        owners = {fact_metrics.get(f["factId"]) for f in supporting if _matches_value(f, _decimal(number.group()))
                  and (not wanted_percent or f.get("unit") == "percent")}
        owners.discard(None)
        return next(iter(owners)) if len(owners) == 1 else None
    # Range dates describe scope, not a point. In particular the end date of
    # "from A to B, KPI rises from X ..." must not be attached to X.
    range_dates = {m.start() + d.start() for m in SCOPE_RANGE.finditer(body)
        for d in DATE.finditer(m.group())}
    # Numeric membership is typed and metric-bound, not a global bag of numbers.
    series = metrics
    point_metrics = {p["factId"]: m["metricCode"] for m in series for p in m["series"]}
    fact_metrics = {f["factId"]: m["metricCode"] for m in metrics for f in m.get("facts", snapshot["facts"] if len(metrics) == 1 else [])}
    for match in NUMBER.finditer(numerical_body):
        value = _decimal(match.group())
        code = metric_at(match.start())
        unit_tail = numerical_body[match.end():match.end() + 24].strip()
        if code is None:
            owners = {fact_metrics.get(f["factId"]) for f in supporting if _matches_value(f, value)
                      and (not unit_tail.startswith("%") or f.get("unit") == "percent")}
            owners.discard(None)
            if len(owners) == 1:
                code = next(iter(owners))
        wanted = "percentage_point" if unit_tail.startswith(("điểm phần trăm", "pp")) else "percent" if unit_tail.startswith(("%", "phần trăm")) or code == "error_rate" else None
        adjacent_date = re.match(r"\s*(?:%|lượt)?\s*(?:vào|ngày|tại|ở|trong)\s+(?:(?:ngày|kỳ|tuần|tháng)\s+)?" + DATE.pattern.replace(r"\b", ""), body[match.end():])
        period_count = bool(re.match(r"(?:kỳ|ngày|tuần|tháng)\b", unit_tail)) and not adjacent_date
        eligible = [f for f in supporting if isinstance(f.get("value"), (int, float)) and not isinstance(f["value"], bool)
                    and (fact_metrics.get(f["factId"], point_metrics.get(f["factId"], code)) == code)
                    and (wanted is None or f.get("unit") == wanted)
                    and (not period_count or f.get("kind") in {"period_count", "historical_period_count", "period_sequence_count"})]
        count_word = unit_tail.split()[0].strip(".,;:!?") if unit_tail else ""
        group_word = {"day": "ngày", "week": "tuần", "month": "tháng", "quarter": "quý"}[snapshot["window"]["groupBy"]]
        anchored_count = len({a["evidenceId"] for a in candidate["anchors"] if a["metricCode"] == code})
        scope_count = period_count and count_word in {"kỳ", group_word} and value == anchored_count
        if not scope_count and not any(_matches_value(f, value) for f in eligible):
            errors.append("unsupported_numeric_mention")
        prefix = numerical_body[max(0, match.start() - 45):match.start()]
        explicit_delta = bool(re.search(r"chênh lệch\s*$", prefix))
        if explicit_delta and not any(f.get('kind') == 'period_change' and _matches_value(f, value) for f in eligible):
            errors.append('numeric_role_mismatch')
        if re.search(r"(?:tăng|giảm)\s*$", prefix):
            change_kind = "period_relative_change" if wanted == "percent" else "period_change"
            if not any(f.get("kind") in {change_kind, "relative_change" if wanted == "percent" else "absolute_change"}
                       and _matches_value(f, value) for f in eligible):
                errors.append("numeric_role_mismatch")
        aliases = "|".join(re.escape(alias) for alias in ALIASES.get(code, []))
        role_tail = r"(?:\s+của\s+(?:" + (aliases or r"(?!)") + r"))?\s*(?:là|ở mức)?\s*$"
        if re.search(r"(?:cao nhất|đỉnh)" + role_tail, prefix):
            if not any(f.get("kind") in {"peak", "period_peak", "period_highest_value"} and _matches_value(f, value) for f in eligible):
                errors.append("numeric_role_mismatch")
        if re.search(r"(?:thấp nhất|đáy)" + role_tail, prefix):
            if not any(f.get("kind") in {"lowest", "period_lowest", "period_lowest_value"} and _matches_value(f, value) for f in eligible):
                errors.append("numeric_role_mismatch")
        # A date and KPI value in one clause must refer to the SAME point.
        suffix = body[match.end():]
        adjacent = re.match(r"\s*(?:%|lượt)?\s*(?:vào|ngày|tại|ở|trong)\s+(?:(?:ngày|kỳ|tuần|tháng)\s+)?(" + DATE.pattern.replace(r"\b", "") + r")", suffix)
        cited_dates = [adjacent.group(1)] if adjacent else []
        previous_dates = [d for d in DATE.finditer(body[:match.start()])
                          if d.start() not in range_dates and d.start() >= _sentence_start(body, match.start())]
        if not cited_dates and previous_dates:
            previous_date = previous_dates[-1]
            between = body[previous_date.end():match.start()]
            if (_subject_at(body, previous_date.start(), candidate) == code
                    and len(between) < 90 and not NUMBER.search(between) and not re.search(r"rồi|sau đó|trước khi|xuống|lên|đến|sang|tới|(?:tăng|giảm)\s+(?:liên tiếp|liên tục|qua)|\. |;", between)):
                cited_dates = [previous_date.group()]
        if len(cited_dates) == 1 and value is not None and not explicit_delta:
            raw = next(iter(dates.get(cited_dates[0], set())), None)
            points = [p for m in series if m["metricCode"] == code for p in m["series"] if p["factId"] in refs]
            if not any(_matches_value(p, value) and raw in {p["periodStart"], p["periodEnd"]} for p in points):
                errors.append("numeric_period_mismatch")
            local_motion = re.search(r"(giảm xuống|tăng lên|giữ nguyên ở)\s*$", prefix)
            if local_motion:
                ordered = next((m["series"] for m in metrics if m["metricCode"] == code), [])
                point_index = next((i for i, p in enumerate(ordered) if raw in {p["periodStart"], p["periodEnd"]}), None)
                if point_index is None or point_index == 0 or ordered[point_index - 1].get("value") is None:
                    errors.append("numeric_role_mismatch")
                else:
                    actual = ((ordered[point_index]["value"] > ordered[point_index - 1]["value"])
                              - (ordered[point_index]["value"] < ordered[point_index - 1]["value"]))
                    expected = {"giảm xuống": -1, "tăng lên": 1, "giữ nguyên ở": 0}[local_motion.group(1)]
                    if actual != expected:
                        errors.append("direction_conflict")
        if not cited_dates and re.search(r"(?:giảm xuống|tăng lên|giữ nguyên ở)\s*$", prefix) and code:
            anchors = [a for a in candidate["anchors"] if a["metricCode"] == code]
            if candidate["kind"] in {"phase_description", "window_overview"}:
                points = [p for m in metrics if m["metricCode"] == code for p in m["series"] if p["factId"] in {a["factId"] for a in anchors}]
                direction = -1 if re.search(r"giảm xuống\s*$", prefix) else 1 if re.search(r"tăng lên\s*$", prefix) else 0
                if not any(_matches_value(b, value) and ((b["value"] > a["value"]) - (b["value"] < a["value"])) == direction for a, b in zip(points, points[1:])):
                    errors.append("numeric_role_mismatch")
                continue
            terminal = next((p for m in metrics if m["metricCode"] == code for p in m["series"]
                             if anchors and p["factId"] == anchors[-1]["factId"]), None)
            if terminal is None or not _matches_value(terminal, value):
                errors.append("numeric_role_mismatch")
    for match in DATE.finditer(body):
        before = body[max(0, match.start() - 90):match.start()]
        role = "period_highest_value" if re.search(r"(?:cao nhất|đỉnh)(?:\s+" + NUMBER.pattern + r")?\s+(?:vào\s+)?(?:ngày\s+)?$", before) else "period_lowest_value" if re.search(r"(?:thấp nhất|đáy)(?:\s+" + NUMBER.pattern + r")?\s+(?:vào\s+)?(?:ngày\s+)?$", before) else None
        # Check every date in an extrema sentence, including tied dates joined
        # with 'và'. Merely existing elsewhere in the phase is not sufficient.
        if candidate.get("phaseExtrema"):
            clause = re.split(r"\.(?!\d)|;", body[:match.start()])[-1]
            mentions = list(re.finditer(r"cao nhất|đỉnh|thấp nhất|đáy", clause))
            masked = DATE.sub(lambda m: " " * len(m.group()), clause)
            numbers = list(NUMBER.finditer(masked[mentions[-1].end():])) if mentions else []
            tail = masked[mentions[-1].end() + numbers[-1].end():] if numbers else ""
            role_to_value = masked[mentions[-1].end():mentions[-1].end() + numbers[-1].start()] if numbers else ""
            is_extremum_date = (bool(mentions) and len(numbers) <= 1
                                and not re.search(r"rồi|sau đó|trước khi|xuống|lên|tăng|giảm", role_to_value + tail))
            if is_extremum_date:
                highlight_role = "peak" if mentions[-1].group() in {"cao nhất", "đỉnh"} else "lowest"
                code = metric_at(match.start())
                allowed = {day for h in candidate["phaseExtrema"] if h["metricCode"] == code and h["role"] == highlight_role for period in h.get("periods", [{"start": d, "end": d} for d in h["dates"]]) for day in (period["start"], period["end"])}
                if not dates.get(match.group(), set()) <= allowed:
                    errors.append("numeric_period_mismatch")
        if role:
            code = metric_at(match.start())
            matched = [f for f in supporting if f.get("kind") == role and fact_metrics.get(f["factId"], code) == code]
            raw = next(iter(dates.get(match.group(), set())), None)
            ranked_points = [p for m in metrics if m["metricCode"] == code for p in m["series"]
                             if p["factId"] in refs and any(p["value"] == f["value"] for f in matched)]
            if not any(raw in {p["periodStart"], p["periodEnd"]} for p in ranked_points):
                errors.append("numeric_period_mismatch")
    return list(dict.fromkeys(errors)), dates


def validate_semantics(text: str, candidate: dict[str, Any], snapshot: dict[str, Any], refs: list[str], dates: dict[str, set[str]]) -> list[str]:
    """Layer 4: metric-bound directions, chronology and relation predicates."""
    errors: list[str] = []
    metrics = snapshot.get("metrics") or [{"metricCode": snapshot["scope"]["metricCode"], "series": snapshot.get("series", [])}]
    evidence = {p["evidenceId"]: p for m in metrics for p in m["series"]}
    body = text.lower()
    # Remove limitations sentence-by-sentence; negation never excuses another
    # clause asserting a cause, prediction, quality or unsupported magnitude.
    # A full stop after a date/value still ends a sentence; only a decimal
    # point followed by a digit must be preserved.
    sentences = [s.strip() for s in re.split(r"\.(?!\d)|;", body) if s.strip()]
    analytical = []
    for sentence in sentences:
        if LIMITATION.fullmatch(sentence) and not re.search(r"\b(nhưng|và|đã|sẽ|do|vì)\b", sentence):
            continue
        analytical.append(sentence)
        if re.search(r"\b(dự báo|sẽ|chất lượng|tốt hơn|xấu hơn|nghiêm trọng)\b", sentence):
            errors.append("unsupported_meaning")
        data_gap = (candidate["kind"] == "window_overview" and not _subjects(sentence, candidate)
                    and bool(re.search(r"(?:dữ liệu|chuỗi|thông tin).*(?:do|vì) thiếu (?:kỳ|dữ liệu)", sentence))
                    and not MOTION.search(sentence)
                    and any(m.get("quality", snapshot.get("quality", {})).get("validPeriodCount", 0)
                            < m.get("quality", snapshot.get("quality", {})).get("expectedPeriodCount", 0) for m in metrics))
        if re.search(r"\b(nguyên nhân|gây ra|khiến|do|vì|dẫn đến)\b", sentence) and not (_denominator_explanation(sentence, candidate) or data_gap):
            errors.append("unsupported_meaning")
        if UNSUPPORTED_BUSINESS.search(sentence):
            errors.append("unsupported_business_claim")
        if re.search(r"\b(mạnh|nhẹ|đáng kể)\b", sentence):
            errors.append("unquantified_magnitude")
    prose = ". ".join(analytical)
    # A real endpoint pair does not prove monotonic movement through its interior.
    # Bound this check to explicitly stated from/to movements; it is not general NLI.
    for movement in re.finditer(r"(?:tăng|giảm)\s+(?:(?:liên tiếp|liên tục)\s+)?từ\s+(" + NUMBER.pattern + r")\s+(?:lên|xuống|đến)\s+(" + NUMBER.pattern + r")", prose):
        code = _subject_at(prose, movement.start(), candidate)
        rows = [p for m in metrics if m["metricCode"] == code for p in m.get("series", []) if p["factId"] in refs]
        left, right = (_decimal(movement.group(i)) for i in (1, 2))
        intervals = [(i, j) for i, a in enumerate(rows) for j, b in enumerate(rows) if i < j
                     and _decimal(str(a["value"])) == left and _decimal(str(b["value"])) == right]
        sign = 1 if movement.group().startswith("tăng") else -1
        strict = bool(re.search(r'liên tiếp|liên tục', movement.group()))
        if intervals and not any(all((rows[k + 1]["value"] - rows[k]["value"]) * sign > 0 if strict else (rows[k + 1]["value"] - rows[k]["value"]) * sign >= 0 for k in range(i, j)) for i, j in intervals):
            errors.append("chronology_mismatch")
    # A single whole-sequence continuous assertion cannot hide a plateau.
    # Local multi-stage stories remain covered by their own operands above.
    for movement in re.finditer(r'(tăng|giảm)\s+(?:liên tiếp|liên tục)', prose):
        code = _subject_at(prose, movement.start(), candidate)
        same_subject = [m for m in MOTION.finditer(prose) if _subject_at(prose, m.start(), candidate) == code]
        if candidate['kind'] not in REPORT_TYPES or code is None or len(same_subject) != 1:
            continue
        if re.search(r'ở đầu|lúc đầu|ở cuối|trước khi|sau khi|sau đó|rồi', prose):
            continue
        anchor_ids = {a['factId'] for a in candidate['anchors']}
        rows = [p for m in metrics if m['metricCode'] == code for p in m.get('series', []) if p['factId'] in anchor_ids]
        # Dependency closure can include tied extrema outside the local stage.
        # A dated local run must not inherit those extra periods.
        sentence_start = _sentence_start(prose, movement.start())
        stop = re.search(r'\.(?!\d)|;', prose[movement.end():])
        sentence_end = movement.end() + stop.start() if stop else len(prose)
        mentioned = {raw for match in DATE.finditer(prose[sentence_start:sentence_end]) for raw in dates.get(match.group(), set())}
        if len(mentioned) >= 2:
            rows = [p for p in rows if min(mentioned) <= p['periodStart'] <= max(mentioned)]
        sign = 1 if movement.group(1) == 'tăng' else -1
        if len(rows) > 1 and any((b['value'] - a['value']) * sign <= 0 for a, b in zip(rows, rows[1:])):
            errors.append('chronology_mismatch')
    if not prose:
        return [*errors, "missing_supported_claim"]
    if not _subjects(prose, candidate):
        errors.append("missing_supported_claim")
    bounds = semantic_spec(candidate, snapshot)["anchors"]
    explicit_dates = {raw for match in DATE.finditer(prose) for raw in dates.get(match.group(), set())}
    for match in DATE.finditer(prose):
        if re.fullmatch(r"\d{1,2}/\d{4}", match.group()):
            explicit_dates.update(a["periodEnd"] for a in bounds if a["periodStart"] in dates.get(match.group(), set()))
    anchored_scope = bool(bounds) and {min(a["periodStart"] for a in bounds), max(a["periodEnd"] for a in bounds)} <= explicit_dates
    if candidate["scope"] == "contiguous_block" and not anchored_scope and not re.search(r"đoạn có dữ liệu|đoạn .*liền nhau|từ \d|giai đoạn từ \d", prose):
        errors.append("period_scope_mismatch")
    if candidate["scope"] == "contiguous_block" and re.search(r"thời gian (?:đã |đang )?chọn|toàn bộ (?:chuỗi|thời gian|khoảng)", prose):
        errors.append("period_scope_mismatch")
    range_mention = SCOPE_RANGE.search(prose)
    if range_mention:
        bounds = semantic_spec(candidate, snapshot)["anchors"]
        starts = [a["periodStart"] for a in bounds]
        ends = [a["periodEnd"] for a in bounds]
        def boundary(token: str, ending: bool) -> set[str]:
            parts = list(DATE.finditer(token))
            if not parts:
                return set()
            spelling = parts[-1 if ending else 0].group()
            resolved = dates.get(spelling, set())
            if ending and re.fullmatch(r"\d{1,2}/\d{4}", spelling):
                return {a["periodEnd"] for a in bounds if a["periodStart"] in resolved}
            return resolved
        stated_start = boundary(range_mention.group("start"), False)
        stated_end = boundary(range_mention.group("end"), True)
        # A window overview may locate a sub-stage before describing the rest.
        # A local phase must still name its exact captured boundaries.
        valid_range = (bool(starts) and len(stated_start) == len(stated_end) == 1
                       and min(starts) <= min(stated_start) <= max(stated_end) <= max(ends))
        if candidate["scope"] == "contiguous_block":
            valid_range = valid_range and stated_start == {min(starts)} and stated_end == {max(ends)}
        if not valid_range:
            errors.append("period_scope_mismatch")
    kind = candidate["kind"]
    period_points = {p["periodStart"] for m in metrics for p in m["series"] if p["factId"] in refs}
    if kind in REPORT_TYPES:
        if len({a["periodStart"] for a in bounds}) < 4:
            without_limit = re.sub(r"(?:chưa đủ|không đủ)(?:\s+để)?\s+(?:(?:kết luận|xác lập|xác định)\s+)?xu hướng|(?:chưa|không)\s+(?:xác định\s+)?xu hướng", "", prose)
            if re.search(r"xu hướng|qua các kỳ", without_limit) or (not candidate.get("phaseExtrema") and re.search(r"cao nhất|thấp nhất|đỉnh|đáy", without_limit)):
                errors.append("insufficient_trend_periods")
        if kind in {"phase_description", "metric_pair_movement"}:
            for motion in MOTION.finditer(prose):
                if re.search(r"không (?:có nghĩa|đồng nghĩa).*$", prose[max(0, motion.start()-60):motion.start()]):
                    continue
                codes = _motion_subjects(prose, motion.start(), candidate)
                if not codes:
                    errors.append("ambiguous_metric_subject")
                for code in codes:
                    if (kind == 'metric_pair_movement' and motion.group() in {'không tăng', 'không giảm'}
                            and candidate['allowedDirections'].get(code) == [0]):
                        continue  # Constant facts prove either bounded negation.
                    if _direction(motion.group()) not in candidate["allowedDirections"].get(code, []):
                        errors.append("direction_conflict")
        if kind == "window_extrema":
            if not re.search(r"cao nhất|đỉnh", prose) or not re.search(r"thấp nhất|đáy", prose):
                errors.append("relation_not_expressed")
        return list(dict.fromkeys(errors))
    if kind in {"period_comparison", "short_sequence"} or kind in SIGNATURES and len(period_points) < 4:
        without_limit = re.sub(r"(?:chưa đủ để|chưa|không) (?:xác định )?xu hướng", "", prose)
        if re.search(r"xu hướng|qua các kỳ|cao nhất|thấp nhất|đỉnh|đáy", without_limit):
            errors.append("insufficient_trend_periods")
    peak = bool(re.search(r"đỉnh|cao nhất", prose))
    trough = bool(re.search(r"đáy|thấp nhất", prose))
    down_after = bool(re.search(r"(?:sau.*(?:đỉnh|cao nhất).*giảm|giảm.*sau.*(?:đỉnh|cao nhất)|(?:đỉnh|cao nhất).*(?:rồi|sau đó) (?:đảo chiều )?giảm)", prose))
    up_after = bool(re.search(r"(?:sau.*(?:đáy|thấp nhất).*tăng|(?:đáy|thấp nhất).*tăng trở lại|(?:đáy|thấp nhất).*hồi phục)", prose))
    if kind == "peak_retreat" and not (peak and down_after):
        errors.append("relation_not_expressed")
    if kind in {"trough_recovery", "endpoint_masks"} and not (trough and up_after):
        errors.append("relation_not_expressed")
    if re.search(r"không (?:đảo chiều|giảm sau|tăng trở lại)", prose) or ("không đạt" in prose and "cùng kỳ" not in prose):
        errors.append("direction_conflict")
    if peak and kind not in {"peak_retreat", "peak_offset"} or trough and kind not in {"trough_recovery", "endpoint_masks"}:
        errors.append("unsupported_extremum")
    if kind == "peak_offset":
        anchors = candidate["anchors"]
        later = evidence[anchors[0]["evidenceId"]]["periodStart"] > evidence[anchors[1]["evidenceId"]]["periodStart"]
        ordered_wording = ("muộn hơn" if later else "sớm hơn") in prose
        dated_comparison = anchored_scope and bool(re.search(r"không (?:trùng|.*cùng kỳ)|thời điểm.*khác nhau|trong khi", prose))
        if not peak or not (ordered_wording or dated_comparison):
            errors.append("relation_not_expressed")
        if ("sớm hơn" if later else "muộn hơn") in prose:
            errors.append("direction_conflict")
        if re.search(r"(?:đỉnh|cao nhất).*(?:cùng ngày|cùng kỳ|trùng nhau)", prose) and not re.search(r"không (?:trùng|.*cùng)", prose):
            errors.append("direction_conflict")
    elif kind in SIGNATURES:
        observed: dict[str, set[int]] = {}
        for motion in MOTION.finditer(prose):
            codes = _motion_subjects(prose, motion.start(), candidate)
            if not codes:
                errors.append("ambiguous_metric_subject")
                continue
            # Explicit negated inference is not an assertion of this direction.
            prefix = prose[max(0, motion.start() - 50):motion.start()]
            if re.search(r"không (?:có nghĩa|đồng nghĩa).*$", prefix):
                continue
            for code in codes:
                observed.setdefault(code, set()).add(_direction(motion.group()))
        expected = dict(zip(("total", "error", "error_rate"), SIGNATURES[kind]))
        if any(values != {expected[code]} for code, values in observed.items()):
            errors.append("direction_conflict")
        if not {"error", "error_rate"} <= observed.keys():
            errors.append("relation_not_expressed")
        local_subjects = _subjects(prose, candidate)
        for comparison in re.finditer(r"(?:tăng|giảm) (?:nhanh|chậm) hơn", prose):
            before = [code for start, _, code in local_subjects if start < comparison.start()]
            after = [code for start, _, code in local_subjects if start >= comparison.end()]
            faster = "total" if kind in {"count_rate_contrast", "errors_down_share_up"} else "error" if kind in {"errors_outpace_volume", "errors_fall_faster"} else None
            expected_subject = faster if "nhanh" in comparison.group() else ({"total", "error"} - {faster}).pop() if faster else None
            if not before or not after or before[-1] != expected_subject or {before[-1], after[0]} != {"total", "error"}:
                errors.append("unsupported_relative_change")
    else:
        motions = [(m, _direction(m.group())) for m in MOTION.finditer(prose)]
        if not motions:
            errors.append("relation_not_expressed")
        if kind in {"sustained_increase", "sustained_decrease", "unchanged", "period_comparison", "short_sequence"}:
            expected = {"sustained_increase": [1], "sustained_decrease": [-1], "unchanged": [0]}.get(kind)
            expected = expected or [{"tăng": 1, "giảm": -1, "giữ nguyên": 0}[w] for w in candidate.get("observedDirections", [])]
            dirs = [direction for _, direction in motions]
            compressed = [d for i, d in enumerate(dirs) if not i or d != dirs[i-1]]
            if kind == "short_sequence" and compressed != expected or kind != "short_sequence" and any(d not in [*expected, *([0] if kind.startswith("sustained") else [])] for d in dirs):
                errors.append("direction_conflict")
        if kind == "peak_retreat" and re.search(r"(?:sau (?:đỉnh|khi đạt mức cao nhất).*tăng|tăng sau (?:khi đạt )?(?:đỉnh|mức cao nhất)|trước đỉnh.*giảm)", prose):
            errors.append("direction_conflict")
        if kind in {"trough_recovery", "endpoint_masks"} and re.search(r"sau (?:đáy|khi đạt mức thấp nhất).*giảm", prose):
            errors.append("direction_conflict")
        if kind in {"peak_retreat", "trough_recovery", "endpoint_masks"}:
            last_anchor = candidate["anchors"][-1]
            matching = next(m["series"] for m in metrics if m["metricCode"] == last_anchor["metricCode"])
            end = next(i for i, p in enumerate(matching) if p["factId"] == last_anchor["factId"])
            ending_direction = (matching[end]["value"] > matching[end-1]["value"]) - (matching[end]["value"] < matching[end-1]["value"])
            for sentence in analytical:
                for motion in MOTION.finditer(sentence):
                    if re.search(r"không (?:có nghĩa|đồng nghĩa).*$", sentence[:motion.start()]):
                        continue
                    direction = _direction(motion.group())
                    if "cuối" in _motion_clause(sentence, motion.start()) and direction != ending_direction:
                        errors.append("direction_conflict")
                    if direction == 0 and ending_direction != 0:
                        errors.append("direction_conflict")
                    peak_position = re.search(r"đỉnh|cao nhất", sentence)
                    increasing_before_peak = peak_position is not None and motion.start() < peak_position.start()
                    if kind == "peak_retreat" and direction == 1 and not increasing_before_peak and not re.search(r"nhịp tăng|đà tăng|tăng (?:lên|tới)|sau khi tăng từ|trước", sentence):
                        errors.append("direction_conflict")
                    if kind != "peak_retreat" and direction == -1 and not re.search(r"giảm (?:xuống|tới)|trước", sentence):
                        errors.append("direction_conflict")
    return list(dict.fromkeys(errors))


def validate_text(text: str, candidate: dict[str, Any], snapshot: dict[str, Any], refs: list[str]) -> tuple[list[str], list[str]]:
    # Q3/2026 is a canonical quarter label, not the number 2026. Normalize its
    # spelling for parsing only; preserve the original model wording for display.
    text = re.sub(r"\bQ([1-4])/(\d{4})\b", r"quý \1/\2", text, flags=re.I)
    numerical_errors, dates = validate_numbers_and_dates(text, candidate, snapshot, refs)
    semantic_errors = validate_semantics(text, candidate, snapshot, refs, dates)
    return (list(dict.fromkeys([*numerical_errors, *(code for code in semantic_errors if code not in WORDING_WARNINGS)])),
            [code for code in semantic_errors if code in WORDING_WARNINGS])
