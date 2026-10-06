"""Presentation-only chart/prose pairs over retained report points.

No text matching, new arithmetic, or reads from the current dashboard.
"""
from collections import OrderedDict


def legacy_story_panels(document: dict) -> list[dict]:
    panels = OrderedDict()
    for chart in document['charts']:
        panels.setdefault(chart['entityRef'], []).append(chart)
    result = []
    for entity, charts in panels.items():
        # Different units keep separate axes. Never overlay three unrelated units.
        units = list(dict.fromkeys(c['unit'] for c in charts))
        batches = [charts] if len(units) <= 2 else [[c for c in charts if c['unit'] == unit] for unit in units]
        assigned = set()
        for index, batch in enumerate(batches):
            calculations = list(dict.fromkeys(c['calculation'] for c in batch))
            blocks = [b for b in document['blocks'] if b['section'] not in {'overview', 'group_relationships'}
                      and b.get('entityRef') == entity and b.get('calculation') in calculations
                      and b['blockId'] not in assigned]
            assigned.update(b['blockId'] for b in blocks)
            result.append({'panelId': batch[0]['chartId'], 'entityRef': entity,
                           'entityLabel': batch[0]['entityLabel'], 'chartIds': [c['chartId'] for c in batch],
                           'blockIds': [b['blockId'] for b in blocks],
                           'figure': panel_figure(batch)})
    return result


def metric_readings(document: dict, chart: dict, *, compact: bool = False) -> list[dict]:
    """Read the retained Engine narrative, never infer ownership from AI prose."""
    prefix = f"{chart['entityRef']}:{chart['calculation']}:{chart['metricCode']}:"
    facts = [f for f in document.get('facts', []) if f['factId'].startswith(prefix)]
    points = [p for p in chart['points'] if p['value'] is not None]
    fact = next((f for f in facts if f.get('kind') == 'temporal_narrative'), None)
    if not fact:
        return []
    text = fact['displayValue']
    refs = [fact['factId']]
    if 2 <= len(points) < 4:
        # Two periods support a comparison, not extrema or a sustained trend.
        parts = []
        for index, (first, last) in enumerate(zip(points, points[1:]), 1):
            evidence = {first['evidenceId'], last['evidenceId']}
            change = next((f for f in facts if f['kind'] == 'period_change'
                           and set(f['evidenceIds']) == evidence), None)
            label = f"Kỳ {index} ({period_label(first)}) → Kỳ {index+1} ({period_label(last)})"
            if not change:
                parts.append(f"{label}: {first['displayValue']} → {last['displayValue']}; chưa có căn cứ so sánh hai kỳ liền nhau.")
                continue
            direction = 'tăng' if change['value'] > 0 else 'giảm' if change['value'] < 0 else 'giữ nguyên'
            unit = 'điểm phần trăm' if chart['metricCode'] == 'error_rate' else chart['unit']
            delta = change['displayValue'].removesuffix(' ' + change.get('unit', '')).removesuffix(' pp').removesuffix('%') if chart['metricCode'] == 'error_rate' else change['displayValue']
            parts.append(f"{label}: {chart['metricLabel']} {direction} từ {first['displayValue']} đến {last['displayValue']}, chênh lệch {delta} {unit}.")
            refs.extend([first['factId'], last['factId'], change['factId']])
        text = ' '.join(parts) + ('' if compact else ' Chưa đủ kỳ để đánh giá xu hướng.')
    # Engine summary can truncate windows with >6 phases. Use its complete,
    # already computed stages so 'below' never points to omitted information.
    issues = document.get('_bundle', {}).get('report', {}).get('issues', [])
    issue = next((i for i in issues if i['entityRef'] == chart['entityRef']
                  and i['calculation'] == chart['calculation']), None)
    metric = next((m for m in issue['metrics'] if m['metricCode'] == chart['metricCode']), None) if issue else None
    temporal = metric.get('periodAnalytics', {}).get('temporalStructure', {}) if metric else {}
    if compact and len(points) >= 4 and temporal.get('stages'):
        return stage_readings(chart, facts, points, temporal)
    if len(points) >= 4 and len(temporal.get('stages', [])) > 6:
        parts = sorted([*temporal['stages'], *temporal.get('gaps', [])], key=lambda p: p.get('startIndex', 0))
        text = temporal['overviewText'] + ' ' + ' '.join(p['text'] for p in parts)
    for stage in temporal.get('stages', []):
        if stage.get('startLabel') and stage.get('endLabel'):
            text = text.replace(stage['startLabel'] + '–' + stage['endLabel'],
                                stage['startLabel'] + ' → ' + stage['endLabel'])
    text = text.replace('Chỉ số', chart['metricLabel']).replace('trong toàn khoảng', 'trong thời gian được chọn')
    return [{'blockId': 'reading_' + chart['chartId'], 'text': text, 'source': 'deterministic',
             'section': 'phases', 'entityRef': chart['entityRef'], 'calculation': chart['calculation'],
             'metricCode': chart['metricCode'], 'factIds': list(dict.fromkeys(refs)),
             'evidenceIds': fact.get('evidenceIds', []), 'editable': False}]


