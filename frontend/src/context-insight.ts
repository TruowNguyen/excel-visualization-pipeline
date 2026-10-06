import { formatMetricText, formatEntityText } from './terminology';
import type { Entity } from './types';
import { renderInsightParagraph, renderInsightPhase, type InsightParagraph } from './insight-text';

type Paragraph = InsightParagraph & { source: string; factIds?: string[] };
type Metric = { metricCode: string; metricDisplayName: string; unit: string; quality: { limitations: string[] };
  series: { periodLabel: string; displayValue: string; evidenceId: string }[] };
export type ContextInsight = {
  analysisId: string; status: string; dataAsOf: { stale: boolean; committedImportRef: string };
  window: { start: string; end: string; groupBy: string };
  context: { view: string; selection: string; parentEntityRef: string; calculation: string;
    requestedCount: number; analyzedCount: number; requestedEntityRefs: string[];
    excluded: { entityRef: string; entityLabel: string; reason: string }[] };
  provider: { generatedCandidateCount: number; engineOnlyCandidateCount: number };
  validation: { status: string; errors: string[] };
  evidence: { evidenceId: string; observedDate: string; target: { kind: string; aggregateRef?: string; observationRef?: string; lineageRef?: string } }[];
  report: { overview: Paragraph[]; relationships: Paragraph[]; relationshipDetails: Paragraph[]; limitations: string[];
    issues: { entityRef: string; entityLabel: string; calculation: string; metrics: Metric[];
      report: { overview: Paragraph[]; phases: Paragraph[]; relationships: Paragraph[]; comparisonPromoted?: boolean } }[] };
};

const escape = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const calc = (value: string): string => ({ sum: 'Tổng trong kỳ', average_per_day: 'Trung bình/ngày', both: 'Tổng và trung bình/ngày' }[value] || value);
const grouping = (value: string): string => ({ day: 'Theo ngày', week: 'Theo tuần', month: 'Theo tháng', quarter: 'Theo quý' }[value] || value);
const isStale = (result: ContextInsight, stale: boolean): boolean => stale || result.dataAsOf.stale || result.status === 'stale';

