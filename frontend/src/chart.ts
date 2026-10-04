import type { ChartPointSelection, Figure } from './types';
import { formatMetricText, getMetricDisplayLabel } from './terminology';

let plotlyModule: Promise<typeof import('plotly.js-basic-dist-min')> | null = null;
const renderVersions = new WeakMap<HTMLElement, number>();
const CHART_TEXT_COLOR = '#526176';

/** Presentation-only overrides; numerical data, lineage metadata and trace order stay intact. */
export function presentationFigure(figure: Figure, height = 420, identity?: string): Figure {
  const data = figure.data.map(trace => {
    const styled = { ...trace };
    if (typeof styled.name === 'string') styled.name = formatMetricText(styled.name);
    if (typeof styled.hovertemplate === 'string') styled.hovertemplate = formatMetricText(styled.hovertemplate);
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
  const labels = [...new Set(data.flatMap(trace => Array.isArray(trace.x) ? trace.x.filter((x): x is string => typeof x === 'string') : []))];
  const weeks = labels.filter(label => /^Tuần\s+\d{1,2}\/\d{4}/i.test(label));
  const xaxis = { ...(figure.layout.xaxis ?? {}) };
  if (weeks.length && weeks.length === labels.length) {
    xaxis.tickmode = 'array';
    xaxis.tickvals = weeks;
    xaxis.ticktext = weeks.map(label => `T${Number(label.match(/^Tuần\s+(\d+)/i)?.[1])}`);
    xaxis.tickangle = 0;
  }
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
      font: { family: 'Inter, Segoe UI, sans-serif', color: CHART_TEXT_COLOR, size: 12 },
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
  const styled = presentationFigure(figure, height, identity);
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
