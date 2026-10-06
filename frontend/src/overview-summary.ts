export type OverviewSource = { entityRef: string; label: string; scope: 'project' | 'source'; effectiveUnit: string | null; eligible: boolean; reason: string | null };
type PeriodValue = { status: string; value?: number | null; reason?: string | null; unit?: string; period?: { start: string; end: string; label: string; complete: boolean; observedDayCount: number; expectedDayCount: number }; tieCount?: number };
export type OverviewSummary = {
  schemaVersion: number; policyVersion: string; project: string; grain: 'day' | 'week' | 'month' | 'quarter';
  calculation?: 'sum' | 'average_per_day'; requestedMode?: 'sum' | 'average' | 'both';
  metricKey: string; metricDisplayName: string; scope: 'project' | 'source' | null;
  window: { start: string; end: string } | null; source: OverviewSource | null; sourceChoices: OverviewSource[];
  issueCount: { status: string; value: number | null; reason: string | null; excludedCount: number };
  peak: PeriodValue; lowest: PeriodValue;
  largestChange: { status: string; reason?: string | null; absolute?: number; relativePercent?: number | null; relativeReason?: string | null; direction?: string; unit?: string; from?: PeriodValue; to?: PeriodValue; tieCount?: number };
  limitations: string[]; validPeriodCount: number; expectedPeriodCount: number;
};

const esc = (value: unknown) => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]!));
const fmt = (value: number) => value.toLocaleString('vi-VN', { maximumFractionDigits: 2 });
const day = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN');

