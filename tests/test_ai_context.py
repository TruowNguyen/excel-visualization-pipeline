from datetime import date
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import api
from excel_visualization_pipeline.ai import AIApplicationService, AnalysisSnapshotRepository, LLMResult
from excel_visualization_pipeline.ai.context import resolve_members, statistics_computation, build_issue, cross_issue_reading
from excel_visualization_pipeline.ai.context import cross_issue_phases, cross_issue_landmark, select_context_candidates, compose_context_overview
from excel_visualization_pipeline.ai.context import calculation_contrasts
from excel_visualization_pipeline.ai.analytics import AnalyticsEngine
from excel_visualization_pipeline.ai.semantic import validate_text
from excel_visualization_pipeline.visualization import prepare_period_statistics
from test_ai import _import_sample, enabled_config
from test_ai_filters import data as daily_data
from test_ai_synthesis import snapshot as synthesis_snapshot


def test_calculation_contrast_uses_independent_changes_and_cannot_cross_a_gap():
    def issue(calculation, values, delta, unit):
        prefix = calculation + ':'
        points = [{'periodStart': '2026-09-01', 'periodEnd': '2026-09-01', 'periodLabel': '01/09', 'value': values[0],
                   'displayValue': str(values[0]), 'factId': prefix+'a', 'evidenceId': prefix+'ea'},
                  {'periodStart': '2026-09-02', 'periodEnd': '2026-09-02', 'periodLabel': '02/09', 'value': values[1],
                   'displayValue': str(values[1]), 'factId': prefix+'b', 'evidenceId': prefix+'eb',
                   'change': {'fromPeriodStart': '2026-09-01', 'factIds': [prefix+'delta']}}]
        facts = [{'factId': p['factId'], 'evidenceIds': [p['evidenceId']]} for p in points]
        facts.append({'factId': prefix+'delta', 'kind': 'period_change', 'value': delta, 'displayValue': str(delta),
                      'unit': unit, 'evidenceIds': [prefix+'ea', prefix+'eb']})
        return {'entityRef': 'group', 'entityLabel': 'Nhóm', 'calculation': calculation,
                'metrics': [{'metricCode': 'error', 'unit': unit, 'metricDisplayName': 'Số lỗi', 'series': points, 'facts': facts}]}
    issues = [issue('sum', [441, 299], -142, 'lỗi'), issue('average_per_day', [16.33, 19.93], 3.6, 'lỗi/ngày')]
    result = calculation_contrasts(issues, {'group'})
    assert len(result) == 1 and '441 đến 299' in result[0]['text'] and '16.33 đến 19.93' in result[0]['text']
    assert set(result[0]['factIds']) == {'sum:a', 'sum:b', 'sum:delta', 'average_per_day:a', 'average_per_day:b', 'average_per_day:delta'}
    assert calculation_contrasts(issues, {'another'}) == []
    for row in issues:
        row['metrics'][0]['series'][1]['periodStart'] = '2026-09-03'
        row['metrics'][0]['series'][1]['periodEnd'] = '2026-09-03'
    assert calculation_contrasts(issues, {'group'}) == []


def test_context_preserves_aligned_ratio_basis_for_relationships():
    value = synthesis_snapshot([22, 22], [657, 420])
    for metric in value['metrics']:
        metric['evidence'] = []
    issue = build_issue(value['metrics'], analysis_id=value['analysisId'], entity={'entity_id': 'group', 'entity_label': 'Nhóm'},
                        calculation='sum', project='VSO', window=value['window'], comparison_basis=value['comparisonBasis'])
    assert issue['snapshot']['comparisonBasis'] == value['comparisonBasis']
    assert any(c['kind'] == 'unchanged_errors_share_up' for c in issue['snapshot']['synthesis']['candidates'])
    assert issue['report']['relationships']


