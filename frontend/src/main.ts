import './style.css';
import { clearChartSelection, renderChart, selectChartPoint } from './chart';
import { entityCardTitle, entityTrail } from './presentation';
import type { ChartPointSelection, Entity, Figure } from './types';

type Project = { label: string; records: number; chartable: number; entities: number; units: number; minDate: string | null; maxDate: string | null };
type Chart = { entityId: string; title: string; figure: Figure };
type AuditRow = Record<string, string | number | null>;
type Workspace = {
  window: { start: string; end: string };
  selectedEntity: string;
  scopeIds: string[];
  overview: Chart[];
  statistics: Chart[];
  statisticsPeriods: { start: string; label: string; complete: boolean }[];
  comparisonCandidates: { entity_id: string; entity_label: string; effective_unit: string }[];
  comparison: Figure | null;
  audit: { total: number; offset: number; rows: AuditRow[] };
  capabilities?: { lineage?: { contractVersion: number; exactObservation: boolean; aggregateObservation: boolean } };
};
type Tab = 'overview' | 'statistics' | 'comparison' | 'audit' | 'import' | 'history';
type State = {
  project: string; mode: 'recent' | 'week' | 'month' | 'custom'; count: number;
  start: string; end: string; entity: string; scope: 'node' | 'children';
  statisticsGroup: 'day' | 'week' | 'month' | 'quarter';
  statisticsMode: 'both' | 'sum' | 'average';
  statisticsRange: 'recent' | 'all' | 'custom'; statisticsCount: number;
  statisticsFrom: string; statisticsTo: string; includeIncomplete: boolean;
  comparisonMetric: string; comparisonEntities: string[]; auditOffset: number; tab: Tab;
};
type ValidationIssue = { severity: string; code: string; message: string };
type Preview = {
  manifest: {
    source_file: string; source_hash: string; record_count: number; date_count: number;
    observed_date_min?: string | null; observed_date_max?: string | null; projects?: string[];
  };
  valid: boolean; errorCount: number; warningCount: number; issues: ValidationIssue[];
};
type ImportOutcome = {
  attempt_id: number; status: string; run_id: number | null; duplicate_of_run_id: number | null;
  inserted_count: number; updated_count: number; unchanged_count: number; restored_count: number;
  deleted_count: number; lineage_changed_count: number; message: string | null;
};
type ImportResult = {
  outcome: ImportOutcome; preview: Preview; fileName: string; fileSize: number;
  mode: 'full_snapshot' | 'incremental'; committedAt: string;
};

type Provenance = {
  contractVersion: number; status: 'available'; observationRef: string; lineageRef: string;
  context: {
    project: { label: string };
    entity: { ref: string; label: string; level: string; hierarchyPath: string[]; effectiveUnit: string | null };
    metric: { key: string; label: string };
    observedDate: string;
  };
  source: { workbookName: string; workbookHash: { algorithm: string; value: string }; sheet: string; cell: string; cellReference: string };
  values: { raw: { text: string | null; type: string }; display: string; chart: number | null; valueKind: string; numberFormat: string | null };
  transformation: { parserRule: string | null; parserConfidence: string | null; note: string | null };
  validation: { status: string; issues: { severity: string; code: string; message: string }[]; issueLinkage?: string };
  revision: { revisionRef?: string | null; changeType: string; recordedAt: string; state: 'current' | 'superseded'; revisionCurrent?: boolean; sourcePresenceCurrent?: boolean };
  import: { mode: string; committedAt: string | null; importRef?: string | null; attemptRef?: string | null };
  freshness: { observedThrough: string | null; isCurrent: boolean; newerSnapshotAvailable: boolean; newerSourceDataAvailable?: boolean; sourceCommittedAt?: string | null };
};
type AggregateProvenance = {
  contractVersion: 2; kind: 'aggregate'; aggregateRef: string;
  context: { project: string; entity: { ref: string; label: string; hierarchyPath: string[]; effectiveUnit: string | null }; metric: string; series: string; period: { start: string; end: string }; observedThrough: string | null };
  result: { chartValue: number; displayValue: string };
  aggregation: { ruleCode: string; explanation: string; valueObservationCount: number; coverageObservationCount: number; eligibleDayCount: number | null; calendarDayCount: number | null; inferredZero: boolean };
  contributors: { total: number; pageSize: number };
  freshness: { snapshotCreatedAt: string; observedThrough: string | null; newerDataAvailable: boolean };
};
type Contributor = { observationRef: string; lineageRef: string; role: string; included: boolean; contributionValue: number | null; note: string | null; date: string; entityLabel: string; metric: string; displayValue: string; chartValue: number | null; validationStatus: string };
type ContributorPage = { contractVersion: 2; aggregateRef: string; total: number; items: Contributor[]; nextCursor: string | null };
type RevisionHistory = { contractVersion: 2; observationRef: string; items: { revisionRef: string | null; lineageRef: string | null; changeType: string; recordedAt: string; displayValue: string; chartValue: number | null; validationStatus: string; state: string; importRef: string | null; attemptRef: string | null }[] };
type ImportRun = { contractVersion: 2; importRef: string; attemptRef: string; status: string; workbookName: string; workbookHash: string; mode: string; committedAt: string; dataRange: { start: string | null; end: string | null }; outcome: { inserted: number; updated: number; unchanged: number; restored: number; deleted: number } };
type SelectionOrigin = {
  plotKey: string; tab: Tab; entityRef: string; seriesName: string; observedDate: string;
  displayedValue: string; curveNumber: number; pointNumber: number;
  viewport?: { xRange?: unknown[]; yRange?: unknown[]; y2Range?: unknown[] };
};
type InvestigationSelection = { kind: 'exact-observation' | 'aggregate'; aggregateRef: string | null; observationRef: string | null; lineageRef: string | null; origin: SelectionOrigin };
type InvestigationState =
  | { status: 'closed' }
  | { status: 'loading'; selection: InvestigationSelection }
  | { status: 'ready'; selection: InvestigationSelection; provenance: Provenance }
  | { status: 'aggregate-ready'; selection: InvestigationSelection; provenance: AggregateProvenance; contributors: Contributor[]; nextCursor: string | null; pageStatus: 'idle' | 'loading' | 'error' }
  | { status: 'unavailable'; selection: InvestigationSelection }
  | { status: 'error'; selection: InvestigationSelection; error: string };
type AuditLookup = { contractVersion: number; observationRef: string; lineageRef: string; row: AuditRow; recommendedContext: { entityRef: string; start: string; end: string; metric: string } };
type AuditFocus =
  | { status: 'loading'; selection: InvestigationSelection }
  | { status: 'ready'; selection: InvestigationSelection; lookup: AuditLookup }
  | { status: 'error'; selection: InvestigationSelection; error: string };

