export type Entity = {
  entity_id: string;
  parent_entity_id: string | null;
  entity_label: string;
  entity_path: string;
  entity_level: string;
  entity_depth: number;
  effective_unit: string | null;
};

export type ChartTrace = {
  type?: string;
  name?: string;
  x?: unknown[];
  y?: unknown[] | { dtype?: string; bdata?: string };
  mode?: string;
  text?: unknown;
  textposition?: unknown;
  opacity?: number;
  ids?: (string | null)[];
  meta?: {
    lineage?: {
      contractVersion: number;
      kind: string;
      selectable: boolean;
      lineageRefs?: (string | null)[];
      aggregateRefs?: (string | null)[];
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

export type AccessibleChartPoint = {
  key: string;
  label: string;
  selection: ChartPointSelection;
  hasProvenance: boolean;
};

export type ChartPointSelection = {
  kind: 'exact-observation' | 'aggregate';
  aggregateRef: string | null;
  observationRef: string | null;
  lineageRef: string | null;
  seriesName: string;
  x: unknown;
  y: unknown;
  curveNumber: number;
  pointNumber: number;
};

export type Figure = {
  data: ChartTrace[];
  layout: Record<string, unknown> & {
    xaxis?: Record<string, unknown>;
    legend?: Record<string, unknown>;
  };
};
