import type { Entity } from './types';
import { getEntityDisplayName, formatEntityText, formatMetricText } from './terminology';
import { renderInsightText } from './insight-text';
import { drawReportChart, purgeReportChart } from './report-chart';
import type { Figure } from './types';
import { uiIcon } from './ui-icons';
import './report-workspace.css';

export type ReportPoint = { periodStart: string; periodEnd: string; periodLabel: string; value: number | null;
  displayValue: string; factId: string | null; evidenceId: string | null };
export type ReportChart = { chartId: string; entityRef: string; entityLabel: string; metricCode: string; metricLabel: string;
  calculation: string; calculationLabel: string; unit: string; points: ReportPoint[];
  quality: { validPeriodCount: number; expectedPeriodCount: number; limitations: string[] } };
export type ReportFinding = { findingId: string; title: string; text: string; source: string; kind: string; anchorType: string;
  entityRef: string; entityLabel: string; calculation: string; blockId: string | null;
  anchors: (ReportPoint & { anchorId: string; chartId: string; entityRef: string; metricCode: string; calculation: string; factId: string; evidenceId: string })[] };
type Block = { blockId: string; text: string; source: string; section: string; entityRef?: string; calculation?: string;
  candidateId?: string; editable?: boolean; startLabel?: string; endLabel?: string };
export type ReportStoryPanel = { panelId: string; entityRef: string; entityLabel: string; chartIds: string[]; blockIds: string[];
  kind?: 'general' | 'metric'; title?: string; readings?: Block[]; figure?: Figure };
export type ReportEvidence = { evidenceId: string; observedDate: string; periodStart: string; periodEnd: string; periodLabel: string;
  target: { kind: 'exact' | 'aggregate'; observationRef?: string; lineageRef?: string; aggregateRef?: string } };
type Context = { view: 'overview' | 'statistics'; parentEntityRef: string; selection: 'node' | 'selected' | 'all'; entityRefs: string[];
  metricCode: string; start: string; end: string; groupBy: string; calculation: string; rangeMode: string;
  periodCount: number; periodFrom: string | null; periodTo: string | null; includeIncomplete: boolean; expectedImportRef?: string | null };
export type ReportDocument = { schemaVersion: string; reportId: string; revision: number; title: string; createdAt: string; updatedAt: string;
  context: Context & { project: string; requestedCount: number; analyzedCount: number; excluded: { entityLabel: string; reason: string }[] };
  window: { start: string; end: string; groupBy: string }; dataAsOf: { snapshotId: string; committedImportRef: string; generatedAt: string; sourceCommittedAt: string; checksum: string };
  review: { status: string; publicationStatus: string; checkedAt: string | null }; freshness: { newerDataAvailable: boolean };
  generation: { status: string; provider: { model: string; latencyMs?: number }; validation: { status: string; errors: string[] } };
  executiveSummary: Block[]; blocks: Block[]; charts: ReportChart[]; storyPanels?: ReportStoryPanel[]; findings: ReportFinding[]; selectedFindingIds: string[];
  kpis: (Pick<ReportChart, 'entityLabel' | 'entityRef' | 'metricLabel' | 'calculationLabel' | 'unit' | 'quality'> &
    { chartId: string; value: number; displayValue: string; periodStart: string; periodEnd: string; periodLabel: string;
      evidenceIds: string[]; change: { absoluteDisplay: string; relativeDisplay: string; direction: string } | null })[];
  limitations: string[]; userNotes: string; evidence: ReportEvidence[];
  versions: { revision: number; createdAt: string; checkedAt: string | null }[] };
type Saved = Pick<ReportDocument, 'reportId' | 'revision' | 'title' | 'updatedAt' | 'window'>;
export type ReportSeed = { project: string; entities: Entity[]; context: Context; minDate: string; maxDate: string;
  canGenerate: boolean; onEvidence: (document: ReportDocument, evidence: ReportEvidence, entityRef: string) => void };
type Api = <T>(path: string, init?: RequestInit) => Promise<T>;

const esc = (value: unknown) => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
const dateText = (value: string) => value.split('-').reverse().join('/');
const at = (value: string) => new Date(value).toLocaleString('vi-VN');
const requestId = () => crypto.randomUUID();
const calcName = (value: string) => ({ sum: 'Tổng trong kỳ', average_per_day: 'Trung bình/ngày', both: 'Tổng và trung bình/ngày' })[value] || value;
const groupName = (value: string) => ({ day: 'Ngày', week: 'Tuần', month: 'Tháng', quarter: 'Quý' })[value] || value;
const options = (values: [string, string][], chosen: string) => values.map(([value, label]) => `<option value="${esc(value)}" ${value === chosen ? 'selected' : ''}>${esc(label)}</option>`).join('');

export class ReportWorkspace {
  private host: HTMLElement | null = null;
  private seed: ReportSeed | null = null;
  private form: Context | null = null;
  private title = 'Báo cáo diễn biến KPI';
  private document: ReportDocument | null = null;
  private selected: string[] = [];
  private notes = '';
  private draftTitle = '';
  private edits: Record<string, string> = {};
  private editBlock = '';
  private activeFinding = '';
  private saved: Saved[] = [];
  private busy = '';
  private error = '';
  private notice = '';
  private listError = '';
  private events: AbortController | null = null;
  private operation: AbortController | null = null;
  private listEpoch = 0;
  private creating = false;
  private closeSetup = false;
  private closeHistory = false;
  private openSetup = false;
  private pendingDashboardSeed: ReportSeed | null = null;
  private exportFormat = 'pdf';

  constructor(private api: Api) {
    window.addEventListener('beforeunload', event => { if (this.dirty()) { event.preventDefault(); } });
  }

