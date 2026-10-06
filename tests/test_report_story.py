from copy import deepcopy

from excel_visualization_pipeline.reporting.story import story_panels
from excel_visualization_pipeline.reporting.story import stage_readings
from excel_visualization_pipeline.reporting.composer import limitation_notes


def chart(entity, code, calc='sum', unit='ticket'):
    return {'chartId': f'{entity}-{code}-{calc}', 'entityRef': entity, 'entityLabel': entity,
            'metricCode': code, 'metricLabel': code, 'calculation': calc, 'calculationLabel': calc, 'unit': unit,
            'points': [{'periodStart': '2026-09-07', 'periodEnd': '2026-09-13', 'periodLabel': 'Tuần 37/2026',
                        'value': 12, 'displayValue': '12', 'factId': 'a', 'evidenceId': 'ev'},
                       {'periodStart': '2026-09-14', 'periodEnd': '2026-09-20', 'periodLabel': 'Tuần 38/2026',
                        'value': None, 'displayValue': 'Chưa ghi nhận', 'factId': None, 'evidenceId': None}]}


def test_overview_chart_and_prose_are_owned_by_one_entity_and_keep_gaps():
    document = {'charts': [chart('A','total'),chart('A','error'),chart('A','error_rate',unit='percent'),chart('B','error')],
                'blocks': [{'blockId':'A-phase','entityRef':'A','calculation':'sum','section':'phases'},
                           {'blockId':'B-phase','entityRef':'B','calculation':'sum','section':'phases'},
                           {'blockId':'shared','section':'group_relationships'}]}
    before = deepcopy(document)
    panels = story_panels(document)
    assert [p['blockIds'] for p in panels] == [['A-phase'],[],[],[],['B-phase']]
    assert [p['kind'] for p in panels] == ['general','metric','metric','metric','metric']
    assert [t['type'] for t in panels[0]['figure']['data']] == ['bar','bar','scatter']
    assert [t['marker']['color'] for t in panels[0]['figure']['data']] == ['#8ecae6','#d1495b','#ff9f1c']
    assert panels[0]['figure']['data'][2]['yaxis'] == 'y2'
    assert panels[0]['figure']['layout']['xaxis']['ticktext'] == ['07/09 – 13/09','Thiếu dữ liệu']
    assert all(t['y'] == [12,None] and not t['connectgaps'] for t in panels[0]['figure']['data'])
    assert document == before


def test_statistics_both_keeps_calculations_on_their_own_unit_axes():
    document = {'charts':[chart('A','error'),chart('A','error','average_per_day','ticket/day')],
                'blocks':[{'blockId':'sum','section':'phases','entityRef':'A','calculation':'sum'},
                          {'blockId':'avg','section':'relationships','entityRef':'A','calculation':'average_per_day'}]}
    panel, = story_panels(document)
    assert panel['blockIds'] == ['sum','avg']
    assert [t['type'] for t in panel['figure']['data']] == ['bar','scatter']
    assert panel['figure']['layout']['yaxis']['title']['text'] == 'ticket'
    assert panel['figure']['layout']['yaxis2']['title']['text'] == 'ticket/day'


def test_three_units_are_not_overlaid_or_narratives_duplicated():
    document = {'charts':[chart('A','total',unit='ticket'),chart('A','error',unit='person'),chart('A','error_rate',unit='percent')],
                'blocks':[{'blockId':'phase','section':'phases','entityRef':'A','calculation':'sum'}]}
    panels = story_panels(document)
    assert len(panels) == 6
    assert [bid for p in panels for bid in p['blockIds']] == ['phase']


def test_single_period_uses_a_narrow_bar_without_implying_a_trend():
    single = chart('A', 'error')
    single['points'] = single['points'][:1]
    panel, = story_panels({'charts':[single], 'blocks':[]})
    assert panel['figure']['data'][0]['width'] == .22
    assert panel['figure']['layout']['xaxis']['range'] == [-1.5, 1.5]
    assert panel['blockIds'] == []


def test_metric_readings_bind_retained_fact_identity_not_names_or_prose():
    charts = [chart('A','total'), chart('A','error'), chart('A','error_rate',unit='percent')]
    facts = [{'factId': f"A:sum:{c['metricCode']}:fact-temporal-story", 'kind':'temporal_narrative',
              'displayValue':f"Verified {c['metricCode']}", 'evidenceIds':['ev']} for c in charts]
    document = {'charts':charts, 'blocks':[{'blockId':'joint','entityRef':'A','calculation':'sum','section':'phases'}], 'facts':facts}
    before = deepcopy(document)
    general, *details = story_panels(document)
    assert general['blockIds'] == ['joint'] and not general['readings']
    assert [p['readings'][0]['text'] for p in details] == ['Verified total','Verified error','Verified error_rate']
    assert all(p['readings'][0]['editable'] is False for p in details)
    assert document == before


def test_retained_template_11_keeps_its_original_grouped_layout():
    document = {'template':{'version':'1.1'}, 'charts':[chart('A','total'), chart('A','error')], 'blocks':[]}
    panel, = story_panels(document)
    assert len(panel['chartIds']) == 2


def test_statistics_all_metrics_both_never_overlays_three_units():
    charts = [chart('A',code,calc,unit) for calc in ['sum','average_per_day']
              for code, unit in [('total','ticket' if calc == 'sum' else 'ticket/day'),
                                 ('error','ticket' if calc == 'sum' else 'ticket/day'), ('error_rate','percent')]]
    panels = story_panels({'charts':charts,'blocks':[]})
    assert [p['kind'] for p in panels] == ['general','general','metric','metric','metric']
    assert all(len({c['unit'] for c in charts if c['chartId'] in p['chartIds']}) <= 2 for p in panels)
    assert all(len(p['chartIds']) == 2 for p in panels[2:])


