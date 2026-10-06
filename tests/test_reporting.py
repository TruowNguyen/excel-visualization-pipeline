from copy import deepcopy
from io import BytesIO
import json
import zipfile

import pytest

from app import api
from test_ai_context import context_api, request
from excel_visualization_pipeline.reporting.composer import summary_blocks
from excel_visualization_pipeline.reporting.export import chart_png
from excel_visualization_pipeline.reporting.repository import ReportRepository


def create(client, leaf, **changes):
    payload = {'context': request(leaf, metricCode='all'), 'title': 'Báo cáo chất lượng CX', 'requestId': 'create-report-001', **changes}
    response = client.post('/api/projects/Alpha/reports', json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


def test_delete_draft_is_scoped_revision_checked_and_recoverable(context_api):
    from excel_visualization_pipeline.storage.connection import connect_database
    client, leaf, adapter = context_api
    document, payload = create(client, leaf)
    other, _ = create(client, leaf, requestId='create-other-001')
    base = f"/api/projects/Alpha/reports/{document['reportId']}"
    repository = ReportRepository(api.DB_PATH, api.SOURCE_KEY, 'Alpha')
    repository.store_export(repository.get(document['reportId']), 'pdf', b'cached-test-export', 'test-only')
    changed = client.post(base+'/revisions', json={'baseRevision':1, 'requestId':'edit-before-delete', 'title':'Bản mới'})
    assert changed.status_code == 200
    assert client.request('DELETE', base, json={'baseRevision':1}).status_code == 409
    assert client.request('DELETE', base.replace('Alpha', 'Beta'), json={'baseRevision':2}).status_code == 404
    with pytest.raises(LookupError):
        ReportRepository(api.DB_PATH, 'other-source', 'Alpha').delete(document['reportId'], 2)
    assert client.request('DELETE', base, json={'baseRevision':0}).status_code == 422
    assert client.request('DELETE', base, json={'baseRevision':2}).status_code == 200
    assert [item['reportId'] for item in client.get('/api/projects/Alpha/reports').json()['items']] == [other['reportId']]
    assert client.get(base).status_code == 404
    assert client.get(base+'/revisions/1').status_code == 404
    assert client.post(base+'/revisions/1/exports', json={'format':'pdf'}).status_code == 404
    assert client.post(base+'/revisions/2/check').status_code == 404
    assert client.post(base+'/regenerate', json={'baseRevision':2,'requestId':'generate-deleted'}).status_code == 404
    assert client.post('/api/projects/Alpha/reports', json=payload).status_code == 409
    assert client.request('DELETE', base, json={'baseRevision':2}).status_code == 404
    with pytest.raises(LookupError):
        repository.append({**document, 'revision':3}, 2, 'late-append', 'hash')
    with connect_database(api.DB_PATH) as connection:
        assert connection.execute('SELECT COUNT(*) FROM report_revisions WHERE report_id=?', (document['reportId'],)).fetchone()[0] == 2
        assert connection.execute('SELECT COUNT(*) FROM report_exports WHERE report_id=?', (document['reportId'],)).fetchone()[0] == 1
    assert not adapter.calls


def test_deterministic_preview_create_idempotency_and_restart(context_api):
    client, leaf, adapter = context_api
    payload = {'context': request(leaf, metricCode='all'), 'title': 'Báo cáo CX', 'requestId': 'create-report-001'}
    preview = client.post('/api/projects/Alpha/reports/preview', json=payload)
    assert preview.status_code == 200, preview.text
    assert client.get('/api/projects/Alpha/reports').json()['items'] == []
    document, payload = create(client, leaf)
    assert not adapter.calls
    assert document['generation']['status'] == 'engine_only'
    assert document['review']['publicationStatus'] == 'draft'
    assert document['template']['sections'] == ['metadata', 'executive_summary', 'kpi_overview', 'period_story', 'key_findings']
    assert '_bundle' not in document
    assert [p['value'] for p in document['charts'][0]['points']] == [100, 120]
    assert document['kpis'][0]['valueRole'] == 'latest_observed_period'
    duplicate = client.post('/api/projects/Alpha/reports', json=payload).json()
    assert duplicate['reportId'] == document['reportId'] and duplicate['revision'] == 1
    changed = {**payload, 'title': 'Khác'}
    assert client.post('/api/projects/Alpha/reports', json=changed).status_code == 409
    # A new repository/server can read the entire pinned bundle, not an AI-cache ID.
    repository = ReportRepository(api.DB_PATH, api.SOURCE_KEY, 'Alpha')
    pinned = repository.get(document['reportId'])
    assert pinned['_bundle']['facts'] == document['facts']
    assert repository.items()[0]['reportId'] == document['reportId']
    assert client.get(f"/api/projects/Beta/reports/{document['reportId']}").status_code == 404


def test_regenerate_pins_snapshot_validates_prose_and_deduplicates_provider(context_api):
    client, leaf, adapter = context_api
    document, _ = create(client, leaf)
    url = f"/api/projects/Alpha/reports/{document['reportId']}"
    payload = {'baseRevision': 1, 'requestId': 'generate-report-001'}
    response = client.post(url+'/regenerate', json=payload)
    assert response.status_code == 200, response.text
    generated = response.json()
    assert generated['revision'] == 2 and len(adapter.calls) == 1
    assert generated['dataAsOf'] == document['dataAsOf']
    assert generated['charts'] == document['charts']
    assert generated['generation']['validation']['status'] == 'accepted'
    assert client.post(url+'/regenerate', json=payload).json()['revision'] == 2
    assert len(adapter.calls) == 1
    adapter.wrong = True
    rejected = client.post(url+'/regenerate', json={'baseRevision':2, 'requestId':'generate-report-002'}).json()
    assert rejected['generation']['status'] == 'rejected_output'
    assert '999999' not in json.dumps(rejected['blocks'])
    assert rejected['charts'] == document['charts']


def test_revision_review_conflict_and_numbers_are_locked(context_api):
    client, leaf, _ = context_api
    document, _ = create(client, leaf)
    base = f"/api/projects/Alpha/reports/{document['reportId']}"
    checked = client.post(base+'/revisions/1/check').json()
    assert checked['review']['status'] == 'checked'
    assert checked['review']['authority'] == 'local_check_only'
    edited = client.post(base+'/revisions', json={'baseRevision':1, 'requestId':'edit-report-001',
        'title':'Báo cáo đã chỉnh', 'userNotes':'Ý kiến nghiệp vụ — chưa kiểm chứng', 'selectedFindingIds':[]})
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body['revision'] == 2 and body['review']['status'] == 'needs_review'
    assert body['charts'] == document['charts'] and body['facts'] == document['facts']
    assert client.get(base+'/revisions/1').json()['title'] == document['title']
    assert client.get(base+'/revisions/1').json()['review']['status'] == 'checked'
    assert client.post(base+'/revisions/1/check').status_code == 409
    assert client.post(base+'/revisions', json={'baseRevision':1, 'requestId':'edit-report-002','title':'stale'}).status_code == 409
    assert client.post(base+'/revisions', json={'baseRevision':2, 'requestId':'edit-report-003','selectedFindingIds':['fake']}).status_code == 422
    assert client.post(base+'/revisions', json={'baseRevision':2, 'requestId':'edit-report-004','facts':[]}).status_code == 422


@pytest.mark.parametrize('group', ['day', 'week', 'month', 'quarter'])
@pytest.mark.parametrize('calculation', ['sum', 'average_per_day', 'both'])
def test_statistics_exact_parity_across_all_supported_grains(context_api, group, calculation):
    client, leaf, adapter = context_api
    document, _ = create(client, leaf, context=request(leaf, view='statistics', metricCode='all', groupBy=group, calculation=calculation, rangeMode='all'))
    assert not adapter.calls
    assert {c['metricCode'] for c in document['charts']} <= {'total','error'}
    assert all(c['calculation'] in ({'sum','average_per_day'} if calculation == 'both' else {calculation}) for c in document['charts'])
    assert all(e['target']['kind'] == 'aggregate' for e in document['evidence'])
    # Reuse the independent existing prepared-chart parity test machinery.
    context = client.post('/api/projects/Alpha/ai/context-insight', json=request(leaf, view='statistics', metricCode='all', groupBy=group, calculation=calculation, rangeMode='all')).json()
    expected = {(i['entityRef'],i['calculation'],m['metricCode']):m['series'] for i in context['report']['issues'] for m in i['metrics'] if m['series']}
    for chart in document['charts']:
        rows = expected[(chart['entityRef'],chart['calculation'],chart['metricCode'])]
        assert [(p['periodStart'],p['value']) for p in chart['points']] == [(p['periodStart'],p['value']) for p in rows]
    if group != 'day':
        assert document['findings'] == []
        assert all('xu hướng' not in b['text'].lower() or 'chưa' in b['text'].lower() for b in document['blocks'])


@pytest.mark.parametrize('format', ['pdf','docx'])
def test_real_exports_are_unicode_complete_immutable_and_idempotent(context_api, format):
    client, leaf, _ = context_api
    document, _ = create(client, leaf, title='Đỉnh và đáy — Báo cáo tiếng Việt')
    base = f"/api/projects/Alpha/reports/{document['reportId']}"
    url = base+'/revisions/1/exports'
    response = client.post(url, json={'format':format})
    assert response.status_code == 200, response.text[:300]
    assert response.headers['x-report-revision'] == '1'
    assert client.post(url, json={'format':format}).content == response.content
    if format == 'pdf':
        assert response.content.startswith(b'%PDF-')
        from pypdf import PdfReader
        pdf = PdfReader(BytesIO(response.content))
        text = '\n'.join(page.extract_text() for page in pdf.pages)
        assert 'Đỉnh và đáy' in text and 'DRAFT' in text
        assert all(section in text for section in ['Thông tin báo cáo','Tóm tắt điều hành','Tổng quan KPI','Diễn biến trong kỳ','Điểm đáng chú ý'])
    else:
        with zipfile.ZipFile(BytesIO(response.content)) as package:
            text = package.read('word/document.xml').decode()
            assert 'Đỉnh và đáy' in text and 'DRAFT' in text
            assert len([n for n in package.namelist() if n.startswith('word/media/')]) == len(document['storyPanels'])
    client.post(base+'/revisions', json={'baseRevision':1,'requestId':'edit-export-001','title':'Phiên bản khác'})
    assert client.post(url, json={'format':format}).content == response.content
    assert client.post(url, json={'format':'pptx'}).status_code == 422
    assert client.post(url, json={'format':format, 'path':'C:/Windows/anything'}).status_code == 422


def test_unsafe_text_cannot_become_active_markup_in_exports(context_api):
    client, leaf, _ = context_api
    document, _ = create(client, leaf, title='<script>alert(1)</script>')
    response = client.post(f"/api/projects/Alpha/reports/{document['reportId']}/revisions/1/exports", json={'format':'docx'})
    with zipfile.ZipFile(BytesIO(response.content)) as package:
        xml = package.read('word/document.xml').decode()
        assert '&lt;script&gt;' in xml and '<script>' not in xml


def test_deterministic_reports_work_when_ai_is_disabled(context_api):
    from dataclasses import replace
    client, leaf, adapter = context_api
    service = api._ai_service()
    service.config = replace(service.config, enabled=False)
    document, _ = create(client, leaf)
    assert document['charts'] and not adapter.calls
    assert client.post(f"/api/projects/Alpha/reports/{document['reportId']}/regenerate", json={'baseRevision':1,'requestId':'disabled-001'}).status_code == 409


def test_manual_prose_is_validated_audited_and_preserved_after_regeneration(context_api):
    client, leaf, adapter = context_api
    document, _ = create(client, leaf)
    base = f"/api/projects/Alpha/reports/{document['reportId']}"
    block = next(b for b in document['blocks'] if b.get('candidateId'))
    original = block['text']
    payload = {'baseRevision':1,'requestId':'manual-report-001','narrativeEdits':{block['blockId']:original}}
    edited = client.post(base+'/revisions', json=payload)
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert next(b for b in body['blocks'] if b['blockId'] == block['blockId'])['source'] == 'manual'
    assert body['manualEdits'][0]['originalText'] == original
    assert not adapter.calls
    invalid = client.post(base+'/revisions', json={'baseRevision':2,'requestId':'manual-report-002',
        'narrativeEdits':{block['blockId']:original+' Số liệu là 999999.'}})
    assert invalid.status_code == 422
    assert client.get(base).json()['revision'] == 2
    generated = client.post(base+'/regenerate',json={'baseRevision':2,'requestId':'manual-report-003'}).json()
    retained = next(b for b in generated['blocks'] if b['blockId'] == block['blockId'])
    assert retained['text'] == original and retained['source'] == 'manual'
    assert generated['manualEdits'] == body['manualEdits']
    assert generated['charts'] == document['charts']


def test_saved_report_and_regeneration_remain_pinned_when_new_import_is_available(context_api, monkeypatch):
    from types import SimpleNamespace
    client, leaf, _ = context_api
    document, _ = create(client, leaf)
    monkeypatch.setattr(api, 'latest_committed_version', lambda *args: SimpleNamespace(import_ref='imp_newer', run_id='newer'))
    base = f"/api/projects/Alpha/reports/{document['reportId']}"
    reopened = client.get(base).json()
    assert reopened['freshness']['newerDataAvailable'] is True
    regenerated = client.post(base+'/regenerate',json={'baseRevision':1,'requestId':'pinned-report-001'}).json()
    for key in ['dataAsOf','charts','facts','evidence','window']:
        assert regenerated[key] == document[key]
    assert regenerated['freshness']['newerDataAvailable'] is True


def test_import_changed_during_capture_cannot_save_mixed_report(context_api, monkeypatch):
    from types import SimpleNamespace
    client, leaf, _ = context_api
    original_build = api._build_context_bundle
    def concurrent_import(*args, **kwargs):
        bundle = original_build(*args, **kwargs)
        monkeypatch.setattr(api, 'latest_committed_version', lambda *args: SimpleNamespace(import_ref='imp_newer',run_id='newer'))
        return bundle
    monkeypatch.setattr(api, '_build_context_bundle', concurrent_import)
    response = client.post('/api/projects/Alpha/reports',json={'context':request(leaf),'title':'Báo cáo','requestId':'mixed-report-001'})
    assert response.status_code == 409
    assert client.get('/api/projects/Alpha/reports').json()['items'] == []


def test_executive_summary_keeps_issue_identity_numbers_and_calculation_contrast():
    def block(key, entity, text, section='overview', calculation='sum', candidate='report-overview-00'):
        return {'blockId':key,'entityRef':entity,'entityLabel':entity,'text':text,'section':section,
                'candidateId':candidate,'calculation':calculation,'source':'deterministic','factIds':[key]}
    same = 'Số lỗi tăng rồi giảm. Cuối kỳ số lỗi giảm.'
    a = block('a','Camera',same)
    b = block('b','Đèn pha',same)
    phase = block('p','Camera','Số lỗi tăng từ 11 lên 17, chênh lệch 6.',section='phases')
    result = summary_blocks([a,b,phase],[])
    assert result[0]['text'] != result[1]['text']
    assert 'Camera' in result[0]['text'] and 'Đèn pha' in result[1]['text']
    assert '11 lên 17' in result[0]['text']
    assert result[0]['dependencyBlockIds'] == ['a','p'] and result[0]['factIds'] == ['a','p']
    contrast = block('c','Camera','Tổng kỳ giảm nhưng trung bình/ngày tăng. Tổng từ 441 xuống 299, chênh lệch -142. Trung bình/ngày từ 16.33 lên 19.93, chênh lệch 3.6. Không đồng nhất tổng với mức mỗi ngày.',calculation=None,candidate=None)
    result = summary_blocks([a,phase,contrast],[])
    assert '441 xuống 299' in result[1]['text'] and '16.33 lên 19.93' in result[1]['text']


def test_export_provenance_keeps_manual_and_engine_authorship_and_chart_origin(context_api):
    from PIL import Image
    from excel_visualization_pipeline.reporting.export import prose_rows, sections
    client, leaf, _ = context_api
    document, _ = create(client, leaf)
    rows = prose_rows([{'source':'ai','text':'Một nhận định'}, {'source':'manual','text':'Nội dung sửa'},
                       {'source':'deterministic','text':'Diễn giải từ số liệu'}])
    assert [v for kind,v in rows if kind == 'note'] == ['Nguồn diễn giải: AI đã kiểm chứng',
        'Nguồn diễn giải: Người dùng chỉnh sửa — đã kiểm chứng','Nguồn diễn giải: Tổng hợp từ số liệu']
    assert 'Nhóm kỳ: Ngày' in str(sections(document)[0]) and 'Cách tính: Tổng trong kỳ' in str(sections(document)[0])
    image = Image.open(BytesIO(chart_png(document, document['charts'][0])))
    assert 'Deterministic Analytics Engine' in image.info['Origin']
    assert document['dataAsOf']['checksum'] == image.info['SourceChecksum']