def stage_readings(chart: dict, facts: list[dict], points: list[dict], temporal: dict) -> list[dict]:
    """Two chronological phases per paragraph, retaining all phases and gaps."""
    parts = sorted([*temporal['stages'], *temporal.get('gaps', [])], key=lambda s: s.get('startIndex', 0))
    result = []
    for offset in range(0, len(parts), 2):
        texts, refs, evidence = [], [], []
        for part in parts[offset:offset+2]:
            text = part['text']
            if 'endIndex' in part:
                first, last = points[part['startIndex']], points[part['endIndex']]
                old = part['startPeriodLabel'] + '–' + part['endPeriodLabel'] + ': '
                lead = period_label(first) + ' → ' + period_label(last) + ': ' + chart['metricLabel'] + ' '
                if text.startswith(old):
                    text = lead + text[len(old):]
                if part['transitionCount'] == 1:
                    change = next((f for f in facts if f['kind'] == 'period_change' and f['factId'] in part['factIds']), None)
                    if change and change['value'] != 0:
                        delta = change['displayValue'].removesuffix(' ' + change.get('unit', '')).removesuffix(' pp').removesuffix('%') if chart['metricCode'] == 'error_rate' else change['displayValue']
                        unit = 'điểm phần trăm' if chart['metricCode'] == 'error_rate' else chart['unit']
                        text = text.rstrip('.') + f", chênh lệch {delta} {unit}."
            texts.append(text)
            refs.extend(part['factIds']); evidence.extend(part.get('evidenceIds', []))
        result.append({'blockId':f"reading_{chart['chartId']}_{offset//2}", 'text':' '.join(texts),
            'source':'deterministic', 'section':'phases', 'entityRef':chart['entityRef'],
            'calculation':chart['calculation'], 'metricCode':chart['metricCode'],
            'factIds':list(dict.fromkeys(refs)), 'evidenceIds':list(dict.fromkeys(evidence)), 'editable':False})
    return result


def period_label(point: dict) -> str:
    """A single readable interval; never join two ranges with a third dash."""
    first, last = point['periodStart'], point['periodEnd']
    fmt = lambda d: '/'.join(reversed(d.split('-')))
    if first == last:
        return fmt(first)
    if first[:7] == last[:7]:
        return first[8:] + '–' + fmt(last)
    return fmt(first) + ' – ' + fmt(last)


def story_panels(document: dict) -> list[dict]:
    # Retained reports keep their original template. New reports use 1.2.
    if document.get('template', {}).get('version') in {'1.0', '1.1'}:
        return legacy_story_panels(document)
    compact = document.get('template', {}).get('version') == '1.3'
    entities = OrderedDict()
    for chart in document['charts']:
        entities.setdefault(chart['entityRef'], []).append(chart)
    result = []
    for entity, charts in entities.items():
        codes = list(dict.fromkeys(c['metricCode'] for c in charts))
        blocks = [b for b in document['blocks'] if b['section'] not in {'overview', 'group_relationships'}
                  and b.get('entityRef') == entity]
        if compact and len(codes) > 1:
            # Generated phase prose duplicates the complete metric stages below.
            # Keep it in the saved document/findings, but use joint relations in
            # the general view. Manual edits must never disappear.
            joint = [b for b in blocks if b['section'] == 'relationships' or b.get('source') == 'manual']
            contrasts = [b for b in document['blocks'] if b['section'] == 'overview'
                         and b.get('entityRef') == entity and not b.get('candidateId') and b.get('factIds')]
            blocks = contrasts + joint if joint or contrasts else blocks[:1]
        assigned = set()
        if len(codes) > 1:
            # Statistics both can have three units. Split the general view by
            # calculation first, not into misleading three-axis overlays.
            calculations = list(dict.fromkeys(c['calculation'] for c in charts))
            batches_by_calculation = [charts] if len({c['unit'] for c in charts}) <= 2 else [
                [c for c in charts if c['calculation'] == calc] for calc in calculations]
            for batch in batches_by_calculation:
                units = list(dict.fromkeys(c['unit'] for c in batch))
                batches = [batch] if len(units) <= 2 else [[c for c in batch if c['unit'] == unit] for unit in units]
                for index, group in enumerate(batches):
                    owned = [b['blockId'] for b in blocks if (not b.get('calculation') or b.get('calculation') in {c['calculation'] for c in group})
                             and b['blockId'] not in assigned]
                    assigned.update(owned)
                    result.append({'panelId': 'general_' + group[0]['chartId'], 'kind': 'general',
                        'title': 'Diễn biến tổng quát' + (f" · {group[0]['unit']}" if len(batches) > 1 else ''),
                        'entityRef': entity, 'entityLabel': group[0]['entityLabel'],
                        'chartIds': [c['chartId'] for c in group], 'blockIds': owned, 'readings': [],
                        'figure': panel_figure(group)})
        for code in codes:
            batch = [c for c in charts if c['metricCode'] == code]
            owned = [b['blockId'] for b in blocks if b['blockId'] not in assigned] if len(codes) == 1 else []
            assigned.update(owned)
            result.append({'panelId': batch[0]['chartId'], 'kind': 'metric', 'title': batch[0]['metricLabel'],
                'entityRef': entity, 'entityLabel': batch[0]['entityLabel'],
                'chartIds': [c['chartId'] for c in batch], 'blockIds': owned,
                'readings': [] if owned else [r for c in batch for r in metric_readings(document, c, compact=compact)],
                'figure': panel_figure(batch)})
    return result


