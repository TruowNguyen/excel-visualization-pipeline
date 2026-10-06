import type { ReportChart, ReportFinding } from './report-workspace';
import type { Figure } from './types';
import { presentationFigure } from './chart';

let plotly: Promise<typeof import('plotly.js-basic-dist-min')> | null = null;
const observers = new WeakMap<HTMLElement, ResizeObserver>();
const versions = new WeakMap<HTMLElement, number>();

export function reportFigure(chart: ReportChart, findings: ReportFinding[], selected: string[], active: string, width = 900, numbering = selected) {
  const marks = selected.flatMap(id => (findings.find(f => f.findingId === id)?.anchors || [])
    .filter(a => a.chartId === chart.chartId).map(a => ({ ...a, number: numbering.indexOf(id) + 1, findingId: id })));
  const pointIds = new Map(chart.points.map(p => [p.factId, p]));
  const groupedMarks = new Map<string, typeof marks>();
  for (const mark of marks) groupedMarks.set(mark.factId, [...(groupedMarks.get(mark.factId) || []), mark]);
  const annotations = [...groupedMarks.values()].map(rows => ({ x: rows[0].periodStart, y: pointIds.get(rows[0].factId)?.value,
    text: [...new Set(rows.map(r => r.number))].join(','), showarrow: true, arrowhead: 0, ax: 0, ay: -28,
    bgcolor: rows.some(r => r.findingId === active) ? '#50429b' : '#6253b5', borderpad: 4,
    font: { color: 'white', size: 12 }, arrowcolor: '#6253b5' }));
  const shapes = selected.flatMap(id => {
    const anchors = findings.find(f => f.findingId === id)?.anchors.filter(a => a.chartId === chart.chartId) || [];
    const dates = [...new Set(anchors.map(a => a.periodStart))].sort();
    if (dates.length < 2) return [];
    // Never paint a continuous phase over a null/gap.
    if (chart.points.some(p => p.value === null && p.periodStart > dates[0] && p.periodStart < dates.at(-1)!)) return [];
    return [{ type: 'rect', xref: 'x', yref: 'paper', x0: dates[0], x1: dates.at(-1), y0: 0, y1: 1,
      fillcolor: id === active ? 'rgba(98,83,181,.13)' : 'rgba(98,83,181,.04)', line: { width: 0 }, layer: 'below' }];
  });
  const tickCount = Math.min(chart.points.length, Math.max(2, Math.min(6, Math.floor((width-90)/115))));
  const indices = [...new Set(Array.from({ length: tickCount }, (_, i) =>
    Math.round(i * (chart.points.length - 1) / Math.max(1, tickCount - 1))))];
  const dateText = (date: string) => date.split('-').reverse().join('/');
  return {
    data: [{ type: 'scatter', mode: 'lines+markers', name: chart.metricLabel,
      x: chart.points.map(p => p.periodStart), y: chart.points.map(p => p.value),
      customdata: chart.points.map(p => [p.periodLabel, p.displayValue, p.factId, p.evidenceId]),
      connectgaps: false, line: { color: '#315b83', width: 2 }, marker: { size: 6, color: '#315b83' },
      hovertemplate: '%{customdata[0]}<br>%{customdata[1]}<extra></extra>' }],
    layout: { autosize: true, height: 360, margin: { l: 65, r: 25, t: 45, b: 65 },
      paper_bgcolor: '#ffffff', plot_bgcolor: '#ffffff', showlegend: false,
      font: { family: 'Segoe UI, system-ui, sans-serif', size: 12, color: '#526176' },
      hoverlabel: { bgcolor: '#172238', font: { color: 'white' } },
      xaxis: { type: 'date', tickmode: 'array', tickvals: indices.map(i => chart.points[i].periodStart),
        ticktext: indices.map(i => dateText(chart.points[i].periodStart)), automargin: true },
      yaxis: { title: { text: chart.unit }, zerolinecolor: '#dde2e8', gridcolor: '#eef0f4', automargin: true },
      annotations, shapes, uirevision: chart.chartId },
  };
}