export function overviewSummaryMarkup(summary: OverviewSummary | undefined | null, pending: boolean, error: string, fresh: boolean, requestedSource = '', statistics = false): string {
  const ready = Boolean(summary && fresh && !pending && !error);
  const placeholder = pending ? 'Đang cập nhật…' : error ? 'Chưa tải được số liệu. Hãy thử lại.' : !summary ? 'Chưa có dữ liệu tổng quan mới.' : 'Chờ cập nhật phạm vi đã chọn.';
  const card = (id: string, label: string, value: string, detail: string, scope = '') => `<div class="overview-kpi" data-overview-card="${id}" data-value-state="${value === '—' ? 'unavailable' : 'ready'}"><h3>${label}</h3><strong>${value}</strong>${scope ? `<p class="overview-kpi-scope">${esc(scope)}</p>` : ''}<p>${detail}</p></div>`;
  const calculation = statistics && ready ? summary?.calculation === 'average_per_day' ? 'Trung bình mỗi ngày' : 'Tổng trong kỳ' : '';
  const point = (id: string, label: string, value?: PeriodValue) => {
    if (!ready || value?.status !== 'ready' || value.value == null) return card(id, label, '—', esc(ready ? value?.reason : placeholder));
    const p = value.period!;
    const notes = [p.label, p.complete ? '' : 'Kỳ chưa đầy đủ', p.observedDayCount < p.expectedDayCount ? `${p.observedDayCount}/${p.expectedDayCount} ngày có dữ liệu` : '', (value.tieCount || 0) > 1 ? `${value.tieCount} kỳ đồng hạng · chọn kỳ mới nhất` : ''].filter(Boolean).join(' · ');
    return card(id, label, `${fmt(value.value)} <small>${esc(value.unit)}</small>`, esc(notes), calculation);
  };
  const c = summary?.largestChange;
  const change = ready && c?.status === 'ready' && c.absolute != null
    ? card('change', 'Thay đổi lớn nhất', `${c.absolute > 0 ? '+' : ''}${fmt(c.absolute)} <small>${esc(c.unit)}</small>`,
      `${esc(c.absolute === 0 ? 'Không thay đổi' : c.absolute > 0 ? 'Tăng' : 'Giảm')}${c.relativePercent != null ? ` ${fmt(Math.abs(c.relativePercent))}%` : ` · ${esc(c.relativeReason || 'Không tính được phần trăm')}`}<br>${esc(c.from?.period?.label)} → ${esc(c.to?.period?.label)}${c.from?.period && c.to?.period && (c.from.period.observedDayCount < c.from.period.expectedDayCount || c.to.period.observedDayCount < c.to.period.expectedDayCount) ? `<br>Ngày có dữ liệu: ${c.from.period.observedDayCount}/${c.from.period.expectedDayCount} → ${c.to.period.observedDayCount}/${c.to.period.expectedDayCount}` : ''}${(c.tieCount || 0) > 1 ? `<br>${c.tieCount} cặp đồng hạng · chọn cặp mới nhất` : ''}`, calculation)
    : card('change', 'Thay đổi lớn nhất', '—', esc(ready ? c?.reason : placeholder));
  const choices = summary?.sourceChoices || [];
  const source = choices.find(choice => choice.entityRef === requestedSource) || summary?.source;
  const selected = requestedSource || source?.entityRef;
  const context = ready ? `Tổng số ghi nhận · ${summary ? ({ day: 'Theo ngày', week: 'Theo tuần', month: 'Theo tháng', quarter: 'Theo quý' })[summary.grain] : ''}${summary?.window ? ` · ${day(summary.window.start)}–${day(summary.window.end)}` : ''}${calculation ? ` · ${calculation}` : ''}` : pending ? 'Đang cập nhật theo khoảng thời gian và nguồn đã chọn…' : placeholder;
  return `<div class="overview-kpi-grid">${card('issues', 'Vấn đề có dữ liệu', ready && summary!.issueCount.status === 'ready' && summary!.issueCount.value != null ? fmt(summary!.issueCount.value) : '—', ready ? esc(summary!.issueCount.reason || `${summary!.issueCount.excludedCount ? `Có ${summary!.issueCount.excludedCount} vấn đề không xác định được phân cấp. ` : ''}Trong khoảng thời gian đã chọn`) : esc(placeholder), 'Toàn dự án')}${point('peak', 'Ghi nhận cao nhất', summary?.peak)}${point('lowest', 'Ghi nhận thấp nhất', summary?.lowest)}${change}</div>
    ${ready && summary?.limitations.length ? `<p class="overview-summary-limitation">${summary.limitations.map(esc).join(' ')}</p>` : ''}
    ${error && requestedSource ? '<button class="ghost" data-action="reset-overview-source">Khôi phục nguồn mặc định</button>' : ''}
    <details class="overview-summary-method"><summary>Cách đọc các chỉ số</summary>
      <div class="overview-summary-heading"><p>${esc(context)}</p>${choices.length > 1 ? `<label>Nguồn phân tích<select data-overview-source aria-label="Nguồn phân tích">${choices.map(choice => `<option value="${esc(choice.entityRef)}" ${choice.entityRef === selected ? 'selected' : ''} ${!choice.eligible ? 'disabled' : ''}>${esc(choice.label)}</option>`).join('')}</select></label>` : ''}</div>
      ${source ? `<p class="overview-source-note">${source.scope === 'project' ? 'Nguồn tổng hợp cấp dự án' : 'Nguồn theo dõi riêng, không phải tổng toàn dự án'}: <strong>${esc(source.label)}</strong>.</p>` : ''}
      ${statistics ? `<p>${summary?.requestedMode === 'both' ? 'Biểu đồ hiển thị cả tổng và trung bình/ngày; ba thẻ diễn biến dùng tổng trong kỳ. ' : ''}Trung bình mỗi ngày dùng số ngày đủ điều kiện theo cách tính Thống kê hiện có, không tự chia cho số ngày lịch; ngày thiếu không tự thành số 0.</p>` : ''}
      <p>Số vấn đề được đếm trên toàn dự án. Ba chỉ số diễn biến chỉ dùng Tổng số ghi nhận của nguồn phân tích, không cộng các nhóm/vấn đề. Giá trị thiếu không được coi là 0. Thay đổi lớn nhất so hai kỳ lịch liền nhau, xếp theo độ lớn chênh lệch tuyệt đối; không phải kết luận về xu hướng hay chất lượng.</p></details>`;
}