const STORAGE_KEY = 'excel_visualization_pipeline.workspace.v1';
const tabs: { key: Tab; icon: string; label: string }[] = [
  { key: 'overview', icon: '◫', label: 'Tổng quan' },
  { key: 'statistics', icon: '▥', label: 'Thống kê' },
  { key: 'comparison', icon: '⇄', label: 'So sánh' },
  { key: 'audit', icon: '▤', label: 'Audit dữ liệu' },
  { key: 'import', icon: '↥', label: 'Nhập Excel' },
  { key: 'history', icon: '◷', label: 'Lịch sử nhập' },
];
const defaults: State = {
  project: '', mode: 'recent', count: 8, start: '', end: '', entity: '', scope: 'node',
  statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
  statisticsFrom: '', statisticsTo: '', includeIncomplete: true,
  comparisonMetric: 'Báo sai/Lỗi', comparisonEntities: [], auditOffset: 0, tab: 'overview',
};
let state: State = { ...defaults };
try { state = { ...defaults, ...JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}') }; } catch { /* Browser storage may be disabled. */ }
let projects: Project[] = [];
let entities: Entity[] = [];
let workspace: Workspace | null = null;
let historyItems: Record<string, unknown>[] = [];
let historyLoading = false;
let selectedFile: File | null = null;
let preview: Preview | null = null;
let importMode: 'full_snapshot' | 'incremental' = 'incremental';
let importPhase: 'idle' | 'previewing' | 'committing' = 'idle';
let importError = '';
let importResult: ImportResult | null = null;
let fullSnapshotConfirmed = false;
let showAllIssues = false;
let lastImportAction: 'preview' | 'commit' = 'preview';
let pendingFocusId = '';
let loading = false;
let message = '';
let bootstrapLoaded = false;
let bootstrapError = '';
let workspaceError = '';
let historyError = '';
let request: AbortController | null = null;
let investigationRequest: AbortController | null = null;
let investigation: InvestigationState = { status: 'closed' };
let auditFocus: AuditFocus | null = null;
let investigationLiveMessage = '';
let aggregateParent: Extract<InvestigationState, { status: 'aggregate-ready' }> | null = null;
let revisionHistory: { status: 'loading' | 'ready' | 'error'; observationRef: string; data?: RevisionHistory; error?: string } | null = null;
let importDetail: { status: 'loading' | 'ready' | 'error'; importRef: string; data?: ImportRun; error?: string } | null = null;
const app = document.querySelector<HTMLDivElement>('#app')!;
const SIDEBAR_KEY = 'excel_visualization_pipeline.sidebar_collapsed.v1';
let sidebarCollapsed = false;
try { sidebarCollapsed = sessionStorage.getItem(SIDEBAR_KEY) === '1'; } catch { /* Optional UI preference. */ }

const esc = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!);
const fmt = (value: number): string => new Intl.NumberFormat('vi-VN').format(value);
const dateLabel = (value: string): string => value ? (/^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN') : value) : '—';
const shortHash = (value: string): string => value.length > 24 ? `${value.slice(0, 12)}…${value.slice(-8)}` : value;
const save = () => { try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* Continue without persistence. */ } };
function restorePendingFocus(): void {
  if (!pendingFocusId) return;
  const id = pendingFocusId; pendingFocusId = '';
  requestAnimationFrame(() => document.getElementById(id)?.focus());
}
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const detailMessage = typeof detail === 'object' && detail && typeof detail.message === 'string' ? detail.message : null;
    throw new Error(typeof detail === 'string' ? detail : detailMessage || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
function select(options: { value: string; label: string }[], current: string): string {
  return options.map(option => `<option value="${esc(option.value)}" ${option.value === current ? 'selected' : ''}>${esc(option.label)}</option>`).join('');
}
function currentProject(): Project | undefined { return projects.find(project => project.label === state.project); }
function renderShell(): void {
  app.innerHTML = `<div class="shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">CX</div><div class="brand-copy"><strong>CX Platform</strong><span>Analytics workspace</span></div><button class="sidebar-toggle" data-action="toggle-sidebar" aria-label="Thu gọn hoặc mở sidebar" title="Thu gọn hoặc mở sidebar">☰</button></div>
      <div class="side-scroll"><div id="side-filters"></div></div>
    <div class="side-bottom"><span class="status-dot"></span><span class="status-copy">Kho dữ liệu nội bộ</span> <small>v1.0 · Internal</small></div>
    </aside>
    <div class="main-column"><header class="topbar"><div class="breadcrumb">Không gian làm việc <span>/</span> <strong>Analytics</strong></div><div class="top-actions"><span class="environment">INTERNAL</span><div class="avatar">CX</div></div></header>
    <main class="workspace"><div id="workspace"></div></main></div>
    <aside id="investigation-drawer" class="investigation-drawer" aria-hidden="true"></aside>
  </div>`;
}
function renderSidebar(): void {
  const root = document.querySelector<HTMLDivElement>('#side-filters')!;
  const project = currentProject();
  root.innerHTML = `<div class="side-heading">Dự án & bộ lọc</div>
    <label class="field"><span>Dự án</span><select data-field="project">${select(projects.map(p => ({ value: p.label, label: p.label })), state.project)}</select></label>
    <div class="side-section"><div class="section-caption">Khoảng thời gian</div>
      <label class="field"><span>Xem theo</span><select data-field="mode">${select([
        { value: 'recent', label: 'Tối đa 10 ngày dữ liệu' }, { value: 'week', label: 'Theo tuần' },
        { value: 'month', label: 'Theo tháng' }, { value: 'custom', label: 'Tùy chỉnh' },
      ], state.mode)}</select></label>
      ${state.mode === 'week' || state.mode === 'month' ? `<label class="field"><span>Số ${state.mode === 'week' ? 'tuần' : 'tháng'} so sánh</span><input data-field="count" type="number" min="1" max="60" value="${state.count}"></label>` : ''}
      ${state.mode === 'custom' ? `<div class="date-pair"><label class="field"><span>Từ ngày</span><input data-field="start" type="date" min="${esc(project?.minDate)}" max="${esc(project?.maxDate)}" value="${esc(state.start)}"></label><label class="field"><span>Đến ngày</span><input data-field="end" type="date" min="${esc(project?.minDate)}" max="${esc(project?.maxDate)}" value="${esc(state.end)}"></label></div>` : ''}
      ${workspace ? `<div class="range-note">◷ ${dateLabel(workspace.window.start)} — ${dateLabel(workspace.window.end)}</div>` : ''}
    </div>
    <div class="side-section"><div class="section-caption">Cây entity</div>
      <label class="field"><span>Entity</span><select data-field="entity">${select(entities.map(e => ({ value: e.entity_id, label: `${'　'.repeat(e.entity_depth)}${e.entity_label}${e.effective_unit ? ` · ${e.effective_unit}` : ''}` })), state.entity)}</select></label>
      <label class="field"><span>Phạm vi</span><select data-field="scope">${select([{ value: 'node', label: 'Entity đã chọn' }, { value: 'children', label: 'Entity con trực tiếp' }], state.scope)}</select></label>
    </div>
    <div class="side-tip"><span>✦</span><strong>Bộ lọc được giữ khi tải lại trang</strong><p>Thiết lập chỉ lưu trong thẻ trình duyệt này, không xuất hiện trên đường dẫn.</p></div>`;
}
function header(title: string, subtitle: string): string {
  return `<div class="page-head"><div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="head-actions"><button class="ghost" data-action="refresh">↻ Làm mới dữ liệu</button>${state.project ? `<a class="primary" href="/api/projects/${encodeURIComponent(state.project)}/export.csv">↓ Tải dữ liệu CSV</a>` : ''}</div></div>`;
}

function selectionViewport(element: HTMLElement): SelectionOrigin['viewport'] {
  const layout = (element as HTMLElement & { layout?: { xaxis?: { range?: unknown[] }; yaxis?: { range?: unknown[] }; yaxis2?: { range?: unknown[] } } }).layout;
  return layout ? {
    xRange: layout.xaxis?.range ? [...layout.xaxis.range] : undefined,
    yRange: layout.yaxis?.range ? [...layout.yaxis.range] : undefined,
    y2Range: layout.yaxis2?.range ? [...layout.yaxis2.range] : undefined,
  } : undefined;
}

function investigationSelection(): InvestigationSelection | null {
  return investigation.status === 'closed' ? null : investigation.selection;
}

function validationLabel(status: string): string {
  return status === 'valid' ? 'Hợp lệ' : status === 'warning' ? 'Có cảnh báo' : status === 'error' ? 'Không hợp lệ' : status;
}
const auditHeaders: Record<string, string> = {
  date: 'Ngày', entity_path: 'Đường dẫn entity', metric_normalized: 'Chỉ số',
  raw_value: 'Giá trị gốc trong Excel', display_value: 'Giá trị hiển thị',
  chart_value: 'Giá trị dùng để vẽ', value_kind: 'Loại giá trị',
  sheet_name: 'Sheet nguồn', cell_address: 'Ô nguồn', validation_status: 'Kiểm tra',
};
const valueKinds: Record<string, string> = {
  numeric: 'Số', number: 'Số', source_marker: 'Dấu nguồn', not_recorded: 'Chưa ghi nhận',
  default_zero_rate: 'Tỷ lệ 0% mặc định', blank: 'Ô trống', text: 'Văn bản',
};
function auditCell(column: string, value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  if (column === 'date' && typeof value === 'string') return dateLabel(value.slice(0, 10));
  if (column === 'validation_status') return validationLabel(String(value));
  if (column === 'value_kind') return valueKinds[String(value)] || String(value);
  return String(value);
}
const historyHeaders: Record<string, string> = {
  attempt_status: 'Kết quả', submitted_file_name: 'Workbook', requested_mode: 'Chế độ',
  input_record_count: 'Quan sát đầu vào', inserted_count: 'Thêm mới', updated_count: 'Cập nhật',
  unchanged_count: 'Giữ nguyên', started_at: 'Bắt đầu lúc',
};
const importStatuses: Record<string, string> = {
  committed: 'Đã ghi', duplicate: 'Đã có trước đó', rejected: 'Không đạt kiểm tra', failed: 'Thất bại',
};
function historyCell(column: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (column === 'attempt_status') return importStatuses[String(value)] || String(value);
  if (column === 'requested_mode') return value === 'full_snapshot' ? 'Snapshot đầy đủ' : value === 'incremental' ? 'Dữ liệu bổ sung' : String(value);
  if (column === 'started_at') {
    const date = new Date(String(value));
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('vi-VN');
  }
  return typeof value === 'number' ? fmt(value) : String(value);
}
function revisionStateLabel(state: string): string {
  return state === 'current' ? 'Hiện hành' : state === 'superseded' ? 'Đã được thay thế' : state === 'deleted' ? 'Không còn hiệu lực' : state;
}
function revisionChangeLabel(change: string): string {
  return ({ inserted: 'Thêm mới', updated: 'Cập nhật', restored: 'Khôi phục', deleted: 'Ngừng hiệu lực', lineage_changed: 'Đổi nguồn tham chiếu' } as Record<string, string>)[change] || change;
}
function confidenceLabel(confidence: string | null): string {
  return confidence === 'high' ? 'Độ tin cậy cao' : confidence === 'medium' ? 'Độ tin cậy trung bình' : confidence === 'low' ? 'Độ tin cậy thấp' : 'Chưa có mức tin cậy';
}

function aggregateMarkup(p: AggregateProvenance, contributors: Contributor[], nextCursor: string | null, pageStatus: string): string {
  const roleLabel: Record<string, string> = { value: 'Giá trị', numerator: 'Tử số', denominator: 'Mẫu số', coverage: 'Ngày hợp lệ', excluded_marker: 'Dấu nguồn', missing: 'Thiếu giá trị' };
  return `<div class="drawer-body">
    ${p.freshness.newerDataAvailable ? '<div class="lineage-banner">Đã có lần nhập dữ liệu mới hơn sau snapshot này. Giá trị tổng hợp đang xem vẫn giữ nguyên; hãy tải lại workspace để đối chiếu.</div>' : ''}
    <section class="provenance-context"><div class="entity-path">${p.context.entity.hierarchyPath.map(esc).join('<span>›</span>')}</div><dl><div><dt>Dự án</dt><dd>${esc(p.context.project)}</dd></div><div><dt>Đơn vị</dt><dd>${esc(p.context.entity.effectiveUnit || '—')}</dd></div><div><dt>Khoảng thời gian</dt><dd>${dateLabel(p.context.period.start)} – ${dateLabel(p.context.period.end)}</dd></div></dl></section>
    <section><h3>Cách tính</h3><p>${esc(p.aggregation.explanation)}</p><dl class="provenance-grid compact"><div><dt>Quy tắc</dt><dd>${esc(p.aggregation.ruleCode)}</dd></div><div><dt>Giá trị tổng hợp</dt><dd>${esc(p.result.displayValue)}</dd></div><div><dt>Observation giá trị</dt><dd>${fmt(p.aggregation.valueObservationCount)}</dd></div><div><dt>Observation ngày hợp lệ</dt><dd>${fmt(p.aggregation.coverageObservationCount)}</dd></div>${p.aggregation.eligibleDayCount !== null ? `<div><dt>Ngày hợp lệ</dt><dd>${fmt(p.aggregation.eligibleDayCount)}</dd></div>` : ''}${p.aggregation.inferredZero ? '<div class="wide-row"><dt>Lưu ý</dt><dd>Giá trị 0 được suy ra theo quy tắc biểu đồ; không có ô Excel chứa giá trị 0 tương ứng.</dd></div>' : ''}</dl></section>
    <section><h3>Observation đóng góp <span class="muted-copy">${fmt(contributors.length)}/${fmt(p.contributors.total)}</span></h3><p class="muted-copy">Điểm tổng hợp không tương ứng với một ô Excel. Chọn một observation để xem nguồn chính xác.</p>
    <div class="contributor-list">${contributors.map((item, index) => `<button class="contributor-item" data-action="open-contributor" data-index="${index}"><span><strong>${esc(item.entityLabel)} · ${esc(item.metric)}</strong><small>${dateLabel(item.date)} · ${esc(roleLabel[item.role] || item.role)}${item.included ? '' : ' · không đưa vào phép tính'}</small></span><span>${esc(item.displayValue)} ›</span></button>`).join('') || '<p>Không có observation được lưu cho điểm này.</p>'}</div>
    ${nextCursor ? `<button class="ghost" data-action="load-contributors" ${pageStatus === 'loading' ? 'disabled' : ''}>${pageStatus === 'loading' ? 'Đang tải…' : 'Xem thêm'}</button>` : ''}${pageStatus === 'error' ? '<p class="lineage-error">Không tải được trang tiếp theo. Bạn có thể thử lại.</p>' : ''}
    </section><section><h3>Độ mới dữ liệu</h3><p>Đến ngày ${esc(p.freshness.observedThrough ? dateLabel(p.freshness.observedThrough) : '—')} · Lưu snapshot ${esc(new Date(p.freshness.snapshotCreatedAt).toLocaleString('vi-VN'))}</p></section>
  </div>`;
}

function revisionMarkup(observationRef: string): string {
  if (!revisionHistory || revisionHistory.observationRef !== observationRef) return '<button class="ghost" data-action="show-revisions">Xem các phiên bản của giá trị này</button>';
  if (revisionHistory.status === 'loading') return '<p aria-live="polite">Đang tải các phiên bản…</p>';
  if (revisionHistory.status === 'error') return `<p class="lineage-error">${esc(revisionHistory.error)}</p><button class="ghost" data-action="show-revisions">Thử lại</button>`;
  return `<div class="revision-list">${revisionHistory.data?.items.map(item => `<div class="revision-item"><strong>${esc(item.displayValue)} · ${esc(revisionStateLabel(item.state))}</strong><small>${esc(new Date(item.recordedAt).toLocaleString('vi-VN'))} · ${esc(revisionChangeLabel(item.changeType))} · ${esc(validationLabel(item.validationStatus))}</small>${item.importRef ? `<button class="ghost" data-action="show-import" data-import-ref="${esc(item.importRef)}">Xem lần nhập</button>` : ''}</div>`).join('') || '<p>Chưa có phiên bản được ghi nhận.</p>'}</div>`;
}

function importMarkup(): string {
  if (!importDetail) return '';
  if (importDetail.status === 'loading') return '<section aria-live="polite">Đang tải lần nhập dữ liệu…</section>';
  if (importDetail.status === 'error') return `<section><p class="lineage-error">${esc(importDetail.error)}</p><button class="ghost" data-action="show-import" data-import-ref="${esc(importDetail.importRef)}">Thử lại</button></section>`;
  const run = importDetail.data!;
  return `<section><h3>Lần nhập dữ liệu</h3><dl class="provenance-grid compact"><div><dt>Workbook</dt><dd>${esc(run.workbookName)}</dd></div><div><dt>Cách nhập</dt><dd>${run.mode === 'full_snapshot' ? 'Snapshot đầy đủ' : 'Dữ liệu bổ sung'}</dd></div><div><dt>Ghi lúc</dt><dd>${esc(new Date(run.committedAt).toLocaleString('vi-VN'))}</dd></div><div><dt>Khoảng dữ liệu</dt><dd>${esc(run.dataRange.start || '—')} – ${esc(run.dataRange.end || '—')}</dd></div><div><dt>Thêm / cập nhật / giữ nguyên</dt><dd>${fmt(run.outcome.inserted)} / ${fmt(run.outcome.updated)} / ${fmt(run.outcome.unchanged)}</dd></div><div class="wide-row"><dt>SHA-256 workbook</dt><dd><code title="${esc(run.workbookHash)}">${esc(shortHash(run.workbookHash))}</code></dd></div></dl></section>`;
}

function renderInvestigation(): void {
  const shell = app.querySelector<HTMLElement>('.shell');
  const drawer = document.querySelector<HTMLElement>('#investigation-drawer');
  if (!shell || !drawer) return;
  const priorAction = drawer.contains(document.activeElement)
    ? (document.activeElement as HTMLElement).dataset.action : null;
  const open = investigation.status !== 'closed';
  shell.classList.toggle('drawer-open', open);
  drawer.setAttribute('aria-hidden', String(!open));
  if (investigation.status === 'closed') {
    drawer.innerHTML = '';
    window.dispatchEvent(new Event('resize'));
    return;
  }
  const activeInvestigation = investigation;
  const selection = activeInvestigation.selection;
  const origin = selection.origin;
  const close = '<button class="drawer-close" data-action="close-investigation">Đóng</button>';
  const live = `<div class="sr-live" role="status" aria-live="polite" aria-atomic="true">${esc(investigationLiveMessage)}</div>`;
  if (activeInvestigation.status === 'aggregate-ready') {
    const p = activeInvestigation.provenance;
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn điểm tổng hợp</span><h2 id="investigation-title">${esc(p.context.metric)} <strong>${esc(p.result.displayValue)}</strong></h2><p>${dateLabel(p.context.period.start)} – ${dateLabel(p.context.period.end)} · ${esc(origin.seriesName)}</p></div>${close}</div>${live}${aggregateMarkup(p, activeInvestigation.contributors, activeInvestigation.nextCursor, activeInvestigation.pageStatus)}`;
  } else if (activeInvestigation.status === 'loading') {
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${esc(origin.seriesName)}</h2><p>${esc(dateLabel(origin.observedDate))} · ${esc(origin.displayedValue)}</p></div>${close}</div>${live}<div class="drawer-body" aria-busy="true"><div class="lineage-loading"><strong>Đang xác minh nguồn dữ liệu…</strong><span>Đối chiếu điểm biểu đồ với ô Excel và lần nhập tương ứng.</span><i></i><i></i><i></i></div></div>`;
  } else if (activeInvestigation.status === 'unavailable') {
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${esc(origin.seriesName)}</h2><p>${esc(dateLabel(origin.observedDate))} · ${esc(origin.displayedValue)}</p></div>${close}</div>${live}<div class="drawer-body"><div class="lineage-state"><strong>Chưa truy vết được điểm này</strong><p>Dữ liệu cũ chưa lưu tham chiếu chính xác đến ô Excel. Để tránh mở nhầm nguồn, hệ thống không tự ghép theo ngày, chỉ số hoặc giá trị. Bạn vẫn có thể xem các điểm khác trên biểu đồ.</p></div></div>`;
  } else if (activeInvestigation.status === 'error') {
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${esc(origin.seriesName)}</h2><p>${esc(dateLabel(origin.observedDate))} · ${esc(origin.displayedValue)}</p></div>${close}</div>${live}<div class="drawer-body"><div class="lineage-state error"><strong>Không tải được nguồn dữ liệu</strong><p>${esc(activeInvestigation.error)}</p><button class="ghost" data-action="retry-provenance">Thử tải lại nguồn</button></div></div>`;
  } else {
    const p = activeInvestigation.provenance;
    const warnings = p.validation.issues.length
      ? `<div class="provenance-issues">${p.validation.issues.map(issue => `<div><strong>${esc(issue.code)}</strong><p>${esc(issue.message)}</p></div>`).join('')}</div>`
      : '<p class="muted-copy">Không có cảnh báo nào gắn trực tiếp với ô nguồn của giá trị này.</p>';
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${esc(p.context.metric.label)} <strong>${esc(p.values.display)}</strong></h2><p>${esc(dateLabel(p.context.observedDate))} · Chuỗi ${esc(origin.seriesName)}</p></div>${close}</div>${live}
      <div class="drawer-body">
        ${p.freshness.newerSnapshotAvailable ? '<div class="lineage-banner">Nguồn của điểm này đã có lần nhập mới hơn. Giá trị đang xem vẫn là phiên bản tại thời điểm chọn.</div>' : ''}
        <section class="provenance-context"><div class="entity-path">${p.context.entity.hierarchyPath.map(esc).join('<span>›</span>')}</div><dl><div><dt>Dự án</dt><dd>${esc(p.context.project.label)}</dd></div><div><dt>Đơn vị tính</dt><dd>${esc(p.context.entity.effectiveUnit || 'Chưa xác định')}</dd></div></dl></section>
        <section><h3>Nguồn Excel</h3><dl class="provenance-grid"><div><dt>Workbook</dt><dd>${esc(p.source.workbookName)}</dd></div><div><dt>Sheet và ô</dt><dd><code>${esc(p.source.cellReference)}</code></dd></div><div class="wide-row"><dt>SHA-256 workbook</dt><dd title="${esc(p.source.workbookHash.value)}"><code>${esc(shortHash(p.source.workbookHash.value))}</code></dd></div></dl><div class="inline-actions"><button data-action="copy-cell">Sao chép tham chiếu ô</button><button data-action="copy-value">Sao chép giá trị hiển thị</button></div></section>
        <section><h3>Giá trị và chuyển đổi</h3><div class="value-flow"><div><span>Gốc trong Excel</span><strong>${esc(p.values.raw.text ?? '—')}</strong></div><b>→</b><div><span>Hiển thị</span><strong>${esc(p.values.display)}</strong></div><b>→</b><div><span>Dùng để vẽ</span><strong>${esc(p.values.chart ?? '—')}</strong></div></div><p class="value-help">Giá trị gốc giữ nguyên nội dung ô; giá trị hiển thị dành cho người đọc; giá trị dùng để vẽ là số sau chuẩn hóa.</p><dl class="provenance-grid compact"><div><dt>Quy tắc đọc file</dt><dd>${esc(p.transformation.parserRule || 'Không ghi nhận')}</dd></div><div><dt>Định dạng Excel</dt><dd>${esc(p.values.numberFormat || 'Không có')}</dd></div>${p.transformation.note ? `<div class="wide-row"><dt>Ghi chú xử lý</dt><dd>${esc(p.transformation.note)}</dd></div>` : ''}</dl></section>
        <section><h3>Kiểm tra dữ liệu</h3><div class="validation-line"><span class="validation-badge ${esc(p.validation.status)}">${esc(validationLabel(p.validation.status))}</span><span>${esc(confidenceLabel(p.transformation.parserConfidence))}</span></div>${warnings}</section>
        <section><h3>Lần nhập và phiên bản</h3><dl class="provenance-grid compact"><div><dt>Thay đổi</dt><dd>${esc(revisionChangeLabel(p.revision.changeType))}</dd></div><div><dt>Trạng thái phiên bản</dt><dd>${p.revision.revisionCurrent && !p.revision.sourcePresenceCurrent ? 'Còn hiệu lực · nguồn đã mới hơn' : esc(revisionStateLabel(p.revision.state))}</dd></div><div><dt>Ghi lúc</dt><dd>${esc(p.import.committedAt ? new Date(p.import.committedAt).toLocaleString('vi-VN') : '—')}</dd></div><div><dt>Dữ liệu đến ngày</dt><dd>${esc(p.freshness.observedThrough ? dateLabel(p.freshness.observedThrough) : '—')}</dd></div></dl></section>
      </div><div class="drawer-actions"><button class="primary" data-action="open-exact-audit">Mở đúng dòng Audit</button></div>`;
  }
  if (activeInvestigation.status === 'ready') {
    const p = activeInvestigation.provenance;
    const body = drawer.querySelector<HTMLElement>('.drawer-body');
    body?.insertAdjacentHTML('beforeend', `<section><h3>Lịch sử của giá trị</h3>${revisionMarkup(p.observationRef)}${p.import.importRef ? `<button class="ghost" data-action="show-import" data-import-ref="${esc(p.import.importRef)}">Xem lần nhập nguồn này</button>` : ''}</section>${importMarkup()}`);
    if (aggregateParent) drawer.querySelector<HTMLElement>('.drawer-actions')?.insertAdjacentHTML('afterbegin', '<button class="ghost" data-action="back-to-aggregate">Về điểm tổng hợp</button>');
  }
  requestAnimationFrame(() => {
    if (investigation.status === 'closed') return;
    const target = (priorAction
      ? Array.from(drawer.querySelectorAll<HTMLElement>('[data-action]')).find(button => button.dataset.action === priorAction)
      : null) ?? drawer.querySelector<HTMLElement>('.drawer-close');
    target?.focus({ preventScroll: true });
  });
  window.dispatchEvent(new Event('resize'));
}

async function loadProvenance(selection: InvestigationSelection): Promise<void> {
  if (selection.kind === 'aggregate') { await loadAggregate(selection); return; }
  if (!selection.observationRef || !selection.lineageRef) {
    investigation = { status: 'unavailable', selection };
    investigationLiveMessage = 'Điểm đã chọn chưa có thông tin provenance.';
    renderInvestigation();
    return;
  }
  investigationRequest?.abort();
  const current = new AbortController(); investigationRequest = current;
  investigation = { status: 'loading', selection };
  investigationLiveMessage = 'Đang tải nguồn dữ liệu của điểm đã chọn.';
  renderInvestigation();
  try {
    const params = new URLSearchParams({ lineageRef: selection.lineageRef });
    const provenance = await api<Provenance>(`/projects/${encodeURIComponent(state.project)}/observations/${encodeURIComponent(selection.observationRef)}/provenance?${params}`, { signal: current.signal });
    if (current !== investigationRequest) return;
    if (provenance.observationRef !== selection.observationRef || provenance.lineageRef !== selection.lineageRef) throw new Error('API trả về lineage không khớp điểm đã chọn.');
    investigation = { status: 'ready', selection, provenance };
    investigationLiveMessage = `Đã tải nguồn cho ${provenance.context.metric.label}, ngày ${dateLabel(provenance.context.observedDate)}.`;
  } catch (error) {
    if (current.signal.aborted) return;
    investigation = { status: 'error', selection, error: (error as Error).message };
    investigationLiveMessage = 'Không tải được nguồn dữ liệu.';
  }
  renderInvestigation();
}

async function loadAggregate(selection: InvestigationSelection): Promise<void> {
  if (!selection.aggregateRef) {
    investigation = { status: 'unavailable', selection };
    investigationLiveMessage = 'Điểm tổng hợp chưa có nguồn được lưu.';
    renderInvestigation(); return;
  }
  investigationRequest?.abort();
  const current = new AbortController(); investigationRequest = current;
  investigation = { status: 'loading', selection };
  investigationLiveMessage = 'Đang tải bằng chứng của điểm tổng hợp.';
  renderInvestigation();
  try {
    const path = `/projects/${encodeURIComponent(state.project)}/aggregates/${encodeURIComponent(selection.aggregateRef)}`;
    const [provenance, page] = await Promise.all([
      api<AggregateProvenance>(`${path}/provenance`, { signal: current.signal }),
      api<ContributorPage>(`${path}/contributors`, { signal: current.signal }),
    ]);
    if (current !== investigationRequest) return;
    if (provenance.aggregateRef !== selection.aggregateRef || page.aggregateRef !== selection.aggregateRef) throw new Error('Bằng chứng tổng hợp không khớp với điểm đã chọn.');
    investigation = { status: 'aggregate-ready', selection, provenance, contributors: page.items, nextCursor: page.nextCursor, pageStatus: 'idle' };
    investigationLiveMessage = `Đã tải ${page.items.length} trong ${page.total} observation đóng góp.`;
  } catch (error) {
    if (current.signal.aborted) return;
    investigation = { status: 'error', selection, error: (error as Error).message };
    investigationLiveMessage = 'Không tải được bằng chứng tổng hợp.';
  }
  renderInvestigation();
}

async function loadMoreContributors(): Promise<void> {
  if (investigation.status !== 'aggregate-ready' || !investigation.nextCursor || investigation.pageStatus === 'loading') return;
  const before = investigation;
  investigation = { ...before, pageStatus: 'loading' }; renderInvestigation();
  try {
    const path = `/projects/${encodeURIComponent(state.project)}/aggregates/${encodeURIComponent(before.provenance.aggregateRef)}/contributors`;
    const page = await api<ContributorPage>(`${path}?${new URLSearchParams({ cursor: before.nextCursor! })}`);
    if (investigation.status !== 'aggregate-ready' || investigation.provenance.aggregateRef !== page.aggregateRef) return;
    investigation = { ...investigation, contributors: [...investigation.contributors, ...page.items], nextCursor: page.nextCursor, pageStatus: 'idle' };
    investigationLiveMessage = `Đã tải ${investigation.contributors.length} trong ${page.total} observation.`;
  } catch {
    if (investigation.status === 'aggregate-ready' && investigation.provenance.aggregateRef === before.provenance.aggregateRef) investigation = { ...investigation, pageStatus: 'error' };
  }
  renderInvestigation();
}

async function loadRevisions(): Promise<void> {
  if (investigation.status !== 'ready') return;
  const observationRef = investigation.provenance.observationRef;
  revisionHistory = { status: 'loading', observationRef }; renderInvestigation();
  try {
    const data = await api<RevisionHistory>(`/projects/${encodeURIComponent(state.project)}/observations/${encodeURIComponent(observationRef)}/revisions`);
    if (data.observationRef !== observationRef) throw new Error('Lịch sử revision không khớp observation.');
    revisionHistory = { status: 'ready', observationRef, data };
  } catch (error) { revisionHistory = { status: 'error', observationRef, error: (error as Error).message }; }
  if (investigation.status === 'ready' && investigation.provenance.observationRef === observationRef) renderInvestigation();
}

async function loadImport(importRef: string): Promise<void> {
  importDetail = { status: 'loading', importRef }; renderInvestigation();
  try {
    const data = await api<ImportRun>(`/projects/${encodeURIComponent(state.project)}/imports/${encodeURIComponent(importRef)}`);
    if (data.importRef !== importRef) throw new Error('Lần nhập không khớp tham chiếu.');
    importDetail = { status: 'ready', importRef, data };
  } catch (error) { importDetail = { status: 'error', importRef, error: (error as Error).message }; }
  if (investigation.status !== 'closed') renderInvestigation();
}

function openInvestigation(plotKey: string, entityRef: string, point: ChartPointSelection): void {
  const plot = document.querySelector<HTMLElement>(`[data-plot="${plotKey}"]`);
  if (!plot) return;
  const selection: InvestigationSelection = {
    kind: point.kind,
    aggregateRef: point.aggregateRef,
    observationRef: point.observationRef,
    lineageRef: point.lineageRef,
    origin: {
      plotKey, tab: state.tab, entityRef, seriesName: point.seriesName,
      observedDate: String(point.x).slice(0, 10), displayedValue: String(point.y ?? '—'),
      curveNumber: point.curveNumber, pointNumber: point.pointNumber,
      viewport: selectionViewport(plot),
    },
  };
  aggregateParent = null; revisionHistory = null; importDetail = null;
  selectChartPoint(plot, point.curveNumber, point.pointNumber);
  void loadProvenance(selection);
}

async function loadAuditLookup(selection: InvestigationSelection): Promise<void> {
  if (!selection.observationRef || !selection.lineageRef) return;
  auditFocus = { status: 'loading', selection };
  state.tab = 'audit'; save(); renderMain(); renderInvestigation();
  try {
    const params = new URLSearchParams({ observationRef: selection.observationRef, lineageRef: selection.lineageRef });
    const lookup = await api<AuditLookup>(`/projects/${encodeURIComponent(state.project)}/audit/lookup?${params}`);
    if (lookup.observationRef !== selection.observationRef || lookup.lineageRef !== selection.lineageRef) throw new Error('API trả về Audit row không khớp điểm đã chọn.');
    auditFocus = { status: 'ready', selection, lookup };
    pendingFocusId = 'focused-audit-row';
  } catch (error) {
    auditFocus = { status: 'error', selection, error: (error as Error).message };
  }
  renderTab();
}

function returnToChart(): void {
  if (!auditFocus) return;
  const selection = auditFocus.selection;
  auditFocus = null;
  state.tab = selection.origin.tab; save(); renderMain(); renderInvestigation();
  requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-plot="${selection.origin.plotKey}"]`)?.focus());
}