class ContextAdapter:
    provider_name = "fake"
    model = "test"

    def __init__(self, wrong=False):
        self.calls = []
        self.wrong = wrong

    def generate(self, *, system_prompt, payload):
        self.calls.append(payload)
        candidate = next((c for c in payload["candidates"] if c["kind"] == "phase_description"), payload["candidates"][0])
        anchors = candidate["anchors"]
        first, last = anchors[0], anchors[-1]
        text = f"{first['metricDisplayName']} ghi nhận {first['displayValue']} vào {first['periodLabel']}. {last['metricDisplayName']} ghi nhận {last['displayValue']} vào {last['periodLabel']}."
        if self.wrong:
            text += " Tổng số là 999999."
        return LLMResult(json.dumps({"schemaVersion": "ai-context-narrative-v1", "analysisId": payload["analysisId"],
            "status": "ready", "claims": [{"candidateId": candidate["candidateId"], "section": candidate["section"],
            "claimType": candidate["kind"], "text": text, "factIds": candidate["factIds"]}]}, ensure_ascii=False), self.model)


@pytest.fixture
def context_api(monkeypatch, storage_workspace, sample_workbook):
    monkeypatch.setattr(api, "DB_PATH", storage_workspace / "context.sqlite3")
    monkeypatch.setattr(api, "SOURCE_KEY", "sample")
    adapter = ContextAdapter()
    service = AIApplicationService(config=enabled_config(), adapter=adapter, repository=AnalysisSnapshotRepository())
    monkeypatch.setattr(api, "_ai_service", lambda: service)
    client = TestClient(api.app)
    _import_sample(client, sample_workbook)
    entities = client.get("/api/projects/Alpha/entities").json()["entities"]
    leaf = next(e for e in entities if "Camera" in e["entity_label"])
    return client, leaf, adapter


def request(leaf, **changes):
    return {"view": "overview", "parentEntityRef": leaf["entity_id"], "selection": "node",
            "metricCode": "total", "start": "2026-09-12", "end": "2026-09-13", "groupBy": "day", **changes}


def test_context_single_issue_preserves_identity_numbers_sources_and_old_endpoint(context_api):
    client, leaf, adapter = context_api
    response = client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready", body["validation"]
    assert body["context"]["analyzedEntityRefs"] == [leaf["entity_id"]]
    assert [p["value"] for p in body["report"]["issues"][0]["metrics"][0]["series"]] == [100, 120]
    assert all(e["target"]["kind"] == "exact" for e in body["evidence"])
    assert len(adapter.calls) == 1
    assert not any(k in json.dumps(adapter.calls) for k in ["lineageRef", "observationRef", "raw_value"])
    assert client.get(f"/api/ai/analyses/{body['analysisId']}").status_code == 200
    # New API does not change legacy request validation or schema.
    assert client.post("/api/projects/Alpha/ai/trend-summary", json={"entityRef": leaf["entity_id"], "metricCode": "total", "start": "2026-09-12", "end": "2026-09-13", "groupBy": "quarter"}).status_code == 422


def test_selected_and_all_membership_and_empty_selection(context_api):
    client, leaf, _ = context_api
    parent = leaf["parent_entity_id"]
    selected = client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf, parentEntityRef=parent, selection="selected", entityRefs=[leaf["entity_id"], leaf["entity_id"]]))
    assert selected.status_code == 200, selected.text
    assert selected.json()["context"]["requestedCount"] == 1
    all_result = client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf, parentEntityRef=parent, selection="all"))
    assert all_result.status_code == 200 and all_result.json()["context"]["requestedEntityRefs"] == [leaf["entity_id"]]
    for ids in ([], [parent], ["foreign"]):
        assert client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf, parentEntityRef=parent, selection="selected", entityRefs=ids)).status_code == 422


@pytest.mark.parametrize("group", ["day", "week", "month", "quarter"])
@pytest.mark.parametrize("calculation", ["sum", "average_per_day", "both"])
def test_statistics_context_matches_canonical_prepared_chart(context_api, group, calculation):
    client, leaf, adapter = context_api
    response = client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf, view="statistics", groupBy=group, calculation=calculation, rangeMode="all", start="2025-01-01", end="2025-01-02"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["window"]["start"] == "2026-09-12"
    data, _ = api._project("Alpha")
    frame = prepare_period_statistics(data[data.entity_id.eq(leaf["entity_id"])], date(2026, 9, 12), date(2026, 9, 13), group, coverage_data=data)
    for issue in body["report"]["issues"]:
        for metric in issue['metrics']:
            assert ' · ' not in metric['metricDisplayName']
            assert ('trung bình/ngày' in metric['metricDisplayName']) == (issue['calculation'] == 'average_per_day')
        column = "period_sum" if issue["calculation"] == "sum" else "average_per_day"
        values = frame[frame.metric_normalized.eq("Tổng số")].sort_values("period_start")[column].dropna().tolist()
        assert [p["value"] for p in issue["metrics"][0]["series"]] == values
    assert all(e["target"]["kind"] == "aggregate" for e in body["evidence"])
    if group != "day":
        assert not adapter.calls  # One actual grouped point cannot earn a trend/model call.
    ids = [f["factId"] for f in body["facts"]]
    assert len(ids) == len(set(ids))


