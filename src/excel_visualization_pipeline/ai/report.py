"""A whole-window reading plan over existing engine facts, not new KPI maths."""
from __future__ import annotations

from typing import Any
from datetime import date, timedelta

SECTIONS = {"overview": 1, "phases": 8, "relationships": 4}


def quantitative_evidence(metrics: list[dict], points: dict[str, list[dict]]) -> list[dict]:
    """Two salient observed transitions, never endpoint arithmetic or gap bridging."""
    choices = []
    for metric in metrics:
        rows = points.get(metric['metricCode'], [])
        facts = {f['factId']: f for f in metric['facts']}
        transitions = []
        for left, right in zip(rows, rows[1:]):
            change = right.get('change')
            if not change or change['fromPeriodStart'] != left['periodStart']:
                continue
            if date.fromisoformat(left['periodEnd']) + timedelta(days=1) != date.fromisoformat(right['periodStart']):
                continue
            delta = next((facts[ref] for ref in change['factIds'] if ref in facts and facts[ref]['kind'] == 'period_change'), None)
            if not delta or delta['value'] == 0:
                continue
            relative = next((facts[ref] for ref in change['factIds'] if ref in facts and facts[ref]['kind'] == 'period_relative_change'), None)
            transitions.append({'metricCode': metric['metricCode'], 'metricDisplayName': metric['metricDisplayName'],
                'fromLabel': left['periodLabel'], 'toLabel': right['periodLabel'],
                'fromDisplay': left['displayValue'], 'toDisplay': right['displayValue'],
                'absoluteDisplay': delta['displayValue'], 'unit': delta['unit'],
                'relativeDisplay': relative['displayValue'] if relative else None,
                'direction': 'tăng' if delta['value'] > 0 else 'giảm',
                'factIds': [left['factId'], right['factId'], delta['factId'], *([relative['factId']] if relative else [])],
                '_magnitude': abs(delta['value']), '_start': left['periodStart']})
        if transitions:
            # Prefer changing errors, then changing counts; do not rank different units.
            for direction in ('tăng', 'giảm'):
                matching = [row for row in transitions if row['direction'] == direction]
                if matching:
                    choices.append(max(matching, key=lambda row: row['_magnitude']))
            break
    for row in choices:
        row.pop('_magnitude')
    choices.sort(key=lambda row: row.pop('_start'))
    return choices


