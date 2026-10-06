"""Exercise real report endpoints against an isolated copy of the current data.

--live opts into actual configured LLM calls. Raw/validated prose is test
evidence only, never persisted in a production report or printed with secrets.
"""
from __future__ import annotations

import argparse
from datetime import date
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote
from uuid import uuid4
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from fastapi.testclient import TestClient
from app import api
from excel_visualization_pipeline.ai import AIApplicationService, AnalysisSnapshotRepository
from excel_visualization_pipeline.ai.analytics import AnalyticsEngine, TrendStrategy
from excel_visualization_pipeline.ai.llm import DisabledLLMAdapter
from excel_visualization_pipeline.storage.connection import backup_database
from excel_visualization_pipeline.visualization import prepare_period_statistics
from excel_visualization_pipeline.reporting.export import chart_png, sections
import pandas as pd


def check_chart(document: dict) -> dict:
    data, _ = api._project(document['context']['project'])
    ctx, window = document['context'], document['window']
    start, end = date.fromisoformat(window['start']), date.fromisoformat(window['end'])
    strategy = TrendStrategy()
    strategy.max_periods = 20_000
    engine = AnalyticsEngine(strategy)
    results = []
    for chart in document['charts']:
        if ctx['view'] == 'overview':
            computation = engine.trend(data, entity_ref=chart['entityRef'], metric_code=chart['metricCode'], start=start, end=end, group_by=ctx['groupBy'])
            expected = {p['periodStart']: p['value'] for p in computation.series}
        else:
            rows = data[data.entity_id.eq(chart['entityRef'])]
            frame = prepare_period_statistics(rows, start, end, ctx['groupBy'], coverage_data=data)
            metric = {'total':'Tổng số','error':'Báo sai/Lỗi'}[chart['metricCode']]
            column = 'period_sum' if chart['calculation'] == 'sum' else 'average_per_day'
            expected = {pd.Timestamp(row.period_start).date().isoformat():getattr(row,column)
                        for row in frame[frame.metric_normalized.eq(metric)].itertuples(index=False)}
        for point in chart['points']:
            if point['value'] is not None:
                results.append({'chartId':chart['chartId'],'period':point['periodStart'], 'matches':expected.get(point['periodStart']) == point['value']})
    anchors = [a for f in document['findings'] for a in f['anchors']]
    by_chart = {c['chartId']: c for c in document['charts']}
    mismatched_anchors = [a['anchorId'] for a in anchors if not any(p['periodStart'] == a['periodStart'] and p['periodEnd'] == a['periodEnd']
        and p['value'] == a['value'] and p['factId'] == a['factId'] for p in by_chart[a['chartId']]['points'])]
    return {'pointCount':len(results),'mismatches':[r for r in results if not r['matches']],
            'anchorCount':len(anchors),'anchorMismatches':mismatched_anchors}


def run(args):
    args.output.parent.mkdir(parents=True, exist_ok=True)
    artifacts = ROOT / 'data/report-evaluation' / uuid4().hex
    artifacts.mkdir(parents=True)
    original_path, original_service = api.DB_PATH, api._ai_service
    api.DB_PATH = backup_database(original_path, artifacts/'evaluation.sqlite3')
    cases = json.loads(args.manifest.read_text(encoding='utf-8'))
    results = []
    client = TestClient(api.app)
    try:
        for index, case in enumerate(cases):
            project, context = case['project'], case['request']
            service = AIApplicationService.configured(repository=AnalysisSnapshotRepository())
            if args.live and not service.config.can_call_external:
                raise ValueError('LLM feature/config/privacy gate does not permit a live test.')
            if not args.live:
                service.config = replace(service.config, enabled=True, external_allowed=False)
                service.adapter = DisabledLLMAdapter(service.config.model, 'offline_evaluation')
            adapter, raw = service.adapter, []
            class Capture:
                def generate(self, *, system_prompt, payload):
                    value = adapter.generate(system_prompt=system_prompt,payload=payload)
                    raw.append(value.content)
                    return value
            service.adapter = Capture()
            api._ai_service = lambda: service
            started = time.perf_counter()
            prefix = f'/api/projects/{quote(project,safe="")}/reports'
            response = client.post(prefix, json={'context':context,'title':f'Báo cáo {project} — {index+1}', 'requestId':uuid4().hex})
            if response.status_code != 200:
                results.append({'project':project,'request':context,'httpStatus':response.status_code,'body':response.json()})
                print(json.dumps({'case':index+1,'httpStatus':response.status_code}, ensure_ascii=False), flush=True)
                continue
            baseline = response.json()
            prepare_ms = round((time.perf_counter()-started)*1000)
            started = time.perf_counter()
            response = client.post(prefix+f"/{baseline['reportId']}/regenerate", json={'baseRevision':1,'requestId':uuid4().hex})
            body = response.json()
            generation_ms = round((time.perf_counter()-started)*1000)
            result = {'project':project,'request':context,'live':args.live,'httpStatus':response.status_code,
                'prepareLatencyMs':prepare_ms,'generationLatencyMs':generation_ms,'rawNarrative':raw,'body':body}
            if response.status_code == 200:
                result['sourceChecks'] = check_chart(body)
                result['unchangedSnapshot'] = baseline['dataAsOf'] == body['dataAsOf'] and baseline['charts'] == body['charts'] and baseline['facts'] == body['facts']
                result['exportChecks'] = {}
                for format in ['pdf','docx']:
                    exported = client.post(prefix+f"/{body['reportId']}/revisions/{body['revision']}/exports",json={'format':format})
                    artifact = artifacts/f'case-{index+1}.{format}'
                    check = {'httpStatus':exported.status_code}
                    if exported.status_code == 200:
                        artifact.write_bytes(exported.content)
                        if format == 'pdf':
                            from pypdf import PdfReader
                            reader = PdfReader(BytesIO(exported.content))
                            text = '\n'.join(p.extract_text() for p in reader.pages)
                            check['pages'] = len(reader.pages)
                        else:
                            from docx import Document
                            doc = Document(BytesIO(exported.content))
                            text = '\n'.join(p.text for p in doc.paragraphs)
                            check['chartImageCount'] = len(doc.inline_shapes)
                        check.update(artifactPath=str(artifact), bytes=len(exported.content), contentHash=exported.headers['x-content-sha256'],
                            allFiveSections=all(title in text for title,_ in sections(body)), draftLabel='DRAFT' in text,
                            reportIdentity=body['reportId'] in text)
                    else:
                        check['error'] = exported.json()
                    result['exportChecks'][format] = check
                if index in (0,1,2,4):
                    for j, chart in enumerate(body['charts'][:3]):
                        (artifacts/f'case-{index+1}-chart-{j+1}.png').write_bytes(chart_png(body, chart))
            results.append(result)
            print(json.dumps({'case':index+1,'project':project,'status':body.get('generation',{}).get('status'),
                'validation':body.get('generation',{}).get('validation',{}).get('status'), 'providerCalls':len(raw),
                'prepareMs':prepare_ms, 'generationMs':generation_ms,'sourceChecks':result.get('sourceChecks'),
                'exports':{k:v.get('httpStatus') for k,v in result.get('exportChecks',{}).items()}},ensure_ascii=False), flush=True)
            args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2),encoding='utf-8')
    finally:
        api.DB_PATH, api._ai_service = original_path, original_service
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