def test_weekly_two_period_reading_is_a_comparison_with_verified_delta():
    c = chart('A','total')
    c['points'][1].update(value=8, displayValue='8',factId='b',evidenceId='ev2')
    document = {'charts':[c],'blocks':[],'facts':[
        {'factId':'A:sum:total:fact-temporal-story','kind':'temporal_narrative',
         'displayValue':'highest/lowest should not appear','evidenceIds':['ev','ev2']},
        {'factId':'A:sum:total:fact-change-001','kind':'period_change',
         'displayValue':'-4','value':-4,'evidenceIds':['ev','ev2']}]}
    reading = story_panels(document)[0]['readings'][0]
    assert 'Kỳ 1 (07–13/09/2026) → Kỳ 2 (14–20/09/2026)' in reading['text']
    assert 'chênh lệch -4 ticket' in reading['text']
    assert 'highest' not in reading['text'] and 'lowest' not in reading['text']
    assert 'A:sum:total:fact-change-001' in reading['factIds']


def test_statistics_two_metrics_both_has_one_general_then_two_details():
    charts = [chart('A',code,calc,'ticket' if calc == 'sum' else 'ticket/day')
              for calc in ['sum','average_per_day'] for code in ['total','error']]
    panels = story_panels({'charts':charts,'blocks':[]})
    assert [p['kind'] for p in panels] == ['general','metric','metric']
    assert len(panels[0]['chartIds']) == 4


def test_rate_comparison_spells_out_percentage_points_only_once():
    c = chart('A','error_rate',unit='percent')
    c['points'][1].update(value=12.28, displayValue='12.28%',factId='b',evidenceId='ev2')
    document = {'charts':[c],'blocks':[],'facts':[
        {'factId':'A:sum:error_rate:story','kind':'temporal_narrative','displayValue':'unused','evidenceIds':['ev','ev2']},
        {'factId':'A:sum:error_rate:change','kind':'period_change','unit':'percentage_point',
         'displayValue':'0.28 pp','value':0.28,'evidenceIds':['ev','ev2']}]}
    text = story_panels(document)[0]['readings'][0]['text']
    assert 'chênh lệch 0.28 điểm phần trăm' in text
    assert ' pp' not in text


def test_template_13_general_keeps_relationships_contrast_and_manual_not_duplicate_phases():
    blocks = [{'blockId':key,'section':section,'source':source,'entityRef':'A',
               'calculation':calc,'factIds':['f']} for key,section,source,calc in [
                   ('phase','phases','ai','sum'),('relation','relationships','ai','sum'),
                   ('edited','phases','manual','sum'),('contrast','overview','deterministic',None)]]
    document = {'template':{'version':'1.3'},'charts':[chart('A','total'),chart('A','error')],'blocks':blocks}
    before = deepcopy(document)
    general = story_panels(document)[0]
    assert general['blockIds'] == ['contrast','relation','edited']
    assert document == before  # retained AI phase is still available in snapshot/findings


def test_identical_warnings_are_grouped_without_expanding_partial_scope():
    def issue(code, warnings):
        return {'entityRef':'A','entityLabel':'1.1. Camera','calculation':code,
                'metrics':[{'metricCode':m,'quality':{'limitations':w}} for m,w in warnings]}
    bundle = {'report':{'limitations':[], 'issues':[
        issue('sum',[('total',['Shared']),('error',['Shared','Error only'])]),
        issue('average_per_day',[('total',['Shared']),('error',['Shared'])])]}}
    notes = limitation_notes(bundle)
    assert notes[0] == 'Camera: Shared'
    assert len(notes) == 2
    assert 'Tổng báo sai (lỗi) (Tổng trong kỳ)' in notes[1]
    assert 'Trung bình/ngày' not in notes[1]


def test_compact_stages_preserve_gap_peak_and_source_delta_in_short_paragraphs():
    c = chart('A','error')
    c['points'] = [{**c['points'][0],'periodStart':f'2026-09-{7+i:02d}', 'periodEnd':f'2026-09-{7+i:02d}',
                    'value':v,'displayValue':str(v),'factId':f'p{i}','evidenceId':f'e{i}'} for i,v in enumerate([8,19,43,22])]
    facts = [{'factId':'delta','kind':'period_change','value':11,'displayValue':'11','unit':'ticket'}]
    stages = [
        {'startIndex':0,'endIndex':1,'startPeriodLabel':'first','endPeriodLabel':'second','transitionCount':1,
         'text':'first–second: tăng từ 8 lên 19.','factIds':['p0','p1','delta'],'evidenceIds':['e0','e1']},
        {'startIndex':1,'endIndex':2,'startPeriodLabel':'second','endPeriodLabel':'third','transitionCount':1,
         'text':'second–third: tăng từ 19 lên 43, đạt mức cao nhất trong khoảng.','factIds':['p1','p2'],'evidenceIds':['e1','e2']}]
    gap = {'startIndex':2,'text':'Thiếu kỳ; không xác định diễn biến.','factIds':['p2','p3'],'evidenceIds':['e2','e3']}
    rows = stage_readings(c,facts,c['points'],{'stages':stages,'gaps':[gap]})
    assert len(rows) == 2
    assert 'chênh lệch 11 ticket' in rows[0]['text']
    assert '07/09/2026 → 08/09/2026: error tăng' in rows[0]['text']
    assert 'cao nhất' in rows[0]['text'] and 'Thiếu kỳ' in rows[1]['text']
    assert rows[0]['factIds'] == ['p0','p1','delta','p2']
