import type { Page, Route } from '@playwright/test';
import wholeSeriesFixture from './whole-series.json' with { type: 'json' };
import currentInsightFixture from './current-insight.json' with { type: 'json' };
import twoPointInsightFixture from './two-point-insight.json' with { type: 'json' };

type HarnessOptions = {
  weeklyCharts?: boolean;
  overviewSummaryByRequest?: Record<string, unknown>[];
  statisticsSummaryByRequest?: Record<string, unknown>[];
  provenanceFailures?: number;
  provenanceDelayMs?: number;
  workspaceDelayMs?: number;
  workspaceDelaysMs?: number[];
  workspaceFailureRequests?: number[];
  workspaceValuesByRequest?: number[][];
  workspaceVersionsByRequest?: string[];
  contextualIneligibleMetrics?: string[];
  contextualIneligibleReason?: string;
  legacyUnavailable?: boolean;
  aiDelayMs?: number;
  aiFailureRequests?: number[];
  aiResponseStatus?: 'ready' | 'provider_unavailable' | 'rejected_output' | 'insufficient_data';
  aiLimitedComparison?: boolean;
  aiWholeSeries?: boolean;
  aiCurrentDataset?: boolean;
  aiFixture?: unknown;
  historyDelaysMs?: number[];
  historyFailureRequests?: number[];
  historyItemsByRequest?: Record<string, unknown>[][];
  commitDelayMs?: number;
  commitFailureStatus?: number;
  commitNetworkFailure?: boolean;
  importOutcome?: Record<string, unknown>;
  previewFixture?: unknown;
  bootstrapEmpty?: boolean;
  bootstrapFailure?: boolean;
};
export type ApiCall = { pathname: string; search: string; method: string; body?: unknown };

const dates = ['2026-09-16T00:00:00', '2026-09-17T00:00:00'];

function exactTrace(name: string, prefix: string, values = [10, 14]) {
  return {
    type: 'bar', name, x: dates, y: values,
    ids: [`obs_${prefix}_1`, `obs_${prefix}_2`],
    meta: { lineage: { contractVersion: 1, kind: 'exact-observation', selectable: true, lineageRefs: [`lin_${prefix}_1`, `lin_${prefix}_2`] } },
    hovertemplate: '%{x}<br>%{y}<extra></extra>',
  };
}

