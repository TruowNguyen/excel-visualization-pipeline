"""Read-only full committed-data/filter audit. No provider call or source writes.

Print JSON to stdout; persist evidence via the caller. Every data-bearing entity,
three groupings, four metric selectors and five date windows are evaluated.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from app import api
from excel_visualization_pipeline.ai import AnalyticsEngine, AIApplicationService, OutputValidator
from excel_visualization_pipeline.ai.overview import build_overview
from excel_visualization_pipeline.ai.synthesis import build_synthesis, provider_plan, synthesis_fallback


def snapshot(data, entity, project, start, end, group, selector, computations_cache=None):
    engine = AnalyticsEngine()
    computations, metrics = {}, []
    for code in ("total", "error", "error_rate") if selector == "all" else (selector,):
        c = (computations_cache or {}).get(code)
        if c is None:
            c = engine.trend(data, entity_ref=entity, metric_code=code, start=start, end=end, group_by=group)
            if computations_cache is not None:
                computations_cache[code] = c
        computations[code] = c
        metric = {"metricCode": code, "metricDisplayName": c.metric_display_name, "status": c.status,
                  "unit": c.unit, "aggregationRule": c.aggregation_rule, "series": list(c.series),
                  "facts": list(c.facts), "quality": c.quality, "periodAnalytics": c.period_analytics,
                  "historicalContext": c.historical_context,
                  "evidence": [{"evidenceId": p.evidence_id, "periodStart": p.period_start.isoformat(),
                                "periodEnd": p.period_end.isoformat(), "periodLabel": p.period_label}
                               for p in (*c.points, *c.historical_points)]}
        metrics.append(AIApplicationService._prefix_analysis_ids(metric, code) if selector == "all" else metric)
    value = {"analysisId": "audit", "scope": {"metricCode": selector, "metricDisplayName": metrics[0]["metricDisplayName"],
                                               "entityRef": entity, "project": project},
             "window": {"start": start.isoformat(), "end": end.isoformat(), "groupBy": group}}
    if selector == "all":
        overview = build_overview(computations, metrics)
        value.update(schemaVersion="ai-overview-v2", metrics=metrics,
                     facts=[f for m in metrics for f in m["facts"]] + overview["facts"],
                     evidence=[e for m in metrics for e in m["evidence"]])
    else:
        value.update(schemaVersion="ai-trend-v3", **{k: metrics[0][k] for k in ("series", "facts", "quality", "periodAnalytics", "evidence")})
    value["synthesis"] = build_synthesis(value)
    value["facts"].extend(value["synthesis"]["facts"])
    return value, metrics


def audit(value, metrics):
    plan = value["synthesis"]
    candidates = {c["candidateId"]: c for c in plan["candidates"]}
    claims = []
    for section, ids in provider_plan(value)["reportPlan"]["sections"].items():
        for cid in ids:
            c = candidates[cid]
            text = c["fallbackText"]
            if section == "phases":
                text = f"Từ {c['start']} đến {c['end']}, " + text
            # This mock proves grounding, not generation style/length. Engine
            # fallback may retain many tied dates beyond the model text limit.
            while len(text) > 650 and ". " in text:
                text = text.rsplit(". ", 1)[0] + "."
            claims.append({"section": section, "candidateId": cid, "claimType": c["kind"], "text": text,
                           "factIds": c["factIds"][:1]})
    issues = []
    if claims:
        result = OutputValidator().validate(json.dumps({"schemaVersion": "ai-narrative-v5", "analysisId": value["analysisId"],
                                                       "status": "ready", "claims": claims}, ensure_ascii=False), value)
        if result.errors:
            issues.extend(result.errors)
    else:
        result = None
    phases = [c for c in candidates.values() if c.get("section") == "phases"]
    missing = []
    for m in metrics:
        if len(m["series"]) < 4:
            continue
        peak, low = (m["periodAnalytics"].get(k) for k in ("peak", "lowest"))
        if not peak or not low or peak["value"] == low["value"]:
            continue
        for role, ranked in (("peak", peak), ("lowest", low)):
            expected = {p["periodStart"] for p in m["series"] if p["value"] == ranked["value"]}
            actual = {day for c in phases for h in c.get("phaseExtrema", []) if h["metricCode"] == m["metricCode"] and h["role"] == role for day in h["dates"]}
            if expected - actual:
                missing.append({"metric": m["metricCode"], "role": role, "periods": sorted(expected - actual)})
    if missing:
        issues.append("extrema_not_in_report")
    return {"errors": list(dict.fromkeys(issues)), "claimResults": list(result.claim_results) if result and result.errors else [],
            "missingExtrema": missing, "periods": {m["metricCode"]: len(m["series"]) for m in metrics},
            "totalPhases": plan["reportPlan"]["totalPhaseCount"], "shownPhases": len(phases),
            "inputBytes": len(json.dumps(provider_plan(value)).encode()) if claims else 0}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    data, entities = api._source()
    records = []
    for (project, entity), rows in data.groupby(["project_label", "entity_id"]):
        start, end = date.fromisoformat(str(rows.date.min())[:10]), date.fromisoformat(str(rows.date.max())[:10])
        windows = {"full": (start, end), "tail": (max(start, end - timedelta(days=9)), end),
                   "clipped": (start + timedelta(days=3), end - timedelta(days=2)),
                   "one_day": (end, end), "empty": (end + timedelta(days=1), end + timedelta(days=7))}
        for window, (first, last) in windows.items():
            for group in ("day", "week", "month"):
                computations_cache = {}
                for selector in ("all", "total", "error", "error_rate"):
                    request = {"project": project, "entity": entity, "start": first.isoformat(), "end": last.isoformat(),
                               "groupBy": group, "metric": selector, "window": window}
                    try:
                        value, metrics = snapshot(rows, entity, project, first, last, group, selector, computations_cache)
                        records.append({**request, **audit(value, metrics)})
                    except Exception as exc:
                        records.append({**request, "errors": [type(exc).__name__], "exception": str(exc)})
    print(json.dumps({"projects": sorted(data.project_label.unique()), "entities": data.entity_id.nunique(),
                      "sourceRows": len(data), "caseCount": len(records),
                      "errorCounts": dict(Counter(error for r in records for error in r["errors"])),
                      "passed": sum(not r["errors"] for r in records),
                      "groups": {group: {"cases": sum(r["groupBy"] == group for r in records), "failed": sum(r["groupBy"] == group and bool(r["errors"]) for r in records)} for group in ("day", "week", "month")},
                      "entitiesCovered": [{"project": p, "entity": e} for p, e in data.groupby(["project_label", "entity_id"]).groups],
                      "examples": [r for r in records if r["errors"]][:24]}, ensure_ascii=False))
    return 1 if any(r["errors"] for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
