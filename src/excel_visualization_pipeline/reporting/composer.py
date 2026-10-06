"""Five report sections over a single retained Analytics Engine bundle.

No new KPI arithmetic, cross-unit ranking or prose-generated coordinates.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import re
from uuid import uuid4

from ..storage.connection import utc_now
from ..visualization import display_entity_label
from ..ai.reading import plain_text

TEMPLATE = {'id': 'cx-period-report', 'version': '1.3', 'schemaVersion': 'cx-report-v1',
            'sections': ['metadata', 'executive_summary', 'kpi_overview', 'period_story', 'key_findings']}
METRIC_LABELS = {'total': 'Tổng số ghi nhận', 'error': 'Tổng báo sai (lỗi)', 'error_rate': 'Tỷ lệ báo sai'}
CALC_LABELS = {'sum': 'Tổng trong kỳ', 'average_per_day': 'Trung bình/ngày'}


def identity(*parts) -> str:
    return sha256('|'.join(map(str, parts)).encode('utf-8')).hexdigest()[:20]


def readable(text: str) -> str:
    return re.sub(r'^\s*\d+(?:\.\d+)*[.)]?\s+', '', text).strip()


def presentation_text(bundle: dict, text: str) -> str:
    for issue in bundle['report']['issues']:
        text = text.replace(issue['entityLabel'], readable(issue['entityLabel']))
    for old, new in [('Báo sai/Lỗi', 'Tổng báo sai (lỗi)'), ('Tổng số trung bình/ngày', 'Tổng số ghi nhận trung bình/ngày'),
                     ('Tổng số', 'Tổng số ghi nhận'), ('% báo sai', 'Tỷ lệ báo sai')]:
        # Avoid substituting a label inside its own presentation form twice.
        if old == 'Tổng số':
            text = re.sub(r'Tổng số(?! ghi nhận)', new, text)
        else:
            text = text.replace(old, new)
    return plain_text(text)


def block_id(issue: dict, section: str, paragraph: dict) -> str:
    return 'block_' + identity(issue['entityRef'], issue['calculation'], section, paragraph['candidateId'])


def narrative_blocks(bundle: dict) -> list[dict]:
    blocks = []
    for issue in bundle['report']['issues']:
        for section in ('overview', 'phases', 'relationships'):
            for paragraph in issue['report'][section]:
                blocks.append({**deepcopy(paragraph), 'blockId': block_id(issue, section, paragraph),
                    'section': section, 'entityRef': issue['entityRef'], 'entityLabel': readable(issue['entityLabel']),
                    'calculation': issue['calculation']})
    # Overview promotion already de-duplicates the original issue paragraphs.
    for index, paragraph in enumerate(bundle['report']['overview']):
        issue = next((i for i in bundle['report']['issues'] if i['entityRef'] == paragraph.get('entityRef')
                      and i['calculation'] == paragraph.get('calculation')), None)
        section = next((s for s, ids in issue['snapshot']['synthesis']['reportPlan']['sections'].items()
                        if paragraph.get('candidateId') in ids), 'overview') if issue else 'overview'
        blocks.append({**deepcopy(paragraph), 'blockId': block_id(issue, section, paragraph) if issue and paragraph.get('candidateId')
                       else 'context_' + identity(index, paragraph['text']), 'section': 'overview',
                       'entityLabel': readable(issue['entityLabel']) if issue else '',
                       'editable': bool(issue and paragraph.get('candidateId'))})
    for index, paragraph in enumerate(bundle['report']['relationships']):
        blocks.append({**deepcopy(paragraph), 'blockId': 'group_' + identity(index, paragraph['text']),
                       'section': 'group_relationships', 'entityLabel': 'Các vấn đề trong nhóm', 'editable': False})
    for block in blocks:
        block['text'] = presentation_text(bundle, block['text'])
    return blocks


def chart_documents(bundle: dict) -> list[dict]:
    charts = []
    for issue in bundle['report']['issues']:
        for metric in issue['metrics']:
            if not metric['series']:
                continue
            points = []
            previous = None
            for row in metric['series']:
                if previous and date.fromisoformat(previous['periodEnd']) + timedelta(days=1) < date.fromisoformat(row['periodStart']):
                    points.append({'periodStart': (date.fromisoformat(previous['periodEnd']) + timedelta(days=1)).isoformat(),
                                   'periodEnd': row['periodStart'], 'periodLabel': 'Thiếu dữ liệu', 'value': None,
                                   'displayValue': 'Chưa ghi nhận', 'factId': None, 'evidenceId': None})
                points.append(deepcopy(row))
                previous = row
            charts.append({'chartId': 'chart_' + identity(issue['entityRef'], issue['calculation'], metric['metricCode']),
                'entityRef': issue['entityRef'], 'entityLabel': readable(issue['entityLabel']),
                'metricCode': metric['metricCode'], 'metricLabel': METRIC_LABELS[metric['metricCode']],
                'calculation': issue['calculation'], 'calculationLabel': CALC_LABELS[issue['calculation']],
                'unit': metric['unit'], 'aggregationRule': metric['aggregationRule'], 'points': points,
                'quality': deepcopy(metric['quality'])})
    return charts


def select_findings(bundle: dict, charts: list[dict], blocks: list[dict]) -> list[dict]:
    chart_lookup = {(c['entityRef'], c['calculation'], c['metricCode']): c for c in charts}
    readings = {b['blockId']: b for b in blocks}
    buckets = []
    for issue in bundle['report']['issues']:
        candidates = issue['snapshot']['synthesis']['candidates']
        plan = issue['snapshot']['synthesis']['reportPlan']['sections']
        pool = [c for c in candidates if c['candidateId'] in plan['relationships'] or
                (c.get('section') == 'phases') or c['candidateId'] in issue['snapshot']['synthesis']['selectedCandidateIds']]
        pool = [c for c in pool if c['kind'] not in {'window_overview', 'descriptive_only', 'period_comparison', 'short_sequence', 'unchanged'}]
        pool.sort(key=lambda c: (-c.get('priority', 0), c.get('section') == 'phases'))
        rows, signatures = [], set()
        for candidate in pool:
            anchors = []
            # Match Engine point fact identity, never a model-supplied date/value.
            for code in candidate['metricCodes']:
                chart = chart_lookup.get((issue['entityRef'], issue['calculation'], code))
                if not chart:
                    continue
                anchor_refs = {a['factId'] for a in candidate['anchors'] if a['metricCode'] == code}
                points = [p for p in chart['points'] if p['factId'] in anchor_refs and p['value'] is not None]
                if not points:
                    continue
                # Keep boundary and tied extrema points from this candidate.
                landmark_points = [points[0], points[-1], min(points, key=lambda p: p['value']), max(points, key=lambda p: p['value'])]
                for point in {p['factId']: p for p in landmark_points}.values():
                    anchors.append({'anchorId': 'anchor_' + identity(chart['chartId'], point['periodStart'], point['periodEnd']),
                        'chartId': chart['chartId'], 'entityRef': issue['entityRef'], 'metricCode': code,
                        'calculation': issue['calculation'], **{k: point[k] for k in
                        ('periodStart', 'periodEnd', 'periodLabel', 'value', 'displayValue', 'factId', 'evidenceId')}})
            if not anchors:
                continue
            signature = tuple(sorted(a['factId'] for a in anchors))
            if signature in signatures:
                continue
            signatures.add(signature)
            section = next((s for s, ids in plan.items() if candidate['candidateId'] in ids), 'relationships')
            bid = block_id(issue, section, candidate)
            paragraph = readings.get(bid)
            # Promoted paragraphs still carry their grounded identity.
            if not paragraph:
                paragraph = next((b for b in blocks if b.get('entityRef') == issue['entityRef']
                    and b.get('calculation') == issue['calculation'] and b.get('candidateId') == candidate['candidateId']), None)
            dates = {a['periodStart'] for a in anchors}
            rows.append({'findingId': 'finding_' + identity(issue['entityRef'], issue['calculation'], candidate['candidateId']),
                'candidateId': candidate['candidateId'], 'kind': candidate['kind'], 'blockId': paragraph['blockId'] if paragraph else None,
                'entityRef': issue['entityRef'], 'entityLabel': readable(issue['entityLabel']), 'calculation': issue['calculation'],
                'title': 'Liên hệ giữa các KPI' if len(candidate['metricCodes']) > 1 else METRIC_LABELS[candidate['metricCodes'][0]],
                'anchorType': 'multi_metric' if len(candidate['metricCodes']) > 1 else 'interval' if len(dates) > 1 else 'point',
                'text': paragraph['text'] if paragraph else presentation_text(bundle, candidate['fallbackText']),
                'source': paragraph['source'] if paragraph else 'deterministic', 'anchors': anchors,
                'factIds': paragraph['factIds'] if paragraph else candidate['factIds'],
                'evidenceIds': candidate['evidenceIds']})
        buckets.append(rows)
    result = []
    # Shared issue movements get a place before per-issue highlights. These are
    # Engine relations, not statistical correlation or unverified causality.
    for paragraph in (b for b in blocks if b['section'] == 'group_relationships'):
        anchors = []
        refs = set(paragraph.get('factIds', []))
        for chart in charts:
            if chart['calculation'] != paragraph.get('calculation'):
                continue
            points = [p for p in chart['points'] if p['factId'] in refs and p['value'] is not None]
            for point in {p['factId']: p for p in (points[:1] + points[-1:])}.values():
                anchors.append({'anchorId':'anchor_' + identity(chart['chartId'],point['periodStart'],point['periodEnd']),
                    'chartId':chart['chartId'],'entityRef':chart['entityRef'],'metricCode':chart['metricCode'],'calculation':chart['calculation'],
                    **{k:point[k] for k in ('periodStart','periodEnd','periodLabel','value','displayValue','factId','evidenceId')}})
        if len({a['entityRef'] for a in anchors}) > 1:
            result.append({'findingId':'finding_' + identity(paragraph['blockId']), 'candidateId':None,
                'kind':'cross_issue_movement', 'blockId':paragraph['blockId'], 'entityRef':bundle['context']['parentEntityRef'],
                'entityLabel':'Các vấn đề trong nhóm', 'calculation':paragraph['calculation'], 'title':'Diễn biến giữa các vấn đề',
                'anchorType':'multi_metric', 'text':paragraph['text'], 'source':'deterministic', 'anchors':anchors,
                'factIds':paragraph['factIds'], 'evidenceIds':paragraph['evidenceIds']})
            break
    while any(buckets) and len(result) < 12:
        for rows in buckets:
            if rows and len(result) < 12:
                result.append(rows.pop(0))
    return result


def summary_blocks(blocks: list[dict], findings: list[dict]) -> list[dict]:
    """Executive Summary is a short extraction of accepted prose, not another ungrounded model request."""
    overviews = [b for b in blocks if b['section'] == 'overview' and b.get('factIds')]
    entities = list(dict.fromkeys(b.get('entityRef') for b in overviews if b.get('entityRef')))
    chosen = []
    # One time-course paragraph per issue before a second paragraph about the
    # same issue. Prefer a quantified accepted overview, not a daily fact list.
    quantified = lambda text: bool(re.search(r'(?:từ|lên|xuống|chênh lệch|giữ nguyên ở|cao nhất|thấp nhất).*\d', text))
    for entity in entities[:2]:
        windows = [b for b in overviews if b.get('entityRef') == entity and str(b.get('candidateId', '')).startswith('report-overview')]
        if windows:
            chosen.append(next((b for b in windows if quantified(b['text'])), windows[0]))
    if len(chosen) < 2:
        # Calculation contrasts have no candidate: keep the total AND daily
        # average values together, otherwise the warning is easy to misread.
        contrasts = [b for b in overviews if b.get('entityRef') and not b.get('candidateId')]
        others = [b for b in overviews if b not in chosen and b not in contrasts]
        chosen += (contrasts + others)[:2-len(chosen)]
    result = []
    for block in chosen:
        # Keep complete sentences; decimal points and dates are not sentence separators.
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÀ-ỴĐ])', block['text'])
        selected_sentences = sentences[:1]
        # Retain one quantitative sentence if available. A date alone does not
        # satisfy this evidence role; neither do endpoint-only comparisons.
        quantitative = next((s for s in sentences[1:] if quantified(s)), None)
        dependencies = [block]
        if quantitative:
            selected_sentences.append(quantitative)
        elif len(sentences) > 1:
            selected_sentences.append(sentences[1])
        if not quantified(' '.join(selected_sentences)):
            support = next((b for b in blocks if b['section'] == 'phases' and b.get('entityRef') == block.get('entityRef')
                            and b.get('calculation') == block.get('calculation') and b.get('factIds') and quantified(b['text'])), None)
            if support:
                sentence = next(s for s in re.split(r'(?<=[.!?])\s+(?=[A-ZÀ-ỴĐ])', support['text']) if quantified(s))
                selected_sentences = [selected_sentences[0], sentence]
                dependencies.append(support)
        if block.get('entityRef') and not block.get('candidateId'):
            selected_sentences = sentences[:3]
        text = ' '.join(selected_sentences)
        label = block.get('entityLabel', '')
        if len(entities) == 1 and label:
            # The report heading already identifies this issue. Keep calculation
            # identity, but do not repeat the full issue name in every paragraph.
            for prefix in (label + ' · ', label + ': '):
                if text.startswith(prefix):
                    text = text[len(prefix):]
                    break
        if len(entities) > 1 and label and label.lower() not in text.lower():
            text = f"{label} · {CALC_LABELS[block['calculation']]}: {text}"
        sources = list(dict.fromkeys(b['source'] for b in dependencies))
        result.append({**deepcopy(block), 'text': text,
                       'source': sources[0] if len(sources) == 1 else 'mixed', 'contributingSources': sources,
                       'factIds': list(dict.fromkeys(f for b in dependencies for f in b['factIds'])),
                       'dependencyBlockIds': [b['blockId'] for b in dependencies]})
    if not result:
        result = [deepcopy(b) for b in blocks if b['section'] == 'overview'][:1]
    shared = next((b for b in blocks if b['section'] == 'group_relationships'), None)
    if shared and len(result) < 3:
        result.append(deepcopy(shared))
    # Selecting/removing chart highlights does not rewrite the underlying analysis.
    # It is intentionally not a list of each selected finding.
    for row in result:
        row.setdefault('dependencyBlockIds', [row['blockId']])
    return result


def compose(bundle: dict, title: str, *, prior: dict | None = None) -> dict:
    now = utc_now()
    charts, blocks = chart_documents(bundle), narrative_blocks(bundle)
    findings = select_findings(bundle, charts, blocks)
    previous_selection = set(prior['selectedFindingIds']) if prior else None
    selected = ([f['findingId'] for f in findings if f['findingId'] in previous_selection]
                if previous_selection is not None else [f['findingId'] for f in findings[:5]])
    kpis = []
    for chart in charts:
        points = [p for p in chart['points'] if p['value'] is not None]
        current = points[-1]
        # Latest observed level, not a bogus SUM over cumulative/rate/average series.
        kpis.append({**{k: chart[k] for k in ('chartId', 'entityRef', 'entityLabel', 'metricCode', 'metricLabel', 'unit', 'calculation', 'calculationLabel', 'quality')},
            'valueRole': 'latest_observed_period', 'value': current['value'], 'displayValue': current['displayValue'],
            'periodStart': current['periodStart'], 'periodEnd': current['periodEnd'], 'periodLabel': current['periodLabel'],
            'factIds': [current['factId']], 'evidenceIds': [current['evidenceId']],
            'change': deepcopy(current.get('change'))})
    limits = limitation_notes(bundle)
    document = {'schemaVersion': TEMPLATE['schemaVersion'], 'template': deepcopy(TEMPLATE),
        'reportId': prior['reportId'] if prior else 'rpt_' + uuid4().hex,
        'revision': prior['revision'] + 1 if prior else 1, 'title': title,
        'createdAt': prior['createdAt'] if prior else now, 'updatedAt': now,
        'context': deepcopy(bundle['context']), 'window': deepcopy(bundle['window']),
        'dataAsOf': deepcopy(bundle['dataAsOf']), 'generation': {'status': bundle['status'],
            'provider': deepcopy(bundle['provider']), 'validation': deepcopy(bundle['validation'])},
        'kpis': kpis, 'charts': charts, 'blocks': blocks, 'executiveSummary': summary_blocks(blocks, findings),
        'findings': findings, 'selectedFindingIds': selected, 'limitations': limits,
        'userNotes': prior.get('userNotes', '') if prior else '',
        'manualEdits': deepcopy(prior.get('manualEdits', [])) if prior else [],
        'facts': deepcopy(bundle['facts']), 'evidence': deepcopy(bundle['evidence']),
        '_bundle': deepcopy(bundle)}
    return document


def limitation_notes(bundle: dict) -> list[str]:
    """Group identical warnings by their typed scope, not by fuzzy prose."""
    limits = list(dict.fromkeys(bundle['report']['limitations']))
    groups, members = {}, {}
    for issue in bundle['report']['issues']:
        entity = issue['entityRef']
        members.setdefault(entity, set()).update((issue['calculation'], m['metricCode']) for m in issue['metrics'])
        for metric in issue['metrics']:
            for warning in metric['quality']['limitations']:
                group = groups.setdefault((entity, warning), {'label':readable(issue['entityLabel']), 'members':set()})
                group['members'].add((issue['calculation'], metric['metricCode']))
    for (entity, warning), group in groups.items():
        label = group['label']
        if group['members'] != members[entity]:
            # Do not imply a warning applies to unaffected metric/calculation pairs.
            scopes = [f"{METRIC_LABELS[code]} ({CALC_LABELS[calc]})" for calc, code in sorted(group['members'])]
            label += ' · ' + ' / '.join(scopes)
        note = label + ': ' + warning
        if note not in limits:
            limits.append(note)
    return limits


def validate_edit(service, document: dict, block: dict, text: str) -> None:
    issue = next((i for i in document['_bundle']['report']['issues'] if i['entityRef'] == block.get('entityRef')
                  and i['calculation'] == block.get('calculation')), None)
    if not issue or not block.get('candidateId'):
        raise ValueError('Đoạn tổng hợp này không hỗ trợ sửa nhận định. Có thể thêm ghi chú riêng.')
    candidate = next((c for c in issue['snapshot']['synthesis']['candidates'] if c['candidateId'] == block['candidateId']), None)
    if not candidate:
        raise ValueError('Không tìm thấy căn cứ của đoạn diễn giải.')
    lower = text.lower()
    if any(i['entityLabel'] != issue['entityLabel'] and i['entityLabel'].lower() in lower for i in document['_bundle']['report']['issues']):
        raise ValueError('Diễn giải không được đổi sang vấn đề khác.')
    if (issue['calculation'] == 'sum' and 'trung bình' in lower) or (issue['calculation'] == 'average_per_day' and 'tổng trong kỳ' in lower):
        raise ValueError('Diễn giải không đúng cách tính của đoạn này.')
    import json
    section = next(s for s, ids in issue['snapshot']['synthesis']['reportPlan']['sections'].items() if candidate['candidateId'] in ids)
    claim = {'candidateId': candidate['candidateId'], 'section': section,
             'claimType': candidate['kind'], 'text': text, 'factIds': candidate['factIds']}
    result = service.validator.validate(json.dumps({'schemaVersion': 'ai-narrative-v5', 'analysisId': document['_bundle']['analysisId'],
        'status': 'ready', 'claims': [claim]}, ensure_ascii=False), issue['snapshot'])
    if result.errors:
        raise ValueError('Nội dung chưa đối chiếu được với dữ liệu: ' + ', '.join(result.errors) + '. Số liệu cũ vẫn được giữ nguyên; ý kiến nghiệp vụ có thể đặt ở Ghi chú.')


def revise(document: dict, *, title: str | None = None, notes: str | None = None,
           selected: list[str] | None = None, edits: dict[str, str] | None = None, service=None) -> dict:
    updated = deepcopy(document)
    if selected is not None:
        if len(set(selected)) > 5 or not set(selected) <= {f['findingId'] for f in document['findings']}:
            raise ValueError('Chọn tối đa 5 điểm được hệ thống đề xuất; không nhận điểm ngoài dữ liệu báo cáo.')
        updated['selectedFindingIds'] = list(dict.fromkeys(selected))
    if title is not None:
        updated['title'] = title
    if notes is not None:
        updated['userNotes'] = notes
    for key, text in (edits or {}).items():
        block = next((b for b in updated['blocks'] if b['blockId'] == key), None)
        if block is None:
            raise ValueError('Đoạn diễn giải không tồn tại trong bản nháp.')
        validate_edit(service, updated, block, text)
        updated['manualEdits'].append({'blockId': key, 'originalText': block['text'], 'latestText': text,
                                      'editedAt': utc_now(), 'author': 'local_unverified_user'})
        block.update(text=text, source='manual', validation='accepted')
        for finding in updated['findings']:
            if finding.get('blockId') == key:
                finding.update(text=text, source='manual')
    updated['executiveSummary'] = summary_blocks(updated['blocks'], updated['findings'])
    updated['revision'] += 1
    updated['updatedAt'] = utc_now()
    return updated


def public_document(document: dict, review: dict, *, current_import: str | None) -> dict:
    from .story import story_panels
    result = {key: deepcopy(value) for key, value in document.items() if not key.startswith('_')}
    result['review'] = review
    result['freshness'] = {'newerDataAvailable': current_import is not None and current_import != document['dataAsOf']['committedImportRef']}
    result['storyPanels'] = story_panels(document)
    return result