function aggregateTrace(name: string, prefix: string, entityId: string, metric: string, values = [10, 14], calculation = 'sum') {
  const average = calculation === 'average_per_day';
  return {
    type: average ? 'scatter' : 'bar', mode: average ? 'lines+markers' : undefined,
    line: average ? { dash: 'solid', width: 3 } : undefined,
    marker: average ? { size: 8, symbol: metric === 'Tổng số' ? 'circle' : 'diamond' } : undefined,
    opacity: average ? undefined : metric === 'Tổng số' ? 0.82 : 0.58,
    name, legendgroup: entityId, x: ['Tuần 37/2026', 'Tuần 38/2026'], y: values,
    meta: { statisticsMetric: metric, lineage: { contractVersion: 2, kind: 'aggregate', selectable: true, aggregateRefs: [`agg_${prefix}_1`, `agg_${prefix}_2`] } },
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
  { entity_id: 'project-root', parent_entity_id: null, entity_label: 'VSO', entity_path: 'VSO', entity_level: 'project', entity_depth: 0, effective_unit: 'ticket' },
  { entity_id: 'root', parent_entity_id: 'project-root', entity_label: '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', entity_path: 'VSO / 1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', entity_level: 'section', entity_depth: 1, effective_unit: 'ticket' },
  { entity_id: 'child-a', parent_entity_id: 'root', entity_label: 'Camera 360 lỗi kết nối', entity_path: 'VSO / 1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống / Camera 360 lỗi kết nối', entity_level: 'item', entity_depth: 2, effective_unit: 'ticket' },
  { entity_id: 'child-b', parent_entity_id: 'root', entity_label: '5G mất kết nối', entity_path: 'VSO / 1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống / 5G mất kết nối', entity_level: 'item', entity_depth: 2, effective_unit: 'ticket' },
];

function workspace(url: URL, options: HarnessOptions, requestNumber: number) {
  const children = url.searchParams.get('scope') === 'children';
  const compared = (url.searchParams.get('comparison_entities') || '').split(',').filter(Boolean);
  const contextualAnchor = url.searchParams.get('comparison_anchor');
  const comparisonMetric = url.searchParams.get('comparison_metric') || 'Báo sai/Lỗi';
  const comparisonLens = url.searchParams.get('comparison_lens') || 'metric';
  const comparisonCalculation = url.searchParams.get('comparison_calculation') || 'sum';
  const viewMode = url.searchParams.get('mode');
  const valueOffset = viewMode === 'week' ? 1 : viewMode === 'month' ? 2 : 0;
  const requestValues = options.workspaceValuesByRequest?.[requestNumber - 1] ?? [10, 14];
  const committedImportRef = options.workspaceVersionsByRequest?.[requestNumber - 1] ?? 'imp_1';
  const weeklyFigure = (prefix: string, name = 'Tổng số', values = requestValues) => ({
    data: [aggregateTrace(name, prefix, prefix, 'Tổng số', values)],
    layout: { hovermode: 'closest', xaxis: { type: 'category' }, yaxis: { rangemode: 'tozero' }, showlegend: true },
  });
  const viewFigure = (prefix: string, name?: string, values = requestValues) => options.weeklyCharts && viewMode === 'week'
    ? weeklyFigure(prefix, name, values.map(value => value + valueOffset))
    : figure(prefix, name, values.map(value => value + valueOffset));
  const childStatistics = (prefix: string) => ({
    data: options.weeklyCharts
      ? [aggregateTrace('Tổng · Tổng số', `${prefix}_total`, prefix, 'Tổng số', requestValues), aggregateTrace('Tổng · Báo sai/Lỗi', `${prefix}_error`, prefix, 'Báo sai/Lỗi', [2, 3])]
      : [exactTrace('Tổng · Tổng số', `${prefix}_total`, requestValues), exactTrace('Tổng · Báo sai/Lỗi', `${prefix}_error`, [2, 3]), helperTrace()],
    layout: { hovermode: 'closest', xaxis: { type: 'category' }, yaxis: { rangemode: 'tozero' }, showlegend: true },
  });
  const statisticsSummary = options.statisticsSummaryByRequest?.[requestNumber - 1] ?? options.statisticsSummaryByRequest?.at(-1);
  const summaryPoint = statisticsSummary?.largestChange as { from: { value: number; period: { start: string; label: string } }; to: { value: number; period: { start: string; label: string } } } | undefined;
  const summaryStatisticsFigure = summaryPoint ? {
    data: [aggregateTrace(statisticsSummary?.calculation === 'average_per_day' ? 'Trung bình/ngày · Tổng số' : 'Tổng · Tổng số', 'statistics', 'root', 'Tổng số',
      [summaryPoint.from.value, summaryPoint.to.value], String(statisticsSummary?.calculation || 'sum'))],
    layout: { hovermode: 'closest', xaxis: { type: 'category' }, yaxis: { rangemode: 'tozero' }, showlegend: true },
  } : undefined;
  const contextualCandidates = contextualAnchor
    ? entities.filter(item => item.parent_entity_id === 'root' && item.entity_id !== contextualAnchor).map(item => ({
        entity_id: item.entity_id, entity_label: item.entity_label, effective_unit: item.effective_unit,
        eligible: !options.contextualIneligibleMetrics?.includes(comparisonMetric),
        reason: options.contextualIneligibleMetrics?.includes(comparisonMetric)
          ? options.contextualIneligibleReason || 'NO_METRIC_VALUE' : null,
        comparablePeriodCount: options.contextualIneligibleMetrics?.includes(comparisonMetric) ? 0 : 1,
      }))
    : null;
  const eligibleIds = new Set((contextualCandidates || []).filter(item => item.eligible).map(item => item.entity_id));
  const accepted = contextualAnchor
    ? [contextualAnchor, ...compared.filter(id => id !== contextualAnchor && eligibleIds.has(id))].slice(0, 3)
    : [];
  const removed = contextualAnchor
    ? compared.filter(id => id !== contextualAnchor && !eligibleIds.has(id)).map(entityId => ({ entityId, reason: contextualCandidates?.find(item => item.entity_id === entityId)?.reason || 'NOT_SIBLING' }))
    : [];
  return {
    overviewSummary: options.overviewSummaryByRequest?.[requestNumber - 1] ?? options.overviewSummaryByRequest?.at(-1),
    statisticsSummary,
    dataVersion: { committedImportRef, committedAt: committedImportRef === 'imp_1' ? '2026-09-17T08:00:00Z' : '2026-09-18T08:00:00Z' },
    window: { start: viewMode === 'month' ? '2026-09-01' : viewMode === 'week' ? '2026-09-10' : '2026-09-16', end: '2026-09-17' }, selectedEntity: 'root',
    scopeIds: children ? ['child-a', 'child-b'] : ['root'],
    overview: children
      ? [
          { entityId: 'child-a', title: 'Camera 360 lỗi kết nối', figure: viewFigure('child_a') },
          { entityId: 'child-b', title: '5G mất kết nối', figure: viewFigure('child_b') },
        ]
      : [{ entityId: 'root', title: '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', figure: options.legacyUnavailable ? {
          ...figure('overview'),
          data: [
            ...figure('overview').data,
            { type: 'bar', name: 'Dữ liệu cũ', x: [dates[0]], y: [3], ids: [null], meta: { lineage: { contractVersion: 1, kind: 'exact-observation', selectable: true, lineageRefs: [null] } } },
          ],
        } : viewFigure('overview') }],
    statistics: children
      ? [
          { entityId: 'child-a', title: 'Camera 360 lỗi kết nối', figure: childStatistics('statistics_child_a') },
          { entityId: 'child-b', title: '5G mất kết nối', figure: childStatistics('statistics_child_b') },
        ]
      : [{ entityId: 'root', title: '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', figure: summaryStatisticsFigure || (options.weeklyCharts ? weeklyFigure('statistics', 'Tổng · Tổng số') : viewFigure('statistics', 'Tổng · Tổng số')) }],
    statisticsPeriods: summaryPoint ? [summaryPoint.from, summaryPoint.to].map(point => ({ start: point.period.start, label: point.period.label, complete: true })) : [{ start: '2026-09-16', label: '16/09/2026', complete: true }],
    comparisonCandidates: contextualCandidates || [
      { entity_id: 'child-a', entity_label: 'Camera 360 lỗi kết nối', effective_unit: 'ticket' },
      { entity_id: 'child-b', entity_label: '5G mất kết nối', effective_unit: 'ticket' },
    ],
    comparison: (contextualAnchor ? accepted.length >= 2 : compared.length >= 2) ? {
      data: comparisonLens === 'statistics'
        ? accepted.flatMap((entityId, entityIndex) => {
            const label = entityId === 'child-a' ? 'Camera 360 lỗi kết nối' : '5G mất kết nối';
            const prefix = entityId === 'child-a' ? 'comparison_a' : 'comparison_b';
            return [
              aggregateTrace(`${label} · Tổng số`, `${prefix}_total`, entityId, 'Tổng số', [80 - entityIndex * 5, 120 - entityIndex * 5], comparisonCalculation),
              aggregateTrace(`${label} · Báo sai/Lỗi`, `${prefix}_error`, entityId, 'Báo sai/Lỗi', [8 - entityIndex, 12 - entityIndex], comparisonCalculation),
            ];
          })
        : [exactTrace('Camera 360 lỗi kết nối', 'comparison_a', [8, 12]), exactTrace('5G mất kết nối', 'comparison_b', [7, 11])],
      layout: { hovermode: 'x unified', xaxis: { type: comparisonLens === 'statistics' ? 'category' : 'date' }, yaxis: { rangemode: 'tozero' } },
    } : null,
    comparisonTable: comparisonLens === 'statistics' && accepted.length >= 2 ? {
      columns: ['period', 'entity', 'metric', 'value', 'eligibleDays'],
      rows: accepted.flatMap((entityId, entityIndex) => ['Tổng số', 'Báo sai/Lỗi'].flatMap(metric => ['Tuần 37/2026', 'Tuần 38/2026'].map((period, periodIndex) => {
        const values = metric === 'Tổng số' ? [80 - entityIndex * 5, 120 - entityIndex * 5] : [8 - entityIndex, 12 - entityIndex];
        const metricKey = metric === 'Tổng số' ? 'total' : 'error';
        return {
          period, periodStart: periodIndex ? '2026-09-14' : '2026-09-07', periodEnd: periodIndex ? '2026-09-20' : '2026-09-13',
          entityId, entity: entityId === 'child-a' ? 'Camera 360 lỗi kết nối' : '5G mất kết nối', metric,
          value: values[periodIndex], displayValue: String(values[periodIndex]),
          eligibleDays: 2, calendarDays: 7, coverageSourceEntityId: 'root', inferredZero: false,
          aggregateRef: `agg_comparison_${entityId === 'child-a' ? 'a' : 'b'}_${metricKey}_${periodIndex + 1}`,
        };
      }))),
    } : null,
    comparisonContext: contextualAnchor ? {
      lens: comparisonLens,
      anchor: { entityId: contextualAnchor, entityLabel: contextualAnchor === 'child-a' ? 'Camera 360 lỗi kết nối' : '5G mất kết nối', parentEntityId: 'root', effectiveUnit: 'ticket' },
      metric: comparisonLens === 'statistics' ? null : comparisonMetric,
      metrics: comparisonLens === 'statistics' ? ['Tổng số', 'Báo sai/Lỗi'] : undefined,
      calculation: comparisonLens === 'statistics' ? comparisonCalculation : comparisonMetric === '% báo sai' ? 'weighted_rate' : 'sum',
      grain: url.searchParams.get('statistics_group') || 'week',
      range: { start: '2026-09-16', end: '2026-09-17' }, anchorEligible: true, anchorReason: null,
    } : null,
    comparisonSelection: contextualAnchor ? { accepted, removed, limit: 3 } : null,
    capabilities: { lineage: { contractVersion: 1, exactObservation: true, aggregateObservation: true } },
    audit: { total: 1, offset: 0, rows: [{ date: '2026-09-17', entity_path: 'VSO / 1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', metric_normalized: 'Tổng số', raw_value: '14', display_value: '14', chart_value: 14, value_kind: 'numeric', sheet_name: 'Daily', cell_address: 'D7', validation_status: 'valid' }] },
  };
}

function provenance(observationRef: string, lineageRef: string) {
  const historical = observationRef.endsWith('_2');
  return {
    contractVersion: 1, status: 'available', observationRef, lineageRef,
    context: { project: { label: 'VSO' }, entity: { ref: 'root', label: '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', level: 'section', hierarchyPath: ['VSO', '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống'], effectiveUnit: 'ticket' }, metric: { key: 'total', label: 'Tổng số' }, observedDate: historical ? '2026-09-17' : '2026-09-16' },
    source: { workbookName: 'vso.xlsx', workbookHash: { algorithm: 'sha256', value: 'a'.repeat(64) }, sheet: 'Daily', cell: historical ? 'D7' : 'C7', cellReference: historical ? 'Daily!D7' : 'Daily!C7' },
    values: { raw: { text: historical ? '14' : '10', type: 'number' }, display: historical ? '14' : '10', chart: historical ? 14 : 10, valueKind: 'numeric', numberFormat: '0' },
    transformation: { parserRule: 'numeric', parserConfidence: 'high', note: null },
    validation: { status: 'valid', issues: [] },
    revision: { revisionRef: historical ? 'rev_old' : 'rev_current', changeType: 'inserted', recordedAt: '2026-09-17T08:00:00Z', state: historical ? 'superseded' : 'current', revisionCurrent: !historical, sourcePresenceCurrent: true },
    import: { mode: 'incremental', committedAt: '2026-09-17T08:00:00Z', importRef: 'imp_1', attemptRef: 'attempt_1' },
    freshness: { observedThrough: '2026-09-17', isCurrent: !historical, newerSnapshotAvailable: historical, newerSourceDataAvailable: historical, sourceCommittedAt: '2026-09-17T08:00:00Z' },
  };
}

function aggregateProvenance(aggregateRef: string) {
  const childB = aggregateRef.includes('_b_');
  const metric = aggregateRef.includes('_total_') ? 'Tổng số' : 'Báo sai/Lỗi';
  const chartValue = metric === 'Tổng số' ? 80 : 8;
  return {
    contractVersion: 2, kind: 'aggregate', aggregateRef,
    context: {
      project: 'VSO', entity: { ref: childB ? 'child-b' : 'child-a', label: childB ? '5G mất kết nối' : 'Camera 360 lỗi kết nối', hierarchyPath: ['VSO', 'Chất lượng cảnh báo', childB ? '5G mất kết nối' : 'Camera 360 lỗi kết nối'], effectiveUnit: 'ticket' },
      metric, series: childB ? '5G mất kết nối' : 'Camera 360 lỗi kết nối',
      period: { start: aggregateRef.endsWith('_2') ? '2026-09-14' : '2026-09-07', end: aggregateRef.endsWith('_2') ? '2026-09-20' : '2026-09-13' }, observedThrough: '2026-09-17',
    },
    result: { chartValue, displayValue: String(chartValue) },
    aggregation: { ruleCode: 'period_sum', explanation: 'Cộng các giá trị số trong kỳ.', valueObservationCount: 2, coverageObservationCount: 0, eligibleDayCount: 2, calendarDayCount: 7, inferredZero: false },
    contributors: { total: 2, pageSize: 50 },
    freshness: { snapshotCreatedAt: '2026-09-17T08:00:00Z', observedThrough: '2026-09-17', newerDataAvailable: false },
  };
}

function prefixFixtureIds(value: unknown, prefix: string, key = ''): any {
  if (Array.isArray(value)) return value.map(item => prefixFixtureIds(item, prefix, key));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([childKey, child]) => (
      [childKey, prefixFixtureIds(child, prefix, childKey)]
    )));
  }
  if (typeof value === 'string' && ['factId', 'factIds', 'evidenceId', 'evidenceIds'].includes(key)) {
    return `${prefix}:${value}`;
  }
  return value;
}

