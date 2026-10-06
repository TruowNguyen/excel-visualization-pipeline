import type { ChartPointSelection, Figure } from './types';
import { formatMetricText, getMetricDisplayLabel } from './terminology';

let plotlyModule: Promise<typeof import('plotly.js-basic-dist-min')> | null = null;
const renderVersions = new WeakMap<HTMLElement, number>();
const chartObservers = new WeakMap<HTMLElement, ResizeObserver>();
const CHART_TEXT_COLOR = '#526176';
const ISO_WEEK_LABEL = /^Tuần\s+(\d{1,2})\/(\d{4})(?:\s|$)/i;

/** Keep the category key intact; use UTC to avoid shifting ISO week boundaries. */
function weekDates(label: string): { start: Date; end: Date; year: number } | null {
  const match = label.match(ISO_WEEK_LABEL);
  if (!match) return null;
  const week = Number(match[1]);
  const year = Number(match[2]);
  if (week < 1 || week > 53 || year < 1000) return null;
  const januaryFourth = new Date(Date.UTC(year, 0, 4));
  const mondayOffset = (januaryFourth.getUTCDay() + 6) % 7;
  const start = new Date(Date.UTC(year, 0, 4 - mondayOffset + (week - 1) * 7));
  const thursday = new Date(start.getTime() + 3 * 86_400_000);
  if (thursday.getUTCFullYear() !== year) return null; // Do not invent an invalid week 53.
  return { start, end: new Date(start.getTime() + 6 * 86_400_000), year };
}

function weekDateLabel(label: string, includeYear: boolean): string {
  const dates = weekDates(label);
  if (!dates) return label;
  const showYear = includeYear || dates.start.getUTCFullYear() !== dates.end.getUTCFullYear();
  const format = (date: Date) => `${String(date.getUTCDate()).padStart(2, '0')}/${String(date.getUTCMonth() + 1).padStart(2, '0')}${showYear ? `/${date.getUTCFullYear()}` : ''}`;
  return `${format(dates.start)} - ${format(dates.end)}`;
}

function weeklyAxis(figure: Figure, width?: number): Record<string, unknown> | null {
  const labels = [...new Set(figure.data.flatMap(trace => Array.isArray(trace.x) ? trace.x.filter((x): x is string => typeof x === 'string') : []))];
  if (!labels.length || !labels.every(label => ISO_WEEK_LABEL.test(label))) return null;
  const multipleYears = new Set(labels.map(label => label.match(ISO_WEEK_LABEL)![2])).size > 1;
  const text = labels.map(label => weekDateLabel(label, multipleYears));
  const hasYear = text.some(label => /\/\d{4}/.test(label));
  const available = Math.max(1, (width ?? Infinity) - 100);
  const compact = available / labels.length < (hasYear ? 200 : 112);
  const capacity = Math.max(2, Math.floor(available / (hasYear ? 100 : 56)));
  const count = Math.min(labels.length, capacity);
  // Even spacing preserves the first and last week without crowded trailing ticks.
  const indices = Array.from({ length: count }, (_, index) => count === 1 ? 0 : Math.round(index * (labels.length - 1) / (count - 1)));
  return {
    tickmode: 'array', tickvals: indices.map(index => labels[index]),
    ticktext: indices.map(index => compact ? text[index].replace(' - ', '<br>- ') : text[index]),
    tickangle: 0, automargin: true,
  };
}