export function contextInsightOutput(result: ContextInsight, stale: boolean, entities: readonly Pick<Entity, 'entity_label' | 'entity_level'>[] = []): string {
  const readable = (text: string): string => formatMetricText(formatEntityText(text, entities));
  const paragraph = (p: Paragraph): string => renderInsightParagraph({ ...p, text: readable(p.text) });
  const notice = isStale(result, stale)
    ? '<p class="ai-stale" role="status">Phân tích này không còn khớp bộ lọc hoặc phiên dữ liệu. Hãy tạo lại trước khi sử dụng.</p>'
    : result.status === 'provider_unavailable'
      ? '<p class="ai-muted" role="status">Dịch vụ diễn giải chưa phản hồi. Các kết quả bên dưới vẫn được tổng hợp từ số liệu đã kiểm chứng.</p>'
      : result.validation.status === 'partial' || result.status === 'rejected_output'
        ? '<p class="ai-muted" role="status">Một số đoạn được thay bằng diễn giải từ số liệu để giữ đúng căn cứ.</p>' : '';
  const issues = result.report.issues;
  const groups = new Map<string, typeof issues>();
  for (const issue of issues) groups.set(issue.entityRef, [...(groups.get(issue.entityRef) || []), issue]);
  // Hide only a known presentation prefix whose context is already visible.
  // Keep paragraph order, analytical prose, numbers, source badges and payload intact.
  const prefixes = issues.flatMap(issue => {
    const label = readable(issue.entityLabel);
    return [`${label} · ${calc(issue.calculation)}:`, `${label}:`];
  }).sort((a, b) => b.length - a.length);
  const paragraphs = (items: Paragraph[], visiblePrefix = ''): string => {
    let previous = visiblePrefix;
    return items.map(p => {
      const text = readable(p.text);
      const prefix = prefixes.find(value => text.startsWith(`${value} `) || text === value);
      const rendered = renderInsightParagraph({ ...p,
        text: prefix && prefix === previous ? text.slice(prefix.length).trimStart() : text });
      previous = prefix || ''; // Unlabelled prose must not hide a later context switch.
      return rendered;
    }).join('');
  };
  return `${notice}<div class="ai-result-receipt"><strong>Phạm vi đã phân tích:</strong> <span>${result.context.analyzedCount}/${result.context.requestedCount} nội dung có dữ liệu · ${escape(grouping(result.window.groupBy))} · ${escape(calc(result.context.calculation))} · ${escape(result.window.start)} → ${escape(result.window.end)}</span></div>
    <section class="ai-report-section"><h4>Tổng quan trong thời gian đã chọn</h4>${paragraphs(result.report.overview)}</section>
    ${result.report.relationships.length ? `<section class="ai-report-section"><h4>Diễn biến liên quan giữa các vấn đề</h4>${result.report.relationships.map(paragraph).join('')}</section>` : ''}
    ${result.report.limitations.length ? `<p class="ai-muted">${escape(readable(result.report.limitations.join(' ')))}</p>` : ''}
    ${result.provider.engineOnlyCandidateCount > 0 ? '<p class="ai-muted">AI chỉ diễn giải các phần được ưu tiên để giới hạn thời gian chờ. Các phần còn lại vẫn có kết quả từ số liệu đã kiểm chứng trong chi tiết từng vấn đề.</p>' : ''}
    <section class="ai-report-section"><h4>${groups.size === 1 ? 'Các chỉ số thay đổi như thế nào?' : 'Chi tiết từng vấn đề'}</h4>
    ${[...groups.values()].map(variants => `<details class="ai-issue-detail" ${groups.size === 1 ? 'open' : ''}><summary>${escape(formatEntityText(variants[0].entityLabel, entities))}${variants.length === 1 ? ` · ${escape(calc(variants[0].calculation))}` : ''}</summary>
    ${[...variants].sort((a, b) => Number(b.calculation === 'average_per_day') - Number(a.calculation === 'average_per_day')).map(issue => `<section class="ai-calculation-section" data-calculation="${escape(issue.calculation)}">
      ${variants.length > 1 ? `<h5 class="ai-calculation-title">${escape(calc(issue.calculation))}</h5>` : ''}
      ${paragraphs(issue.report.overview, `${readable(issue.entityLabel)} · ${calc(issue.calculation)}:`)}<ol class="ai-reading-phases">${issue.report.phases.map(phase => renderInsightPhase({ ...phase, text: readable(phase.text) })).join('')}</ol>${paragraphs(issue.report.relationships, `${readable(issue.entityLabel)} · ${calc(issue.calculation)}:`)}
      ${!issue.report.phases.length && !issue.report.comparisonPromoted ? '<p>Chưa đủ kỳ hợp lệ để diễn giải thay đổi.</p>' : ''}
      <details class="ai-disclosure"><summary>Xem số liệu và nguồn</summary>${issue.metrics.map(metric => `<h5>${escape(formatMetricText(metric.metricDisplayName))} · ${escape(metric.unit)}</h5><div class="ai-table-scroll ai-period-table"><table><thead><tr><th>Kỳ</th><th>Giá trị</th><th>Nguồn</th></tr></thead><tbody>${metric.series.map(p => `<tr><td>${escape(p.periodLabel)}</td><td>${escape(p.displayValue)}</td><td><button class="text-action" data-action="open-context-insight-evidence" data-evidence-id="${escape(p.evidenceId)}">Mở nguồn</button></td></tr>`).join('')}</tbody></table></div>`).join('')}</details>
    </section>`).join('')}${[...new Set(variants.flatMap(issue => issue.metrics.flatMap(m => m.quality.limitations)))].map(t => `<p class="ai-muted">${escape(readable(t))}</p>`).join('')}</details>`).join('')}</section>
    ${result.context.excluded.length ? `<details class="ai-disclosure"><summary>Nội dung chưa đủ dữ liệu (${result.context.excluded.length})</summary><ul>${result.context.excluded.map(e => `<li>${escape(formatEntityText(e.entityLabel, entities))}: ${e.reason === 'NO_DIRECT_DATA' ? 'chưa có dữ liệu riêng' : 'chưa có kỳ hợp lệ trong phạm vi đang xem'}.</li>`).join('')}</ul></details>` : ''}
    ${result.report.relationshipDetails.length > result.report.relationships.length ? `<details class="ai-disclosure"><summary>Xem các kỳ liên quan khác</summary>${result.report.relationshipDetails.map(paragraph).join('')}</details>` : ''}`;
}