def attach_report(plan: dict[str, Any], metrics: list[dict[str, Any]]) -> None:
    facts = {f["factId"]: f for m in metrics for f in m["facts"]}
    facts.update({f["factId"]: f for f in plan["facts"]})
    by_code = {m["metricCode"]: m for m in metrics}
    sections: dict[str, list[str]] = {name: [] for name in SECTIONS}
    reading = plan["reading"]
    focus = next((m for m in metrics if m["metricCode"] == "error" and m["series"]), None)
    focus = focus or next((m for m in metrics if m["series"]), None)

    def add(section: str, kind: str, codes: list[str], refs: list[str], text: str,
            points: dict[str, list[dict[str, Any]]], **metadata: Any) -> None:
        numeric = quantitative_evidence(sorted(metrics, key=lambda m: m['metricCode'] != 'error'), points)
        refs = [*refs, *(ref for row in numeric for ref in row['factIds'])]
        if section == 'phases' and numeric:
            row = numeric[0]
            text += (f" Nhịp đáng chú ý từ {row['fromLabel']} đến {row['toLabel']}:"
                     f" {row['metricDisplayName']} {row['direction']} từ {row['fromDisplay']}"
                     f" {'lên' if row['direction'] == 'tăng' else 'xuống'} {row['toDisplay']},"
                     f" chênh lệch {row['absoluteDisplay']}. Đây là thay đổi giữa hai kỳ này, không phải cả giai đoạn.")
        refs = list(dict.fromkeys(ref for ref in refs if ref in facts))
        if not refs:
            return
        cid = f"report-{section}-{len(sections[section]):02d}"
        fid = f"relation:{cid}"
        evidence = list(dict.fromkeys(eid for ref in refs for eid in facts[ref]["evidenceIds"]))
        relation = {"factId": fid, "kind": "insight_relation", "value": kind,
                    "displayValue": kind, "unit": "enum", "operandFactIds": refs,
                    "evidenceIds": evidence, "policyVersion": "analytical-report-v1"}
        plan["facts"].append(relation)
        facts[fid] = relation
        anchors = [{"metricCode": code, "metricDisplayName": by_code[code]["metricDisplayName"],
                    **{key: point[key] for key in ("periodLabel", "displayValue", "factId", "evidenceId")}}
                   for code, rows in points.items() for point in rows]
        directions = {code: list(dict.fromkeys((b["value"] > a["value"]) - (b["value"] < a["value"])
                                              for a, b in zip(rows, rows[1:]))) for code, rows in points.items()}
        plan["candidates"].append({"candidateId": cid, "kind": kind, "section": section,
                                   "metricCodes": codes, "factIds": [fid, *refs],
                                   "evidenceIds": evidence, "anchors": anchors,
                                   "scope": "contiguous_block" if section == "phases" else "selected_window",
                                   "priority": 0, "expressions": [], "fallbackText": text,
                                   "allowedDirections": directions, "quantitativeEvidence": numeric, **metadata})
        sections[section].append(cid)

    if focus and reading["overview"]:
        code = focus["metricCode"]
        refs = [p["factId"] for metric in metrics for p in metric["series"]]
        # Include engine extrema so an overview can legitimately mention both.
        for name in ("peak", "lowest"):
            highlight = focus["periodAnalytics"].get(name)
            if highlight:
                refs.extend(highlight["factIds"])
        add("overview", "window_overview", list(by_code), refs, reading["overview"]["text"],
            {metric["metricCode"]: metric["series"] for metric in metrics}, hasGaps=focus["quality"]["validPeriodCount"] < focus["quality"]["expectedPeriodCount"])
    for phase in reading["phases"]:
        rows = {m["metricCode"]: [p for p in m["series"] if p["factId"] in phase["factIds"]] for m in metrics}
        rows = {code: points for code, points in rows.items() if points}
        refs = list(phase["factIds"])
        highlights = []
        descriptions = []
        for metric in metrics:
            series = metric["series"]
            peak, lowest = (metric["periodAnalytics"].get(name) for name in ("peak", "lowest"))
            if len(series) < 4 or not peak or not lowest or peak["value"] == lowest["value"]:
                continue
            for role, ranked, wording in (("peak", peak, "cao nhất"), ("lowest", lowest, "thấp nhất")):
                points = [p for p in rows.get(metric["metricCode"], []) if p["value"] == ranked["value"]]
                if not points:
                    continue
                refs.extend(ranked["factIds"])
                highlights.append({"metricCode": metric["metricCode"], "role": role,
                                   "value": ranked["value"], "displayValue": ranked["displayValue"],
                                   "dates": [p["periodStart"] for p in points],
                                   "periods": [{"start": p["periodStart"], "end": p["periodEnd"], "label": p["periodLabel"]} for p in points]})
                descriptions.append(f"{metric['metricDisplayName']} {wording} {ranked['displayValue']} vào {', '.join(p['periodLabel'] for p in points)}.")
        add("phases", "phase_description", list(rows), refs, " ".join([phase["text"], *descriptions]), rows,
            phaseExtrema=highlights,
            **{key: phase[key] for key in ("start", "end", "startLabel", "endLabel")})

    # Keep relationships from different times; don't let the first/longest
    # candidate monopolize the selected report. Shared phase facts remain in input.
    relationships = [c for c in plan["candidates"] if c.get("relationshipDescription") or c["kind"] == "count_rate_contrast"]
    periods = {p["evidenceId"]: p["periodStart"] for metric in metrics for p in metric["series"]}
    relationships.sort(key=lambda c: max(periods[eid] for eid in c["evidenceIds"]))
    # Preserve the first and last relationship plus meaningful changes inside.
    chosen = relationships if len(relationships) <= SECTIONS["relationships"] else [relationships[0], *relationships[-3:]]
    for candidate in chosen:
        sections["relationships"].append(candidate["candidateId"])

    plan["reportPlan"] = {"policyVersion": "analytical-report-v1", "sections": sections,
                          "totalPhaseCount": len(reading["phases"]), "shownPhaseCount": len(sections["phases"])}


def report_output(plan: dict[str, Any], claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Retain engine-backed paragraphs for absent/rejected sections."""
    candidates = {c["candidateId"]: c for c in plan["candidates"]}
    accepted = {c["candidateId"]: c for c in claims}
    result: dict[str, Any] = {"policyVersion": "analytical-report-v1"}
    for section, ids in plan["reportPlan"]["sections"].items():
        items = []
        for cid in ids:
            candidate = candidates[cid]
            claim = accepted.get(cid)
            items.append({"candidateId": cid, "text": claim["text"] if claim else candidate["fallbackText"],
                          "factIds": claim["factIds"] if claim else candidate["factIds"],
                          "source": "ai" if claim else "deterministic",
                          **{key: candidate[key] for key in ("start", "end", "startLabel", "endLabel", "metricDisplayName") if key in candidate}})
        result[section] = items
    result["omittedPhaseCount"] = plan["reportPlan"]["totalPhaseCount"] - plan["reportPlan"]["shownPhaseCount"]
    return result