/** Presentation-only overrides; numerical data, lineage metadata and trace order stay intact. */
export function presentationFigure(figure: Figure, height = 420, identity?: string, width?: number): Figure {
  const weekAxis = weeklyAxis(figure, width);
  const weekLabels = weekAxis ? figure.data.flatMap(trace => Array.isArray(trace.x) ? trace.x : []) : [];
  const multipleYears = new Set(weekLabels.map(label => String(label).match(ISO_WEEK_LABEL)?.[2])).size > 1;
  const data = figure.data.map(trace => {
    const styled = { ...trace };
    if (typeof styled.name === 'string') styled.name = formatMetricText(styled.name);
    if (typeof styled.hovertemplate === 'string') styled.hovertemplate = formatMetricText(styled.hovertemplate);
    if (weekAxis && Array.isArray(styled.x) && styled.hovertext == null) {
      styled.hovertext = styled.x.map(label => weekDateLabel(String(label), multipleYears));
      styled.hovertemplate = typeof styled.hovertemplate === 'string'
        ? styled.hovertemplate.replaceAll('%{x}', '%{hovertext}')
        : '%{hovertext}<br>%{y}<extra></extra>';
    }
    // Map only exact metric keys: dates, values and other source text remain untouched.
    if (Array.isArray(styled.customdata)) styled.customdata = styled.customdata.map(row =>
      Array.isArray(row) ? row.map(cell => typeof cell === 'string' ? getMetricDisplayLabel(cell) : cell) : row,
    );
    if (styled.type === 'bar') {
      styled.textposition = 'none';
      styled.opacity = Math.min(Number(styled.opacity ?? 1), 0.82);
    }
    if (styled.type === 'scatter' && typeof styled.mode === 'string' && styled.mode.includes('text')) {
      styled.mode = styled.mode.split('+').filter(part => part !== 'text').join('+');
      styled.text = undefined;
    }
    return styled;
  });
  const xaxis = { ...(figure.layout.xaxis ?? {}), ...weekAxis };
  const displayAxis = (axis: unknown): Record<string, unknown> => {
    const source = axis && typeof axis === 'object' ? axis as Record<string, unknown> : {};
    const title = source.title;
    return { ...source, ...(typeof title === 'string' ? { title: formatMetricText(title) }
      : title && typeof title === 'object' && 'text' in title && typeof title.text === 'string'
        ? { title: { ...title, text: formatMetricText(title.text) } } : {}) };
  };
  return {
    data,
    layout: {
      ...figure.layout,
      title: { text: '' },
      autosize: true,
      height,
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      font: { family: 'Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, sans-serif', color: CHART_TEXT_COLOR, size: 12 },
      hovermode: figure.layout.hovermode ?? 'x unified',
      hoverdistance: figure.layout.hoverdistance ?? -1,
      hoverlabel: { bgcolor: '#172238', bordercolor: '#172238', font: { color: '#fff', size: 12 } },
      legend: {
        ...(figure.layout.legend ?? {}),
        orientation: 'h', x: 0, xanchor: 'left', y: 1.13, yanchor: 'bottom',
        font: { color: CHART_TEXT_COLOR, size: 11 }, itemwidth: 28, tracegroupgap: 14,
        bgcolor: 'rgba(0,0,0,0)', borderwidth: 0,
      },
      xaxis,
      yaxis: displayAxis(figure.layout.yaxis),
      ...(figure.layout.yaxis2 ? { yaxis2: displayAxis(figure.layout.yaxis2) } : {}),
      uirevision: figure.layout.uirevision ?? identity,
      margin: { l: 58, r: 42, t: 88, b: 64 },
    },
  };
}

type PlotClickEvent = {
  points?: { curveNumber: number; pointNumber: number; x: unknown; y: unknown }[];
};

type PlotElement = HTMLElement & {
  on?: (event: string, listener: (payload: PlotClickEvent) => void) => void;
  removeAllListeners?: (event: string) => void;
};