def test_wrong_numbers_do_not_reach_displayed_report(context_api):
    client, leaf, adapter = context_api
    adapter.wrong = True
    body = client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf)).json()
    assert body["status"] == "rejected_output"
    assert "999999" not in json.dumps(body["report"])
    assert body["validation"]["errors"]


def test_expected_data_version_and_statistics_rate_are_rejected(context_api):
    client, leaf, _ = context_api
    assert client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf, expectedImportRef="imp_old")).status_code == 422
    assert client.post("/api/projects/Alpha/ai/context-insight", json=request(leaf, view="statistics", metricCode="error_rate")).status_code == 422


def test_direct_children_only_and_empty_node_membership():
    entities = pd.DataFrame([{"entity_id": "root", "parent_entity_id": None}, {"entity_id": "a", "parent_entity_id": "root"}, {"entity_id": "b", "parent_entity_id": "a"}])
    assert resolve_members(entities, "root", "all", []) == ["a"]
    assert resolve_members(entities, "b", "all", []) == []
    with pytest.raises(ValueError):
        resolve_members(entities, "root", "selected", ["b"])


def test_ordered_chronology_does_not_accept_endpoint_proxy():
    from scripts.evaluate_ai_filter_matrix import snapshot
    dates = [f"2026-03-{i:02d}" for i in range(1, 7)]
    value, _ = snapshot(daily_data(dates, [16, 12, 11, 17, 21, 18]), "example", "sample", date(2026, 3, 1), date(2026, 3, 6), "day", "error")
    candidate = next(c for c in value["synthesis"]["candidates"] if c["kind"] == "window_overview")
    errors, _ = validate_text("Số lỗi tăng từ 16 lên 21 rồi giảm xuống 18.", candidate, value, candidate["factIds"])
    assert "chronology_mismatch" in errors
    errors, _ = validate_text("Số lỗi giảm ở đầu giai đoạn, tăng trở lại rồi giảm ở cuối.", candidate, value, candidate["factIds"])
    assert "chronology_mismatch" not in errors


def test_cross_issue_facts_aligned_not_rollup_and_missing_not_bridged():
    def issue(name, values, dates):
        series = [{"periodStart": d, "periodEnd": d, "periodLabel": d, "value": v,
                   "factId": f"{name}:{d}", "evidenceId": f"ev:{name}:{d}"} for d, v in zip(dates, values)]
        return {"entityRef": name, "entityLabel": name, "calculation": "sum", "metrics": [{"metricCode": "error", "series": series}]}
    dates = ["2026-01-01", "2026-01-02"]
    result = cross_issue_reading([issue("A", [1, 4], dates), issue("B", [7, 2], dates)])
    assert len(result) == 1 and result[0]["differentDirections"]
    assert len(result[0]["factIds"]) == 4
    assert "che mất" in result[0]["text"]
    assert not cross_issue_reading([issue("A", [1, 4], ["2026-01-01", "2026-01-03"]), issue("B", [7, 2], ["2026-01-01", "2026-01-03"])])