async function copyInvestigationValue(kind: 'cell' | 'value'): Promise<void> {
  if (investigation.status !== 'ready') return;
  const value = kind === 'cell' ? investigation.provenance.source.cellReference : investigation.provenance.values.display;
  try {
    await navigator.clipboard.writeText(value);
    investigationLiveMessage = kind === 'cell' ? 'Đã sao chép tham chiếu ô.' : 'Đã sao chép giá trị hiển thị.';
  } catch {
    investigationLiveMessage = 'Trình duyệt không cho phép sao chép tự động.';
  }
  renderInvestigation();
}
function renderMain(): void {
  const root = document.querySelector<HTMLDivElement>('#workspace')!;
  const project = currentProject();
  const chosenTab = tabs.find(tab => tab.key === state.tab)!;
  const trail = entityTrail(entities, state.entity);
  root.innerHTML = `<nav class="tabbar" aria-label="Tính năng workspace">${tabs.map(tab => `<button class="tab ${tab.key === state.tab ? 'active' : ''}" data-tab="${tab.key}" aria-current="${tab.key === state.tab ? 'page' : 'false'}"><span>${tab.icon}</span>${tab.label}</button>`).join('')}</nav>
    ${header(state.project || 'Không gian phân tích', project ? `${fmt(project.records)} quan sát đã lưu · ${fmt(project.chartable)} quan sát có thể vẽ` : bootstrapError ? 'Chưa kết nối được kho dữ liệu.' : bootstrapLoaded ? 'Chưa có workbook nào được nhập.' : 'Đang kiểm tra dữ liệu…')}
    ${trail.length ? `<div class="hierarchy-context"><span class="context-label">Vị trí trong hierarchy</span><div class="entity-breadcrumb" aria-label="Đường dẫn entity">${trail.map((entity, index) => `<span class="crumb ${index === trail.length - 1 ? 'current' : ''}">${esc(entity.entity_label)}</span>${index < trail.length - 1 ? '<span class="crumb-separator" aria-hidden="true">›</span>' : ''}`).join('')}</div></div>` : ''}
    ${message ? `<div class="notice">${esc(message)}</div>` : ''}
    ${project ? `<div class="kpi-grid">
      <div class="kpi"><div class="kpi-icon violet">◈</div><span>DỰ ÁN</span><strong>${esc(project.label)}</strong><small>Đang xem</small></div>
      <div class="kpi"><div class="kpi-icon blue">◇</div><span>ENTITY</span><strong>${fmt(project.entities)}</strong><small>Trong cây phân cấp</small></div>
      <div class="kpi"><div class="kpi-icon teal">▣</div><span>ĐƠN VỊ</span><strong>${fmt(project.units)}</strong><small>Đơn vị của entity</small></div>
      <div class="kpi"><div class="kpi-icon amber">▤</div><span>QUAN SÁT</span><strong>${fmt(project.records)}</strong><small>Đã lưu, gồm cả ô không vẽ được</small></div>
    </div>` : ''}
    <div class="content-card"><div class="tab-content"><div class="section-title"><div><h2>${chosenTab.label}</h2></div>${loading ? '<span class="loading">Đang cập nhật biểu đồ…</span>' : ''}</div><div id="tab-body"></div></div></div>`;
  renderTab();
}
function chartCard(chart: Chart, index: number, section: string): string {
  const entity = entities.find(item => item.entity_id === chart.entityId);
  const path = entityTrail(entities, chart.entityId).map(item => item.entity_label).join(' / ');
  const metadata = `${path}${entity?.effective_unit ? ` · Đơn vị: ${entity.effective_unit}` : ''}`;
  return `<article class="chart-card"><div class="card-top"><div><h3>${esc(entityCardTitle(entity, chart.title))}</h3><span>${esc(metadata)}</span></div><span class="pill">Theo bộ lọc</span></div><div class="plot" data-plot="${section}-${index}" tabindex="0" aria-label="Biểu đồ ${esc(entityCardTitle(entity, chart.title))}"></div></article>`;
}
function hasSiblingCharts(charts: Chart[]): boolean {
  return state.scope === 'children' && (workspace?.scopeIds.length || 0) > 1 && charts.length > 1;
}
function statePanel(title: string, detail: string, retry = false, retryAction = 'refresh'): string {
  return `<div class="empty ${retry ? 'state-error' : ''}" role="${retry ? 'alert' : 'status'}"><h3>${esc(title)}</h3><p>${esc(detail)}</p>${retry ? `<button class="ghost" data-action="${retryAction}">Thử tải lại</button>` : ''}</div>`;
}
function renderTab(): void {
  const body = document.querySelector<HTMLDivElement>('#tab-body');
  if (!body) return;
  if (!bootstrapLoaded) { body.innerHTML = statePanel('Đang kiểm tra dữ liệu', 'Vui lòng chờ trong khi kết nối kho dữ liệu.'); return; }
  if (bootstrapError) {
    if (state.tab === 'import' && importResult) {
      renderImport(body);
      body.insertAdjacentHTML('afterbegin', statePanel('Chưa tải lại được dashboard', 'Kết quả nhập bên dưới vẫn được giữ trong thẻ này. Kiểm tra kết nối rồi thử tải lại dữ liệu.', true));
    } else body.innerHTML = statePanel('Không kết nối được kho dữ liệu', 'Máy chủ chưa phản hồi. Kiểm tra kết nối hoặc thử lại; chưa cần nhập lại workbook.', true);
    return;
  }
  if (!currentProject()) {
    body.innerHTML = statePanel('Chưa có dữ liệu đã nhập', 'Mở Nhập Excel để chọn workbook đầu tiên.');
    if (state.tab === 'import') renderImport(body);
    if (state.tab === 'history') renderHistory(body);
    return;
  }
  if (workspaceError && ['overview', 'statistics', 'comparison', 'audit'].includes(state.tab)) {
    body.innerHTML = statePanel('Không tải được dữ liệu phân tích', `Bộ lọc được giữ nguyên. ${workspaceError} Thử tải lại khi máy chủ hoạt động.`, true);
    return;
  }
  if (loading && !workspace && ['overview', 'statistics', 'comparison', 'audit'].includes(state.tab)) {
    body.innerHTML = statePanel('Đang tải dữ liệu', 'Đang áp dụng dự án, entity và khoảng thời gian đã chọn.');
    return;
  }
  if (state.tab === 'overview') {
    body.innerHTML = `<p class="section-desc">Biểu đồ Tổng số, Báo sai/Lỗi và % báo sai theo ${state.scope === 'children' ? 'từng entity con trực tiếp' : 'entity đã chọn'}.</p>${workspace?.overview.length ? `<div class="chart-grid ${hasSiblingCharts(workspace.overview) ? 'children-grid' : ''}">${workspace.overview.map((chart, i) => chartCard(chart, i, 'overview')).join('')}</div>` : empty('Không có dữ liệu trong khoảng thời gian đã chọn.')}`;
    workspace?.overview.forEach((chart, i) => draw(`overview-${i}`, chart.figure, chart.entityId));
  } else if (state.tab === 'statistics') {
    body.innerHTML = `<div class="control-bar"><label>Nhóm theo<select data-field="statisticsGroup">${select([{value:'day',label:'Ngày'},{value:'week',label:'Tuần'},{value:'month',label:'Tháng'},{value:'quarter',label:'Quý'}], state.statisticsGroup)}</select></label>
      <label>Hiển thị<select data-field="statisticsMode">${select([{value:'both',label:'SUM & AVG/ngày'},{value:'sum',label:'Chỉ SUM'},{value:'average',label:'Chỉ AVG/ngày'}], state.statisticsMode)}</select></label>
      <label>Phạm vi<select data-field="statisticsRange">${select([{value:'recent',label:'Các kỳ gần nhất'},{value:'all',label:'Toàn bộ dữ liệu'},{value:'custom',label:'Chọn khoảng kỳ'}], state.statisticsRange)}</select></label>
      ${state.statisticsRange === 'recent' ? `<label>Số kỳ<input data-field="statisticsCount" type="number" min="1" max="60" value="${state.statisticsCount}"></label>` : ''}
      ${state.statisticsRange === 'custom' ? `<label>Từ kỳ<input data-field="statisticsFrom" type="date" value="${esc(state.statisticsFrom)}"></label><label>Đến kỳ<input data-field="statisticsTo" type="date" value="${esc(state.statisticsTo)}"></label>` : ''}
      <label class="check"><input data-field="includeIncomplete" type="checkbox" ${state.includeIncomplete ? 'checked' : ''}> Kỳ chưa đầy đủ</label></div>
      <p class="section-desc">SUM và AVG/ngày dùng toàn bộ lịch sử của entity, độc lập với khoảng ngày sidebar. ${workspace?.statisticsPeriods.length || 0} kỳ đang hiển thị.</p>
      ${workspace?.statistics.length ? `<div class="chart-grid ${hasSiblingCharts(workspace.statistics) ? 'children-grid' : ''}">${workspace.statistics.map((chart, i) => chartCard(chart, i, 'statistics')).join('')}</div>` : empty('Không có kỳ dữ liệu phù hợp.')}`;
    workspace?.statistics.forEach((chart, i) => draw(`statistics-${i}`, chart.figure, chart.entityId));
  } else if (state.tab === 'comparison') {
    const candidates = workspace?.comparisonCandidates || [];
    body.innerHTML = `<div class="control-bar"><label>Chỉ số<select data-field="comparisonMetric">${select(['Tổng số','Báo sai/Lỗi','% báo sai'].map(value => ({value,label:value})), state.comparisonMetric)}</select></label><div class="comparison-hint">Chọn 2–3 entity có dữ liệu trong khoảng thời gian đang xem và cùng đơn vị. Tối đa 3 entity.</div></div>
      <div class="entity-picks">${candidates.map(item => `<label class="entity-pick"><input type="checkbox" data-compare="${esc(item.entity_id)}" ${state.comparisonEntities.includes(item.entity_id) ? 'checked' : ''}><span>${esc(item.entity_label)}<small>${esc(item.effective_unit)}</small></span></label>`).join('')}</div>
      ${workspace?.comparison ? `<div class="chart-grid one"><article class="chart-card"><div class="card-top"><h3>So sánh ${esc(state.comparisonMetric)}</h3><span class="pill">Cùng đơn vị</span></div><div class="plot" data-plot="comparison" tabindex="0" aria-label="Biểu đồ so sánh ${esc(state.comparisonMetric)}"></div></article></div>` : state.comparisonEntities.length >= 2 ? statePanel('Không tạo được biểu đồ so sánh', 'Các entity được chọn cần cùng đơn vị và có dữ liệu cho chỉ số, khoảng thời gian hiện tại.') : statePanel('Chưa đủ entity để so sánh', candidates.length < 2 ? 'Không đủ entity có dữ liệu cho chỉ số và khoảng thời gian hiện tại. Hãy đổi bộ lọc.' : 'Chọn thêm entity cùng đơn vị; cần ít nhất 2 và tối đa 3 entity.')}`;
    if (workspace?.comparison) draw('comparison', workspace.comparison, 'comparison');
  } else if (state.tab === 'audit') {
    const audit = workspace?.audit;
    const columns = ['date','entity_path','metric_normalized','raw_value','display_value','chart_value','value_kind','sheet_name','cell_address','validation_status'];
    const focused = auditFocus?.status === 'ready' ? auditFocus.lookup.row : null;
    const focusPanel = !auditFocus ? '' : auditFocus.status === 'loading'
      ? '<section class="audit-focus" aria-busy="true"><strong>Đang mở đúng observation và revision…</strong></section>'
      : auditFocus.status === 'error'
        ? `<section class="audit-focus error"><strong>Không mở được dòng Audit</strong><p>${esc(auditFocus.error)}</p><button class="ghost" data-action="retry-audit-lookup">Thử lại</button><button class="ghost" data-action="return-to-chart">Quay lại biểu đồ</button></section>`
        : `<section class="audit-focus"><div><strong>Dòng Audit của điểm đã chọn</strong><p>Đã mở đúng quan sát và phiên bản nguồn của điểm biểu đồ, kể cả khi dòng này không nằm trong trang Audit hiện tại.</p></div><button class="ghost" data-action="return-to-chart">Quay lại biểu đồ</button><div class="table-wrap"><table><thead><tr>${columns.map(col => `<th>${esc(auditHeaders[col])}</th>`).join('')}</tr></thead><tbody><tr id="focused-audit-row" class="focused-audit-row" tabindex="-1">${columns.map(col => `<td title="${esc(auditCell(col, focused?.[col]))}">${esc(auditCell(col, focused?.[col]))}</td>`).join('')}</tr></tbody></table></div></section>`;
    body.innerHTML = `${focusPanel}<p class="section-desc">Đối chiếu giá trị đã nhập với sheet và ô Excel nguồn · ${fmt(audit?.total || 0)} quan sát theo bộ lọc.</p>
      ${audit?.total ? `<div class="table-wrap"><table><thead><tr>${columns.map(col => `<th>${esc(auditHeaders[col])}</th>`).join('')}</tr></thead><tbody>${audit.rows.map(row => `<tr>${columns.map(col => `<td title="${esc(auditCell(col, row[col]))}">${esc(auditCell(col, row[col]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <div class="pager"><button data-action="audit-prev" ${!audit.offset ? 'disabled' : ''}>← Trước</button><span>${fmt(audit.offset + 1)}–${fmt(Math.min(audit.offset + audit.rows.length, audit.total))} / ${fmt(audit.total)}</span><button data-action="audit-next" ${audit.offset + audit.rows.length >= audit.total ? 'disabled' : ''}>Sau →</button></div>` : statePanel('Không có dòng Audit theo bộ lọc', 'Hãy đổi entity hoặc khoảng thời gian để xem dữ liệu nguồn.')}`;
  } else if (state.tab === 'import') renderImport(body);
  else renderHistory(body);
  restorePendingFocus();
}
function empty(messageText: string): string { return `<div class="empty"><div class="empty-icon">▥</div><h3>${esc(messageText)}</h3><p>Thử đổi project, entity hoặc khoảng thời gian trong sidebar.</p></div>`; }
function draw(key: string, figure: Figure, entityRef: string): void {
  const element = document.querySelector<HTMLElement>(`[data-plot="${key}"]`);
  if (!element) return;
  const selection = investigationSelection();
  const viewport = selection?.origin.plotKey === key ? selection.origin.viewport : undefined;
  const prepared = viewport ? {
    ...figure,
    layout: {
      ...figure.layout,
      xaxis: { ...(figure.layout.xaxis ?? {}), ...(viewport.xRange ? { range: viewport.xRange } : {}) },
      yaxis: { ...((figure.layout.yaxis as Record<string, unknown> | undefined) ?? {}), ...(viewport.yRange ? { range: viewport.yRange } : {}) },
      yaxis2: { ...((figure.layout.yaxis2 as Record<string, unknown> | undefined) ?? {}), ...(viewport.y2Range ? { range: viewport.y2Range } : {}) },
    },
  } : figure;
  renderChart(
    element,
    prepared,
    point => openInvestigation(key, entityRef, point),
    selection?.origin.plotKey === key ? aggregateParent?.selection.aggregateRef || selection.aggregateRef || selection.observationRef || undefined : undefined,
    element.closest('.children-grid') ? 380 : 420,
  );
}
function previewDestination(value: Preview): string {
  return value.manifest.projects?.join(', ') || currentProject()?.label || 'Chưa xác định';
}
function previewDateRange(value: Preview): string {
  const start = value.manifest.observed_date_min;
  const end = value.manifest.observed_date_max;
  if (start && end) return start === end ? dateLabel(start) : `${dateLabel(start)} — ${dateLabel(end)}`;
  return `${fmt(value.manifest.date_count)} ngày dữ liệu`;
}
function importModeGuidance(mode: typeof importMode): { title: string; body: string } {
  return mode === 'full_snapshot'
    ? {
        title: 'Snapshot đầy đủ · cần xác nhận bổ sung',
        body: 'Giá trị trùng khóa trong workbook có thể tạo phiên bản mới, thay phiên bản hiện hành. Giá trị vắng mặt trong file không bị tự động xóa theo chính sách hiện tại.',
      }
    : {
        title: 'Dữ liệu bổ sung · rủi ro thấp hơn',
        body: 'Chỉ giá trị xuất hiện trong workbook được thêm hoặc cập nhật. Dữ liệu hiện có nhưng không xuất hiện trong file vẫn được giữ nguyên.',
      };
}
function validationIssues(value: Preview): string {
  const visible = showAllIssues ? value.issues : value.issues.slice(0, 8);
  if (!visible.length) return `<p class="issue-empty">${value.errorCount + value.warningCount ? 'Có lỗi hoặc cảnh báo, nhưng máy chủ chưa trả chi tiết trong phần xem trước.' : 'Không có lỗi hoặc cảnh báo.'}</p>`;
  const rows = visible.map(issue => `<div class="issue-row"><span class="issue-severity ${issue.severity.toLowerCase()}">${esc(validationLabel(issue.severity.toLowerCase()))}</span><div><strong>${esc(issue.code)}</strong><p>${esc(issue.message)}</p></div></div>`).join('');
  const hidden = value.issues.length - visible.length;
  return `${rows}${hidden > 0 ? `<button class="text-action" data-action="toggle-issues">Xem thêm ${fmt(hidden)} mục kiểm tra</button>` : showAllIssues && value.issues.length > 8 ? '<button class="text-action" data-action="toggle-issues">Thu gọn danh sách</button>' : ''}`;
}
function reportIsTruncated(value: Preview): boolean { return value.issues.length < value.errorCount + value.warningCount; }
function reportDownloadLabel(value: Preview): string { return reportIsTruncated(value) ? 'Tải phần kết quả đã trả về (JSON)' : 'Tải kết quả kiểm tra (JSON)'; }
function importOutcomeCard(result: ImportResult): string {
  const outcome = result.outcome;
  const revisionId = outcome.run_id ?? outcome.duplicate_of_run_id;
  const isCommitted = outcome.status === 'committed';
  const title = isCommitted ? 'Đã nhập workbook' : outcome.status === 'duplicate' ? 'Workbook đã được nhập trước đó' : 'Lần nhập đã kết thúc';
  return `<section id="import-result" class="import-result ${isCommitted ? 'success' : 'neutral'}" role="status" aria-live="polite" aria-atomic="true" tabindex="-1">
    <div class="result-heading"><div><span>Kết quả nhập dữ liệu</span><h3>${esc(title)}</h3><p>${isCommitted ? importPhase === 'committing' ? 'Dữ liệu đã được ghi. Đang tải lại biểu đồ và lịch sử nhập…' : bootstrapError || workspaceError ? 'Dữ liệu đã được ghi. Dashboard chưa tải lại được; thử làm mới khi kết nối ổn định.' : 'Dữ liệu đã được ghi vào kho nội bộ. Biểu đồ đã được tải lại.' : outcome.status === 'duplicate' ? 'Không ghi thêm dữ liệu trùng; bạn có thể xem lần nhập trước trong lịch sử.' : esc(outcome.message || 'Hãy xem lịch sử nhập để kiểm tra kết quả.')}</p></div><strong>${new Date(result.committedAt).toLocaleString('vi-VN')}</strong></div>
    <dl class="outcome-grid">
      <div><dt>Thêm mới</dt><dd>${fmt(outcome.inserted_count)}</dd></div><div><dt>Cập nhật phiên bản</dt><dd>${fmt(outcome.updated_count)}</dd></div>
      <div><dt>Giữ nguyên</dt><dd>${fmt(outcome.unchanged_count)}</dd></div><div><dt>Khôi phục</dt><dd>${fmt(outcome.restored_count)}</dd></div>
      <div><dt>Không còn hiệu lực</dt><dd>${fmt(outcome.deleted_count)}</dd></div><div><dt>Đổi nguồn tham chiếu</dt><dd>${fmt(outcome.lineage_changed_count)}</dd></div>
    </dl>
    <div class="result-context"><span><strong>Workbook:</strong> ${esc(result.fileName)}</span><span><strong>Project:</strong> ${esc(previewDestination(result.preview))}</span><span><strong>Phạm vi:</strong> ${esc(previewDateRange(result.preview))}</span><span><strong>Hash:</strong> <code title="${esc(result.preview.manifest.source_hash)}">${esc(shortHash(result.preview.manifest.source_hash))}</code></span></div>
    <div class="result-actions">
      <button class="primary" data-action="view-revision" ${revisionId ? '' : 'disabled'}>Xem lịch sử nhập</button>
      <button class="ghost" data-action="audit-import">Xem Audit hiện hành</button>
      <button class="ghost" data-action="show-validation">Xem kết quả kiểm tra</button>
      <button class="ghost" data-action="download-validation">${reportDownloadLabel(result.preview)}</button>
    </div>
  </section>`;
}
function renderImport(body: HTMLDivElement): void {
  const busy = importPhase !== 'idle';
  const guidance = importModeGuidance(importMode);
  const report = preview || importResult?.preview || null;
  const commitDisabled = !preview?.valid || busy || (importMode === 'full_snapshot' && !fullSnapshotConfirmed);
  body.innerHTML = `${importResult ? importOutcomeCard(importResult) : ''}
    <div id="import-live-status" class="import-live-status" role="status" aria-live="polite" aria-atomic="true">${importPhase === 'previewing' ? 'Đang đọc workbook và kiểm tra dữ liệu…' : importPhase === 'committing' ? importResult ? 'Đã ghi dữ liệu. Đang tải lại biểu đồ và lịch sử nhập…' : 'Đang ghi dữ liệu và lưu phiên bản… Không đóng tab.' : ''}</div>
    ${importError ? `<div class="import-error" role="alert"><strong>${lastImportAction === 'preview' ? 'Không xem trước được workbook.' : 'Chưa xác nhận được kết quả nhập.'}</strong><p>${esc(importError)}</p><p>${lastImportAction === 'preview' ? 'Kiểm tra file .xlsx rồi thử lại. Chưa có dữ liệu nào được ghi ở bước xem trước.' : 'Hãy xem Lịch sử nhập trước khi thử ghi lại, vì yêu cầu có thể đã được máy chủ xử lý.'}</p><button class="ghost" data-action="${lastImportAction === 'preview' ? 'retry-import' : 'check-import-history'}">${lastImportAction === 'preview' ? 'Thử xem trước lại' : 'Kiểm tra lịch sử nhập'}</button></div>` : ''}
    <div class="import-layout"><div class="upload-card"><div class="upload-symbol" aria-hidden="true">↥</div><h3>Nhập workbook Excel</h3><p>Kiểm tra chất lượng trước khi ghi vào kho dữ liệu. File .xlsx tối đa 50 MB.</p>
      <input id="file-input" type="file" accept=".xlsx" ${busy ? 'disabled' : ''} aria-describedby="file-constraints"/><label class="upload-button" for="file-input">Chọn file Excel</label><p id="file-constraints" class="field-hint">Bước xem trước chỉ đọc file, chưa ghi dữ liệu.</p>
      ${selectedFile ? `<div class="selected-file"><strong>${esc(selectedFile.name)}</strong><span>${fmt(Math.round(selectedFile.size / 1024))} KB</span></div>` : ''}
      <label class="field import-mode"><span>Cách nhập dữ liệu</span><select id="import-mode" ${busy ? 'disabled' : ''}>${select([{value:'incremental',label:'Chỉ dữ liệu bổ sung'},{value:'full_snapshot',label:'Snapshot đầy đủ'}], importMode)}</select></label>
      <div class="mode-guidance ${importMode === 'full_snapshot' ? 'high-risk' : ''}"><strong>${esc(guidance.title)}</strong><p>${esc(guidance.body)}</p></div>
      <button id="preview-action" class="primary wide" data-action="preview" ${selectedFile && !busy ? '' : 'disabled'}>${preview ? 'Kiểm tra lại workbook' : 'Xem trước và kiểm tra'}</button></div>
      <div class="preview-card" aria-busy="${busy}"><h3 id="preview-result-heading" tabindex="-1">Kết quả xem trước</h3>${preview ? `<div class="preview-status ${preview.valid ? 'valid' : 'invalid'}" role="${preview.valid ? 'status' : 'alert'}">${preview.valid ? 'Đạt kiểm tra · có thể xác nhận nhập' : 'Không đạt kiểm tra · chưa ghi dữ liệu'}</div>
      <dl class="preview-identity"><div><dt>Dự án đích</dt><dd>${esc(previewDestination(preview))}</dd></div><div><dt>Workbook</dt><dd>${esc(selectedFile?.name || preview.manifest.source_file)}</dd></div><div><dt>Phạm vi ngày</dt><dd>${esc(previewDateRange(preview))}</dd></div><div><dt>SHA-256 workbook</dt><dd><code title="${esc(preview.manifest.source_hash)}">${esc(shortHash(preview.manifest.source_hash))}</code></dd></div></dl>
      <div class="preview-metrics"><div><strong>${fmt(preview.manifest.record_count)}</strong><span>Quan sát đầu vào</span></div><div><strong>${fmt(preview.manifest.date_count)}</strong><span>Ngày có dữ liệu</span></div><div><strong>${fmt(preview.errorCount)}</strong><span>Lỗi</span></div><div><strong>${fmt(preview.warningCount)}</strong><span>Cảnh báo</span></div></div>
      <section class="impact-summary" aria-labelledby="impact-heading"><div class="subsection-heading"><h4 id="impact-heading">Tác động khi ghi</h4><span>Xác định sau khi xác nhận</span></div><dl><div><dt>Thêm mới</dt><dd>—</dd></div><div><dt>Cập nhật phiên bản</dt><dd>—</dd></div><div><dt>Giữ nguyên</dt><dd>—</dd></div><div><dt>Thay phiên bản</dt><dd>—</dd></div></dl><p>Hệ thống chưa tính được số thay đổi chính xác ở bước xem trước. Kết quả thực tế sẽ hiển thị sau khi nhập.</p></section>
      <section class="revision-behavior"><h4>Cách lưu phiên bản</h4><p>${esc(guidance.body)}</p><p>Thay đổi giá trị được lưu thành phiên bản mới; workbook nguồn và lịch sử nhập vẫn được giữ để đối chiếu.</p></section>
      <section class="validation-report" aria-labelledby="validation-heading"><div class="subsection-heading"><h4 id="validation-heading">Kết quả kiểm tra</h4><button class="text-action" data-action="download-validation">${reportDownloadLabel(preview)}</button></div><div class="issue-list">${validationIssues(preview)}</div>${reportIsTruncated(preview) ? `<p class="issue-limit">Chỉ hiển thị và tải được ${fmt(preview.issues.length)} / ${fmt(preview.errorCount + preview.warningCount)} mục kiểm tra; tổng lỗi và cảnh báo ở trên vẫn đầy đủ.</p>` : ''}</section>
      ${importMode === 'full_snapshot' && preview.valid ? `<label class="snapshot-confirm"><input id="snapshot-confirm" type="checkbox" ${fullSnapshotConfirmed ? 'checked' : ''}><span><strong>Tôi xác nhận nhập snapshot đầy đủ.</strong>Tôi hiểu giá trị trùng khóa có thể tạo phiên bản mới; giá trị vắng mặt trong file không bị tự động xóa theo chính sách hiện tại.</span></label>` : ''}
      <button class="primary wide commit-button" data-action="commit" ${commitDisabled ? 'disabled' : ''}>${importMode === 'full_snapshot' ? 'Xác nhận nhập snapshot' : 'Xác nhận nhập dữ liệu bổ sung'}</button>` : '<div class="preview-placeholder"><p>Chọn workbook rồi xem trước dự án đích, phạm vi ngày, định danh file và kết quả kiểm tra.</p><strong>Chỉ ghi dữ liệu sau khi bạn xác nhận.</strong></div>'}</div></div>
    ${importResult && showAllIssues && report ? `<section id="committed-validation" class="committed-validation" tabindex="-1"><div class="subsection-heading"><h3>Kết quả kiểm tra của workbook vừa nhập</h3><button class="text-action" data-action="download-validation">${reportDownloadLabel(report)}</button></div><div class="issue-list">${validationIssues(report)}</div>${reportIsTruncated(report) ? `<p class="issue-limit">Chỉ có ${fmt(report.issues.length)} / ${fmt(report.errorCount + report.warningCount)} mục chi tiết trong bản xem trước này.</p>` : ''}</section>` : ''}`;
  restorePendingFocus();
}
function renderHistory(body: HTMLDivElement): void {
  if (historyLoading) { body.innerHTML = statePanel('Đang tải lịch sử nhập', 'Đang lấy các lần nhập gần nhất từ kho dữ liệu.'); return; }
  if (historyError) { body.innerHTML = statePanel('Không tải được lịch sử nhập', `${historyError} Dữ liệu đã nhập không bị thay đổi.`, true, 'retry-history'); return; }
  const cols = ['started_at','submitted_file_name','attempt_status','requested_mode','input_record_count','inserted_count','updated_count','unchanged_count'];
  const latestAttempt = importResult?.outcome.attempt_id;
  body.innerHTML = `<p class="section-desc">Tối đa 100 lần nhập gần nhất, gồm lần đã ghi, trùng, không đạt kiểm tra và thất bại.</p>${historyItems.length ? `<div class="table-wrap"><table><thead><tr>${cols.map(col => `<th>${esc(historyHeaders[col])}</th>`).join('')}</tr></thead><tbody>${historyItems.map(item => { const current = Number(item.attempt_id) === latestAttempt; return `<tr ${current ? 'id="latest-import-row" class="current-import" tabindex="-1" aria-current="true"' : ''}>${cols.map(col => `<td title="${esc(historyCell(col, item[col]))}">${esc(historyCell(col, item[col]))}</td>`).join('')}</tr>`; }).join('')}</tbody></table></div>` : statePanel('Chưa có lần nhập nào', 'Sau khi kiểm tra và xác nhận workbook đầu tiên, kết quả sẽ xuất hiện ở đây.')}`;
  restorePendingFocus();
}
function downloadValidationReport(): void {
  const value = preview || importResult?.preview;
  if (!value) return;
  const payload = {
    generated_at: new Date().toISOString(),
    workbook: selectedFile?.name || importResult?.fileName || value.manifest.source_file,
    mode: importResult?.mode || importMode,
    destination_projects: value.manifest.projects || [],
    observed_date_range: { start: value.manifest.observed_date_min || null, end: value.manifest.observed_date_max || null },
    source_hash: value.manifest.source_hash,
    validation: { valid: value.valid, error_count: value.errorCount, warning_count: value.warningCount, issues_returned: value.issues.length, issues_total: value.errorCount + value.warningCount, truncated: reportIsTruncated(value), issues: value.issues },
    import_outcome: importResult?.outcome || null,
  };
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url; link.download = `validation-${value.manifest.source_hash.slice(0, 12)}.json`; link.click();
  URL.revokeObjectURL(url);
}
async function loadEntities(): Promise<void> {
  if (!state.project) { entities = []; return; }
  const response = await api<{ entities: Entity[] }>(`/projects/${encodeURIComponent(state.project)}/entities`);
  entities = response.entities;
  if (!entities.some(entity => entity.entity_id === state.entity)) state.entity = '';
}
async function loadWorkspace(): Promise<void> {
  request?.abort();
  workspaceError = '';
  if (!state.project) { workspace = null; renderSidebar(); renderMain(); return; }
  const current = new AbortController(); request = current;
  loading = true; renderSidebar(); renderMain();
  const params = new URLSearchParams({
    mode: state.mode, count: String(state.count), scope: state.scope,
    statistics_group: state.statisticsGroup, statistics_mode: state.statisticsMode,
    statistics_count: String(state.statisticsRange === 'all' ? 3660 : state.statisticsCount),
    include_incomplete: String(state.includeIncomplete), comparison_metric: state.comparisonMetric,
    comparison_entities: state.comparisonEntities.join(','), audit_offset: String(state.auditOffset),
  });
  if (state.mode === 'custom' && state.start && state.end) { params.set('start', state.start); params.set('end', state.end); }
  if (state.entity) params.set('entity', state.entity);
  if (state.statisticsRange === 'custom') {
    if (state.statisticsFrom) params.set('statistics_from', state.statisticsFrom);
    if (state.statisticsTo) params.set('statistics_to', state.statisticsTo);
  }
  try {
    workspace = await api<Workspace>(`/projects/${encodeURIComponent(state.project)}/workspace?${params}`, { signal: current.signal });
    if (current !== request) return;
    state.entity = workspace.selectedEntity;
    loading = false; workspaceError = ''; message = ''; save(); renderSidebar(); renderMain();
  } catch (error) {
    if (current.signal.aborted) return;
    loading = false; workspace = null; workspaceError = (error as Error).message; renderSidebar(); renderMain();
  }
}
async function refreshProject(): Promise<void> {
  workspace = null;
  try { await loadEntities(); await loadWorkspace(); }
  catch (error) { workspaceError = (error as Error).message; renderMain(); }
}
async function refreshHistory(): Promise<void> {
  historyError = ''; historyLoading = true; if (state.tab === 'history') renderTab();
  try { historyItems = (await api<{items: Record<string, unknown>[]}>('/imports')).items; }
  catch (error) { historyError = (error as Error).message; }
  historyLoading = false; if (state.tab === 'history') renderTab();
}
app.addEventListener('change', event => {
  const target = event.target as HTMLInputElement | HTMLSelectElement;
  if (target.id === 'file-input' && target instanceof HTMLInputElement) {
    selectedFile = target.files?.[0] || null; preview = null; importResult = null; importError = '';
    fullSnapshotConfirmed = false; showAllIssues = false; pendingFocusId = selectedFile ? 'preview-action' : 'file-input'; renderTab(); return;
  }
  if (target.id === 'import-mode') { importMode = target.value as typeof importMode; fullSnapshotConfirmed = false; pendingFocusId = 'import-mode'; renderTab(); return; }
  if (target.id === 'snapshot-confirm' && target instanceof HTMLInputElement) { fullSnapshotConfirmed = target.checked; pendingFocusId = 'snapshot-confirm'; renderTab(); return; }
  if (target.dataset.compare) {
    const id = target.dataset.compare;
    const selected = new Set(state.comparisonEntities);
    if (target instanceof HTMLInputElement && target.checked) selected.add(id); else selected.delete(id);
    if (selected.size > 3) { message = 'Chỉ được chọn tối đa 3 entity.'; if (target instanceof HTMLInputElement) target.checked = false; renderMain(); return; }
    state.comparisonEntities = [...selected]; save(); void loadWorkspace(); return;
  }
  const field = target.dataset.field as keyof State | undefined;
  if (!field) return;
  const value: string | number | boolean = target instanceof HTMLInputElement && target.type === 'checkbox' ? target.checked : target.type === 'number' ? Number(target.value) : target.value;
  (state as unknown as Record<string, string | number | boolean>)[field] = value;
  if (field === 'project') {
    state.entity = ''; state.comparisonEntities = []; state.start = ''; state.end = '';
    investigationRequest?.abort(); investigation = { status: 'closed' }; auditFocus = null; renderInvestigation();
  }
  if (field === 'comparisonMetric') state.comparisonEntities = [];
  if (field === 'mode') { state.count = state.mode === 'month' ? 6 : 8; const p = currentProject(); state.start = p?.minDate || ''; state.end = p?.maxDate || ''; }
  if (field === 'entity') state.scope = 'node';
  if (field !== 'auditOffset') state.auditOffset = 0;
  save();
  if (field === 'project') void refreshProject(); else void loadWorkspace();
});
app.addEventListener('click', event => {
  const element = (event.target as HTMLElement).closest<HTMLElement>('[data-tab], [data-action]');
  if (!element) return;
  if (element.dataset.action === 'toggle-sidebar') {
    sidebarCollapsed = !sidebarCollapsed;
    app.querySelector('.shell')?.classList.toggle('sidebar-collapsed', sidebarCollapsed);
    try { sessionStorage.setItem(SIDEBAR_KEY, sidebarCollapsed ? '1' : '0'); } catch { /* Optional UI preference. */ }
    window.dispatchEvent(new Event('resize'));
    return;
  }
  if (element.dataset.tab) { state.tab = element.dataset.tab as Tab; save(); renderMain(); if (state.tab === 'history') void refreshHistory(); return; }
  const action = element.dataset.action;
  if (action === 'close-investigation') {
    const selection = investigationSelection();
    investigationRequest?.abort(); investigation = { status: 'closed' }; aggregateParent = null; revisionHistory = null; importDetail = null; investigationLiveMessage = '';
    if (selection) {
      const plot = document.querySelector<HTMLElement>(`[data-plot="${selection.origin.plotKey}"]`);
      if (plot) { clearChartSelection(plot); requestAnimationFrame(() => plot.focus()); }
    }
    renderInvestigation(); return;
  }
  if (action === 'retry-provenance') {
    const selection = investigationSelection(); if (selection) void loadProvenance(selection); return;
  }
  if (action === 'load-contributors') { void loadMoreContributors(); return; }
  if (action === 'open-contributor' && investigation.status === 'aggregate-ready') {
    const item = investigation.contributors[Number(element.dataset.index)];
    if (!item) return;
    aggregateParent = investigation; revisionHistory = null; importDetail = null;
    void loadProvenance({ kind: 'exact-observation', aggregateRef: null, observationRef: item.observationRef, lineageRef: item.lineageRef, origin: investigation.selection.origin });
    return;
  }
  if (action === 'back-to-aggregate' && aggregateParent) {
    investigationRequest?.abort(); investigation = aggregateParent; aggregateParent = null; revisionHistory = null; importDetail = null;
    if (state.tab !== investigation.selection.origin.tab) {
      state.tab = investigation.selection.origin.tab; auditFocus = null; save(); renderMain();
    }
    investigationLiveMessage = 'Đã quay lại điểm tổng hợp.'; renderInvestigation(); return;
  }
  if (action === 'show-revisions') { void loadRevisions(); return; }
  if (action === 'show-import' && element.dataset.importRef) { void loadImport(element.dataset.importRef); return; }
  if (action === 'check-import-history') { state.tab = 'history'; save(); renderMain(); void refreshHistory(); return; }
  if (action === 'copy-cell') { void copyInvestigationValue('cell'); return; }
  if (action === 'copy-value') { void copyInvestigationValue('value'); return; }
  if (action === 'open-exact-audit') {
    const selection = investigationSelection(); if (selection) void loadAuditLookup(selection); return;
  }
  if (action === 'return-to-chart') { returnToChart(); return; }
  if (action === 'retry-audit-lookup') { if (auditFocus) void loadAuditLookup(auditFocus.selection); return; }
  if (action === 'refresh') { void bootstrap(); return; }
  if (action === 'retry-history') { void refreshHistory(); return; }
  if (action === 'audit-prev' || action === 'audit-next') {
    state.auditOffset = Math.max(0, state.auditOffset + (action === 'audit-next' ? 100 : -100)); save(); void loadWorkspace(); return;
  }
  if (action === 'toggle-issues') { showAllIssues = !showAllIssues; pendingFocusId = 'validation-heading'; renderTab(); return; }
  if (action === 'download-validation') { downloadValidationReport(); return; }
  if (action === 'show-validation') { showAllIssues = true; pendingFocusId = 'committed-validation'; renderTab(); return; }
  if (action === 'view-revision') {
    state.tab = 'history'; save(); renderMain();
    void refreshHistory().then(() => { pendingFocusId = 'latest-import-row'; renderTab(); }); return;
  }
  if (action === 'audit-import') {
    state.tab = 'audit'; state.auditOffset = 0; save();
    const runId = importResult?.outcome.run_id ?? importResult?.outcome.duplicate_of_run_id;
    message = runId ? 'Audit hiển thị các quan sát hiện hành sau lần nhập; đây không phải danh sách thay đổi riêng của lần đó.' : 'Audit hiển thị các quan sát hiện hành, không phải danh sách thay đổi riêng của lần nhập.';
    pendingFocusId = 'tab-body'; renderMain(); return;
  }
  if (action === 'retry-import') {
    if (lastImportAction === 'commit' && preview?.valid) void commitFile(); else if (selectedFile) void previewFile();
    return;
  }
  if (action === 'preview' && selectedFile) void previewFile();
  if (action === 'commit' && selectedFile && preview?.valid && (importMode !== 'full_snapshot' || fullSnapshotConfirmed)) void commitFile();
});
app.addEventListener('keydown', event => {
  if (event.key === 'Escape' && investigation.status !== 'closed') {
    event.preventDefault();
    app.querySelector<HTMLButtonElement>('#investigation-drawer [data-action="close-investigation"]')?.click();
  }
});
async function previewFile(): Promise<void> {
  if (!selectedFile || importPhase !== 'idle') return;
  const form = new FormData(); form.append('file', selectedFile);
  lastImportAction = 'preview'; importPhase = 'previewing'; importError = ''; importResult = null;
  fullSnapshotConfirmed = false; showAllIssues = false; renderMain();
  try { preview = await api<Preview>('/imports/preview', { method: 'POST', body: form }); }
  catch (error) { preview = null; importError = (error as Error).message; }
  importPhase = 'idle'; pendingFocusId = preview ? 'preview-result-heading' : '';
  renderMain();
}
async function commitFile(): Promise<void> {
  if (!selectedFile || !preview?.valid || importPhase !== 'idle') return;
  if (importMode === 'full_snapshot' && !fullSnapshotConfirmed) return;
  const committedFile = selectedFile;
  const committedPreview = preview;
  const committedMode = importMode;
  const form = new FormData(); form.append('file', selectedFile); form.append('mode', importMode); form.append('expected_hash', preview.manifest.source_hash);
  lastImportAction = 'commit'; importPhase = 'committing'; importError = ''; renderMain();
  try {
    const result = await api<ImportOutcome>('/imports', { method: 'POST', body: form });
    importResult = { outcome: result, preview: committedPreview, fileName: committedFile.name, fileSize: committedFile.size, mode: committedMode, committedAt: new Date().toISOString() };
    preview = null; selectedFile = null;
    await bootstrap(); await refreshHistory();
    importPhase = 'idle'; fullSnapshotConfirmed = false; showAllIssues = false; pendingFocusId = 'import-result'; renderMain();
  } catch (error) {
    importPhase = 'idle'; importError = (error as Error).message; pendingFocusId = 'preview-result-heading'; renderMain();
  }
}
async function bootstrap(): Promise<void> {
  bootstrapError = '';
  try {
    projects = (await api<{projects:Project[]}>('/bootstrap')).projects;
    bootstrapLoaded = true;
    if (!projects.some(project => project.label === state.project)) state.project = projects[0]?.label || '';
    const p = currentProject();
    if (!state.start) state.start = p?.minDate || '';
    if (!state.end) state.end = p?.maxDate || '';
    save(); await refreshProject();
  } catch (error) { bootstrapLoaded = true; bootstrapError = (error as Error).message; renderSidebar(); renderMain(); }
}
renderShell(); renderSidebar(); renderMain(); void bootstrap();