export function contextInsightPanel(options: { children: { id: string; label: string }[]; selection: string; selected: string[];
    focusedLabel: string; receipt: string; loading: boolean; available: boolean; privateMode: boolean;
    error: string; result: ContextInsight | null; stale: boolean; metricControls?: string;
    entities?: readonly Pick<Entity, 'entity_label' | 'entity_level'>[] }): string {
  const { children, selection, selected, focusedLabel, receipt, loading, available, privateMode, error, result, stale } = options;
  const emptySelection = !focusedLabel && selection === 'selected' && !selected.length;
  const resultStale = result ? isStale(result, stale) : false;
  const list = !focusedLabel && selection === 'selected'
    ? `<fieldset class="ai-issue-picker"><legend>Chọn nội dung cần phân tích · ${selected.length} đã chọn</legend><label>Tìm vấn đề<input type="search" data-context-insight-search placeholder="Nhập tên vấn đề"></label><div class="ai-issue-options">${children.map(c => `<label data-context-issue-label="${escape(c.label.toLocaleLowerCase('vi'))}"><input type="checkbox" data-context-insight-issue="${escape(c.id)}" ${selected.includes(c.id) ? 'checked' : ''}> ${escape(c.label)}</label>`).join('')}</div></fieldset>` : '';
  return `<section id="ai-insights" class="ai-panel ai-context-panel" aria-labelledby="ai-insights-title"><div class="ai-panel-head"><div><h3 id="ai-insights-title">Phân tích KPI tự động</h3><p>Hiểu diễn biến từng vấn đề và những thay đổi liên quan; không tự cộng các vấn đề thành tổng nhóm.</p></div></div>
    <div class="ai-context-body"><div class="ai-context-controls">${options.metricControls || ''}
    ${focusedLabel ? `<p class="ai-context-focus">Phân tích riêng: <strong>${escape(focusedLabel)}</strong> <button class="text-action" data-action="clear-context-insight-focus">Quay lại phạm vi đang xem</button></p>` : `<label class="ai-metric">Phạm vi vấn đề<select data-context-insight-selection><option value="all" ${selection === 'all' ? 'selected' : ''}>Tất cả vấn đề trong nhóm</option><option value="selected" ${selection === 'selected' ? 'selected' : ''}>Các vấn đề đã chọn</option></select></label>`}</div>
    ${list}<p class="ai-result-receipt"><strong>Phạm vi đang chọn:</strong> <span>${escape(receipt)}${focusedLabel ? '' : ` · ${selection === 'all' ? children.length : selected.length} vấn đề`}</span></p>
    <p class="ai-trust-note">${privateMode ? 'Chế độ riêng tư: chỉ dùng kết quả từ số liệu trong máy chủ.' : 'Chỉ gửi số liệu đã chuẩn hóa đến dịch vụ AI; tệp Excel và thông tin truy vết ở lại máy chủ.'}</p>
    <button class="primary ai-generate" data-action="generate-context-insight" ${!available || loading || emptySelection || (!focusedLabel && !children.length) ? 'disabled' : ''}>${loading ? 'Đang phân tích…' : result ? 'Phân tích lại' : 'Phân tích phạm vi đang xem'}</button>
    ${!available ? '<p class="ai-muted">Tính năng phân tích chưa sẵn sàng ở môi trường này.</p>' : emptySelection ? '<p class="ai-muted">Chọn ít nhất một vấn đề để phân tích.</p>' : !focusedLabel && !children.length ? '<p class="ai-muted">Nội dung đang chọn không có vấn đề con. Có thể mở phân tích riêng từ biểu đồ.</p>' : ''}
    <p role="status" aria-live="polite" aria-atomic="true" class="ai-muted">${loading ? 'Đang phân tích phạm vi đã chọn. Biểu đồ vẫn có thể sử dụng.' : error ? escape(error) : resultStale ? 'Phạm vi đã thay đổi. Hãy phân tích lại để cập nhật kết quả.' : result ? 'Đã hoàn tất phân tích.' : ''}</p>
    <div class="ai-output ai-context-result" aria-busy="${loading}">${result ? contextInsightOutput(result, stale, options.entities) : '<p class="ai-muted">Tạo phân tích để xem diễn biến và những nội dung cần chú ý.</p>'}</div></div></section>`;
}