@pytest.mark.parametrize('group,dates', [
    ('week', ['2025-12-29', '2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26', '2026-02-02']),
    ('month', ['2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01']),
    ('quarter', ['2025-07-01', '2025-10-01', '2026-01-01', '2026-04-01', '2026-07-01', '2026-10-01']),
])
def test_statistics_multi_period_year_crossing_keeps_canonical_values_and_labels(group, dates):
    rows = daily_data(dates, [8, 16, 4, 20, 12, 12])
    rows['entity_label'], rows['entity_level'] = 'Sample', 'Item'
    first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    frame = prepare_period_statistics(rows, first, last, group, coverage_data=rows)
    targets = {(calc, row.metric_normalized, row.period_label): {'kind': 'aggregate', 'aggregateRef': 'test'}
               for row in frame.itertuples() for calc in ['sum', 'average_per_day']}
    for calc, column in [('sum', 'period_sum'), ('average_per_day', 'average_per_day')]:
        result, evidence = statistics_computation(frame, metric_code='error', calculation=calc, group_by=group,
            start=first, end=last, periods=[{}] * 6, targets=targets, rows=rows)
        expected = frame[frame.metric_normalized.eq('Báo sai/Lỗi')].sort_values('period_start')
        assert [p['value'] for p in result.series] == expected[column].tolist()
        assert [p['periodLabel'] for p in result.series] == expected.period_label.tolist()
        assert len(evidence) == 6


def test_budget_rejects_before_prepared_chart_and_disabled_blocks_provider(context_api, monkeypatch):
    from dataclasses import replace
    from excel_visualization_pipeline.ai.context import check_context_budget
    with pytest.raises(ValueError, match='Phạm vi quá lớn'):
        check_context_budget({'view': 'statistics', 'calculation': 'both', 'metricCode': 'all', 'periods': [{}]*100}, ['a']*100)
    client, leaf, adapter = context_api
    service = api._ai_service()
    service.config = replace(service.config, enabled=False)
    monkeypatch.setattr(api, 'prepare_period_statistics', lambda *a, **k: pytest.fail('must gate before preparing statistics'))
    assert client.post('/api/projects/Alpha/ai/context-insight', json=request(leaf, view='statistics')).status_code == 409
    assert not adapter.calls


def test_continuous_whole_sequence_claim_cannot_hide_a_plateau():
    from scripts.evaluate_ai_filter_matrix import snapshot
    dates = [f'2026-03-{i:02d}' for i in range(1, 7)]
    value, _ = snapshot(daily_data(dates, [7, 10, 12, 15, 15, 17]), 'example', 'sample', date(2026,3,1), date(2026,3,6), 'day', 'error')
    candidate = next(c for c in value['synthesis']['candidates'] if c['kind'] == 'window_overview')
    for text in ['Số lỗi tăng liên tục qua các kỳ.', 'Số lỗi tăng liên tiếp từ 7 lên 17.']:
        errors, _ = validate_text(text, candidate, value, candidate['factIds'])
        assert 'chronology_mismatch' in errors
    errors, _ = validate_text('Số lỗi tăng, có hai kỳ giữ nguyên rồi tăng trở lại.', candidate, value, candidate['factIds'])
    assert 'chronology_mismatch' not in errors


def test_dated_continuous_stage_does_not_inherit_later_tied_trough():
    from scripts.evaluate_ai_filter_matrix import snapshot
    dates = [f'2026-03-{i:02d}' for i in range(1, 7)]
    value, _ = snapshot(daily_data(dates, [12, 7, 3, 3, 11, 3]), 'example', 'sample', date(2026,3,1), date(2026,3,6), 'day', 'error')
    candidate = next(c for c in value['synthesis']['candidates'] if c['kind'] == 'window_overview')
    errors, _ = validate_text('Số lỗi giảm liên tiếp từ 12 vào 01/03/2026 xuống 3 vào 03/03/2026.', candidate, value, candidate['factIds'])
    assert 'chronology_mismatch' not in errors


def test_context_generation_reserves_stages_and_relations_for_large_groups():
    candidates = [{'candidateId': f'issue-{i}:report-{section}-00', 'section': section, 'issueIndex': i}
                  for section in ('overview', 'phases', 'relationships') for i in range(9)]
    chosen = select_context_candidates(candidates)
    assert len(chosen) == 12
    assert {c['section'] for c in chosen} == {'overview', 'phases', 'relationships'}
    assert len({c['issueIndex'] for c in chosen}) == 4