export function renderChart(
  element: HTMLElement,
  figure: Figure,
  onPointClick?: (selection: ChartPointSelection) => void,
  selectedRef?: string,
  height = 420,
  identity?: string,
): Promise<void> {
  plotlyModule ??= import('plotly.js-basic-dist-min');
  const version = (renderVersions.get(element) ?? 0) + 1;
  renderVersions.set(element, version);
  chartObservers.get(element)?.disconnect();
  chartObservers.delete(element);
  const styled = presentationFigure(figure, height, identity, element.clientWidth);
  styled.data = styled.data.map(trace => {
    const lineage = trace.meta?.lineage;
    if (!lineage || !['exact-observation', 'aggregate'].includes(lineage.kind)) return trace;
    const refs = lineage.kind === 'aggregate' ? lineage.aggregateRefs : trace.ids;
    const selectedIndex = selectedRef ? refs?.indexOf(selectedRef) ?? -1 : -1;
    return {
      ...trace,
      ...(selectedIndex >= 0 ? { selectedpoints: [selectedIndex] } : {}),
      selected: { marker: { opacity: 1, line: { color: '#5144b8', width: 2 } } },
      unselected: { marker: { opacity: .48 } },
    };
  });
  return plotlyModule.then(({ default: Plotly }) => {
    if (!element.isConnected) return;
    element.dispatchEvent(new CustomEvent('cx:plotly-render-start', { bubbles: true }));
    return Plotly.react(element, styled.data, styled.layout, {
      responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: false,
    }).then(() => {
      if (!element.isConnected || renderVersions.get(element) !== version) return;
      element.dispatchEvent(new CustomEvent('cx:plotly-render-complete', { bubbles: true }));
      const plot = element as PlotElement;
      plot.removeAllListeners?.('plotly_click');
      if (weeklyAxis(figure) && typeof ResizeObserver !== 'undefined') {
        let lastWidth = element.clientWidth;
        const observer = new ResizeObserver(() => {
          if (!element.isConnected || renderVersions.get(element) !== version) return;
          const width = element.clientWidth;
          if (!width || width === lastWidth) return;
          lastWidth = width;
          const axis = weeklyAxis(figure, width)!;
          const update = Object.fromEntries(Object.entries(axis).map(([key, value]) => [`xaxis.${key}`, value]));
          // Update only axis presentation: no new workspace fetch or trace replacement.
          void Plotly.relayout(element, { autosize: true, ...update });
        });
        observer.observe(element);
        chartObservers.set(element, observer);
      }
      if (!onPointClick) return;
      plot.on?.('plotly_click', event => {
        const point = event.points?.[0];
        if (!point) return;
        const trace = styled.data[point.curveNumber];
        const lineage = trace?.meta?.lineage;
        if (!lineage || !['exact-observation', 'aggregate'].includes(lineage.kind)) return;
        onPointClick({
          kind: lineage.kind as ChartPointSelection['kind'],
          aggregateRef: lineage.aggregateRefs?.[point.pointNumber] ?? null,
          observationRef: lineage.kind === 'exact-observation' ? trace.ids?.[point.pointNumber] ?? null : null,
          lineageRef: lineage.kind === 'exact-observation' ? lineage.lineageRefs?.[point.pointNumber] ?? null : null,
          seriesName: String(trace.name ?? ''),
          x: point.x,
          y: point.y,
          curveNumber: point.curveNumber,
          pointNumber: point.pointNumber,
        });
      });
    });
  });
}

/** Release Plotly listeners and observers when a keyed chart leaves the workspace. */
export function purgeChart(element: HTMLElement): void {
  chartObservers.get(element)?.disconnect();
  chartObservers.delete(element);
  renderVersions.delete(element);
  if (!plotlyModule) return;
  void plotlyModule.then(({ default: Plotly }) => Plotly.purge(element));
}

export function selectChartPoint(element: HTMLElement, curveNumber: number, pointNumber: number): void {
  plotlyModule ??= import('plotly.js-basic-dist-min');
  void plotlyModule.then(({ default: Plotly }) => {
    if (!element.isConnected) return;
    return Plotly.restyle(element, { selectedpoints: [null] })
      .then(() => Plotly.restyle(element, { selectedpoints: [[pointNumber]] }, [curveNumber]));
  });
}

export function clearChartSelection(element: HTMLElement): void {
  plotlyModule ??= import('plotly.js-basic-dist-min');
  void plotlyModule.then(({ default: Plotly }) => {
    if (!element.isConnected) return;
    return Plotly.restyle(element, { selectedpoints: [null] });
  });
}
