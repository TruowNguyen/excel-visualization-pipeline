import type { AccessibleChartPoint, ChartPointSelection, ChartTrace, Figure } from './types';

function decodeNumericArray(value: ChartTrace['y']): unknown[] {
  if (Array.isArray(value)) return value;
  if (!value?.bdata || !value.dtype) return [];
  try {
    const bytes = Uint8Array.from(atob(value.bdata), character => character.charCodeAt(0));
    const view = new DataView(bytes.buffer);
    const readers: Record<string, { size: number; read: (offset: number) => number }> = {
      f8: { size: 8, read: offset => view.getFloat64(offset, true) },
      f4: { size: 4, read: offset => view.getFloat32(offset, true) },
      i4: { size: 4, read: offset => view.getInt32(offset, true) },
      i2: { size: 2, read: offset => view.getInt16(offset, true) },
      i1: { size: 1, read: offset => view.getInt8(offset) },
      u4: { size: 4, read: offset => view.getUint32(offset, true) },
      u2: { size: 2, read: offset => view.getUint16(offset, true) },
      u1: { size: 1, read: offset => view.getUint8(offset) },
    };
    const reader = readers[value.dtype.replace(/[<>|=]/g, '')];
    if (!reader || bytes.byteLength % reader.size !== 0) return [];
    return Array.from({ length: bytes.byteLength / reader.size }, (_, index) => reader.read(index * reader.size));
  } catch {
    return [];
  }
}

function pointValueLabel(value: unknown, seriesName: string): string {
  if (value === null || value === undefined || (typeof value === 'number' && !Number.isFinite(value))) return 'không có giá trị';
  if (typeof value !== 'number') return String(value);
  const formatted = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 }).format(value);
  return seriesName.includes('%') ? `${formatted}%` : formatted;
}

function pointDateLabel(value: unknown): string {
  const text = String(value ?? 'Không rõ thời điểm');
  const date = text.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(date)
    ? new Date(`${date}T00:00:00`).toLocaleDateString('vi-VN')
    : text;
}

/** Build the keyboard surface only from stable lineage metadata shipped with each trace. */
export function accessibleChartPoints(figure: Figure): AccessibleChartPoint[] {
  const points: AccessibleChartPoint[] = [];
  figure.data.forEach((trace, curveNumber) => {
    const lineage = trace.meta?.lineage;
    if (!lineage?.selectable || !['exact-observation', 'aggregate'].includes(lineage.kind)) return;
    const xValues = Array.isArray(trace.x) ? trace.x : [];
    const yValues = decodeNumericArray(trace.y);
    const length = Math.max(xValues.length, yValues.length, trace.ids?.length ?? 0, lineage.aggregateRefs?.length ?? 0);
    for (let pointNumber = 0; pointNumber < length; pointNumber += 1) {
      const y = yValues[pointNumber];
      if (y === null || y === undefined || (typeof y === 'number' && !Number.isFinite(y))) continue;
      const kind = lineage.kind as ChartPointSelection['kind'];
      const observationRef = kind === 'exact-observation' ? trace.ids?.[pointNumber] ?? null : null;
      const lineageRef = kind === 'exact-observation' ? lineage.lineageRefs?.[pointNumber] ?? null : null;
      const aggregateRef = kind === 'aggregate' ? lineage.aggregateRefs?.[pointNumber] ?? null : null;
      const seriesName = String(trace.name ?? 'Chuỗi dữ liệu');
      const hasProvenance = kind === 'aggregate' ? Boolean(aggregateRef) : Boolean(observationRef && lineageRef);
      const suffix = hasProvenance ? '' : ' · chưa có nguồn truy vết';
      points.push({
        key: `${curveNumber}:${pointNumber}`,
        label: `${seriesName} · ${pointDateLabel(xValues[pointNumber])} · ${pointValueLabel(y, seriesName)}${suffix}`,
        hasProvenance,
        selection: {
          kind,
          aggregateRef,
          observationRef,
          lineageRef,
          seriesName,
          x: xValues[pointNumber],
          y,
          curveNumber,
          pointNumber,
        },
      });
    }
  });
  return points;
}