def test_cross_issue_phases_preserve_interiors_and_do_not_bridge_gaps():
    def issue(label, values, dates):
        return {'entityRef': label, 'entityLabel': label, 'calculation': 'average_per_day',
                'metrics': [{'metricCode': 'error', 'series': [
                    {'periodStart': d, 'periodEnd': d, 'periodLabel': d, 'value': v,
                     'factId': f'{label}:{d}', 'evidenceId': f'ev:{label}:{d}'} for d, v in zip(dates, values)]}]}
    dates = [f'2026-01-{i:02d}' for i in range(1, 5)]
    readings = cross_issue_reading([issue('A', [1, 2, 3, 4], dates), issue('B', [9, 8, 7, 6], dates)])
    phases = cross_issue_phases(readings)
    assert len(phases) == 1 and phases[0]['transitionCount'] == 3
    assert len(phases[0]['factIds']) == 8
    assert phases[0]['start'] == dates[0] and phases[0]['end'] == dates[-1]
    assert 'trung bình/ngày' in phases[0]['text']
    dates = ['2026-01-01', '2026-01-02', '2026-01-04', '2026-01-05']
    readings = cross_issue_reading([issue('A', [1, 2, 3, 4], dates), issue('B', [9, 8, 7, 6], dates)])
    assert len(cross_issue_phases(readings)) == 2


def test_context_overview_promotes_real_reading_once_and_preserves_basis():
    def issue(calc, text):
        return {'entityRef': 'a', 'entityLabel': 'A', 'calculation': calc,
                'metrics': [{'periodAnalytics': {}, 'quality': {'limitations': []}}],
                'report': {'overview': [{'text': text, 'source': 'ai', 'factIds': [calc]}], 'phases': []}}
    issues = [issue('sum', 'Số lỗi giảm.'), issue('average_per_day', 'Số lỗi trung bình/ngày tăng.')]
    overview = compose_context_overview(issues, {'calculation': 'both'})
    assert 'trung bình/ngày tăng' in overview[0]['text']
    assert overview[0]['factIds'] == ['average_per_day']
    assert overview[0]['source'] == 'ai'
    assert issues[1]['report']['overview'] == []
    assert issues[0]['report']['overview'][0]['text'] == 'Số lỗi giảm.'
    assert any('mỗi cách tính được đối chiếu riêng' in p['text'] for p in overview)


def test_overview_intermediate_level_is_not_forced_to_terminal_value():
    from scripts.evaluate_ai_filter_matrix import snapshot
    dates = [f'2026-03-{i:02d}' for i in range(1, 5)]
    value, _ = snapshot(daily_data(dates, [7, 17, 8, 22]), 'example', 'sample', date(2026, 3, 1), date(2026, 3, 4), 'day', 'error')
    candidate = next(c for c in value['synthesis']['candidates'] if c['kind'] == 'window_overview')
    errors, _ = validate_text('Số lỗi tăng lên 17 rồi giảm xuống 8 trước khi tăng trở lại.', candidate, value, candidate['factIds'])
    assert 'numeric_role_mismatch' not in errors
    errors, _ = validate_text('Số lỗi tăng lên 8 rồi giảm xuống 17.', candidate, value, candidate['factIds'])
    assert 'numeric_role_mismatch' in errors


def test_quantitative_evidence_uses_engine_changes_and_keeps_gap_boundary():
    from scripts.evaluate_ai_filter_matrix import snapshot
    from excel_visualization_pipeline.ai.report import quantitative_evidence
    dates = [f'2026-03-{i:02d}' for i in range(1, 5)]
    value, metrics = snapshot(daily_data(dates, [0, 17, 8, 22]), 'example', 'sample', date(2026, 3, 1), date(2026, 3, 4), 'day', 'error')
    candidate = next(c for c in value['synthesis']['candidates'] if c['kind'] == 'window_overview')
    numeric = candidate['quantitativeEvidence']
    assert len(numeric) == 2
    assert numeric[0]['relativeDisplay'] is None
    assert numeric[0]['fromDisplay'] == '0' and numeric[0]['toDisplay'] == '17'
    assert numeric[1]['direction'] == 'giảm'
    assert all(set(row['factIds']) <= set(candidate['factIds']) for row in numeric)
    errors, _ = validate_text('Số lỗi tăng từ 0 lên 17, chênh lệch 17, rồi giảm từ 17 xuống 8, chênh lệch -9.', candidate, value, candidate['factIds'])
    assert not errors
    errors, _ = validate_text('Số lỗi tăng từ 0 lên 17, chênh lệch 9999.', candidate, value, candidate['factIds'])
    assert 'unsupported_numeric_mention' in errors
    errors, _ = validate_text('Số lỗi tăng từ 0 lên 17, chênh lệch 8.', candidate, value, candidate['factIds'])
    assert 'numeric_role_mismatch' in errors
    metric = metrics[0]
    gap_rows = [metric['series'][0], metric['series'][2]]
    assert quantitative_evidence([metric], {'error': gap_rows}) == []