export function aiAnalysis(requestBody: Record<string, string>, status: HarnessOptions['aiResponseStatus'] = 'ready', limitedComparison = false, wholeSeries = false, currentDataset = false): any {
  if (currentDataset) return currentInsightFixture;
  const metric = requestBody.metricCode || 'error';
  const groupBy = requestBody.groupBy || 'day';
  if (metric === 'all') {
    let metrics = (['total', 'error', 'error_rate'] as const).map(metricCode => {
      const trend = aiAnalysis({ ...requestBody, metricCode }, status);
      const values = metricCode === 'total' ? [100, 200] : metricCode === 'error' ? [10, 15] : [10, 7.5];
      const display = (value: number) => `${value}${metricCode === 'error_rate' ? '%' : ''}`;
      trend.series.forEach((point: any, index: number) => {
        point.value = values[index]; point.displayValue = display(values[index]);
        if (point.change) point.change = { ...point.change, absolute: values[1] - values[0], absoluteDisplay: `${values[1] - values[0]}${metricCode === 'error_rate' ? ' pp' : ''}`, relativePercent: (values[1] / values[0] - 1) * 100, relativeDisplay: `${(values[1] / values[0] - 1) * 100}%`, direction: metricCode === 'error_rate' ? 'decreasing' : 'increasing' };
      });
      trend.periodAnalytics = { policyVersion: 'period-level-v1', tieBreak: 'latest_period', peak: null, lowest: null, largestIncrease: null, largestDecrease: null, consecutiveIncrease: null, consecutiveDecrease: null, endingPlateau: null, latestChange: null };
      const direction = metricCode === 'error_rate' ? 'decreasing' : 'increasing';
      const overviewText = direction === 'increasing' ? 'Chỉ số đi lên trong toàn khoảng, không có nhịp giảm.' : 'Chỉ số đi xuống trong toàn khoảng, không có nhịp tăng.';
      const stageText = `16/09/2026–17/09/2026: ${direction === 'increasing' ? 'tăng' : 'giảm'} từ ${display(values[0])} ${direction === 'increasing' ? 'lên' : 'xuống'} ${display(values[1])}.`;
      trend.periodAnalytics.temporalStructure = { policyVersion: 'chronological-stages-v1', overviewText, summaryText: `${overviewText} ${stageText}`, stages: [{ startIndex: 0, endIndex: 1, direction, text: stageText, startPeriodLabel: '16/09/2026', endPeriodLabel: '17/09/2026', factIds: ['fact-period-000', 'fact-period-001'], evidenceIds: ['ev-period-000', 'ev-period-001'] }], turningPoints: [], gaps: [] };
      trend.facts = trend.facts.filter((fact: any) => ['period_value', 'previous', 'current'].includes(fact.kind)).map((fact: any) => {
        const index = fact.kind === 'current' || fact.factId === 'fact-period-001' ? 1 : 0;
        return { ...fact, value: values[index], displayValue: display(values[index]) };
      });
      return prefixFixtureIds({
        metricCode, metricDisplayName: trend.scope.metricDisplayName,
        status: trend.status === 'insufficient_data' ? 'insufficient_data' : 'ready',
        unit: trend.metric.unit, aggregationRule: trend.metric.aggregationRule,
        facts: trend.facts, series: trend.series,
        periodAnalytics: trend.periodAnalytics,
        historicalContext: trend.historicalContext,
        quality: trend.quality, evidence: trend.evidence,
      }, metricCode);
    });
    if (wholeSeries) metrics = wholeSeriesFixture.metrics.map((metric: any) => ({
      ...metrics.find(item => item.metricCode === metric.metricCode), ...metric,
      evidence: metric.series.map((point: any, index: number) => ({ evidenceId: point.evidenceId, period: 'series', periodIndex: index, periodStart: point.periodStart, periodEnd: point.periodEnd, periodLabel: point.periodLabel, observedDate: point.periodStart, target: { kind: 'exact', observationRef: `obs_ai_${index + 1}`, lineageRef: `lin_ai_${index + 1}` } })),
    }));
    const limited = limitedComparison || status === 'insufficient_data';
    const text = limited ? 'Tổng số có dữ liệu nhưng chưa đủ cơ sở liên kết tăng trưởng giữa ba chỉ số.' : 'Từ 16/09/2026 đến 17/09/2026, Tổng số tăng nhanh hơn Báo sai/Lỗi; tỷ trọng Báo sai/Lỗi trên Tổng số giảm trong phép tính tỷ lệ (10% → 7.5%).';
    const candidate = { candidateId: limited ? 'description' : 'relationship', layer: limited ? 'descriptive' : 'relational', text, factIds: metrics.flatMap(item => item.facts.map((fact: any) => fact.factId)), evidenceIds: metrics[0].evidence.map((item: any) => item.evidenceId) };
    const whole = wholeSeries ? wholeSeriesFixture.insightCandidates[0] : { ...candidate, candidateId: 'whole-window', layer: 'whole_series', text: metrics.map(item => `${item.metricDisplayName}: ${item.periodAnalytics.temporalStructure.overviewText}`).join(' ') };
    const plan = wholeSeries ? wholeSeriesFixture.synthesis : twoPointInsightFixture.synthesis;
    const selected = limited ? plan.candidates.filter(c => c.metricCodes.length === 1).slice(0, 1) : plan.selectedCandidateIds.map(id => plan.candidates.find(c => c.candidateId === id)!);
    const endpoint = (index: number) => ({ periodLabel: index ? '17/09/2026' : '16/09/2026', numeratorDisplay: index ? '15' : '10', denominatorDisplay: index ? '200' : '100', rateDisplay: index ? '7.5%' : '10%', eligibleDayCount: 1, expectedDayCount: 1 });
    return {
      schemaVersion: 'ai-overview-v2', analysisId: 'ana_e2e_overview', kind: 'metric_overview', status,
      scope: { project: 'VSO', entityRef: requestBody.entityRef || 'root', entityLabel: '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', mode: 'node', metricCode: 'all', metricDisplayName: 'Tất cả chỉ số' },
      window: { start: wholeSeries ? '2026-09-01' : requestBody.start || '2026-09-16', end: wholeSeries ? '2026-09-09' : requestBody.end || '2026-09-17', groupBy, comparisonBasis: 'per_metric_period_over_period_and_first_last', previousDate: '2026-09-16', currentDate: '2026-09-17' },
      dataAsOf: { committedImportRef: 'imp_1', snapshotId: 'as_e2e_overview', generatedAt: '2026-09-17T09:00:00Z', stale: false, checksum: 'b'.repeat(64) },
      metrics, facts: wholeSeries ? [...metrics.flatMap(item => item.facts), ...plan.facts] : twoPointInsightFixture.facts,
      synthesis: limited ? undefined : plan,
      comparisonBasis: wholeSeries ? wholeSeriesFixture.comparisonBasis : { status: limited ? 'limited' : 'comparable', reason: limited ? 'Kỳ so sánh có ngày thiếu; chưa kết luận quan hệ tăng trưởng.' : 'So sánh kỳ đầu–cuối, dùng cùng cặp tử số/mẫu số của tỷ lệ.', baseline: endpoint(0), current: endpoint(1) },
      insightCandidates: wholeSeries ? wholeSeriesFixture.insightCandidates : [whole, candidate],
      inspectionChecks: plan.inspectionChecks.filter(check => selected.some(c => c.candidateId === check.candidateId)),
      quality: { status: limited ? 'partial' : 'valid', availableMetricCount: 3, expectedMetricCount: 3, validPeriodCount: wholeSeries ? 9 : 2, expectedPeriodCount: wholeSeries ? 9 : 2, limitations: limited ? ['Kỳ so sánh có ngày thiếu; chưa kết luận quan hệ tăng trưởng.'] : [] },
      evidence: metrics.flatMap(item => item.evidence),
      provider: { name: '9router', model: 'fake-gemini' },
      validation: { status: status === 'ready' ? 'accepted' : 'not_run', errors: status === 'provider_unavailable' ? ['timeout'] : [] },
      narrative: {
        mode: status === 'ready' ? 'ai' : 'deterministic',
        summary: { text: selected.map(c => c.fallbackText).join(' '), candidateIds: selected.map(c => c.candidateId), factIds: selected.flatMap(c => c.factIds), claimType: 'descriptive' },
        insights: [], limitations: [], suggestedChecks: [],
      },
    };
  }
  const metricLabel = metric === 'total' ? 'Tổng số' : metric === 'error_rate' ? '% báo sai' : 'Báo sai/Lỗi';
  const facts = status === 'insufficient_data' ? [] : [
    { factId: 'fact-period-000', kind: 'period_value', value: 8, unit: metric === 'error_rate' ? 'percent' : 'ticket', displayValue: metric === 'error_rate' ? '8%' : '8', evidenceIds: ['ev-period-000'] },
    { factId: 'fact-period-001', kind: 'period_value', value: 6, unit: metric === 'error_rate' ? 'percent' : 'ticket', displayValue: metric === 'error_rate' ? '6%' : '6', evidenceIds: ['ev-period-001'] },
    { factId: 'fact-change-001', kind: 'period_change', value: -2, unit: metric === 'error_rate' ? 'percentage_point' : 'ticket', displayValue: metric === 'error_rate' ? '-2 pp' : '-2', evidenceIds: ['ev-period-000', 'ev-period-001'] },
    { factId: 'fact-relative-change-001', kind: 'period_relative_change', value: -25, unit: 'percent', displayValue: '-25%', evidenceIds: ['ev-period-000', 'ev-period-001'] },
    { factId: 'fact-direction-001', kind: 'period_direction', value: 'decreasing', unit: 'enum', displayValue: 'decreasing', evidenceIds: ['ev-period-000', 'ev-period-001'] },
    { factId: 'fact-previous', kind: 'previous', value: 8, unit: metric === 'error_rate' ? 'percent' : 'ticket', displayValue: metric === 'error_rate' ? '8%' : '8', evidenceIds: ['ev-period-000'] },
    { factId: 'fact-current', kind: 'current', value: 6, unit: metric === 'error_rate' ? 'percent' : 'ticket', displayValue: metric === 'error_rate' ? '6%' : '6', evidenceIds: ['ev-period-001'] },
    { factId: 'fact-delta', kind: 'absolute_change', value: -2, unit: metric === 'error_rate' ? 'percentage_point' : 'ticket', displayValue: metric === 'error_rate' ? '-2 pp' : '-2', evidenceIds: ['ev-period-000', 'ev-period-001'] },
    { factId: 'fact-relative', kind: 'relative_change', value: -25, unit: 'percent', displayValue: '-25%', evidenceIds: ['ev-period-000', 'ev-period-001'] },
    { factId: 'fact-direction', kind: 'direction', value: 'decreasing', unit: 'enum', displayValue: 'decreasing', evidenceIds: ['ev-period-000', 'ev-period-001'] },
    { factId: 'fact-trend-pattern', kind: 'trend_pattern', value: 'consistently_decreasing', unit: 'enum', displayValue: 'consistently_decreasing', evidenceIds: ['ev-period-000', 'ev-period-001'] },
  ];
  const evidence = [
    { evidenceId: 'ev-period-000', period: 'series', periodIndex: 0, periodStart: '2026-09-16', periodEnd: '2026-09-16', periodLabel: '16/09/2026', observedDate: '2026-09-16', observedDayCount: 1, expectedDayCount: 1, target: { kind: 'exact', observationRef: 'obs_ai_1', lineageRef: 'lin_ai_1' } },
    { evidenceId: 'ev-period-001', period: 'series', periodIndex: 1, periodStart: '2026-09-17', periodEnd: '2026-09-17', periodLabel: '17/09/2026', observedDate: '2026-09-17', observedDayCount: 1, expectedDayCount: 1, target: { kind: 'exact', observationRef: 'obs_ai_2', lineageRef: 'lin_ai_2' } },
  ];
  const series = [
    { periodIndex: 0, periodStart: '2026-09-16', periodEnd: '2026-09-16', periodLabel: '16/09/2026', value: 8, displayValue: metric === 'error_rate' ? '8%' : '8', rowCount: 1, observedDayCount: 1, expectedDayCount: 1, coverageRatio: 1, evidenceId: 'ev-period-000', factId: 'fact-period-000', inferredZero: false, change: null },
    { periodIndex: 1, periodStart: '2026-09-17', periodEnd: '2026-09-17', periodLabel: '17/09/2026', value: 6, displayValue: metric === 'error_rate' ? '6%' : '6', rowCount: 1, observedDayCount: 1, expectedDayCount: 1, coverageRatio: 1, evidenceId: 'ev-period-001', factId: 'fact-period-001', inferredZero: false, change: { fromPeriodStart: '2026-09-16', absolute: -2, absoluteDisplay: metric === 'error_rate' ? '-2 pp' : '-2', relativePercent: -25, relativeDisplay: '-25%', direction: 'decreasing', factIds: ['fact-change-001', 'fact-relative-change-001', 'fact-direction-001'] } },
  ];
  const periodAnalytics = status === 'insufficient_data' ? {
    policyVersion: 'period-level-v1', tieBreak: 'latest_period',
    peak: null, lowest: null, largestIncrease: null, largestDecrease: null,
    consecutiveIncrease: null, consecutiveDecrease: null, endingPlateau: null, latestChange: null,
  } : {
    policyVersion: 'period-level-v1', tieBreak: 'latest_period',
    peak: { periodStart: '2026-09-16', periodEnd: '2026-09-16', periodLabel: '16/09/2026', value: 8, displayValue: metric === 'error_rate' ? '8%' : '8', coverageRatio: 1, factIds: ['fact-period-highest', 'fact-period-000'] },
    lowest: { periodStart: '2026-09-17', periodEnd: '2026-09-17', periodLabel: '17/09/2026', value: 6, displayValue: metric === 'error_rate' ? '6%' : '6', coverageRatio: 1, factIds: ['fact-period-lowest', 'fact-period-001'] },
    largestIncrease: null,
    largestDecrease: { fromPeriodStart: '2026-09-16', fromPeriodLabel: '16/09/2026', fromValue: 8, fromDisplayValue: metric === 'error_rate' ? '8%' : '8', toPeriodStart: '2026-09-17', toPeriodLabel: '17/09/2026', toValue: 6, toDisplayValue: metric === 'error_rate' ? '6%' : '6', absolute: -2, absoluteDisplay: metric === 'error_rate' ? '-2 pp' : '-2', relativePercent: -25, relativeDisplay: '-25%', direction: 'decreasing', factIds: ['fact-period-largest-decrease', 'fact-change-001'] },
    consecutiveIncrease: null, consecutiveDecrease: null, endingPlateau: null,
    latestChange: { fromPeriodStart: '2026-09-16', fromPeriodLabel: '16/09/2026', fromValue: 8, fromDisplayValue: metric === 'error_rate' ? '8%' : '8', toPeriodStart: '2026-09-17', toPeriodLabel: '17/09/2026', toValue: 6, toDisplayValue: metric === 'error_rate' ? '6%' : '6', absolute: -2, absoluteDisplay: metric === 'error_rate' ? '-2 pp' : '-2', relativePercent: -25, relativeDisplay: '-25%', direction: 'decreasing', factIds: ['fact-period-latest-change', 'fact-change-001'] },
  };
  return {
    schemaVersion: 'ai-trend-v3', analysisId: 'ana_e2e', kind: 'trend', status,
    scope: { project: 'VSO', entityRef: requestBody.entityRef || 'root', entityLabel: '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', mode: 'node', metricCode: metric, metricDisplayName: metricLabel },
    window: { start: requestBody.start || '2026-09-16', end: requestBody.end || '2026-09-17', groupBy, comparisonBasis: 'period_over_period_and_first_last', previousDate: '2026-09-16', currentDate: '2026-09-17' },
    dataAsOf: { committedImportRef: 'imp_1', snapshotId: 'as_e2e', generatedAt: '2026-09-17T09:00:00Z', stale: false, checksum: 'a'.repeat(64) },
    metric: { unit: metric === 'error_rate' ? 'percent' : 'ticket', aggregationRule: metric === 'error_rate' ? 'weighted_error_rate' : `period_${groupBy}_sum` },
    facts,
    series: status === 'insufficient_data' ? series.slice(0, 1) : series,
    periodAnalytics,
    historicalContext: { status: 'unavailable', policyVersion: 'trailing-12-periods-v1', lookbackPeriodLimit: 12, observedPeriodCount: 0, currentPosition: null },
    quality: { status: status === 'insufficient_data' ? 'insufficient_data' : 'valid', validPointCount: status === 'insufficient_data' ? 1 : 2, validPeriodCount: status === 'insufficient_data' ? 1 : 2, expectedPeriodCount: 2, observedInputDayCount: status === 'insufficient_data' ? 1 : 2, expectedCalendarDayCount: 2, coverageRatio: status === 'insufficient_data' ? 0.5 : 1, periodCoverageRatio: status === 'insufficient_data' ? 0.5 : 1, comparisonBasis: 'period_over_period_and_first_last', policyVersion: 'period-series-v3', limitations: status === 'insufficient_data' ? ['Cần ít nhất hai kỳ hợp lệ để phân tích xu hướng.'] : [] },
    evidence: status === 'insufficient_data' ? evidence.slice(0, 1) : evidence,
    provider: { name: '9router', model: 'fake-gemini' },
    validation: { status: status === 'ready' ? 'accepted' : 'not_run', errors: status === 'provider_unavailable' ? ['timeout'] : [] },
    narrative: {
      mode: status === 'ready' ? 'ai' : 'deterministic',
      summary: { text: status === 'insufficient_data' ? 'Chưa có đủ hai điểm dữ liệu hợp lệ để so sánh.' : 'Điểm cuối thấp hơn điểm đầu trong khoảng đã chọn.', factIds: status === 'insufficient_data' ? [] : ['fact-previous', 'fact-current', 'fact-direction'], claimType: 'descriptive' },
      insights: [], limitations: status === 'provider_unavailable' ? ['Không gọi được dịch vụ phân tích; các dữ kiện đã tính vẫn sử dụng được.'] : [], suggestedChecks: ['Mở bằng chứng để đối chiếu.'],
    },
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

export async function installApiHarness(page: Page, options: HarnessOptions = {}) {
  const calls: ApiCall[] = [];
  let failuresLeft = options.provenanceFailures ?? 0;
  let workspaceRequestCount = 0;
  let aiRequestCount = 0;
  let historyRequestCount = 0;
  let committedVersion = 'imp_1';
  await page.route('**/api/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const body = (url.pathname.endsWith('/ai/trend-summary') || url.pathname.endsWith('/ai/context-insight')) && request.method() === 'POST' ? request.postDataJSON() : undefined;
    calls.push({ pathname: url.pathname, search: url.search, method: request.method(), body });
    if (url.pathname === '/api/bootstrap') {
      if (options.bootstrapFailure) return fulfillJson(route, { detail: 'Không tải được danh sách dự án thử nghiệm' }, 503);
      return fulfillJson(route, { projects: options.bootstrapEmpty ? [] : [{ label: 'VSO', records: 12, chartable: 12, entities: 4, units: 1, minDate: '2026-09-16', maxDate: '2026-09-17' }] });
    }
    if (url.pathname === '/api/ai/status') return fulfillJson(route, { enabled: true, configured: true, externalAllowed: true, provider: '9router', model: 'fake-gemini', availability: 'not_checked', privacyMode: 'normalized_facts_only' });
    if (url.pathname === '/api/projects/VSO/ai/context-insight' && request.method() === 'POST') {
      aiRequestCount += 1;
      if (options.aiDelayMs) await new Promise(resolve => setTimeout(resolve, options.aiDelayMs));
      if (options.aiFailureRequests?.includes(aiRequestCount)) return fulfillJson(route, { detail: 'Provider thử nghiệm chưa phản hồi.' }, 503);
      const input = request.postDataJSON();
      const ids: string[] = input.selection === 'node' ? [input.parentEntityRef] : input.selection === 'selected' ? input.entityRefs : ['child-a', 'child-b'];
      const paragraph = { text: 'Số lỗi giảm ở kỳ sau. Hai kỳ chỉ đủ để so sánh, chưa xác định xu hướng dài hạn.', source: 'ai', factIds: ['fact_test'] };
      const calculations = input.calculation === 'both' ? ['sum', 'average_per_day'] : [input.calculation];
      return fulfillJson(route, { schemaVersion: 'ai-context-v1', analysisId: 'ana_context_fixture', status: 'ready',
        window: { start: input.view === 'overview' ? input.start : '2026-09-07', end: input.view === 'overview' ? input.end : '2026-09-20', groupBy: input.groupBy },
        dataAsOf: { committedImportRef: 'imp_1', stale: false }, context: { ...input, requestedCount: ids.length, analyzedCount: ids.length, requestedEntityRefs: ids, excluded: [] },
        provider: { generatedCandidateCount: 2, engineOnlyCandidateCount: 3 }, validation: { status: 'accepted', errors: [] },
        evidence: [{ evidenceId: 'ev_context', observedDate: '2026-09-13', target: { kind: 'aggregate', aggregateRef: 'agg_context_1' } }],
        report: { overview: [{ ...paragraph, text: 'Các vấn đề diễn biến khác nhau. Mức giảm chung không mô tả được từng vấn đề.' }],
          relationships: [{ ...paragraph, text: 'Camera 360 lỗi kết nối giảm, trong khi 5G mất kết nối tăng ở cùng hai kỳ. Chưa có căn cứ kết luận hai vấn đề tác động đến nhau.' }], relationshipDetails: [], limitations: ['Không cộng các vấn đề thành tổng nhóm.'],
          issues: ids.flatMap(id => calculations.map((calculation: string) => ({ entityRef: id, entityLabel: entities.find(e => e.entity_id === id)?.entity_label || id, calculation,
            metrics: [{ metricCode: 'error', metricDisplayName: 'Báo sai/Lỗi', unit: calculation === 'sum' ? 'ticket' : 'ticket/ngày', quality: { limitations: [] },
              series: [{ periodLabel: '07–13/09/2026', displayValue: '8', evidenceId: 'ev_context' }, { periodLabel: '14–20/09/2026', displayValue: '6', evidenceId: 'ev_context' }] }],
            report: { overview: [], phases: [paragraph], relationships: [] } }))) } });
    }
    if (url.pathname === '/api/projects/VSO/ai/trend-summary' && request.method() === 'POST') {
      aiRequestCount += 1;
      if (options.aiDelayMs) await new Promise(resolve => setTimeout(resolve, options.aiDelayMs));
      if (options.aiFailureRequests?.includes(aiRequestCount)) return fulfillJson(route, { detail: { code: 'AI_PROVIDER_TEST_FAILURE', message: 'Provider thử nghiệm không phản hồi.' } }, 503);
      return fulfillJson(route, options.aiFixture || aiAnalysis(request.postDataJSON() as Record<string, string>, options.aiResponseStatus, options.aiLimitedComparison, options.aiWholeSeries, options.aiCurrentDataset));
    }
    if (url.pathname === '/api/ai/analyses/ana_e2e') return fulfillJson(route, aiAnalysis({ entityRef: 'root', metricCode: 'error', start: '2026-09-16', end: '2026-09-17' }, options.aiResponseStatus));
    if (url.pathname === '/api/projects/VSO/entities') {
      const source = options.overviewSummaryByRequest?.[0]?.source as { entityRef?: string; effectiveUnit?: string } | undefined;
      return fulfillJson(route, { entities: entities.map(item => item.entity_id === source?.entityRef ? { ...item, effective_unit: source.effectiveUnit } : item) });
    }
    if (url.pathname === '/api/projects/VSO/workspace') {
      workspaceRequestCount += 1;
      const requestNumber = workspaceRequestCount;
      const delay = options.workspaceDelaysMs?.[requestNumber - 1] ?? options.workspaceDelayMs ?? 0;
      if (delay) await new Promise(resolve => setTimeout(resolve, delay));
      if (options.workspaceFailureRequests?.includes(requestNumber)) return fulfillJson(route, { detail: 'Mất kết nối workspace thử nghiệm' }, 503);
      return fulfillJson(route, workspace(url, { ...options, workspaceVersionsByRequest: options.workspaceVersionsByRequest || Array(requestNumber).fill(committedVersion) }, requestNumber));
    }
    if (/\/observations\/[^/]+\/provenance$/.test(url.pathname)) {
      if (options.provenanceDelayMs) await new Promise(resolve => setTimeout(resolve, options.provenanceDelayMs));
      if (failuresLeft > 0) { failuresLeft -= 1; return fulfillJson(route, { detail: 'Mất kết nối thử nghiệm' }, 500); }
      const observationRef = decodeURIComponent(url.pathname.split('/').at(-2) || '');
      return fulfillJson(route, provenance(observationRef, url.searchParams.get('lineageRef') || ''));
    }
    if (/\/aggregates\/[^/]+\/provenance$/.test(url.pathname)) {
      const aggregateRef = decodeURIComponent(url.pathname.split('/').at(-2) || '');
      return fulfillJson(route, aggregateProvenance(aggregateRef));
    }
    if (/\/aggregates\/[^/]+\/contributors$/.test(url.pathname)) {
      const aggregateRef = decodeURIComponent(url.pathname.split('/').at(-2) || '');
      const metric = aggregateRef.includes('_total_') ? 'Tổng số' : 'Báo sai/Lỗi';
      return fulfillJson(route, {
        contractVersion: 2, aggregateRef, total: 2, nextCursor: null,
        items: [1, 2].map(index => ({
          observationRef: `obs_contributor_${index}`, lineageRef: `lin_contributor_${index}`,
          role: 'value', included: true, contributionValue: index + 2, note: null,
          date: `2026-09-${15 + index}`, entityLabel: aggregateRef.includes('_b_') ? '5G mất kết nối' : 'Camera 360 lỗi kết nối',
          metric, displayValue: String(index + 2), chartValue: index + 2, validationStatus: 'valid',
        })),
      });
    }
    if (url.pathname === '/api/projects/VSO/audit/lookup') {
      const observationRef = url.searchParams.get('observationRef') || '';
      const lineageRef = url.searchParams.get('lineageRef') || '';
      const p = provenance(observationRef, lineageRef);
      return fulfillJson(route, { contractVersion: 1, observationRef, lineageRef, row: { date: p.context.observedDate, entity_path: 'VSO / 1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống', metric_normalized: 'Tổng số', raw_value: p.values.raw.text, display_value: p.values.display, chart_value: p.values.chart, value_kind: 'numeric', sheet_name: 'Daily', cell_address: p.source.cell, validation_status: 'valid' }, recommendedContext: { entityRef: 'root', start: p.context.observedDate, end: p.context.observedDate, metric: 'Tổng số' } });
    }
    if (/\/observations\/[^/]+\/revisions$/.test(url.pathname)) {
      const observationRef = decodeURIComponent(url.pathname.split('/').at(-2) || '');
      return fulfillJson(route, { contractVersion: 2, observationRef, items: [{ revisionRef: 'rev_old', lineageRef: `lin_${observationRef.replace('obs_', '')}`, changeType: 'inserted', recordedAt: '2026-09-17T08:00:00Z', displayValue: '14', chartValue: 14, validationStatus: 'valid', state: 'superseded', importRef: 'imp_1', attemptRef: 'attempt_1' }] });
    }
    if (url.pathname === '/api/projects/VSO/imports/imp_1') return fulfillJson(route, { contractVersion: 2, importRef: 'imp_1', attemptRef: 'attempt_1', status: 'committed', workbookName: 'vso.xlsx', workbookHash: 'a'.repeat(64), mode: 'incremental', committedAt: '2026-09-17T08:00:00Z', dataRange: { start: '2026-09-16', end: '2026-09-17' }, outcome: { inserted: 12, updated: 0, unchanged: 0, restored: 0, deleted: 0 } });
    if (url.pathname === '/api/imports/preview' && request.method() === 'POST') return fulfillJson(route, options.previewFixture || { manifest: { source_file: 'snapshot.xlsx', source_hash: 'b'.repeat(64), record_count: 12, date_count: 2, observed_date_min: '2026-09-16', observed_date_max: '2026-09-17', projects: ['VSO'] }, valid: true, errorCount: 0, warningCount: 0, issues: [] });
    if (url.pathname === '/api/imports' && request.method() === 'POST') {
      if (options.commitDelayMs) await new Promise(resolve => setTimeout(resolve, options.commitDelayMs));
      if (options.commitNetworkFailure) return route.abort('failed');
      if (options.commitFailureStatus) return fulfillJson(route, { detail: options.commitFailureStatus === 409 ? 'Tệp đã thay đổi sau khi xem trước; hãy kiểm tra lại' : 'Dữ liệu không đạt kiểm tra chất lượng; chưa thể nhập tệp' }, options.commitFailureStatus);
      const outcome = options.importOutcome || { attempt_id: 2, status: 'committed', run_id: 2, duplicate_of_run_id: null, inserted_count: 0, updated_count: 2, unchanged_count: 10, restored_count: 0, deleted_count: 0, lineage_changed_count: 0, message: null };
      if (outcome.status === 'committed') committedVersion = 'imp_2';
      return fulfillJson(route, outcome);
    }
    if (url.pathname === '/api/imports') {
      historyRequestCount += 1;
      const requestIndex = historyRequestCount - 1;
      if (options.historyDelaysMs?.[requestIndex]) await new Promise(resolve => setTimeout(resolve, options.historyDelaysMs![requestIndex]));
      if (options.historyFailureRequests?.includes(requestIndex + 1)) return fulfillJson(route, { detail: 'Lịch sử thử nghiệm chưa phản hồi' }, 503);
      return fulfillJson(route, { items: options.historyItemsByRequest?.[requestIndex] ?? options.historyItemsByRequest?.at(-1) ?? [{ attempt_id: 2, attempt_status: 'committed', submitted_file_name: 'update.xlsx', requested_mode: 'incremental', input_record_count: 12, inserted_count: 0, updated_count: 2, unchanged_count: 10, started_at: '2026-09-17T09:00:00Z' }] });
    }
    return fulfillJson(route, { detail: `Unhandled test route: ${url.pathname}` }, 404);
  });
  return { calls, workspaceRequestCount: () => workspaceRequestCount };
}