  mount(host: HTMLElement, seed: ReportSeed): void {
    const entry = this.pendingDashboardSeed?.project === seed.project ? this.pendingDashboardSeed : null;
    this.pendingDashboardSeed = null;
    const projectChanged = this.seed?.project !== seed.project;
    if (projectChanged) {
      this.operation?.abort(); this.operation = null; this.busy = ''; this.document = null; this.saved = [];
      this.form = structuredClone(seed.context); this.title = 'Báo cáo diễn biến KPI';
      this.selected = []; this.edits = {}; this.notes = ''; this.error = ''; this.notice = '';
      this.creating = false;
    }
    this.seed = seed;
    if (entry) {
      this.operation?.abort(); this.operation = null; this.busy = '';
      this.form = structuredClone(entry.context); this.closeSetup = false; this.openSetup = true;
      this.document = null; this.creating = true; this.edits = {}; this.editBlock = '';
      this.notice = 'Đã sao chép phạm vi đang xem. Bản nháp đã lưu không thay đổi.';
    }
    if (!this.form) this.form = structuredClone(seed.context);
    if (this.host !== host) {
      this.events?.abort(); this.events = new AbortController(); this.host = host;
      host.addEventListener('change', event => this.change(event), { signal: this.events.signal });
      host.addEventListener('input', event => this.input(event), { signal: this.events.signal });
      host.addEventListener('click', event => { void this.click(event); }, { signal: this.events.signal });
    }
    this.render();
    void this.loadSaved();
  }

  leave(): void {
    this.operation?.abort(); this.operation = null; this.busy = '';
    this.document = null; this.creating = false; this.edits = {}; this.editBlock = '';
    this.error = ''; this.notice = ''; this.listEpoch++;
  }

  prepareToLeave(): boolean {
    return !this.dirty() || window.confirm('Các chỉnh sửa chưa lưu sẽ mất nếu rời báo cáo. Bạn muốn tiếp tục?');
  }

  seedFromDashboard(seed: ReportSeed): void {
    this.pendingDashboardSeed = seed;
    this.form = structuredClone(seed.context); this.notice = 'Đã sao chép phạm vi đang xem. Bản nháp đã lưu không thay đổi.';
  }

  private base(): string { return `/projects/${encodeURIComponent(this.seed!.project)}/reports`; }
  private dirty(): boolean {
    return !!this.document && (this.draftTitle !== this.document.title || this.notes !== this.document.userNotes ||
      JSON.stringify(this.selected) !== JSON.stringify(this.document.selectedFindingIds) || Object.keys(this.edits).length > 0);
  }

  private accept(document: ReportDocument): void {
    if (document.context.project !== this.seed?.project) return;
    this.document = document; this.selected = [...document.selectedFindingIds]; this.draftTitle = document.title;
    this.notes = document.userNotes; this.edits = {}; this.editBlock = ''; this.activeFinding = '';
    this.closeSetup = true;
    this.closeHistory = true;
    this.creating = false;
  }

  private async loadSaved(): Promise<void> {
    const epoch = ++this.listEpoch, project = this.seed!.project;
    try {
      const response = await this.api<{ items: Saved[] }>(this.base());
      if (this.seed?.project !== project || epoch !== this.listEpoch) return;
      this.saved = response.items; this.listError = '';
      // Do not replace forms, focus or disclosures during a background history fetch.
      const list = this.host?.querySelector('[data-report-history-list]');
      if (list) list.innerHTML = this.historyMarkup();
    } catch (error) {
      if (this.seed?.project !== project || epoch !== this.listEpoch) return;
      this.listError = (error as Error).message;
      const list = this.host?.querySelector('[data-report-history-list]');
      if (list) list.innerHTML = this.historyMarkup();
    }
  }

  private historyMarkup(): string {
    if (this.listError) return `<p role="alert">Chưa tải được danh sách. ${esc(this.listError)}</p><button class="ghost" data-report-action="reload-history">Thử lại</button>`;
    return this.saved.length ? `<ul class="report-history-list">${this.saved.map(item => `<li><div class="report-history-info"><button class="text-button" data-report-action="open" data-report-id="${esc(item.reportId)}" ${this.busy ? 'disabled' : ''}>${esc(item.title)}</button><span>v${item.revision} · ${dateText(item.window.start)} → ${dateText(item.window.end)} · ${at(item.updatedAt)}</span></div><button class="ghost report-delete" data-report-action="delete" data-report-id="${esc(item.reportId)}" aria-label="Xóa bản nháp ${esc(item.title)}" ${this.busy ? 'disabled' : ''}>Xóa bản nháp</button></li>`).join('')}</ul>` : '<p class="section-desc">Chưa có bản nháp đã lưu cho dự án này. Chọn Tạo báo cáo mới để bắt đầu.</p>';
  }

  private async perform(label: string, action: () => Promise<void>): Promise<void> {
    if (this.busy) return;
    const op = new AbortController(); this.operation = op; this.busy = label; this.error = ''; this.notice = ''; this.render();
    const project = this.seed!.project;
    try { await action(); }
    catch (error) { if (!op.signal.aborted && this.seed?.project === project) this.error = (error as Error).message; }
    finally {
      if (this.operation === op) {
        this.busy = ''; this.operation = null; this.render();
        void this.loadSaved();
      }
    }
  }

