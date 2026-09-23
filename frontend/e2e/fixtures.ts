import type { Page, Route } from '@playwright/test';

type HarnessOptions = {
  provenanceFailures?: number;
  provenanceDelayMs?: number;
  workspaceDelayMs?: number;
  workspaceDelaysMs?: number[];
  workspaceFailureRequests?: number[];
  legacyUnavailable?: boolean;
};
export type ApiCall = { pathname: string; search: string; method: string };

const dates = ['2026-09-16T00:00:00', '2026-09-17T00:00:00'];

function exactTrace(name: string, prefix: string, values = [10, 14]) {
  return {
    type: 'bar', name, x: dates, y: values,
    ids: [`obs_${prefix}_1`, `obs_${prefix}_2`],
    meta: { lineage: { contractVersion: 1, kind: 'exact-observation', selectable: true, lineageRefs: [`lin_${prefix}_1`, `lin_${prefix}_2`] } },
    hovertemplate: '%{x}<br>%{y}<extra></extra>',
  };
}

function helperTrace() {
  return {
    type: 'scatter', name: 'tooltip-helper', mode: 'markers', x: dates, y: [0, 0],
    marker: { opacity: 0, size: 28 }, showlegend: false, hoverinfo: 'skip',
  };
}

function figure(prefix: string, name = 'Tổng số', values = [10, 14]) {
  return {
    data: [exactTrace(name, prefix, values), helperTrace()],
    layout: { hovermode: 'closest', xaxis: { type: 'date' }, yaxis: { rangemode: 'tozero' }, showlegend: true },
  };
}

const entities = [
  { entity_id: 'root', parent_entity_id: null, entity_label: 'VSO', entity_path: 'VSO', entity_level: 'project', entity_depth: 0, effective_unit: 'ticket' },
  { entity_id: 'child-a', parent_entity_id: 'root', entity_label: 'Entity A', entity_path: 'VSO / Entity A', entity_level: 'team', entity_depth: 1, effective_unit: 'ticket' },
  { entity_id: 'child-b', parent_entity_id: 'root', entity_label: 'Entity B', entity_path: 'VSO / Entity B', entity_level: 'team', entity_depth: 1, effective_unit: 'ticket' },
];

function workspace(url: URL, options: HarnessOptions) {
  const children = url.searchParams.get('scope') === 'children';
  const compared = (url.searchParams.get('comparison_entities') || '').split(',').filter(Boolean);
  const viewMode = url.searchParams.get('mode');
  const valueOffset = viewMode === 'week' ? 1 : viewMode === 'month' ? 2 : 0;
  const viewFigure = (prefix: string, name?: string, values = [10, 14]) => figure(prefix, name, values.map(value => value + valueOffset));
  return {
    window: { start: viewMode === 'month' ? '2026-09-01' : viewMode === 'week' ? '2026-09-10' : '2026-09-16', end: '2026-09-17' }, selectedEntity: 'root',
    scopeIds: children ? ['child-a', 'child-b'] : ['root'],
    overview: children
      ? [
          { entityId: 'child-a', title: 'Entity A', figure: viewFigure('child_a') },
          { entityId: 'child-b', title: 'Entity B', figure: viewFigure('child_b') },
        ]
      : [{ entityId: 'root', title: 'VSO', figure: options.legacyUnavailable ? {
          ...figure('overview'),
          data: [
            ...figure('overview').data,
            { type: 'bar', name: 'Dữ liệu cũ', x: [dates[0]], y: [3], ids: [null], meta: { lineage: { contractVersion: 1, kind: 'exact-observation', selectable: true, lineageRefs: [null] } } },
          ],
        } : viewFigure('overview') }],
    statistics: [{ entityId: 'root', title: 'VSO', figure: viewFigure('statistics', 'SUM Tổng số') }],
    statisticsPeriods: [{ start: '2026-09-16', label: '16/09/2026', complete: true }],
    comparisonCandidates: [
      { entity_id: 'child-a', entity_label: 'Entity A', effective_unit: 'ticket' },
      { entity_id: 'child-b', entity_label: 'Entity B', effective_unit: 'ticket' },
    ],
    comparison: compared.length >= 2 ? {
      data: [exactTrace('Entity A', 'comparison_a', [8, 12]), exactTrace('Entity B', 'comparison_b', [7, 11])],
      layout: { hovermode: 'x unified', xaxis: { type: 'date' }, yaxis: { rangemode: 'tozero' } },
    } : null,
    capabilities: { lineage: { contractVersion: 1, exactObservation: true, aggregateObservation: true } },
    audit: { total: 1, offset: 0, rows: [{ date: '2026-09-17', entity_path: 'VSO', metric_normalized: 'Tổng số', raw_value: '14', display_value: '14', chart_value: 14, value_kind: 'numeric', sheet_name: 'Daily', cell_address: 'D7', validation_status: 'valid' }] },
  };
}

