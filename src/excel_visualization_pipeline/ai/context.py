"""Context-aware composition over canonical per-entity facts.

No subtree rollup and no chart arithmetic. One bounded provider request; every
entity remains in the receipt and its Engine report remains available.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from importlib.resources import files
import json
from typing import Any
from uuid import uuid4

import pandas as pd

from .analytics import AnalyticsEngine, TrendPoint, TrendStrategy, METRICS
from .evidence import EvidenceBuilder
from .llm import ProviderError
from .overview import build_overview
from .report import report_output, quantitative_evidence
from .synthesis import build_synthesis, provider_plan
from .validation import _load_json

PROMPT_VERSION = "context-insight-v5"
MAX_PROVIDER_CANDIDATES = 12
MAX_PROVIDER_BYTES = 100_000
MAX_ENGINE_CELLS = 20_000


def check_context_budget(context: dict, members: list[str]) -> None:
    calculators = 2 if context['calculation'] == 'both' else 1
    metrics = (3 if context['view'] == 'overview' else 2) if context.get('metricCode', 'all') == 'all' else 1
    count = len(context.get('periods', [])) if context['view'] == 'statistics' else len(pd.date_range(context['start'], context['end']))
    if count * max(1, len(members)) * metrics * calculators > MAX_ENGINE_CELLS:
        raise ValueError('Phạm vi quá lớn để phân tích trong một lần. Hãy giảm số kỳ hoặc số vấn đề; chưa có vấn đề nào bị cắt khỏi phạm vi.')


def resolve_members(entities: pd.DataFrame, parent: str, selection: str, ids: list[str]) -> list[str]:
    if parent not in set(entities.entity_id):
        raise ValueError("Nội dung theo dõi không thuộc dự án đã chọn.")
    if selection == "node":
        if ids:
            raise ValueError("Phạm vi một nội dung không nhận danh sách vấn đề.")
        return [parent]
    children = entities[entities.parent_entity_id.eq(parent)].entity_id.astype(str).tolist()
    if selection == "all":
        if ids:
            raise ValueError("Phạm vi tất cả do máy chủ xác định, không nhận danh sách thay thế.")
        return children
    chosen = list(dict.fromkeys(ids))
    if not chosen:
        raise ValueError("Hãy chọn ít nhất một vấn đề để phân tích.")
    if not set(chosen) <= set(children):
        raise ValueError("Các vấn đề phải là nội dung con trực tiếp trong nhóm đã chọn.")
    return chosen


def statistics_computation(frame: pd.DataFrame, *, metric_code: str, calculation: str,
                           group_by: str, start: date, end: date, periods: list[dict],
                           targets: dict[tuple[str, str, str], dict], rows: pd.DataFrame) -> tuple[Any, list[dict]]:
    label = METRICS[metric_code]["label"]
    column = "period_sum" if calculation == "sum" else "average_per_day"
    selected = frame[frame.metric_normalized.eq(label)] if not frame.empty else frame
    points, evidence = [], []
    unit = next(iter(rows.effective_unit.dropna()), "giá trị")
    if calculation == "average_per_day":
        unit = f"{unit}/ngày"
    for row in (selected.sort_values("period_start").itertuples(index=False) if not selected.empty else []):
        value = getattr(row, column)
        if value is None or pd.isna(value):
            continue
        target = targets.get((calculation, label, row.period_label))
        if not target:
            raise ValueError("Giá trị thống kê chưa có bằng chứng nguồn để phân tích.")
        pid = f"ev-period-{len(points):03d}"
        first, last = pd.Timestamp(row.period_start).date(), pd.Timestamp(row.period_end).date()
        source = rows[pd.to_datetime(rows.date).between(pd.Timestamp(first), pd.Timestamp(last))]
        points.append(TrendPoint(first, last, row.period_label, float(value), source,
                                 int(row.eligible_day_count), int(row.calendar_day_count), pid,
                                 bool(row.inferred_zero)))
        evidence.append({"evidenceId": pid, "period": "series", "periodIndex": len(points) - 1,
                         "periodStart": first.isoformat(), "periodEnd": last.isoformat(),
                         "periodLabel": row.period_label, "observedDate": last.isoformat(), "target": target,
                         "calculation": calculation, "eligibleDayCount": int(row.eligible_day_count),
                         "coverageSourceEntityRef": str(row.coverage_source_entity_id)})
    name = f"{label} trung bình/ngày" if calculation == 'average_per_day' else label
    computation = TrendStrategy().from_points(points, metric_code=metric_code, unit=str(unit),
                       group_by=group_by, start=start, end=end, expected_periods=len(periods),
                       aggregation_rule="period_sum" if calculation == "sum" else "sum_divided_by_eligible_days", label=name)
    return computation, evidence


def metric_payload(computation, evidence: list[dict], prefix: str, service) -> dict:
    return service._prefix_analysis_ids({
        "metricCode": computation.metric_code, "metricDisplayName": computation.metric_display_name,
        "status": computation.status, "unit": computation.unit, "aggregationRule": computation.aggregation_rule,
        "facts": list(computation.facts), "series": list(computation.series),
        "periodAnalytics": computation.period_analytics, "historicalContext": computation.historical_context,
        "quality": computation.quality, "evidence": evidence}, prefix)


def build_issue(metrics: list[dict], *, analysis_id: str, entity: dict, calculation: str,
                project: str, window: dict, comparison_basis: dict | None = None) -> dict:
    snapshot = {"analysisId": analysis_id, "schemaVersion": "ai-overview-v2",
                "scope": {"project": project, "entityRef": entity["entity_id"],
                          "entityLabel": entity["entity_label"], "metricCode": "all"},
                "window": window, "metrics": metrics,
                "facts": [f for m in metrics for f in m["facts"]],
                "evidence": [e for m in metrics for e in m["evidence"]],
                "quality": {"validPeriodCount": max((m["quality"]["validPeriodCount"] for m in metrics), default=0),
                            "expectedPeriodCount": max((m["quality"]["expectedPeriodCount"] for m in metrics), default=0)}}
    if comparison_basis is not None:
        snapshot['comparisonBasis'] = comparison_basis
    snapshot["synthesis"] = build_synthesis(snapshot)
    snapshot["facts"].extend(snapshot["synthesis"]["facts"])
    replacements = {f["factId"]: f"{entity['entity_id']}:{calculation}:{f['factId']}" for f in snapshot["synthesis"]["facts"]}
    def namespace(value):
        if isinstance(value, dict):
            return {k: namespace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [namespace(v) for v in value]
        return replacements.get(value, value) if isinstance(value, str) else value
    snapshot = namespace(snapshot)
    return {"entityRef": entity["entity_id"], "entityLabel": entity["entity_label"],
            "calculation": calculation, "metrics": snapshot["metrics"], "snapshot": snapshot,
            "report": report_output(snapshot["synthesis"], [])}


def cross_issue_reading(issues: list[dict]) -> list[dict]:
    """Group aligned adjacent movements, not all O(n²) entity pairs or correlations."""
    groups: dict[tuple, dict[str, list[dict]]] = {}
    for issue in issues:
        for metric in issue["metrics"]:
            if metric["metricCode"] == "error_rate":
                continue
            for left, right in zip(metric["series"], metric["series"][1:]):
                if date.fromisoformat(left["periodEnd"]) + timedelta(days=1) != date.fromisoformat(right["periodStart"]):
                    continue
                # Unequal calendar length makes sum-based activity comparison unsafe.
                if issue["calculation"] == "sum" and ((date.fromisoformat(left["periodEnd"]) - date.fromisoformat(left["periodStart"])) != (date.fromisoformat(right["periodEnd"]) - date.fromisoformat(right["periodStart"]))):
                    continue
                key = (issue["calculation"], metric["metricCode"], left["periodStart"], right["periodStart"])
                direction = "tăng" if right["value"] > left["value"] else "giảm" if right["value"] < left["value"] else "giữ nguyên"
                groups.setdefault(key, {}).setdefault(direction, []).append({"entityRef": issue["entityRef"],
                    "label": issue["entityLabel"], "factIds": [left["factId"], right["factId"]],
                    "evidenceIds": [left["evidenceId"], right["evidenceId"]], "left": left, "right": right})
    results = []
    for (calculation, metric, _, _), directions in sorted(groups.items()):
        members = [m for rows in directions.values() for m in rows]
        if len({m["entityRef"] for m in members}) < 2:
            continue
        first = members[0]
        wording = " / ".join(f"{', '.join(m['label'] for m in rows)} {direction}" for direction, rows in directions.items())
        meaning = ("Các vấn đề diễn biến khác nhau; một nhận định tăng hoặc giảm chung sẽ che mất sự khác biệt."
                   if len(directions) > 1 else "Các vấn đề thay đổi cùng chiều trong hai kỳ này; điều đó chưa chứng minh chúng tác động đến nhau.")
        text = (f"{first['left']['periodLabel']} → {first['right']['periodLabel']}: "
                f"{METRICS[metric]['label']} ({'tổng trong kỳ' if calculation == 'sum' else 'trung bình/ngày'}) của {wording}. {meaning}")
        results.append({"text": text, "source": "deterministic", "calculation": calculation,
                        "metricCode": metric, "factIds": [f for m in members for f in m["factIds"]],
                        "evidenceIds": [e for m in members for e in m["evidenceIds"]],
                        "start": first["left"]["periodStart"], "end": first["right"]["periodEnd"],
                        "leftPeriodStart": first["left"]["periodStart"], "rightPeriodStart": first["right"]["periodStart"],
                        "startLabel": first["left"]["periodLabel"], "endLabel": first["right"]["periodLabel"],
                        "directions": {direction: [{"entityRef": m["entityRef"], "label": m["label"]} for m in rows] for direction, rows in directions.items()},
                        "differentDirections": len(directions) > 1})
    return results


def cross_issue_phases(readings: list[dict]) -> list[dict]:
    """Join only adjacent transitions with identical membership and directions.

    No endpoint proxy, no crossing gaps/calculations, no unit magnitude ranking.
    Every intermediate period remains in the dependency/evidence union.
    """
    groups: dict[tuple, list[dict]] = {}
    for reading in readings:
        signature = tuple(sorted((direction, tuple(sorted(m['entityRef'] for m in rows)))
                                 for direction, rows in reading['directions'].items()))
        groups.setdefault((reading['calculation'], reading['metricCode'], signature), []).append(reading)
    phases = []
    for rows in groups.values():
        for row in sorted(rows, key=lambda r: r['start']):
            previous = phases[-1] if phases else None
            if (previous and previous['_signature'] == (row['calculation'], row['metricCode'], row['directions'])
                    and previous['rightPeriodStart'] == row['leftPeriodStart']):
                previous.update(end=row['end'], endLabel=row['endLabel'], rightPeriodStart=row['rightPeriodStart'])
                previous['transitionCount'] += 1
                for key in ('factIds', 'evidenceIds'):
                    previous[key] = list(dict.fromkeys([*previous[key], *row[key]]))
            else:
                phases.append({**deepcopy(row), 'transitionCount': 1,
                               '_signature': (row['calculation'], row['metricCode'], row['directions'])})
    for phase in phases:
        phase.pop('_signature')
        metric = 'Số lỗi' if phase['metricCode'] == 'error' else 'Tổng số'
        if phase['calculation'] == 'average_per_day':
            metric += ' trung bình/ngày'
        else:
            metric += ' trong kỳ'
        clauses = []
        for direction, members in phase['directions'].items():
            labels = ', '.join(m['label'] for m in members[:2])
            if len(members) > 2:
                labels += f" và {len(members) - 2} vấn đề khác"
            clauses.append(f"{labels} {direction}")
        basis = f"Từ {phase['startLabel']} đến {phase['endLabel']}"
        meaning = ('Các vấn đề không thay đổi giống nhau. Một nhận định tăng hoặc giảm chung sẽ che mất sự khác biệt.'
                   if phase['differentDirections'] else
                   'Các vấn đề giữ nguyên ở các kỳ được đối chiếu.' if set(phase['directions']) == {'giữ nguyên'} else
                   'Đây là diễn biến cùng chiều trong giai đoạn này, không phải bằng chứng vấn đề này gây ra thay đổi ở vấn đề khác.')
        phase['text'] = f"{basis}, {metric} của {'; '.join(clauses)}. {meaning}"
    return sorted(phases, key=lambda r: (r['start'], r['calculation'], r['metricCode']))


def select_context_candidates(candidates: list[dict]) -> list[dict]:
    """Balance whole-window story, important stages and supported KPI relations."""
    buckets = {section: [c for c in candidates if c['section'] == section]
               for section in ('overview', 'phases', 'relationships')}
    buckets['overview'].sort(key=lambda c: not c.get('leadOverview', False))
    buckets['phases'].sort(key=lambda c: (not bool(c.get('phaseExtrema')), c['candidateId'].split(':', 1)[1], c['issueIndex']))
    selected = []
    # Cycles reserve phase/relationship space even for large all-issue scopes.
    while any(buckets.values()) and len(selected) < MAX_PROVIDER_CANDIDATES:
        for section in ('overview', 'phases', 'relationships'):
            if buckets[section] and len(selected) < MAX_PROVIDER_CANDIDATES:
                selected.append(buckets[section].pop(0))
    return selected


def cross_issue_landmark(issues: list[dict]) -> list[dict]:
    """Compare observed peak TIMING, never sizes or inferred causal influence."""
    buckets: dict[tuple, list[tuple[dict, dict, list[dict]]]] = {}
    for issue in issues:
        for metric in issue['metrics']:
            series = metric['series']
            ranked = metric['periodAnalytics'].get('peak')
            if metric['metricCode'] == 'error_rate' or len(series) < 4 or not ranked:
                continue
            ranked_point = next((p for p in series if p['periodStart'] == ranked['periodStart']), None)
            if not ranked_point or len({p['value'] for p in series}) == 1:
                continue
            ties = [p for p in series if p['value'] == ranked_point['value']]
            buckets.setdefault((issue['calculation'], metric['metricCode']), []).append((issue, metric, ties))
    for calculation, code in sorted(buckets, key=lambda key: (key[0] != 'average_per_day', key[1] != 'error')):
        rows = buckets[(calculation, code)]
        # One contrast is sufficient; bounded comparison against a fixed anchor.
        left = rows[0]
        right = next((row for row in rows[1:] if row[0]['entityRef'] != left[0]['entityRef']
                      and not {p['periodStart'] for p in left[2]} & {p['periodStart'] for p in row[2]}), None)
        if not right:
            continue
        label = 'Số lỗi' if code == 'error' else 'Tổng số'
        label += ' trung bình/ngày' if calculation == 'average_per_day' else ' trong kỳ'
        def describe(row):
            period_labels = ', '.join(p['periodLabel'] for p in row[2][:2])
            if len(row[2]) > 2:
                period_labels += f" và {len(row[2]) - 2} kỳ khác"
            return f"{row[0]['entityLabel']} đạt mức cao nhất trong các kỳ có dữ liệu ở {period_labels}"
        refs = list(dict.fromkeys([ref for row in (left, right) for ref in
                                  [*row[1]['periodAnalytics']['peak']['factIds'], *(p['factId'] for p in row[2])]]))
        evidence = list(dict.fromkeys(p['evidenceId'] for row in (left, right) for p in row[2]))
        return [{'text': f"{label}: {describe(left)}; {describe(right)}. Hai mốc cao nhất không trùng kỳ; không nên dùng mốc của một vấn đề làm mốc cho cả nhóm.",
                 'source': 'deterministic', 'kind': 'cross_issue_peak_timing', 'metricCode': code,
                 'calculation': calculation, 'factIds': refs, 'evidenceIds': evidence,
                 'start': min(p['periodStart'] for row in (left, right) for p in row[2]),
                 'end': max(p['periodEnd'] for row in (left, right) for p in row[2])}]
    return []


def overview_issues(issues: list[dict], context: dict) -> list[dict]:
    eligible = [issue for issue in issues if issue['report']['overview']]
    if context['calculation'] == 'both':
        eligible = [issue for issue in eligible if issue['calculation'] == 'average_per_day']
    # Rank structural complexity, not absolute values across unrelated units.
    def priority(issue):
        return max((len(m['periodAnalytics'].get('temporalStructure', {}).get('stages', []))
                    for m in issue['metrics']), default=0)
    return sorted(eligible, key=priority, reverse=True)


def compose_context_overview(issues: list[dict], context: dict) -> list[dict]:
    """Promote validated whole-window reading, never an ungrounded group claim."""
    eligible = overview_issues(issues, context)
    chosen = eligible[:3]
    output = []
    for issue in chosen:
        label = issue['entityLabel']
        basis = ' · Trung bình/ngày' if issue['calculation'] == 'average_per_day' else ' · Tổng trong kỳ'
        relations = issue['report'].get('relationships', [])
        periods = {p['periodStart'] for m in issue['metrics'] for p in m.get('series', [])}
        short_relation = bool(relations) and 0 < len(periods) <= 2
        for paragraph in ([] if short_relation else issue['report']['overview']):
            output.append({**paragraph, 'text': f"{label}{basis}: {paragraph['text']}",
                           'entityRef': issue['entityRef'], 'calculation': issue['calculation']})
        if relations:
            lookup = {c['candidateId']: c for c in issue.get('snapshot', {}).get('synthesis', {}).get('candidates', [])}
            def significance(paragraph):
                candidate = lookup.get(paragraph['candidateId'], {})
                directions = {d for values in candidate.get('allowedDirections', {}).values() for d in values}
                return (len(directions) > 1, candidate.get('priority', 0))
            relationship = max(relations, key=significance)
            output.append({**relationship, 'text': f"{issue['entityLabel']}{basis}: {relationship['text']}",
                           'entityRef': issue['entityRef'], 'calculation': issue['calculation']})
            issue['report']['relationships'] = [p for p in relations if p is not relationship]
            if short_relation:
                issue['report']['comparisonPromoted'] = True
        # The exact overview was promoted; do not repeat it in issue details.
        issue['report']['overview'] = []
    contrasts = calculation_contrasts(issues, {issue['entityRef'] for issue in chosen}) if context['calculation'] == 'both' else []
    output = [*contrasts, *output]
    if chosen and context['calculation'] == 'both' and not contrasts:
        output.append({'text': 'Tổng quan ưu tiên trung bình/ngày. Tổng trong kỳ có trong chi tiết; mỗi cách tính được đối chiếu riêng.', 'source': 'deterministic'})
    if chosen and any(issue['calculation'] == 'sum' and any('số ngày' in limitation for m in issue['metrics'] for limitation in m['quality']['limitations']) for issue in issues):
        output.append({'text': 'Các kỳ có số ngày được ghi nhận khác nhau. Tổng thấp hơn chưa đủ kết luận hoạt động giảm; cần đọc cùng cách tính và số ngày có dữ liệu.', 'source': 'deterministic'})
    if len(eligible) > len(chosen):
        output.append({'text': f'Tổng quan nêu {len(chosen)} trong {len(eligible)} vấn đề có diễn biến. Các vấn đề còn lại vẫn có kết quả trong chi tiết, không bị loại khỏi phạm vi.', 'source': 'deterministic'})
    if not output:
        output = [{'text': 'Chưa có hai kỳ hợp lệ liền nhau để mô tả diễn biến. Các giá trị đã ghi nhận vẫn có trong số liệu từng vấn đề.', 'source': 'deterministic'}]
    return output


def calculation_contrasts(issues: list[dict], selected: set[str]) -> list[dict]:
    """Explain opposite sum/average movements from independent change facts.

    No subtraction across calculations, inferred denominator or provider retry.
    """
    variants = {(issue['entityRef'], issue['calculation']): issue for issue in issues}
    output = []
    for entity in dict.fromkeys(issue['entityRef'] for issue in issues if issue['entityRef'] in selected):
        summed, averaged = variants.get((entity, 'sum')), variants.get((entity, 'average_per_day'))
        if not summed or not averaged:
            continue
        for code in ('error', 'total'):
            sm = next((m for m in summed['metrics'] if m.get('metricCode') == code), None)
            am = next((m for m in averaged['metrics'] if m.get('metricCode') == code), None)
            if not sm or not am:
                continue
            maps = [{p['periodStart']: p for p in m['series']} for m in (sm, am)]
            common = sorted(set(maps[0]) & set(maps[1]))
            matches = []
            for start, end in zip(common, common[1:]):
                numeric = [quantitative_evidence([m], {code: [points[start], points[end]]}) for m, points in zip((sm, am), maps)]
                if not all(numeric) or any(maps[0][day]['periodEnd'] != maps[1][day]['periodEnd'] for day in (start, end)):
                    continue
                a, b = numeric[0][0], numeric[1][0]
                if a['direction'] != b['direction']:
                    matches.append((a, b))
            if not matches:
                continue
            a, b = matches[-1]
            name = 'Số lỗi' if code == 'error' else 'Tổng số'
            text = (f"{summed['entityLabel']}: {name} trong kỳ {a['direction']}, nhưng mức trung bình/ngày {b['direction']}. "
                    f"Từ {a['fromLabel']} đến {a['toLabel']}, tổng từ {a['fromDisplay']} đến {a['toDisplay']} {sm['unit']}, "
                    f"chênh lệch {a['absoluteDisplay']}; trung bình/ngày từ {b['fromDisplay']} đến {b['toDisplay']} {am['unit']}, "
                    f"chênh lệch {b['absoluteDisplay']}. "
                    'Tổng trong kỳ không đại diện cho mức ghi nhận mỗi ngày; cần đọc cả hai cách tính và số ngày có dữ liệu.')
            refs = list(dict.fromkeys([*a['factIds'], *b['factIds']]))
            facts = {f['factId']: f for m in (sm, am) for f in m['facts']}
            output.append({'text': text, 'source': 'deterministic', 'kind': 'calculation_contrast',
                           'entityRef': entity, 'factIds': refs,
                           'evidenceIds': list(dict.fromkeys(e for ref in refs for e in facts[ref]['evidenceIds']))})
            break
    return output


def context_summary(service, *, db_path, source_key: str, project: str, data: pd.DataFrame,
                    entities: pd.DataFrame, context: dict, members: list[str],
                    prepared: dict[str, tuple[pd.DataFrame, dict]] | None = None,
                    generate_narrative: bool = True, retain_snapshots: bool = False,
                    persist_analysis: bool = True) -> dict:
    if generate_narrative and not service.config.enabled:
        raise PermissionError("Tính năng phân tích đang tắt trong cấu hình hệ thống.")
    builder = EvidenceBuilder(db_path, source_key)
    run_id, import_ref = builder.committed_version()
    if context.get("expectedImportRef") and context["expectedImportRef"] != import_ref:
        raise ValueError("Dữ liệu đã thay đổi. Hãy cập nhật biểu đồ trước khi phân tích.")
    analysis_id = f"ana_{uuid4().hex}"
    window = {k: context[k] for k in ("start", "end", "groupBy")}
    start, end = date.fromisoformat(context["start"]), date.fromisoformat(context["end"])
    calculators = ["sum", "average_per_day"] if context["calculation"] == "both" else [context["calculation"]]
    codes = ("total", "error", "error_rate") if context["view"] == "overview" else ("total", "error")
    if context.get("metricCode", "all") != "all":
        codes = tuple(code for code in codes if code == context["metricCode"])
    # Explicit resource limit, never silently truncate all-history requests.
    check_context_budget(context, members)
    strategy = TrendStrategy()
    strategy.max_periods = MAX_ENGINE_CELLS
    engine = AnalyticsEngine(strategy)
    issues, excluded = [], []
    for entity_id in members:
        entity = entities[entities.entity_id.eq(entity_id)].iloc[0].to_dict()
        rows = data[data.entity_id.eq(entity_id)].copy()
        if rows.empty:
            excluded.append({"entityRef": entity_id, "entityLabel": entity["entity_label"], "reason": "NO_DIRECT_DATA"})
            continue
        available = False
        for calculation in calculators:
            metrics = []
            computations = {}
            for code in codes:
                if context["view"] == "statistics":
                    frame, targets = (prepared or {})[entity_id]
                    computation, evidence = statistics_computation(frame, metric_code=code, calculation=calculation,
                        group_by=context["groupBy"], start=start, end=end, periods=context["periods"], targets=targets, rows=rows)
                else:
                    computation = engine.trend(data, entity_ref=entity_id, metric_code=code, start=start, end=end, group_by=context["groupBy"])
                    evidence = builder.build(computation, project=project, entity=entity, source_run_id=run_id)
                prefix = f"{entity_id}:{calculation}:{code}"
                computations[code] = computation
                metrics.append(metric_payload(computation, evidence, prefix, service))
            if any(m["series"] for m in metrics):
                available = True
            basis = build_overview(computations, metrics)['comparisonBasis'] if context['view'] == 'overview' and set(codes) == {'total', 'error', 'error_rate'} else None
            issues.append(build_issue(metrics, analysis_id=analysis_id, entity=entity, calculation=calculation, project=project, window=window, comparison_basis=basis))
        if not available:
            excluded.append({"entityRef": entity_id, "entityLabel": entity["entity_label"], "reason": "NO_USABLE_PERIOD"})
    analyzed = list(dict.fromkeys(i["entityRef"] for i in issues if any(m["series"] for m in i["metrics"])))
    context = {**context, "project": project, "requestedEntityRefs": members, "analyzedEntityRefs": analyzed,
               "requestedCount": len(members), "analyzedCount": len(analyzed), "excluded": excluded,
               "policyVersion": "context-insight-v5", "promptVersion": PROMPT_VERSION, "model": service.config.model}
    relationships = cross_issue_phases(cross_issue_reading(issues))
    # Show a few informative stages, not every adjacent pair or stable zero.
    meaningful = [r for r in relationships if set(r['directions']) != {'giữ nguyên'}]
    ranked = sorted(meaningful, key=lambda r: (not r['differentDirections'], -r['transitionCount']))
    selected_relationships = ranked[:2] + meaningful[-1:]
    selected_relationships = list({(r["calculation"], r["metricCode"], r["start"], r["end"]): r for r in selected_relationships}.values())
    selected_relationships.sort(key=lambda r: (r['start'], r['end']))
    landmarks = cross_issue_landmark(issues)
    if landmarks:
        selected_relationships = [*landmarks, *selected_relationships[-2:]]
        relationships = [*landmarks, *relationships]
    overview_text = ("Các vấn đề có những nhịp tăng, giảm khác nhau. Hãy chú ý các diễn biến trái chiều bên dưới thay vì coi cả nhóm cùng tăng hoặc cùng giảm."
                     if any(r.get("differentDirections", False) for r in relationships) else
                     "Một số vấn đề thay đổi cùng chiều ở các kỳ được đối chiếu. Chưa có căn cứ kết luận các vấn đề tác động đến nhau."
                     if relationships else "Chưa có đủ kỳ chung để diễn giải liên hệ giữa các vấn đề. Có thể xem diễn biến riêng bên dưới.")
    if len(members) == 1:
        overview_text = "Diễn biến của nội dung đã chọn được trình bày theo từng giai đoạn bên dưới."
    limitations = ["Không cộng các vấn đề thành tổng nhóm và không suy ra tỷ trọng đóng góp khi chưa có căn cứ về tính cộng được."] if len(members) > 1 else []
    if any(m["quality"]["limitations"] for i in issues for m in i["metrics"]):
        limitations.append("Một số kỳ thiếu dữ liệu hoặc có số ngày được ghi nhận khác nhau. Xem giới hạn ngay trong từng vấn đề.")
    base = {"schemaVersion": "ai-context-v1", "analysisId": analysis_id, "status": "insufficient_data",
            "context": context, "window": window,
            "dataAsOf": {"committedImportRef": import_ref, "snapshotId": f"as_{uuid4().hex}",
                         "generatedAt": datetime.now(timezone.utc).isoformat(), "stale": False},
            "scope": {"project": project, "entityRef": context["parentEntityRef"], "mode": context["selection"]},
            "report": {"overview": [{"text": overview_text, "source": "deterministic"}],
                       "relationships": selected_relationships, "relationshipDetails": relationships,
                       "limitations": limitations, "issues": issues},
            "facts": [f for i in issues for f in i["snapshot"]["facts"]],
            "evidence": [e for i in issues for e in i["snapshot"]["evidence"]],
            "provider": {"name": "9router", "model": service.config.model, "promptVersion": PROMPT_VERSION},
            "validation": {"status": "not_run", "errors": [], "claimResults": []}}
    base["dataAsOf"]["checksum"] = builder.checksum({"context": context, "facts": base["facts"], "evidence": base["evidence"], "importRef": import_ref})
    base = narrate_context(service, base, generate=generate_narrative)
    if not retain_snapshots:
        for issue in base['report']['issues']:
            issue.pop('snapshot', None)
    current_run, _ = builder.committed_version()
    if current_run != run_id:
        base['status'] = 'stale'
        base['dataAsOf']['stale'] = True
    if persist_analysis:
        service.repository.put(analysis_id, run_id, base)
    return base


def narrate_context(service, captured: dict, *, generate: bool = True) -> dict:
    """Render a retained evidence bundle without reading current source data.

    Reports use this path for regeneration on an immutable, durable snapshot.
    Provider output still goes through the same claim validator as Insight.
    """
    if generate and not service.config.enabled:
        raise PermissionError('Tính năng phân tích đang tắt trong cấu hình hệ thống.')
    base = deepcopy(captured)
    issues, context = base['report']['issues'], base['context']
    analysis_id = base['analysisId']
    base['status'] = 'insufficient_data' if generate else 'engine_only'
    base['validation'] = {'status': 'not_run', 'errors': [], 'claimResults': []}
    base['provider'] = {'name': '9router', 'model': service.config.model, 'promptVersion': PROMPT_VERSION}
    overview_text = base['report']['overview'][0]['text'] if base['report']['overview'] else ''
    limitations = base['report']['limitations']
    for issue in issues:
        issue['report'] = report_output(issue['snapshot']['synthesis'], [])
    candidates, validators = [], {}
    lead_issues = {id(issue) for issue in overview_issues(issues, context)[:3]}
    for i, issue in enumerate(issues):
        plan = provider_plan(issue["snapshot"])
        # Preserve first/last/extrema generation slots while keeping one request bounded.
        for c in plan["insightCandidates"]:
            c = {**c, 'section': next(section for section, ids in plan['reportPlan']['sections'].items() if c['candidateId'] in ids)}
            cid = f"issue-{i}:{c['candidateId']}"
            validators[cid] = (issue, c["candidateId"])
            candidates.append({**c, "candidateId": cid, "issueIndex": i,
                               "leadOverview": c['section'] == 'overview' and id(issue) in lead_issues,
                               "calculation": issue["calculation"], "entityLabel": issue["entityLabel"]})
    # Round-robin avoids provider input monopolized by the first issue.
    candidates.sort(key=lambda c: (c["section"] != "overview", c["section"] != "relationships", c["candidateId"].split(":", 1)[1], c["issueIndex"]))
    chosen = select_context_candidates(candidates)
    facts = {f["factId"]: f for f in base["facts"]}
    payload = {"schemaVersion": "ai-context-provider-input-v1", "analysisId": analysis_id,
               "context": {k: v for k, v in context.items() if k not in {"expectedImportRef", "excluded"}},
               "overview": overview_text, "limitations": limitations, "candidates": [], "facts": []}
    for c in chosen:
        trial = {**payload, "candidates": [*payload["candidates"], c]}
        refs = {f for item in trial["candidates"] for f in [*item["factIds"], *item.get("supportingFactIds", [])]}
        trial["facts"] = [facts[f] for f in refs]
        if len(json.dumps(trial, ensure_ascii=False).encode()) <= MAX_PROVIDER_BYTES:
            payload = trial
    base["provider"]["generatedCandidateCount"] = len(payload["candidates"])
    payload['leadOverviewCandidateIds'] = [c['candidateId'] for c in payload['candidates'] if c['leadOverview']]
    base["provider"]["engineOnlyCandidateCount"] = len(candidates) - len(payload["candidates"])
    validators = {c['candidateId']: validators[c['candidateId']] for c in payload['candidates']}
    if generate and payload["candidates"]:
        try:
            result = service.adapter.generate(system_prompt=files("excel_visualization_pipeline.ai").joinpath(f"prompts/{PROMPT_VERSION}.md").read_text(encoding="utf-8"), payload=payload)
            base["provider"].update(model=result.model, latencyMs=result.latency_ms, attemptCount=result.attempt_count)
            value = _load_json(service.validator._strip_fence(result.content))
            if not isinstance(value, dict) or set(value) != {"schemaVersion", "analysisId", "status", "claims"} or value["schemaVersion"] != "ai-context-narrative-v1" or value["analysisId"] != analysis_id or value["status"] != "ready" or not isinstance(value["claims"], list) or not 1 <= len(value["claims"]) <= MAX_PROVIDER_CANDIDATES:
                raise ValueError("claim_schema")
            seen, survivors, errors, receipts = set(), {}, [], []
            allowed = {c["candidateId"] for c in payload["candidates"]}
            for claim in value["claims"]:
                cid = claim.get("candidateId") if isinstance(claim, dict) else None
                codes = []
                if not cid or cid in seen or cid not in allowed:
                    codes = ["candidate_reference"]
                else:
                    seen.add(cid)
                    issue, local_id = validators[cid]
                    # Entity ownership is carried by the slot, not inferred from prose.
                    # Do not allow another entity label to override that slot.
                    text = str(claim.get("text", ""))
                    if any(other["entityLabel"] != issue["entityLabel"] and other["entityLabel"].lower() in text.lower() for other in issues):
                        codes.append("entity_scope_mismatch")
                    calc = issue["calculation"]
                    if (calc == "sum" and "trung bình" in text.lower()) or (calc == "average_per_day" and "tổng trong kỳ" in text.lower()):
                        codes.append("calculation_scope_mismatch")
                    local = {**claim, "candidateId": local_id}
                    envelope = {"schemaVersion": "ai-narrative-v5", "analysisId": analysis_id, "status": "ready", "claims": [local]}
                    validated = service.validator.validate(json.dumps(envelope, ensure_ascii=False), issue["snapshot"])
                    codes.extend(validated.errors)
                    if not codes:
                        survivors.setdefault(id(issue), []).append(local)
                errors.extend(codes)
                receipts.append({"candidateId": cid, "status": "rejected" if codes else "accepted", "errors": list(dict.fromkeys(codes))})
            for issue in issues:
                issue["report"] = report_output(issue["snapshot"]["synthesis"], survivors.get(id(issue), []))
            base["validation"] = {"status": "partial" if errors and survivors else "accepted" if survivors else "rejected",
                                  "errors": list(dict.fromkeys(errors)), "claimResults": receipts}
            base["status"] = "ready" if survivors else "rejected_output"
        except ProviderError as exc:
            base["status"] = "provider_unavailable"
            base["validation"]["errors"] = [exc.code]
        except (ValueError, TypeError, KeyError) as exc:
            base["status"] = "rejected_output"
            base["validation"] = {"status": "rejected", "errors": ["claim_schema"], "claimResults": []}
    base['report']['overview'] = compose_context_overview(issues, context)
    for issue in issues:
        periods = {p['periodStart'] for m in issue['metrics'] for p in m['series']}
        if len(periods) <= 2 and len(issue['report']['phases']) == 1:
            issue['report']['overview'] = []
            if issue['report'].get('comparisonPromoted'):
                issue['report']['phases'] = []
                continue
            # Same two-period pair: keep the relational interpretation in the
            # phase instead of repeating the same operands in two sections.
            pair = next((p for p in issue['report']['relationships']
                         if 'metric_pair_movement' in p['candidateId']), None)
            if pair:
                issue['report']['phases'][0] = {**issue['report']['phases'][0], **pair}
                issue['report']['relationships'] = [p for p in issue['report']['relationships'] if p is not pair]
    return base