def chart_style(chart: dict) -> tuple[str, str]:
    line = chart['calculation'] == 'average_per_day' or chart['metricCode'] == 'error_rate'
    colors = {'total': ('#8ecae6', '#0077b6'), 'error': ('#d1495b', '#9d0208'), 'error_rate': ('#ff9f1c', '#ff9f1c')}
    return ('scatter' if line else 'bar', colors.get(chart['metricCode'], ('#0077b6', '#0077b6'))[int(line)])


def panel_figure(charts: list[dict]) -> dict:
    units = list(dict.fromkeys(c['unit'] for c in charts))
    dates = sorted({p['periodStart'] for c in charts for p in c['points']})
    data = []
    for chart in charts:
        kind, color = chart_style(chart)
        axis = 'y' if chart['unit'] == units[0] else 'y2'
        data.append({'type': kind, 'mode': 'lines+markers' if kind == 'scatter' else None,
                     **({'width': .22 if len(dates) == 1 else .7} if kind == 'bar' else {}),
                     'name': chart['metricLabel'] + (' · Tỷ lệ trong kỳ' if chart['metricCode'] == 'error_rate' else ' · ' + chart['calculationLabel']), 'yaxis': axis,
                     'x': [p['periodStart'] for p in chart['points']], 'y': [p['value'] for p in chart['points']],
                     'meta': {'reportChartId': chart['chartId']}, 'connectgaps': False,
                     'line': {'color': color, 'width': 3}, 'marker': {'color': color, 'size': 7},
                     'opacity': .72 if kind == 'bar' and chart['metricCode'] == 'total' else 1,
                     'customdata': [[p['periodLabel'], p['displayValue'], chart['unit']] for p in chart['points']],
                     'hovertemplate': '%{customdata[0]}<br>%{fullData.name}: %{customdata[1]} %{customdata[2]}<extra></extra>'})
    points = {p['periodStart']: p for c in reversed(charts) for p in c['points'] if p['value'] is not None}
    def label(day):
        point = points.get(day)
        if not point:
            return 'Thiếu dữ liệu'
        first, last = point['periodStart'], point['periodEnd']
        fmt = lambda d: '/'.join(reversed(d[5:].split('-')))
        if first[:4] != last[:4] or len({d[:4] for d in dates}) > 1:
            fmt = lambda d: '/'.join(reversed(d.split('-')))
        return fmt(first) if first == last else f'{fmt(first)} – {fmt(last)}'
    layout = {'barmode': 'overlay', 'hovermode': 'x unified', 'showlegend': True,
              'xaxis': {'type': 'category', 'categoryorder': 'array', 'categoryarray': dates,
                        'tickmode': 'array', 'tickvals': dates, 'ticktext': [label(day) for day in dates], 'tickangle': 0},
              'yaxis': {'title': {'text': units[0]}, 'rangemode': 'tozero', 'gridcolor': '#eef0f4'},
              'uirevision': charts[0]['chartId']}
    if len(units) == 2:
        layout['yaxis2'] = {'title': {'text': units[1]}, 'overlaying': 'y', 'side': 'right', 'showgrid': False,
                            'rangemode': 'tozero'}
    if len(dates) == 1:
        layout['xaxis']['range'] = [-1.5, 1.5]
    return {'data': data, 'layout': layout}