export async function drawReportChart(host: HTMLElement, chart: ReportChart, findings: ReportFinding[],
                                      selected: string[], active: string, onSelect: (findingId: string) => void,
                                      charts: ReportChart[] = [chart], base?: Figure): Promise<void> {
  plotly ??= import('plotly.js-basic-dist-min');
  const version = (versions.get(host) || 0) + 1;
  versions.set(host, version);
  const { default: Plotly } = await plotly;
  if (!host.isConnected || versions.get(host) !== version) return;
  const focused = !!active && findings.some(f => f.findingId === active);
  const ids = focused ? [active] : selected;
  const figure = base ? presentationFigure(structuredClone(base), 420, chart.chartId, host.clientWidth)
    : reportFigure(chart, findings, ids, active, host.clientWidth, selected);
  if (!base && focused && !selected.includes(active)) {
    (figure.layout.annotations as {text:string}[]).forEach(annotation => { annotation.text = 'Đang xem'; });
  }
  if (base) {
    const annotations: Record<string, unknown>[] = [];
    const shapes: Record<string, unknown>[] = [];
    for (const member of charts) {
      // Show only the active finding's annotations while focused. All selected
      // markers remain available without overlaying every interval at once.
      const marks = reportFigure(member, findings, ids, active, host.clientWidth, selected);
      const trace = base.data.find(t => t.meta?.reportChartId === member.chartId);
      for (const annotation of marks.layout.annotations) {
        annotations.push({...annotation, text:focused && !selected.includes(active) ? 'Đang xem' : annotation.text, yref:trace?.yaxis || 'y'});
      }
      if (focused) shapes.push(...marks.layout.shapes);
    }
    if (!focused) {
      // One period badge across all series: avoid stacked labels on two axes.
      const periods = new Map<string, Set<string>>();
      for (const annotation of annotations) {
        const date = annotation.x as string;
        const numbers = periods.get(date) || new Set<string>();
        String(annotation.text).split(',').forEach(n => numbers.add(n));
        periods.set(date, numbers);
      }
      annotations.splice(0, annotations.length, ...[...periods].map(([date, numbers]) => ({
        x: date, y: 1.04, yref: 'paper', text: [...numbers].sort().join(','), showarrow: false,
        bgcolor: '#6253b5', borderpad: 4, font: {color: 'white', size: 12},
      })));
    }
    figure.layout.annotations = annotations;
    figure.layout.shapes = shapes;
    const axis = figure.layout.xaxis as Record<string, any>;
    const values = axis.tickvals as string[], labels = axis.ticktext as string[];
    const capacity = Math.max(2, Math.floor((host.clientWidth - 130) / 125));
    const count = Math.min(values.length, capacity);
    const indices = [...new Set(Array.from({length:count}, (_, i) => Math.round(i * (values.length-1) / Math.max(1,count-1))))];
    axis.tickvals = indices.map(i => values[i]); axis.ticktext = indices.map(i => labels[i]);
    figure.layout.margin = {l:65,r:75,t:100,b:65};
  }
  await Plotly.react(host, figure.data, figure.layout, { responsive: true, displayModeBar: false, displaylogo: false });
  if (!host.isConnected || versions.get(host) !== version) return;
  const element = host as HTMLElement & { removeAllListeners?: (event: string) => void; on?: (event: string, callback: (event: { points?: { pointNumber: number; curveNumber?: number }[] }) => void) => void };
  element.removeAllListeners?.('plotly_click');
  element.on?.('plotly_click', event => {
    const hit = event.points?.[0];
    const traceId = base?.data[hit?.curveNumber ?? 0]?.meta?.reportChartId;
    const member = charts.find(c => c.chartId === traceId) || chart;
    const point = member.points[hit?.pointNumber ?? -1];
    if (!point?.factId) return;
    const id = selected.find(id => findings.find(f => f.findingId === id)?.anchors.some(a => a.chartId === member.chartId && a.factId === point.factId));
    if (id) onSelect(id);
  });
  observers.get(host)?.disconnect();
  const observer = new ResizeObserver(() => {
    if (!host.isConnected) return;
    const axis = base?.layout.xaxis as {tickvals?: string[]; ticktext?: string[]} | undefined;
    if (!axis?.tickvals || !axis.ticktext) { void Plotly.relayout(host, {autosize:true}); return; }
    const count = Math.min(axis.tickvals.length, Math.max(2, Math.floor((host.clientWidth-130)/125)));
    const indices = [...new Set(Array.from({length:count}, (_, i) => Math.round(i*(axis.tickvals!.length-1)/Math.max(1,count-1))))];
    void Plotly.relayout(host, {autosize:true, 'xaxis.tickvals':indices.map(i => axis.tickvals![i]), 'xaxis.ticktext':indices.map(i => axis.ticktext![i])});
  });
  observer.observe(host);
  observers.set(host, observer);
  host.dataset.reportChartReady = 'true';
}

export function purgeReportChart(host: HTMLElement): void {
  observers.get(host)?.disconnect(); observers.delete(host); versions.delete(host);
  if (plotly) void plotly.then(({ default: Plotly }) => Plotly.purge(host));
}
