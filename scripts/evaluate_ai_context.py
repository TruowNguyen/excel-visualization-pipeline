"""Application-endpoint evaluation; --live explicitly opts into provider calls."""
from __future__ import annotations
import argparse
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient
from app import api
from excel_visualization_pipeline.ai import AIApplicationService, AnalysisSnapshotRepository
from excel_visualization_pipeline.ai.llm import DisabledLLMAdapter
from excel_visualization_pipeline.ai.analytics import AnalyticsEngine, TrendStrategy
from excel_visualization_pipeline.visualization import prepare_period_statistics
import pandas as pd


def evaluate(project: str, request: dict, *, live: bool = False) -> dict:
    service = AIApplicationService.configured(repository=AnalysisSnapshotRepository())
    if live and not service.config.can_call_external:
        raise ValueError("feature_config_or_privacy_gate")
    if not live:
        service.config = replace(service.config, enabled=True, external_allowed=False)
        service.adapter = DisabledLLMAdapter(service.config.model, "offline_evaluation")
    delegate = service.adapter
    raw = []
    captured_input = []

    class Capture:
        def generate(self, *, system_prompt, payload):
            captured_input.append(payload)
            result = delegate.generate(system_prompt=system_prompt, payload=payload)
            raw.append(result.content)
            return result

    service.adapter = Capture()
    previous = api._ai_service
    api._ai_service = lambda: service
    started = time.monotonic()
    try:
        response = TestClient(api.app).post(f"/api/projects/{quote(project, safe='')}/ai/context-insight", json=request)
    finally:
        api._ai_service = previous
    output = {"project": project, "request": request, "live": live, "httpStatus": response.status_code,
              "requestLatencyMs": round((time.monotonic() - started) * 1000), "rawNarrative": raw[0] if raw else None,
              "body": response.json()}
    output['providerInput'] = captured_input[0] if captured_input else None
    if response.status_code != 200:
        return output
    body = output["body"]
    checks = []
    if request['view'] == 'overview':
        data, _ = api._project(project)
        strategy = TrendStrategy()
        strategy.max_periods = 20_000
        engine = AnalyticsEngine(strategy)
        for issue in body['report']['issues']:
            for metric in issue['metrics']:
                computation = engine.trend(data, entity_ref=issue['entityRef'], metric_code=metric['metricCode'],
                    start=date.fromisoformat(body['window']['start']), end=date.fromisoformat(body['window']['end']), group_by=request['groupBy'])
                expected = {p['periodStart']: p['value'] for p in computation.series}
                for point in metric['series']:
                    checks.append({'entityRef': issue['entityRef'], 'calculation': issue['calculation'], 'metric': metric['metricCode'],
                                   'period': point['periodStart'], 'matchesChart': expected.get(point['periodStart']) == point['value']})
    if request["view"] == "statistics":
        data, _ = api._project(project)
        for issue in body["report"]["issues"]:
            rows = data[data.entity_id.eq(issue["entityRef"])]
            frame = prepare_period_statistics(rows, date.fromisoformat(body["window"]["start"]), date.fromisoformat(body["window"]["end"]), request["groupBy"], coverage_data=data)
            for metric in issue["metrics"]:
                selected = frame[frame.metric_normalized.eq({"total":"Tổng số", "error":"Báo sai/Lỗi"}[metric["metricCode"]])]
                column = "period_sum" if issue["calculation"] == "sum" else "average_per_day"
                lookup = {pd.Timestamp(row.period_start).date().isoformat(): getattr(row, column) for row in selected.itertuples(index=False)}
                for point in metric["series"]:
                    checks.append({"entityRef": issue["entityRef"], "calculation": issue["calculation"], "metric": metric["metricCode"], "period": point["periodStart"],
                                   "matchesChart": lookup.get(point["periodStart"]) == point["value"]})
    refs = [f["factId"] for f in body["facts"]]
    provenance_checks = []
    evidence = {e['evidenceId']: e for e in body['evidence']}
    for issue in body['report']['issues']:
        for metric in issue['metrics']:
            # Inspect actual captured source at the boundaries of each series;
            # this is sampling, not a claim that every contributor was audited.
            for point in metric['series'][:1] + metric['series'][-1:]:
                target = evidence[point['evidenceId']]['target']
                if target['kind'] != 'aggregate':
                    continue
                provenance = api.aggregate_provenance(project, target['aggregateRef'])
                source_value = provenance['result']['chartValue']
                # Legacy overview facts use explicit eight-decimal canonical
                # serialization; statistics preserves the chart float exactly.
                if request['view'] == 'overview':
                    source_value = round(source_value, 8)
                correct = (provenance['context']['entity']['ref'] == issue['entityRef']
                    and source_value == point['value']
                    and provenance['aggregation']['ruleCode'] == metric['aggregationRule'])
                provenance_checks.append({'entityRef': issue['entityRef'], 'calculation': issue['calculation'],
                    'metric': metric['metricCode'], 'period': point['periodStart'], 'matchesSource': correct})
    output["sourceChecks"] = {"pointsCheckedAgainstChart": len(checks), "chartMismatches": [c for c in checks if not c["matchesChart"]],
                              'sampledAggregateSources': len(provenance_checks), 'aggregateSourceMismatches': [p for p in provenance_checks if not p['matchesSource']],
                              "uniqueFactIds": len(set(refs)) == len(refs),
                              "allRequestedAccountedFor": set(body["context"]["requestedEntityRefs"]) == set(body["context"]["analyzedEntityRefs"]) | {e["entityRef"] for e in body["context"]["excluded"]}}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--manifest", required=True, help="JSON list of {project,request}")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--compact", action="store_true", help="Retain raw prose and period facts, omit duplicate fact/evidence bundles from console")
    parser.add_argument("--output", help="Save fresh raw/validated output and source checks without printing the full report")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if isinstance(manifest, dict):
        manifest = manifest["results"]
    results = []
    for case in manifest:
        result = evaluate(case["project"], case["request"], live=args.live)
        if args.compact and result["httpStatus"] == 200:
            result["body"].pop("facts", None)
            result["body"].pop("evidence", None)
            report = result['body']['report']
            report['relationshipDetailCount'] = len(report.pop('relationshipDetails', []))
            for issue in result["body"]["report"]["issues"]:
                for metric in issue["metrics"]:
                    for key in ("facts", "evidence", "periodAnalytics", "historicalContext"):
                        metric.pop(key, None)
                    metric['series'] = [{k: v for k, v in point.items() if k in {
                        'periodStart', 'periodEnd', 'periodLabel', 'value', 'displayValue',
                        'observedDayCount', 'expectedDayCount', 'coverageRatio'}} for point in metric['series']]
        results.append(result)
        if args.summary:
            body = result["body"]
            print(json.dumps({"case": len(results), "httpStatus": result["httpStatus"], "status": body.get("status"), "validation": body.get("validation"),
                              "sourceChecks": result.get("sourceChecks")}, ensure_ascii=False), flush=True)
    if args.output:
        Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.summary:
        print(json.dumps(results, ensure_ascii=False))
    return 0 if all(r["httpStatus"] == 200 and not r.get("sourceChecks", {}).get("chartMismatches") and not r.get('sourceChecks', {}).get('aggregateSourceMismatches') and r.get("sourceChecks", {}).get("uniqueFactIds") and r.get("sourceChecks", {}).get("allRequestedAccountedFor") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