function provenance(observationRef: string, lineageRef: string) {
  const historical = observationRef.endsWith('_2');
  return {
    contractVersion: 1, status: 'available', observationRef, lineageRef,
    context: { project: { label: 'VSO' }, entity: { ref: 'root', label: 'VSO', level: 'project', hierarchyPath: ['Automated CX Report', 'VSO'], effectiveUnit: 'ticket' }, metric: { key: 'total', label: 'Tổng số' }, observedDate: historical ? '2026-09-17' : '2026-09-16' },
    source: { workbookName: 'vso.xlsx', workbookHash: { algorithm: 'sha256', value: 'a'.repeat(64) }, sheet: 'Daily', cell: historical ? 'D7' : 'C7', cellReference: historical ? 'Daily!D7' : 'Daily!C7' },
    values: { raw: { text: historical ? '14' : '10', type: 'number' }, display: historical ? '14' : '10', chart: historical ? 14 : 10, valueKind: 'numeric', numberFormat: '0' },
    transformation: { parserRule: 'numeric', parserConfidence: 'high', note: null },
    validation: { status: 'valid', issues: [] },
    revision: { revisionRef: historical ? 'rev_old' : 'rev_current', changeType: 'inserted', recordedAt: '2026-09-17T08:00:00Z', state: historical ? 'superseded' : 'current', revisionCurrent: !historical, sourcePresenceCurrent: true },
    import: { mode: 'incremental', committedAt: '2026-09-17T08:00:00Z', importRef: 'imp_1', attemptRef: 'attempt_1' },
    freshness: { observedThrough: '2026-09-17', isCurrent: !historical, newerSnapshotAvailable: historical, newerSourceDataAvailable: historical, sourceCommittedAt: '2026-09-17T08:00:00Z' },
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

export async function installApiHarness(page: Page, options: HarnessOptions = {}) {
  const calls: ApiCall[] = [];
  let failuresLeft = options.provenanceFailures ?? 0;
  let workspaceRequestCount = 0;
  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    calls.push({ pathname: url.pathname, search: url.search, method: request.method() });
    if (url.pathname === '/api/bootstrap') return fulfillJson(route, { projects: [{ label: 'VSO', records: 12, chartable: 12, entities: 3, units: 1, minDate: '2026-09-16', maxDate: '2026-09-17' }] });
    if (url.pathname === '/api/projects/VSO/entities') return fulfillJson(route, { entities });
    if (url.pathname === '/api/projects/VSO/workspace') {
      workspaceRequestCount += 1;
      const delay = options.workspaceDelaysMs?.[workspaceRequestCount - 1] ?? options.workspaceDelayMs ?? 0;
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));
      if (options.workspaceFailureRequests?.includes(workspaceRequestCount)) return fulfillJson(route, { detail: 'Mất kết nối workspace thử nghiệm' }, 503);
      return fulfillJson(route, workspace(url, options));
    }
    if (/\/observations\/[^/]+\/provenance$/.test(url.pathname)) {
      if (options.provenanceDelayMs) await new Promise(resolve => setTimeout(resolve, options.provenanceDelayMs));
      if (failuresLeft > 0) { failuresLeft -= 1; return fulfillJson(route, { detail: 'Mất kết nối thử nghiệm' }, 500); }
      const observationRef = decodeURIComponent(url.pathname.split('/').at(-2) || '');
      return fulfillJson(route, provenance(observationRef, url.searchParams.get('lineageRef') || ''));
    }
    if (url.pathname === '/api/projects/VSO/audit/lookup') {
      const observationRef = url.searchParams.get('observationRef') || '';
      const lineageRef = url.searchParams.get('lineageRef') || '';
      const p = provenance(observationRef, lineageRef);
      return fulfillJson(route, { contractVersion: 1, observationRef, lineageRef, row: { date: p.context.observedDate, entity_path: 'VSO', metric_normalized: 'Tổng số', raw_value: p.values.raw.text, display_value: p.values.display, chart_value: p.values.chart, value_kind: 'numeric', sheet_name: 'Daily', cell_address: p.source.cell, validation_status: 'valid' }, recommendedContext: { entityRef: 'root', start: p.context.observedDate, end: p.context.observedDate, metric: 'Tổng số' } });
    }
    if (/\/observations\/[^/]+\/revisions$/.test(url.pathname)) {
      const observationRef = decodeURIComponent(url.pathname.split('/').at(-2) || '');
      return fulfillJson(route, { contractVersion: 2, observationRef, items: [{ revisionRef: 'rev_old', lineageRef: `lin_${observationRef.replace('obs_', '')}`, changeType: 'inserted', recordedAt: '2026-09-17T08:00:00Z', displayValue: '14', chartValue: 14, validationStatus: 'valid', state: 'superseded', importRef: 'imp_1', attemptRef: 'attempt_1' }] });
    }
    if (url.pathname === '/api/projects/VSO/imports/imp_1') return fulfillJson(route, { contractVersion: 2, importRef: 'imp_1', attemptRef: 'attempt_1', status: 'committed', workbookName: 'vso.xlsx', workbookHash: 'a'.repeat(64), mode: 'incremental', committedAt: '2026-09-17T08:00:00Z', dataRange: { start: '2026-09-16', end: '2026-09-17' }, outcome: { inserted: 12, updated: 0, unchanged: 0, restored: 0, deleted: 0 } });
    if (url.pathname === '/api/imports/preview' && request.method() === 'POST') return fulfillJson(route, { manifest: { source_file: 'snapshot.xlsx', source_hash: 'b'.repeat(64), record_count: 12, date_count: 2, observed_date_min: '2026-09-16', observed_date_max: '2026-09-17', projects: ['VSO'] }, valid: true, errorCount: 0, warningCount: 0, issues: [] });
    if (url.pathname === '/api/imports') return fulfillJson(route, { items: [{ attempt_id: 1, attempt_status: 'committed', submitted_file_name: 'vso.xlsx', requested_mode: 'incremental', input_record_count: 12, inserted_count: 12, updated_count: 0, unchanged_count: 0, started_at: '2026-09-17T08:00:00Z' }] });
    return fulfillJson(route, { detail: `Unhandled test route: ${url.pathname}` }, 404);
  });
  return { calls, workspaceRequestCount: () => workspaceRequestCount };
}