def test_window_overview_can_locate_substage_but_not_an_outside_range():
    from scripts.evaluate_ai_filter_matrix import snapshot
    dates = [f'2026-03-{i:02d}' for i in range(1, 7)]
    value, _ = snapshot(daily_data(dates, [1, 2, 3, 4, 3, 2]), 'example', 'sample', date(2026, 3, 1), date(2026, 3, 6), 'day', 'error')
    candidate = next(c for c in value['synthesis']['candidates'] if c['kind'] == 'window_overview')
    errors, _ = validate_text('Số lỗi tăng từ 01/03/2026 đến 04/03/2026 rồi giảm ở cuối.', candidate, value, candidate['factIds'])
    assert 'period_scope_mismatch' not in errors
    errors, _ = validate_text('Số lỗi tăng từ 01/03/2026 đến 07/03/2026 rồi giảm ở cuối.', candidate, value, candidate['factIds'])
    assert 'unsupported_date_mention' in errors or 'period_scope_mismatch' in errors


def test_cross_issue_landmark_compares_all_ties_not_just_first_peak():
    def issue(label, values):
        series = [{'periodStart': f'2026-01-{i+1:02d}', 'periodEnd': f'2026-01-{i+1:02d}',
                   'periodLabel': f'{i+1:02d}/01/2026', 'value': v, 'factId': f'{label}:{i}',
                   'evidenceId': f'ev:{label}:{i}'} for i, v in enumerate(values)]
        maximum = max(values)
        first = series[values.index(maximum)]
        return {'entityRef': label, 'entityLabel': label, 'calculation': 'sum',
                'metrics': [{'metricCode': 'error', 'series': series, 'periodAnalytics': {
                    'peak': {**first, 'factIds': [first['factId']]}}}]}
    a, b = issue('A', [1, 5, 2, 5]), issue('B', [2, 3, 4, 7])
    assert not cross_issue_landmark([a, b])  # Both also peak on day4.
    b = issue('B', [2, 7, 3, 4])
    assert not cross_issue_landmark([a, b])  # Both also peak on day2.
    b = issue('B', [2, 3, 7, 4])
    result = cross_issue_landmark([a, b])
    assert len(result) == 1
    assert {'A:1', 'A:3', 'B:2'} <= set(result[0]['factIds'])
    assert 'không trùng kỳ' in result[0]['text']


def test_constant_error_does_not_hide_volume_story():
    from scripts.evaluate_ai_filter_matrix import snapshot
    dates = [f'2026-03-{i:02d}' for i in range(1, 5)]
    rows = daily_data(dates, [0, 0, 0, 0])
    rows.loc[rows.metric_normalized.eq('Tổng số'), 'chart_value'] = [10, 20, 15, 30]
    value, _ = snapshot(rows, 'example', 'sample', date(2026, 3, 1), date(2026, 3, 4), 'day', 'all')
    overview = value['synthesis']['reading']['overview']['text']
    assert 'Tổng số' in overview


def test_landmark_relation_does_not_require_direction_metadata(context_api, monkeypatch):
    from excel_visualization_pipeline.ai import context as module
    client, leaf, _ = context_api
    monkeypatch.setattr(module, 'cross_issue_landmark', lambda issues: [{
        'kind': 'cross_issue_peak_timing', 'text': 'Các mốc cao nhất không trùng kỳ.',
        'source': 'deterministic', 'factIds': [], 'evidenceIds': []}])
    response = client.post('/api/projects/Alpha/ai/context-insight', json=request(leaf))
    assert response.status_code == 200, response.text
    assert response.json()['report']['relationships'][0]['kind'] == 'cross_issue_peak_timing'