  private async post<T>(path: string, payload: unknown): Promise<T> {
    const signal = this.operation!.signal;
    const result = await this.api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal });
    if (signal.aborted) throw new DOMException('Thao tác đã hủy', 'AbortError');
    return result;
  }

  private cleanText(text: string): string {
    return formatEntityText(formatMetricText(text), this.seed!.entities);
  }

  private isLatest(): boolean {
    return !!this.document && this.document.revision === Math.max(...this.document.versions.map(v => v.revision));
  }

  private canEdit(): boolean { return this.isLatest() && !this.busy; }

  private scrollBehavior(): ScrollBehavior {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  }

  private paragraph(block: Block, showSource = true): string {
    const text = this.edits[block.blockId] ?? block.text;
    const editable = this.isLatest() && block.editable !== false && block.candidateId && block.entityRef;
    const source = block.blockId in this.edits ? 'Người dùng chỉnh sửa — chưa lưu, chờ kiểm chứng' : block.source === 'ai' ? 'AI đã kiểm chứng' : block.source === 'manual' ? 'Người dùng chỉnh sửa — đã kiểm chứng' : 'Tổng hợp từ số liệu';
    return `<div class="report-paragraph" data-report-block="${esc(block.blockId)}"><p>${renderInsightText(this.cleanText(text))}</p>
      ${showSource || block.blockId in this.edits ? `<small class="report-source-label">${source}</small>` : ''}
      ${editable ? `<button class="text-button" data-report-action="edit-block" data-report-block-id="${esc(block.blockId)}" ${this.busy ? 'disabled' : ''}>Sửa diễn giải</button>` : ''}
      ${editable && this.editBlock === block.blockId ? `<label class="report-editor">Diễn giải có căn cứ<textarea data-report-edit="${esc(block.blockId)}" maxlength="5000" rows="4" ${this.busy ? 'disabled' : ''}>${esc(text)}</textarea></label><p class="section-desc">Số liệu được khóa. Nội dung sửa sẽ được kiểm chứng khi lưu; ý kiến nghiệp vụ đặt ở Ghi chú.</p>` : ''}</div>`;
  }

  private setupMarkup(): string {
    const form = this.form!, seed = this.seed!;
    const children = seed.entities.filter(e => e.parent_entity_id === form.parentEntityRef);
    const disabled = this.busy ? 'disabled' : '';
    return `<details class="report-setup" ${this.document ? '' : 'open'}><summary>Thiết lập báo cáo${this.document ? ' mới' : ''}</summary>
      <p class="section-desc">Báo cáo có phạm vi riêng. Thay bộ lọc dashboard không thay dữ liệu hoặc nội dung bản nháp đã lưu.</p>
      <div class="report-form"><label>Tên báo cáo<input data-report-title value="${esc(this.title)}" maxlength="200" ${disabled}></label>
      <label>Nguồn phân tích<select data-report-field="view" ${disabled}>${options([['overview','Tổng quan — 3 KPI'],['statistics','Thống kê — tổng / trung bình mỗi ngày']], form.view)}</select></label>
      <label>Nhóm / nội dung theo dõi<select data-report-field="parentEntityRef" ${disabled}>${seed.entities.map(e => `<option value="${esc(e.entity_id)}" ${e.entity_id === form.parentEntityRef ? 'selected' : ''}>${esc(getEntityDisplayName(e))}</option>`).join('')}</select></label>
      <label>Phạm vi<select data-report-field="selection" ${disabled}>${options([['node','Nội dung đang chọn'], ...(children.length ? [['all','Tất cả vấn đề trong nhóm'],['selected','Chọn vấn đề trong nhóm']] as [string,string][] : [])], form.selection)}</select></label>
      ${form.selection === 'selected' ? `<fieldset class="report-member-picks"><legend>Vấn đề đưa vào báo cáo</legend>${children.map(e => `<label class="check"><input type="checkbox" data-report-member="${esc(e.entity_id)}" ${form.entityRefs.includes(e.entity_id) ? 'checked' : ''} ${disabled}>${esc(getEntityDisplayName(e))}</label>`).join('')}</fieldset>` : ''}
      <label>Nhóm kỳ<select data-report-field="groupBy" ${disabled}>${options([['day','Ngày'],['week','Tuần'],['month','Tháng'], ...(form.view === 'statistics' ? [['quarter','Quý']] as [string,string][] : [])], form.groupBy)}</select></label>
      ${form.view === 'overview' ? `<label>Từ ngày<input data-report-field="start" type="date" value="${esc(form.start)}" min="${seed.minDate}" max="${seed.maxDate}" ${disabled}></label><label>Đến ngày<input data-report-field="end" type="date" value="${esc(form.end)}" min="${seed.minDate}" max="${seed.maxDate}" ${disabled}></label>` :
      `<label>Cách tính<select data-report-field="calculation" ${disabled}>${options([['sum','Tổng trong kỳ'],['average_per_day','Trung bình/ngày'],['both','Tổng và trung bình/ngày']], form.calculation)}</select></label>
      <label>Khoảng thống kê<select data-report-field="rangeMode" ${disabled}>${options([['recent','Các kỳ gần nhất'],['all','Toàn bộ dữ liệu'],['custom','Chọn khoảng kỳ']], form.rangeMode)}</select></label>
      ${form.rangeMode === 'recent' ? `<label>Số kỳ<input data-report-field="periodCount" type="number" min="1" max="3660" value="${form.periodCount}" ${disabled}></label>` : ''}
      ${form.rangeMode === 'custom' ? `<label>Từ kỳ<input data-report-field="periodFrom" type="date" value="${esc(form.periodFrom)}" ${disabled}></label><label>Đến kỳ<input data-report-field="periodTo" type="date" value="${esc(form.periodTo)}" ${disabled}></label>` : ''}
      <label class="check"><input data-report-field="includeIncomplete" type="checkbox" ${form.includeIncomplete ? 'checked' : ''} ${disabled}>Bao gồm kỳ chưa đầy đủ</label>`}</div>
      <div class="report-actions"><button class="${this.document ? 'ghost' : 'primary'}" data-report-action="create" ${disabled}>${this.document ? 'Tạo bản nháp mới' : 'Chuẩn bị bản nháp'}</button><span class="section-desc">Lưu số liệu trước, chưa gọi AI.</span></div></details>`;
  }

  private render(): void {
    if (!this.host?.isConnected || !this.seed || !this.form) return;
    const focused = document.activeElement as HTMLElement | null;
    const focusId = focused?.dataset.reportMember;
    const focusField = focused?.dataset.reportField;
    const focusFinding = focused?.dataset.reportFindingSelect;
    const disclosures = new Set(Array.from(this.host.querySelectorAll<HTMLDetailsElement>('details[open]')).map(d => d.className || d.parentElement?.getAttribute('data-report-finding') || ''));
    if (this.closeSetup) { disclosures.delete('report-setup'); this.closeSetup = false; }
    if (this.closeHistory) { disclosures.delete('report-history'); this.closeHistory = false; }
    if (this.openSetup) { disclosures.add('report-setup'); this.openSetup = false; }
    this.host.querySelectorAll<HTMLElement>('[data-report-chart]').forEach(purgeReportChart);
    this.host.innerHTML = `<div class="report-workspace" aria-busy="${!!this.busy}">
      <div class="report-library-header"><div><h3>Bản nháp báo cáo</h3><p class="section-desc">Chọn bản nháp để xem hoặc tạo báo cáo mới. Không tự mở báo cáo gần nhất.</p></div><div class="report-actions"><button class="primary" data-report-action="new" ${this.busy ? 'disabled' : ''}>Tạo báo cáo mới</button>${this.document || this.creating ? `<button class="ghost" data-report-action="library" ${this.busy ? 'disabled' : ''}>Về danh sách bản nháp</button>` : ''}</div></div>
      ${this.document || this.creating ? this.setupMarkup() : ''}
      <details class="report-history" ${this.document || this.creating ? '' : 'open'}><summary>Bản nháp đã lưu</summary><div data-report-history-list>${this.historyMarkup()}</div></details>
      <div class="report-status" role="status" aria-live="polite">${this.busy ? `<p>${esc(this.busy)} Không cần giữ tab này mở để xem dashboard.</p>` : this.notice ? `<p>${esc(this.notice)}</p>` : ''}</div>
      ${this.error ? `<div class="notice error" role="alert"><strong>Thao tác chưa hoàn tất.</strong> ${esc(this.error)} Bản đã lưu vẫn được giữ nguyên.</div>` : ''}
      ${this.document ? this.documentMarkup(this.document) : ''}</div>`;
    if (focusId) this.host.querySelector<HTMLInputElement>(`[data-report-member="${CSS.escape(focusId)}"]`)?.focus({ preventScroll: true });
    if (focusField) this.host.querySelector<HTMLSelectElement>(`[data-report-field="${CSS.escape(focusField)}"]`)?.focus({ preventScroll: true });
    if (focusFinding) this.host.querySelector<HTMLInputElement>(`[data-report-finding-select="${CSS.escape(focusFinding)}"]`)?.focus({ preventScroll: true });
    this.host.querySelectorAll<HTMLDetailsElement>('details').forEach(d => {
      const key = d.className || d.parentElement?.getAttribute('data-report-finding') || '';
      if (disclosures.has(key)) d.open = true;
    });
    this.paintCharts();
  }

  private documentMarkup(doc: ReportDocument): string {
    const disabled = this.busy ? 'disabled' : '';
    const dirty = this.dirty();
    const isLatest = this.isLatest();
    const panels = this.storyPanels(doc);
    const visibleBlocks = new Set(panels.flatMap(p => p.blockIds));
    const supplemental = doc.blocks.filter(b => b.section === 'phases' && !visibleBlocks.has(b.blockId));
    return `<article class="report-document" aria-label="Bản nháp báo cáo">
      <header class="report-document-header"><div><h3>${esc(doc.title)}</h3><p><span class="report-draft-label">BẢN NHÁP</span> · Phiên bản ${doc.revision} · ${doc.review.status === 'checked' ? 'Đã kiểm tra bản nháp' : 'Cần kiểm tra'}${dirty ? ' · Có chỉnh sửa chưa lưu' : ''}</p></div>
      <label>Phiên bản<select data-report-version ${disabled}>${doc.versions.map(v => `<option value="${v.revision}" ${v.revision === doc.revision ? 'selected' : ''}>v${v.revision}${v.checkedAt ? ' · đã kiểm tra' : ''}</option>`).join('')}</select></label></header>
      <div class="report-toolbar" aria-label="Thao tác báo cáo">
        <button class="ghost" data-report-action="generate" ${disabled || dirty || !isLatest || !this.seed!.canGenerate ? 'disabled' : ''}>${doc.generation.status === 'engine_only' ? 'Tạo diễn giải AI' : 'Sinh lại diễn giải AI'}</button>
        <button class="${dirty ? 'primary' : 'ghost'}" data-report-action="save" ${disabled || !dirty || !isLatest ? 'disabled' : ''}>Lưu phiên bản mới</button>
        <button class="ghost" data-report-action="check" ${disabled || dirty || !isLatest || doc.review.status === 'checked' ? 'disabled' : ''}>Đánh dấu đã kiểm tra</button>
        <label>Định dạng<select data-report-export-format>${options([['pdf','PDF'],['docx','DOCX — có thể chỉnh trong Word']],this.exportFormat)}</select></label>
        <button class="primary" data-report-action="export" ${disabled || dirty ? 'disabled' : ''}>${uiIcon('download')}Xuất phiên bản ${doc.revision}</button>
        <span class="report-save-note" role="status">${dirty ? 'Lưu chỉnh sửa trước khi sinh AI, kiểm tra hoặc xuất.' : 'Xuất đúng phiên bản đang xem · BẢN NHÁP'}</span>
      </div>
      ${doc.freshness.newerDataAvailable ? '<p class="notice">Dữ liệu nguồn đã có phiên bản mới. Báo cáo này giữ nguyên dữ liệu tại thời điểm tạo. Dùng Thiết lập báo cáo mới nếu muốn cập nhật.</p>' : ''}
      ${!isLatest ? '<p class="notice">Đang xem bản cũ, chỉ đọc và xuất được. Mở bản mới nhất trước khi chỉnh sửa.</p>' : ''}
      <nav class="report-toc" aria-label="Các phần báo cáo">${[['metadata','Thông tin'],['summary','Tóm tắt'],['kpis','KPI'],['story','Diễn biến'],['findings','Điểm đáng chú ý']].map(([id,label]) => `<a href="#report-${id}">${label}</a>`).join('')}</nav>
      <section id="report-metadata" class="report-section"><h4>Thông tin báo cáo</h4>
      <p class="report-scope-line">${esc(doc.context.project)} · ${dateText(doc.window.start)} → ${dateText(doc.window.end)} · ${doc.context.selection === 'node' ? 'Một nội dung' : doc.context.selection === 'selected' ? 'Các vấn đề đã chọn' : 'Các vấn đề trong nhóm'} · ${doc.context.analyzedCount}/${doc.context.requestedCount} nội dung có dữ liệu</p>
      <details class="report-metadata-details"><summary>Phạm vi và thông tin chi tiết</summary><dl class="report-metadata">
        <div><dt>Dự án</dt><dd>${esc(doc.context.project)}</dd></div><div><dt>Thời gian dữ liệu</dt><dd>${dateText(doc.window.start)} → ${dateText(doc.window.end)}</dd></div>
        <div><dt>Phân tích</dt><dd>${doc.context.view === 'statistics' ? 'Thống kê' : 'Tổng quan'} · ${groupName(doc.window.groupBy)} · ${calcName(doc.context.calculation)}</dd></div>
        <div><dt>Phạm vi</dt><dd>${doc.context.analyzedCount}/${doc.context.requestedCount} nội dung có dữ liệu</dd></div>
        <div><dt>Dữ liệu cập nhật</dt><dd>${at(doc.dataAsOf.sourceCommittedAt)}</dd></div><div><dt>Tạo bản nháp</dt><dd>${at(doc.createdAt)}</dd></div></dl>
        <p class="report-members">${esc([...new Set(doc.charts.map(c => c.entityLabel))].join(' · '))}</p></details></section>
      <section id="report-summary" class="report-section report-executive"><div class="report-section-head"><h4>Tóm tắt điều hành</h4></div>
        <p class="report-generation-note">${doc.generation.status === 'ready' ? 'AI diễn giải dựa trên số liệu đã kiểm chứng. Đoạn chưa đủ căn cứ được thay bằng nội dung tổng hợp từ số liệu.' : doc.generation.status === 'engine_only' ? 'Bản nháp được tạo từ số liệu đã kiểm chứng. Bạn có thể yêu cầu AI diễn giải sau khi kiểm tra phạm vi.' : doc.generation.status === 'insufficient_data' ? 'Số kỳ còn ít để phân tích xu hướng. Báo cáo giữ các số liệu đã ghi nhận.' : 'AI chưa cung cấp đủ diễn giải hợp lệ. Báo cáo vẫn giữ nội dung đối chiếu được với số liệu.'}</p>
        ${doc.executiveSummary.map(b => `<p class="report-summary-text">${renderInsightText(this.cleanText(b.text))}</p>`).join('')}
        ${!this.seed!.canGenerate ? '<p class="section-desc">AI đang tắt, chưa cấu hình hoặc chưa được phép gửi dữ liệu. Các phần số liệu vẫn dùng được.</p>' : ''}</section>
      <section id="report-kpis" class="report-section"><h4>Tổng quan KPI</h4><p class="section-desc">Mức tại kỳ có dữ liệu cuối. Đây không phải số cộng dồn của tất cả kỳ trong báo cáo.</p><div class="report-table-scroll"><table class="report-kpi-table"><thead><tr><th scope="col">Vấn đề / KPI</th><th scope="col">Mức được ghi nhận</th><th scope="col">Thay đổi ở kỳ cuối</th><th scope="col">Dữ liệu</th></tr></thead><tbody>${doc.kpis.map(k => `<tr><th scope="row">${esc(k.entityLabel)}<small>${esc(k.metricLabel)}</small>${doc.context.view === 'statistics' ? `<small>${esc(k.calculationLabel)}</small>` : ''}</th><td><strong>${esc(k.displayValue)}</strong><span>${esc(k.unit)}</span><small>${esc(k.periodLabel)}</small></td><td>${k.change ? `${esc(k.change.absoluteDisplay)}<small>${esc(k.change.relativeDisplay)}</small>` : 'Chưa có kỳ liền trước'}</td><td>${k.quality.validPeriodCount}/${k.quality.expectedPeriodCount} kỳ <button class="text-button" data-report-action="source" data-report-evidence="${esc(k.evidenceIds[0])}">Xem nguồn</button></td></tr>`).join('')}</tbody></table></div></section>
      <section id="report-story" class="report-section"><h4>Diễn biến trong kỳ</h4>${panels.map(panel => {
        const charts = doc.charts.filter(c => panel.chartIds.includes(c.chartId));
        const blocks = [...panel.blockIds.map(id => doc.blocks.find(b => b.blockId === id)).filter((b): b is Block => !!b), ...(panel.readings || [])];
        return `<section class="report-issue-story" id="report-panel-${esc(panel.panelId)}">${panels.find(p => p.entityRef === panel.entityRef) === panel ? `<h5>${esc(panel.entityLabel)}</h5>` : ''}
          <figure class="report-chart-panel"><figcaption><strong>${esc(panel.title || charts.map(c => c.metricLabel).filter((v,i,a) => a.indexOf(v) === i).join(' · '))}</strong><span>${esc([...new Set(charts.map(c => c.calculationLabel))].join(' / '))}</span></figcaption>
          <div data-report-chart="${esc(panel.panelId)}" class="report-chart" aria-label="Biểu đồ của ${esc(panel.entityLabel)}"></div></figure>
          <div class="report-chart-analysis" aria-label="Diễn giải biểu đồ của ${esc(panel.entityLabel)}">${blocks.map((b,i) => `<div>${doc.context.calculation === 'both' && (i === 0 || blocks[i-1].calculation !== b.calculation) ? `<p class="report-calculation-label">${esc(calcName(b.calculation || 'both'))}</p>` : ''}${this.paragraph(b, i === 0 || blocks[i-1].source !== b.source || blocks[i-1].calculation !== b.calculation)}</div>`).join('')}${!blocks.length ? '<p class="section-desc">Biểu đồ thể hiện các giá trị đã ghi nhận; chưa có đủ kỳ để mô tả diễn biến dài.</p>' : ''}</div></section>`;
}).join('')}${supplemental.length ? `<details class="report-supplemental"><summary>Diễn giải bổ sung đã lưu</summary><p class="section-desc">Các đoạn giai đoạn đã được thể hiện dưới từng biểu đồ nên không lặp trong bản xuất. Bạn vẫn có thể đọc hoặc sửa lời diễn giải đã lưu ở đây.</p>${supplemental.map(b => `<p class="report-calculation-label">${esc(doc.charts.find(c => c.entityRef === b.entityRef)?.entityLabel)} · ${esc(calcName(b.calculation || 'both'))}</p>${this.paragraph(b)}`).join('')}</details>` : ''}${doc.blocks.some(b => b.section === 'group_relationships') ? `<section class="report-group-story"><h5>Liên hệ giữa các vấn đề</h5><p class="section-desc">Đối chiếu với các biểu đồ ở trên:</p><nav class="report-chart-links" aria-label="Biểu đồ hỗ trợ nhận định nhóm">${panels.filter((p,i,a) => a.findIndex(other => other.entityRef === p.entityRef) === i).map(p => `<a href="#report-panel-${esc(p.panelId)}">${esc(p.entityLabel)}</a>`).join('')}</nav>${doc.blocks.filter(b => b.section === 'group_relationships').map(b => this.paragraph(b)).join('')}</section>` : ''}</section>
      <section id="report-findings" class="report-section"><h4>Điểm đáng chú ý</h4><p class="section-desc">Chọn tối đa 5 điểm cho biểu đồ và bản xuất. Nhấp “Xem trên biểu đồ” để kiểm tra vị trí; việc chọn điểm không gọi lại AI.</p>
        ${doc.findings.length ? `<ol class="report-finding-list">${doc.findings.map(f => `<li data-report-finding="${esc(f.findingId)}" ${f.findingId === this.activeFinding ? 'data-active="true"' : ''}>
          <div class="report-finding-heading"><label class="check"><input type="checkbox" data-report-finding-select="${esc(f.findingId)}" ${this.selected.includes(f.findingId) ? 'checked' : ''} ${disabled || !isLatest ? 'disabled' : ''}>
          <strong>${this.selected.includes(f.findingId) ? `${this.selected.indexOf(f.findingId)+1}. ` : ''}${esc(f.entityLabel)} · ${esc(f.title)} · ${calcName(f.calculation)}</strong></label><button class="text-button" data-report-action="locate" data-report-finding-id="${esc(f.findingId)}">Xem trên biểu đồ</button></div>
          <p>${this.findingCaption(f)}</p><details><summary>Đọc nhận định gắn với điểm này</summary><p>${renderInsightText(this.cleanText(f.text))}</p></details>
          <div class="report-finding-sources">${f.anchors.map(a => `<button class="text-button" data-report-action="source" data-report-evidence="${esc(a.evidenceId)}">${esc(doc.charts.find(c => c.chartId === a.chartId)?.metricLabel)} · ${esc(a.periodLabel)}</button>`).join('')}</div></li>`).join('')}</ol>` : '<p>Chưa có điểm nổi bật đủ căn cứ. Không thêm đỉnh/đáy hoặc xu hướng khi chuỗi quá ngắn.</p>'}
        ${doc.limitations.length || doc.context.excluded.length ? `<details class="report-limits" open><summary>Giới hạn khi đọc dữ liệu</summary><ul>${doc.limitations.map(t => `<li>${esc(this.cleanText(t))}</li>`).join('')}${doc.context.excluded.map(e => `<li>${esc(this.cleanText(e.entityLabel))}: chưa có dữ liệu hợp lệ (${esc(e.reason)}).</li>`).join('')}</ul></details>` : ''}
        <details class="report-source-details"><summary>Nguồn và phiên bản phân tích</summary><p>Dữ liệu: ${esc(doc.dataAsOf.committedImportRef)} · Snapshot ${esc(doc.dataAsOf.snapshotId)}</p><p>Model: ${esc(doc.generation.provider.model)} · Kiểm chứng: ${esc(doc.generation.validation.status)}</p><p>Report: ${esc(doc.reportId)} · v${doc.revision}</p><p>Giữ bản dữ liệu đã chụp, không lấy số từ bộ lọc dashboard hiện tại.</p></details></section>
      <section class="report-review"><h4>Lưu và kiểm tra bản nháp</h4><div class="report-edit-fields"><label>Tên bản nháp<input data-report-draft-title maxlength="200" value="${esc(this.draftTitle)}" ${disabled || !isLatest ? 'disabled' : ''}></label><label>Ghi chú của người dùng — chưa kiểm chứng<textarea data-report-notes rows="3" maxlength="5000" ${disabled || !isLatest ? 'disabled' : ''}>${esc(this.notes)}</textarea></label></div>
        <p class="section-desc">Kiểm tra phạm vi, số liệu, đơn vị, vị trí đánh dấu và nhận định. Xác nhận bên dưới không phải phê duyệt chính thức; tệp luôn mang nhãn BẢN NHÁP.</p>
        ${dirty ? '<p class="section-desc" role="status">Lưu chỉnh sửa trước khi sinh AI, kiểm tra hoặc xuất. Bản xuất phải giống phiên bản đang xem.</p>' : ''}</section>
    </article>`;
  }

  private findingCaption(finding: ReportFinding): string {
    const groups = new Map<string, ReportFinding['anchors']>();
    for (const anchor of finding.anchors) {
      const key = `${anchor.entityRef}:${anchor.metricCode}`;
      groups.set(key, [...(groups.get(key) || []), anchor]);
    }
    return [...groups].map(([, rows]) => {
      rows.sort((a,b) => a.periodStart.localeCompare(b.periodStart));
      const first = rows[0];
      const chart = this.document!.charts.find(c => c.chartId === first.chartId)!;
      const metric = `${new Set(finding.anchors.map(a => a.entityRef)).size > 1 ? chart.entityLabel + ' · ' : ''}${chart.metricLabel}`;
      return `${esc(metric)}: ` + rows.map(p => `<strong>${esc(p.displayValue)}</strong> (${esc(p.periodLabel)})`).join(' → ');
    }).join('; ') + '.';
  }

  private paintCharts(): void {
    if (!this.document || !this.host?.isConnected) return;
    for (const panel of this.storyPanels(this.document)) {
      const host = this.host.querySelector<HTMLElement>(`[data-report-chart="${CSS.escape(panel.panelId)}"]`);
      const charts = this.document.charts.filter(c => panel.chartIds.includes(c.chartId));
      if (host) void drawReportChart(host, charts[0], this.document.findings, this.selected, this.activeFinding, id => {
        this.activeFinding = id; this.markActiveFinding(); this.paintCharts();
        this.host?.querySelector(`[data-report-finding="${CSS.escape(id)}"]`)?.scrollIntoView({ block:'center', behavior:this.scrollBehavior() });
      }, charts, panel.figure).catch(error => { if (host.isConnected) host.textContent = `Chưa hiển thị được biểu đồ. ${(error as Error).message}`; });
    }
  }

  private storyPanels(doc: ReportDocument): ReportStoryPanel[] {
    return doc.storyPanels || doc.charts.map((c,i) => ({ panelId:c.chartId, entityRef:c.entityRef,
      entityLabel:c.entityLabel, chartIds:[c.chartId], blockIds:doc.blocks.filter(b => b.section !== 'overview'
        && b.entityRef === c.entityRef && b.calculation === c.calculation
        && doc.charts.findIndex(other => other.entityRef === c.entityRef && other.calculation === c.calculation) === i).map(b => b.blockId) }));
  }

  private markActiveFinding(): void {
    this.host?.querySelectorAll<HTMLElement>('[data-report-finding]').forEach(row => {
      row.toggleAttribute('data-active', row.dataset.reportFinding === this.activeFinding);
    });
  }

  private change(event: Event): void {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (this.busy) return;
    if (target.hasAttribute('data-report-export-format')) { this.exportFormat = target.value; return; }
    if (target.hasAttribute('data-report-version') && this.document) {
      if (!this.prepareToLeave()) { target.value = String(this.document.revision); return; }
      const id = this.document.reportId, version = target.value;
      void this.perform('Đang mở phiên bản…', async () => {
        const signal = this.operation!.signal;
        const doc = await this.api<ReportDocument>(this.base()+`/${id}/revisions/${version}`, {signal});
        if (!signal.aborted) this.accept(doc);
      }); return;
    }
    if (target.dataset.reportFindingSelect) {
      if (!this.canEdit()) return;
      const id = target.dataset.reportFindingSelect;
      if ((target as HTMLInputElement).checked && !this.selected.includes(id)) {
        if (this.selected.length >= 5) { (target as HTMLInputElement).checked = false; this.error = 'Chọn tối đa 5 điểm. Bỏ một điểm trước khi chọn điểm khác.'; }
        else this.selected.push(id);
      } else this.selected = this.selected.filter(x => x !== id);
      this.render(); return;
    }
    if (target.dataset.reportMember) {
      const id = target.dataset.reportMember;
      this.form!.entityRefs = (target as HTMLInputElement).checked ? [...new Set([...this.form!.entityRefs,id])] : this.form!.entityRefs.filter(x => x !== id);
      return;
    }
    const field = target.dataset.reportField;
    if (!field) return;
    const value = target instanceof HTMLInputElement && target.type === 'checkbox' ? target.checked : target.type === 'number' ? Number(target.value) : target.value;
    (this.form as unknown as Record<string, unknown>)[field] = value;
    if (field === 'parentEntityRef') { this.form!.entityRefs = []; this.form!.selection = 'node'; }
    if (field === 'view' && value === 'overview') { this.form!.calculation = 'sum'; if (this.form!.groupBy === 'quarter') this.form!.groupBy = 'month'; }
    if (['parentEntityRef','selection','view','groupBy','rangeMode'].includes(field)) this.render();
  }

  private input(event: Event): void {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement;
    if (target.hasAttribute('data-report-title')) this.title = target.value;
    if (this.canEdit()) {
      if (target.hasAttribute('data-report-draft-title')) this.draftTitle = target.value;
      if (target.hasAttribute('data-report-notes')) this.notes = target.value;
      if (target.dataset.reportEdit) {
        this.edits[target.dataset.reportEdit] = target.value;
        const label = target.closest('[data-report-block]')?.querySelector('.report-source-label');
        if (label) label.textContent = 'Người dùng chỉnh sửa — chưa lưu, chờ kiểm chứng';
      }
    }
    // Update actions without replacing the textarea/selection on each keystroke.
    if (this.document) {
      const dirty = this.dirty();
      for (const action of ['generate','check','export']) {
        const button = this.host?.querySelector<HTMLButtonElement>(`[data-report-action="${action}"]`);
        if (button) button.disabled = !!this.busy || dirty || (action !== 'export' && !this.isLatest()) || (action === 'generate' && !this.seed!.canGenerate) || (action === 'check' && this.document.review.status === 'checked');
      }
      const save = this.host?.querySelector<HTMLButtonElement>('[data-report-action="save"]');
      if (save) { save.disabled = !dirty || !this.canEdit(); save.className = dirty ? 'primary' : 'ghost'; }
      const note = this.host?.querySelector('.report-save-note');
      if (note) note.textContent = dirty ? 'Lưu chỉnh sửa trước khi sinh AI, kiểm tra hoặc xuất.' : 'Xuất đúng phiên bản đang xem · BẢN NHÁP';
    }
  }

  private async click(event: Event): Promise<void> {
    const target = (event.target as HTMLElement).closest<HTMLElement>('[data-report-action]');
    if (!target || target instanceof HTMLButtonElement && target.disabled) return;
    const action = target.dataset.reportAction;
    if (this.busy) return;
    if (action === 'new' || action === 'library') {
      if (!this.prepareToLeave()) return;
      this.leave(); this.creating = action === 'new'; this.openSetup = this.creating;
      this.render();
      this.host?.querySelector<HTMLElement>(this.creating ? '[data-report-title]' : '[data-report-action="new"]')?.focus();
      return;
    }
    if (action === 'delete' && target.dataset.reportId) {
      const item = this.saved.find(item => item.reportId === target.dataset.reportId);
      if (!item) return;
      if (!window.confirm(`Xóa bản nháp “${item.title}” và tất cả phiên bản khỏi danh sách?${this.document?.reportId === item.reportId && this.dirty() ? ' Chỉnh sửa chưa lưu cũng sẽ mất.' : ''} Tệp PDF/DOCX đã tải không bị xóa.`)) return;
      await this.perform('Đang xóa bản nháp…', async () => {
        const signal = this.operation!.signal;
        await this.api(this.base()+`/${encodeURIComponent(item.reportId)}`, {method:'DELETE', headers:{'Content-Type':'application/json'}, body:JSON.stringify({baseRevision:item.revision}), signal});
        if (signal.aborted) return;
        this.listEpoch++; this.saved = this.saved.filter(saved => saved.reportId !== item.reportId);
        if (this.document?.reportId === item.reportId) { this.document = null; this.edits = {}; this.creating = false; }
        this.notice = `Đã xóa bản nháp “${item.title}” khỏi danh sách.`;
      });
      this.host?.querySelector<HTMLElement>('[data-report-action="new"]')?.focus();
      return;
    }
    if (action === 'reload-history') { await this.loadSaved(); return; }
    if (action === 'create') {
      if (!this.prepareToLeave()) return;
      if (!this.title.trim()) { this.error = 'Hãy nhập tên báo cáo.'; this.render(); return; }
      const payload = { title:this.title.trim(), requestId:requestId(), context:{...this.form!, metricCode:'all', expectedImportRef:null} };
      await this.perform('Đang chuẩn bị số liệu và lưu bản nháp…', async () => {
        const doc = await this.post<ReportDocument>(this.base(), payload);
        if (this.operation?.signal.aborted) return;
        this.accept(doc); this.notice = 'Đã lưu bản nháp từ số liệu. Kiểm tra phạm vi rồi yêu cầu AI nếu cần.';
      }); return;
    }
    if (action === 'open' && target.dataset.reportId) {
      if (!this.prepareToLeave()) return;
      const id = target.dataset.reportId;
      await this.perform('Đang mở báo cáo…', async () => { const signal = this.operation!.signal; const doc = await this.api<ReportDocument>(this.base()+`/${encodeURIComponent(id)}`, {signal}); if (!signal.aborted) this.accept(doc); }); return;
    }
    if (!this.document) return;
    const doc = this.document, base = this.base()+`/${doc.reportId}`;
    if (action === 'locate') {
      const finding = doc.findings.find(f => f.findingId === target.dataset.reportFindingId);
      if (!finding) return;
      this.activeFinding = finding.findingId; this.markActiveFinding(); this.paintCharts();
      const candidates = this.storyPanels(doc).filter(p => p.chartIds.includes(finding.anchors[0]?.chartId));
      const codes = new Set(finding.anchors.map(a => a.metricCode));
      const panel = candidates.find(p => p.kind === (codes.size === 1 ? 'metric' : 'general')) || candidates[0];
      if (panel) this.host?.querySelector(`[data-report-chart="${CSS.escape(panel.panelId)}"]`)?.scrollIntoView({block:'center',behavior:this.scrollBehavior()}); return;
    }
    if (action === 'source') {
      const evidence = doc.evidence.find(e => e.evidenceId === target.dataset.reportEvidence);
      const chart = doc.charts.find(c => c.points.some(p => p.evidenceId === evidence?.evidenceId));
      if (evidence) this.seed!.onEvidence(doc, evidence, chart?.entityRef || ''); return;
    }
    if (['edit-block','save','generate','check'].includes(action || '') && !this.canEdit()) return;
    if (action === 'edit-block') { this.editBlock = this.editBlock === target.dataset.reportBlockId ? '' : target.dataset.reportBlockId || ''; this.render(); this.host?.querySelector<HTMLTextAreaElement>('[data-report-edit]')?.focus(); return; }
    if (action === 'save') {
      await this.perform('Đang kiểm chứng và lưu phiên bản mới…', async () => {
        const updated = await this.post<ReportDocument>(base+'/revisions', { baseRevision:doc.revision, requestId:requestId(),
          title:this.draftTitle.trim(), userNotes:this.notes, selectedFindingIds:this.selected, narrativeEdits:this.edits });
        if (!this.operation?.signal.aborted) { this.accept(updated); this.notice = 'Đã lưu phiên bản mới. Cần kiểm tra lại trước khi dùng.'; }
      }); return;
    }
    if (action === 'generate') {
      await this.perform('AI đang diễn giải từ dữ liệu đã chụp…', async () => {
        const updated = await this.post<ReportDocument>(base+'/regenerate', { baseRevision:doc.revision, requestId:requestId() });
        if (!this.operation?.signal.aborted) this.accept(updated);
      }); return;
    }
    if (action === 'check') {
      await this.perform('Đang ghi nhận kiểm tra bản nháp…', async () => { const updated = await this.post<ReportDocument>(base+`/revisions/${doc.revision}/check`, {}); if (!this.operation?.signal.aborted) this.accept(updated); }); return;
    }
    if (action === 'export') {
      const format = this.host?.querySelector<HTMLSelectElement>('[data-report-export-format]')?.value || 'pdf';
      await this.perform('Đang xuất phiên bản đã lưu…', async () => {
        const signal = this.operation!.signal;
        const response = await fetch(`/api${base}/revisions/${doc.revision}/exports`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({format}), signal });
        if (!response.ok) { const error = await response.json().catch(() => null); throw new Error(error?.detail?.message || 'Không xuất được tệp. Hãy thử lại.'); }
        const blob = await response.blob(); if (signal.aborted) return;
        const url = URL.createObjectURL(blob), link = document.createElement('a');
        link.href = url; link.download = `Automated-CX-Report-${doc.reportId}-v${doc.revision}.${format}`; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 10_000); this.notice = `Đã xuất ${format.toUpperCase()} của phiên bản ${doc.revision}. Tệp mang nhãn BẢN NHÁP.`;
      });
    }
  }
}
