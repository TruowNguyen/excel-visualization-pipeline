import './style.css';
import { clearChartSelection, purgeChart, renderChart, selectChartPoint } from './chart';
import { entityCardTitle, entityTrail } from './presentation';
import {
  getChildrenScopeLabel,
  getComparisonButtonDescription,
  getComparisonTerminology,
  getCurrentScopeLabel,
  getEligibilityReasonMessage,
  getEntityDisplayName,
  getEntityLevelLabel,
  getMetricDisplayLabel,
  formatMetricText,
  metricPresentation,
} from './terminology';
import type { ChartPointSelection, Entity, Figure } from './types';
import {
  beginWorkspaceTrace,
  finishWorkspaceTrace,
  noteWorkspaceInteraction,
  recordFingerprint,
  scheduleFeedbackPaint,
  type WorkspacePerformanceTrace,
} from './workspace-performance';

type Project = { label: string; records: number; chartable: number; entities: number; units: number; minDate: string | null; maxDate: string | null };
type Chart = { entityId: string; title: string; figure: Figure };
type AuditRow = Record<string, string | number | null>;
type DataVersion = { committedImportRef: string; committedAt: string } | null;
type ComparisonCandidate = {
  entity_id: string; entity_label: string; effective_unit: string | null;
  eligible?: boolean; reason?: string | null; comparablePeriodCount?: number;
};
type ComparisonContext = {
  anchor: { entityId: string; entityLabel: string; parentEntityId: string | null; effectiveUnit: string | null };
  lens?: 'metric' | 'statistics'; metric: string | null; metrics?: string[];
  calculation: 'sum' | 'weighted_rate' | 'average_per_day'; grain: 'day' | 'week' | 'month' | 'quarter';
  range: { start: string | null; end: string | null };
  anchorEligible: boolean; anchorReason: string | null;
};
type Workspace = {
  dataVersion: DataVersion;
  window: { start: string; end: string };
  selectedEntity: string;
  scopeIds: string[];
  overview: Chart[];
  statistics: Chart[];
  statisticsPeriods: { start: string; label: string; complete: boolean }[];
  comparisonCandidates: ComparisonCandidate[];
  comparison: Figure | null;
  comparisonContext?: ComparisonContext | null;
  comparisonSelection?: { accepted: string[]; removed: { entityId: string; reason: string }[]; limit: number } | null;
  audit: { total: number; offset: number; rows: AuditRow[] };
  capabilities?: { lineage?: { contractVersion: number; exactObservation: boolean; aggregateObservation: boolean } };
};
type ContextualComparison = {
  anchorId: string; sourceButtonId: string; sourceScrollY: number;
  sourceDataVersion: DataVersion; latestDataVersion: DataVersion;
  lens: 'metric' | 'statistics'; calculation: 'sum' | 'average_per_day';
  metric: string | null; selected: string[];
  status: 'choosing' | 'loading' | 'ready' | 'error' | 'stale';
  response: Workspace | null; error: string; notice: string;
};
type AIStatus = {
  enabled: boolean; configured: boolean; externalAllowed: boolean;
  provider: string; model: string; availability: string; privacyMode: string;
};
type AIEvidence = {
  evidenceId: string; period: 'series'; periodIndex: number; periodStart: string; periodEnd: string;
  periodLabel: string; observedDate: string;
  target: { kind: 'exact'; observationRef: string; lineageRef: string }
    | { kind: 'aggregate'; aggregateRef: string };
};
type AIFact = {
  factId: string; kind: string; value: number | string; unit: string;
  displayValue: string; evidenceIds: string[];
};
type AISeriesPoint = {
  periodStart: string; periodEnd: string; periodLabel: string;
  value: number; displayValue: string; observedDayCount: number; expectedDayCount: number;
  coverageRatio: number; evidenceId: string; factId: string;
  change: null | {
    fromPeriodStart: string; absolute: number; absoluteDisplay: string;
    relativePercent: number | null; relativeDisplay: string;
    direction: 'increasing' | 'decreasing' | 'unchanged'; factIds: string[];
  };
};
type AIPeriodHighlight = {
  periodStart: string; periodEnd: string; periodLabel: string;
  value: number; displayValue: string; coverageRatio: number; factIds: string[];
};
type AIChangeHighlight = {
  fromPeriodStart: string; fromPeriodLabel: string; fromValue: number; fromDisplayValue: string;
  toPeriodStart: string; toPeriodLabel: string; toValue: number; toDisplayValue: string;
  absolute: number; absoluteDisplay: string; relativePercent: number | null;
  relativeDisplay: string; direction: 'increasing' | 'decreasing' | 'unchanged'; factIds: string[];
};
type AISequenceHighlight = {
  transitionCount: number; startPeriodLabel: string; endPeriodLabel: string;
  values: number[]; displayValues: string[]; periodLabels: string[]; factIds: string[];
};
type AIPeriodAnalytics = {
  temporalStructure?: {
    overviewText: string; summaryText: string;
    stages: { startIndex: number; endIndex: number; direction: string; text: string; startPeriodLabel: string; endPeriodLabel: string; factIds: string[]; evidenceIds: string[] }[];
    turningPoints: { text: string; periodLabel: string; factIds: string[]; evidenceIds: string[] }[];
    gaps: { startIndex: number; text: string; afterPeriodLabel: string; beforePeriodLabel: string }[];
  };
  policyVersion: string; tieBreak: string;
  peak: AIPeriodHighlight | null; lowest: AIPeriodHighlight | null;
  largestIncrease: AIChangeHighlight | null; largestDecrease: AIChangeHighlight | null;
  consecutiveIncrease: AISequenceHighlight | null; consecutiveDecrease: AISequenceHighlight | null;
  endingPlateau: AISequenceHighlight | null; latestChange: AIChangeHighlight | null;
};
type AIHistoricalContext = {
  status: 'available' | 'unavailable'; policyVersion: string; lookbackPeriodLimit: number;
  observedPeriodCount: number;
  currentPosition: null | { value: 'above_historical_range' | 'below_historical_range' | 'within_historical_range' | 'matches_historical_range'; currentPeriodLabel: string; factIds: string[] };
};
type AIOverviewMetric = {
  metricCode: 'total' | 'error' | 'error_rate'; metricDisplayName: string;
  status: 'ready' | 'insufficient_data'; unit: string; aggregationRule: string;
  facts: AIFact[]; series: AISeriesPoint[]; periodAnalytics: AIPeriodAnalytics;
  historicalContext: AIHistoricalContext;
  quality: { validPeriodCount: number; expectedPeriodCount: number; limitations: string[] };
  evidence: AIEvidence[];
};
type AIAnalysis = {
  schemaVersion: string; analysisId: string; kind: 'trend' | 'metric_overview';
  status: 'ready' | 'insufficient_data' | 'provider_unavailable' | 'rejected_output' | 'stale';
  scope: { project: string; entityRef: string; entityLabel: string; mode: 'node'; metricCode: string; metricDisplayName: string };
  window: { start: string; end: string; groupBy: 'day' | 'week' | 'month'; comparisonBasis: string; previousDate: string | null; currentDate: string | null };
  dataAsOf: { committedImportRef: string; snapshotId: string; generatedAt: string; stale: boolean; checksum: string };
  metric?: { unit: string; aggregationRule: string };
  facts: AIFact[];
  series?: AISeriesPoint[];
  metrics?: AIOverviewMetric[];
  periodAnalytics?: AIPeriodAnalytics;
  historicalContext?: AIHistoricalContext;
  comparisonBasis?: {
    status: 'comparable' | 'limited' | 'unavailable'; reason: string;
    baseline: null | { periodLabel: string; numeratorDisplay: string; denominatorDisplay: string; rateDisplay: string; eligibleDayCount: number; expectedDayCount: number };
    current: null | { periodLabel: string; numeratorDisplay: string; denominatorDisplay: string; rateDisplay: string; eligibleDayCount: number; expectedDayCount: number };
  };
  insightCandidates?: { candidateId: string; layer: string; text: string; factIds: string[]; evidenceIds: string[] }[];
  inspectionChecks?: { checkId: string; text: string; factIds: string[]; evidenceIds: string[] }[];
  synthesis?: {
    reading?: { overview: { text: string; factIds: string[] } | null; phases: { start: string; end: string; startLabel: string; endLabel: string; text: string; explanation: string; factIds: string[]; evidenceIds: string[] }[]; takeaways: { text: string; candidateId: string; factIds: string[] }[] };
    policyVersion: string; selectedCandidateIds: string[];
    candidates: { candidateId: string; kind: string; anchors: { metricDisplayName: string; periodLabel: string; displayValue: string; factId: string; evidenceId: string }[] }[];
  };
  quality: { status: string; validPointCount: number; validPeriodCount: number; expectedPeriodCount: number; expectedCalendarDayCount: number; coverageRatio: number; limitations: string[] };
  evidence: AIEvidence[];
  provider: { name: string; model: string; latencyMs?: number | null; attemptCount?: number };
  validation: { status: string; errors: string[]; categories?: string[]; claimResults?: { index: number; candidateId: string; status: string; errors: string[] }[] };
  narrative: {
    mode: 'ai' | 'deterministic';
    schemaVersion?: string;
    summary: { text: string; factIds: string[]; claimType: string; candidateIds?: string[] };
    insights: { type: string; text: string; factIds: string[]; claimType: string }[];
    limitations: string[]; suggestedChecks: string[];
    report?: {
      policyVersion: string;
      overview: AIReportItem[]; phases: AIReportItem[]; relationships: AIReportItem[];
      omittedPhaseCount: number;
    };
  };
};
type AIReportItem = {
  candidateId: string; text: string; factIds: string[]; source: 'ai' | 'deterministic';
  startLabel?: string; endLabel?: string; metricDisplayName?: string;
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
  aiMetricCode: 'all' | 'total' | 'error' | 'error_rate';
  aiGroupBy: 'day' | 'week' | 'month';
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
const CONTEXTUAL_LENS_KEY = 'excel_visualization_pipeline.contextual_lens.v1';
const tabDefinitions: { key: Tab; icon: string; label: string }[] = [
  { key: 'overview', icon: '◫', label: 'Tổng quan' },
  { key: 'statistics', icon: '▥', label: 'Thống kê' },
  { key: 'comparison', icon: '⇄', label: 'So sánh' },
  { key: 'audit', icon: '▤', label: 'Đối chiếu dữ liệu' },
  { key: 'import', icon: '↥', label: 'Nhập Excel' },
  { key: 'history', icon: '◷', label: 'Lịch sử nhập' },
];
const visibleTabs = tabDefinitions.filter(tab => tab.key !== 'comparison' && tab.key !== 'audit');
const defaults: State = {
  project: '', mode: 'recent', count: 8, start: '', end: '', entity: '', scope: 'node',
  statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
  statisticsFrom: '', statisticsTo: '', includeIncomplete: true,
  comparisonMetric: 'Báo sai/Lỗi', comparisonEntities: [], auditOffset: 0, tab: 'overview',
  aiMetricCode: 'all',
  aiGroupBy: 'day',
};
let state: State = { ...defaults };
try { state = { ...defaults, ...JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}') }; } catch { /* Browser storage may be disabled. */ }
// Hai workspace cũ chỉ còn là luồng nội bộ. Không khôi phục chúng như tab cấp cao
// từ session trước; Đối chiếu vẫn được mở đúng ngữ cảnh qua bảng Điều tra.
if (state.tab === 'comparison' || state.tab === 'audit') state.tab = 'statistics';
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
let workspaceProject = '';
let workspaceView: 'overview' | 'statistics' | 'comparison' | 'audit' | '' = '';
let displayedFilterLabel = '';
let lastWorkspaceRequestKey = '';
let historyError = '';
let request: AbortController | null = null;
let investigationRequest: AbortController | null = null;
let investigation: InvestigationState = { status: 'closed' };
let auditFocus: AuditFocus | null = null;
let investigationLiveMessage = '';
let aggregateParent: Extract<InvestigationState, { status: 'aggregate-ready' }> | null = null;
let revisionHistory: { status: 'loading' | 'ready' | 'error'; observationRef: string; data?: RevisionHistory; error?: string } | null = null;
let importDetail: { status: 'loading' | 'ready' | 'error'; importRef: string; data?: ImportRun; error?: string } | null = null;
let aiStatus: AIStatus | null = null;
let aiStatusError = '';
let aiAnalysis: AIAnalysis | null = null;
let aiAnalysisError = '';
let aiLoading = false;
let aiLocallyStale = false;
let aiRequest: AbortController | null = null;
let contextualComparison: ContextualComparison | null = null;
let contextualComparisonRequest: AbortController | null = null;
let contextualFocusId = '';
const chartFingerprints = new Map<string, string>();
let pendingChartRenders: Promise<void>[] = [];
let renderingWorkspaceTrace: WorkspacePerformanceTrace | null = null;
const app = document.querySelector<HTMLDivElement>('#app')!;
const SIDEBAR_KEY = 'excel_visualization_pipeline.sidebar_collapsed.v1';
let sidebarCollapsed = false;
try { sidebarCollapsed = sessionStorage.getItem(SIDEBAR_KEY) === '1'; } catch { /* Optional UI preference. */ }

const esc = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!);
const escMetric = (value: unknown): string => esc(formatMetricText(String(value ?? '')));
const fmt = (value: number): string => new Intl.NumberFormat('vi-VN').format(value);
const dateLabel = (value: string): string => value ? (/^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`).toLocaleDateString('vi-VN') : value) : '—';
const shortHash = (value: string): string => value.length > 24 ? `${value.slice(0, 12)}…${value.slice(-8)}` : value;
const save = () => { try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* Continue without persistence. */ } };
function restorePendingFocus(): void {
  if (!pendingFocusId) return;
  const id = pendingFocusId; pendingFocusId = '';
  requestAnimationFrame(() => document.getElementById(id)?.focus());
}
async function api<T>(path: string, init?: RequestInit, trace?: WorkspacePerformanceTrace): Promise<T> {
  if (trace) trace.requestDispatchedAt = performance.now();
  const response = await fetch(`/api${path}`, init);
  if (trace) {
    trace.responseHeadersAt = performance.now();
    trace.backendTiming = response.headers.get('Server-Timing') || undefined;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const detailMessage = typeof detail === 'object' && detail && typeof detail.message === 'string' ? detail.message : null;
    throw new Error(typeof detail === 'string' ? detail : detailMessage || `Máy chủ trả về lỗi ${response.status}`);
  }
  if (!trace) return response.json() as Promise<T>;
  const body = await response.text();
  trace.responseBodyAt = performance.now();
  const parseStarted = performance.now();
  const result = JSON.parse(body) as T;
  trace.jsonParseMs = performance.now() - parseStarted;
  trace.dataReadyAt = performance.now();
  return result;
}
function select(options: { value: string; label: string }[], current: string): string {
  return options.map(option => `<option value="${esc(option.value)}" ${option.value === current ? 'selected' : ''}>${esc(getMetricDisplayLabel(option.label))}</option>`).join('');
}
function currentProject(): Project | undefined { return projects.find(project => project.label === state.project); }
function currentEntity(): Entity | undefined { return entities.find(entity => entity.entity_id === state.entity); }
function displayEntityName(entity: Entity | undefined, fallback = ''): string {
  return entity ? getEntityDisplayName(entity) : fallback;
}
function displayEntityPath(entityId: string): string {
  return entityTrail(entities, entityId).map(getEntityDisplayName).join(' / ');
}
function displayRawEntityPath(rawPath: unknown): string {
  const raw = String(rawPath ?? '');
  const matching = entities.find(entity => entity.entity_path === raw);
  return matching ? displayEntityPath(matching.entity_id) : raw;
}
function displayHierarchyParts(parts: string[]): string[] {
  return parts.map(part => {
    const matching = entities.find(entity => entity.entity_label === part);
    return matching ? getEntityDisplayName(matching) : part;
  });
}
function renderShell(): void {
  app.innerHTML = `<div class="shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">CX</div><div class="brand-copy"><strong>Báo cáo CX tự động</strong><span>Không gian phân tích</span></div><button class="sidebar-toggle" data-action="toggle-sidebar" aria-label="Thu gọn hoặc mở thanh bên" title="Thu gọn hoặc mở thanh bên">☰</button></div>
      <div class="side-scroll"><div id="side-filters"></div></div>
    <div class="side-bottom"><span class="status-dot"></span><span class="status-copy">Kho dữ liệu nội bộ</span> <small>v1.0 · Nội bộ</small></div>
    </aside>
    <div class="main-column"><header class="topbar"><div class="breadcrumb">Không gian làm việc <span aria-hidden="true">/</span> <strong>Phân tích</strong></div><div class="top-actions"><span class="environment">NỘI BỘ</span><div class="avatar">CX</div></div></header>
    <main class="workspace"><div id="workspace"></div></main></div>
    <aside id="investigation-drawer" class="investigation-drawer" aria-hidden="true"></aside>
    <div id="contextual-comparison-root"></div>
  </div>`;
}
function renderSidebar(): void {
  const root = document.querySelector<HTMLDivElement>('#side-filters')!;
  const activeField = document.activeElement instanceof HTMLElement ? document.activeElement.dataset.field : undefined;
  const project = currentProject();
  const selectedEntity = currentEntity();
  const selectedLevel = selectedEntity?.entity_level;
  root.innerHTML = `<div class="side-heading">Bộ lọc báo cáo</div>
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
    <div class="side-section">
      <label class="field"><span>Nội dung theo dõi</span><select data-field="entity">${select(entities.map(e => ({ value: e.entity_id, label: `${'　'.repeat(e.entity_depth)}${getEntityDisplayName(e)}${e.effective_unit ? ` · ${e.effective_unit}` : ''}` })), state.entity)}</select></label>
      <label class="field"><span>Mức hiển thị</span><select data-field="scope">${select([{ value: 'node', label: getCurrentScopeLabel(selectedLevel) }, { value: 'children', label: getChildrenScopeLabel(selectedLevel) }], state.scope)}</select></label>
    </div>
    <div class="side-tip"><span>✦</span><strong>Bộ lọc được giữ khi tải lại trang</strong><p>Thiết lập chỉ lưu trong thẻ trình duyệt này, không xuất hiện trên đường dẫn.</p></div>`;
  if (activeField) requestAnimationFrame(() => root.querySelector<HTMLElement>(`[data-field="${activeField}"]`)?.focus());
}
function header(title: string, subtitle: string): string {
  return `<div class="page-head"><div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="head-actions"><button class="ghost" data-action="refresh">↻ Làm mới dữ liệu</button>${state.project ? `<a class="primary" href="/api/projects/${encodeURIComponent(state.project)}/export.csv">↓ Tải dữ liệu (.csv)</a>` : ''}</div></div>`;
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
  date: 'Ngày', entity_path: 'Dự án / Nhóm vấn đề / Vấn đề', metric_normalized: 'Chỉ số',
  raw_value: 'Giá trị gốc trong Excel', display_value: 'Giá trị hiển thị',
  chart_value: 'Giá trị trên biểu đồ', value_kind: 'Tình trạng dữ liệu',
  sheet_name: 'Trang tính nguồn', cell_address: 'Ô nguồn', validation_status: 'Kiểm tra',
};
const valueKinds: Record<string, string> = {
  numeric: 'Số', number: 'Số', source_marker: 'Ký hiệu từ tệp Excel', not_recorded: 'Chưa ghi nhận',
  default_zero_rate: 'Tỷ lệ 0% mặc định', blank: 'Ô trống', text: 'Văn bản',
};
function auditCell(column: string, value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  if (column === 'date' && typeof value === 'string') return dateLabel(value.slice(0, 10));
  if (column === 'entity_path') return displayRawEntityPath(value);
  if (column === 'metric_normalized') return getMetricDisplayLabel(String(value));
  if (column === 'validation_status') return validationLabel(String(value));
  if (column === 'value_kind') return valueKinds[String(value)] || String(value);
  return String(value);
}
const historyHeaders: Record<string, string> = {
  attempt_status: 'Kết quả', submitted_file_name: 'Tệp Excel', requested_mode: 'Chế độ',
  input_record_count: 'Điểm dữ liệu trong tệp', inserted_count: 'Thêm mới', updated_count: 'Cập nhật',
  unchanged_count: 'Giữ nguyên', started_at: 'Bắt đầu lúc',
};
const importStatuses: Record<string, string> = {
  committed: 'Đã ghi', duplicate: 'Đã có trước đó', rejected: 'Không đạt kiểm tra', failed: 'Thất bại',
};
function historyCell(column: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (column === 'attempt_status') return importStatuses[String(value)] || String(value);
  if (column === 'requested_mode') return value === 'full_snapshot' ? 'Bản chụp đầy đủ' : value === 'incremental' ? 'Dữ liệu bổ sung' : String(value);
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
  const roleLabel: Record<string, string> = { value: 'Giá trị', numerator: 'Tử số', denominator: 'Mẫu số', coverage: 'Ngày hợp lệ', excluded_marker: 'Ký hiệu từ tệp Excel', missing: 'Thiếu giá trị' };
  return `<div class="drawer-body">
    ${p.freshness.newerDataAvailable ? '<div class="lineage-banner">Đã có lần nhập dữ liệu mới hơn sau bản dữ liệu này. Giá trị tổng hợp đang xem vẫn giữ nguyên; hãy tải lại không gian phân tích để đối chiếu.</div>' : ''}
    <section class="provenance-context"><div class="entity-path">${displayHierarchyParts(p.context.entity.hierarchyPath).map(esc).join('<span>›</span>')}</div><dl><div><dt>Dự án</dt><dd>${esc(p.context.project)}</dd></div><div><dt>Đơn vị đo</dt><dd>${esc(p.context.entity.effectiveUnit || '—')}</dd></div><div><dt>Khoảng thời gian</dt><dd>${dateLabel(p.context.period.start)} – ${dateLabel(p.context.period.end)}</dd></div></dl></section>
    <section><h3>Cách tính</h3><p>${escMetric(p.aggregation.explanation)}</p><dl class="provenance-grid compact"><div><dt>Giá trị tổng hợp</dt><dd>${esc(p.result.displayValue)}</dd></div><div><dt>Số giá trị được dùng</dt><dd>${fmt(p.aggregation.valueObservationCount)}</dd></div><div><dt>Điểm dữ liệu xác định ngày hợp lệ</dt><dd>${fmt(p.aggregation.coverageObservationCount)}</dd></div>${p.aggregation.eligibleDayCount !== null ? `<div><dt>Ngày hợp lệ</dt><dd>${fmt(p.aggregation.eligibleDayCount)}</dd></div>` : ''}${p.aggregation.inferredZero ? '<div class="wide-row"><dt>Lưu ý</dt><dd>Giá trị 0 được suy ra theo quy tắc biểu đồ; không có ô Excel chứa giá trị 0 tương ứng.</dd></div>' : ''}</dl></section>
    <section><h3>Dữ liệu dùng để tính <span class="muted-copy">${fmt(contributors.length)}/${fmt(p.contributors.total)}</span></h3><p class="muted-copy">Điểm tổng hợp không tương ứng với một ô Excel. Chọn một điểm dữ liệu để xem nguồn chính xác.</p>
    <div class="contributor-list">${contributors.map((item, index) => `<button class="contributor-item" data-action="open-contributor" data-index="${index}"><span><strong>${esc(displayEntityName(entities.find(entity => entity.entity_label === item.entityLabel), item.entityLabel))} · ${escMetric(item.metric)}</strong><small>${dateLabel(item.date)} · ${esc(roleLabel[item.role] || item.role)}${item.included ? '' : ' · không đưa vào phép tính'}</small></span><span>${esc(item.displayValue)} ›</span></button>`).join('') || '<p>Không có điểm dữ liệu nào được lưu cho điểm này.</p>'}</div>
    ${nextCursor ? `<button class="ghost" data-action="load-contributors" ${pageStatus === 'loading' ? 'disabled' : ''}>${pageStatus === 'loading' ? 'Đang tải…' : 'Xem thêm'}</button>` : ''}${pageStatus === 'error' ? '<p class="lineage-error">Không tải được trang tiếp theo. Bạn có thể thử lại.</p>' : ''}
    </section><section><h3>Thời điểm dữ liệu</h3><p>Đến ngày ${esc(p.freshness.observedThrough ? dateLabel(p.freshness.observedThrough) : '—')} · Lưu phiên bản lúc ${esc(new Date(p.freshness.snapshotCreatedAt).toLocaleString('vi-VN'))}</p></section>
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
  return `<section><h3>Lần nhập dữ liệu</h3><dl class="provenance-grid compact"><div><dt>Tệp Excel</dt><dd>${esc(run.workbookName)}</dd></div><div><dt>Cách nhập</dt><dd>${run.mode === 'full_snapshot' ? 'Bản chụp đầy đủ' : 'Dữ liệu bổ sung'}</dd></div><div><dt>Ghi lúc</dt><dd>${esc(new Date(run.committedAt).toLocaleString('vi-VN'))}</dd></div><div><dt>Khoảng dữ liệu</dt><dd>${esc(run.dataRange.start || '—')} – ${esc(run.dataRange.end || '—')}</dd></div><div><dt>Thêm / cập nhật / giữ nguyên</dt><dd>${fmt(run.outcome.inserted)} / ${fmt(run.outcome.updated)} / ${fmt(run.outcome.unchanged)}</dd></div><div class="wide-row"><dt>Mã nhận diện tệp</dt><dd><code title="${esc(run.workbookHash)}">${esc(shortHash(run.workbookHash))}</code></dd></div></dl></section>`;
}

function renderInvestigation(): void {
  const shell = app.querySelector<HTMLElement>('.shell');
  const drawer = document.querySelector<HTMLElement>('#investigation-drawer');
  if (!shell || !drawer) return;
  const priorAction = drawer.contains(document.activeElement)
    ? (document.activeElement as HTMLElement).dataset.action : null;
  const open = investigation.status !== 'closed';
  const contextualOpen = open && investigationSelection()?.origin.plotKey === 'contextual-comparison';
  document.querySelector('#contextual-comparison-dialog')?.classList.toggle('contextual-investigation-open', contextualOpen);
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
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu tổng hợp</span><h2 id="investigation-title">${escMetric(p.context.metric)} <strong>${esc(p.result.displayValue)}</strong></h2><p>${dateLabel(p.context.period.start)} – ${dateLabel(p.context.period.end)} · ${escMetric(origin.seriesName)}</p></div>${close}</div>${live}${aggregateMarkup(p, activeInvestigation.contributors, activeInvestigation.nextCursor, activeInvestigation.pageStatus)}`;
  } else if (activeInvestigation.status === 'loading') {
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${escMetric(origin.seriesName)}</h2><p>${esc(dateLabel(origin.observedDate))} · ${esc(origin.displayedValue)}</p></div>${close}</div>${live}<div class="drawer-body" aria-busy="true"><div class="lineage-loading"><strong>Đang xác minh nguồn dữ liệu…</strong><span>Đối chiếu điểm biểu đồ với ô Excel và lần nhập tương ứng.</span><i></i><i></i><i></i></div></div>`;
  } else if (activeInvestigation.status === 'unavailable') {
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${escMetric(origin.seriesName)}</h2><p>${esc(dateLabel(origin.observedDate))} · ${esc(origin.displayedValue)}</p></div>${close}</div>${live}<div class="drawer-body"><div class="lineage-state"><strong>Chưa truy vết được điểm này</strong><p>Dữ liệu cũ chưa lưu tham chiếu chính xác đến ô Excel. Để tránh mở nhầm nguồn, hệ thống không tự ghép theo ngày, chỉ số hoặc giá trị. Bạn vẫn có thể xem các điểm khác trên biểu đồ.</p></div></div>`;
  } else if (activeInvestigation.status === 'error') {
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${escMetric(origin.seriesName)}</h2><p>${esc(dateLabel(origin.observedDate))} · ${esc(origin.displayedValue)}</p></div>${close}</div>${live}<div class="drawer-body"><div class="lineage-state error"><strong>Không tải được nguồn dữ liệu</strong><p>${escMetric(activeInvestigation.error)}</p><button class="ghost" data-action="retry-provenance">Thử tải lại nguồn</button></div></div>`;
  } else {
    const p = activeInvestigation.provenance;
    const warnings = p.validation.issues.length
      ? `<div class="provenance-issues">${p.validation.issues.map(issue => `<div><p>${escMetric(issue.message)}</p></div>`).join('')}</div>`
      : '<p class="muted-copy">Không có cảnh báo nào gắn trực tiếp với ô nguồn của giá trị này.</p>';
    drawer.innerHTML = `<div class="drawer-head"><div><span>Nguồn dữ liệu</span><h2 id="investigation-title">${escMetric(p.context.metric.label)} <strong>${esc(p.values.display)}</strong></h2><p>${esc(dateLabel(p.context.observedDate))} · Chuỗi ${escMetric(origin.seriesName)}</p></div>${close}</div>${live}
      <div class="drawer-body">
        ${p.freshness.newerSnapshotAvailable ? '<div class="lineage-banner">Nguồn của điểm này đã có lần nhập mới hơn. Giá trị đang xem vẫn là phiên bản tại thời điểm chọn.</div>' : ''}
        <section class="provenance-context"><div class="entity-path">${displayHierarchyParts(p.context.entity.hierarchyPath).map(esc).join('<span>›</span>')}</div><dl><div><dt>Dự án</dt><dd>${esc(p.context.project.label)}</dd></div><div><dt>Đơn vị đo</dt><dd>${esc(p.context.entity.effectiveUnit || 'Chưa xác định')}</dd></div></dl></section>
        <section><h3>Nguồn Excel</h3><dl class="provenance-grid"><div><dt>Tệp Excel</dt><dd>${esc(p.source.workbookName)}</dd></div><div><dt>Trang tính và ô</dt><dd><code>${esc(p.source.cellReference)}</code></dd></div><div class="wide-row"><dt>Mã nhận diện tệp</dt><dd title="${esc(p.source.workbookHash.value)}"><code>${esc(shortHash(p.source.workbookHash.value))}</code></dd></div></dl><div class="inline-actions"><button data-action="copy-cell">Sao chép vị trí ô</button><button data-action="copy-value">Sao chép giá trị hiển thị</button></div></section>
        <section><h3>Giá trị từ Excel đến biểu đồ</h3><div class="value-flow"><div><span>Giá trị gốc</span><strong>${esc(p.values.raw.text ?? '—')}</strong></div><b>→</b><div><span>Giá trị hiển thị</span><strong>${esc(p.values.display)}</strong></div><b>→</b><div><span>Giá trị trên biểu đồ</span><strong>${esc(p.values.chart ?? '—')}</strong></div></div><p class="value-help">Giá trị gốc giữ nguyên nội dung ô; giá trị hiển thị dành cho người đọc; giá trị trên biểu đồ là số sau chuẩn hóa.</p><dl class="provenance-grid compact"><div><dt>Định dạng Excel</dt><dd>${esc(p.values.numberFormat || 'Không có')}</dd></div>${p.transformation.note ? `<div class="wide-row"><dt>Ghi chú xử lý</dt><dd>${esc(p.transformation.note)}</dd></div>` : ''}</dl></section>
        <section><h3>Kiểm tra dữ liệu</h3><div class="validation-line"><span class="validation-badge ${esc(p.validation.status)}">${esc(validationLabel(p.validation.status))}</span><span>${esc(confidenceLabel(p.transformation.parserConfidence))}</span></div>${warnings}</section>
        <section><h3>Lần nhập và phiên bản</h3><dl class="provenance-grid compact"><div><dt>Thay đổi</dt><dd>${esc(revisionChangeLabel(p.revision.changeType))}</dd></div><div><dt>Trạng thái phiên bản</dt><dd>${p.revision.revisionCurrent && !p.revision.sourcePresenceCurrent ? 'Còn hiệu lực · nguồn đã mới hơn' : esc(revisionStateLabel(p.revision.state))}</dd></div><div><dt>Ghi lúc</dt><dd>${esc(p.import.committedAt ? new Date(p.import.committedAt).toLocaleString('vi-VN') : '—')}</dd></div><div><dt>Dữ liệu đến ngày</dt><dd>${esc(p.freshness.observedThrough ? dateLabel(p.freshness.observedThrough) : '—')}</dd></div></dl></section>
      </div><div class="drawer-actions"><button class="primary" data-action="open-exact-audit">Mở đúng dòng đối chiếu</button></div>`;
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
    investigationLiveMessage = 'Điểm đã chọn chưa có thông tin nguồn dữ liệu.';
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
    if (provenance.observationRef !== selection.observationRef || provenance.lineageRef !== selection.lineageRef) throw new Error('Máy chủ trả về nguồn tham chiếu không khớp điểm đã chọn.');
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
    investigationLiveMessage = `Đã tải ${page.items.length} trong ${page.total} điểm dữ liệu dùng để tính.`;
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
    investigationLiveMessage = `Đã tải ${investigation.contributors.length} trong ${page.total} điểm dữ liệu.`;
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
    if (data.observationRef !== observationRef) throw new Error('Lịch sử phiên bản không khớp điểm dữ liệu đã chọn.');
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
  if (selection.origin.plotKey === 'contextual-comparison') {
    restoreInvestigationDrawerHost();
    document.querySelector<HTMLDialogElement>('#contextual-comparison-dialog')?.close();
    document.body.classList.remove('modal-open');
  }
  state.tab = 'audit'; save(); renderMain(); renderInvestigation();
  try {
    const params = new URLSearchParams({ observationRef: selection.observationRef, lineageRef: selection.lineageRef });
    const lookup = await api<AuditLookup>(`/projects/${encodeURIComponent(state.project)}/audit/lookup?${params}`);
    if (lookup.observationRef !== selection.observationRef || lookup.lineageRef !== selection.lineageRef) throw new Error('Máy chủ trả về dòng đối chiếu không khớp điểm đã chọn.');
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
  state.tab = selection.origin.tab; save(); renderMain();
  if (selection.origin.plotKey === 'contextual-comparison' && contextualComparison) {
    renderContextualComparison();
  }
  renderInvestigation();
  requestAnimationFrame(() => {
    document.querySelector<HTMLElement>(`[data-plot="${selection.origin.plotKey}"]`)?.scrollIntoView({ block: 'nearest' });
  });
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
  disposeCharts(root);
  const project = currentProject();
  const chosenTab = tabDefinitions.find(tab => tab.key === state.tab)!;
  const trail = entityTrail(entities, state.entity);
  root.innerHTML = `<nav class="tabbar" aria-label="Tính năng của không gian phân tích">${visibleTabs.map(tab => `<button class="tab ${tab.key === state.tab ? 'active' : ''}" data-tab="${tab.key}" aria-current="${tab.key === state.tab ? 'page' : 'false'}"><span>${tab.icon}</span>${tab.label}</button>`).join('')}</nav>
    ${header(state.project || 'Không gian phân tích', project ? `${fmt(project.records)} điểm dữ liệu đã lưu · ${fmt(project.chartable)} điểm có thể hiển thị trên biểu đồ` : bootstrapError ? 'Chưa kết nối được kho dữ liệu.' : bootstrapLoaded ? 'Chưa có tệp Excel nào được nhập.' : 'Đang kiểm tra dữ liệu…')}
    <div id="workspace-hierarchy">${hierarchyMarkup(trail)}</div>
    <div id="workspace-message">${message ? `<div class="notice">${esc(message)}</div>` : ''}</div>
    ${project ? `<div class="kpi-grid">
      <div class="kpi"><div class="kpi-icon violet">◈</div><span>DỰ ÁN</span><strong>${esc(project.label)}</strong><small>Đang xem</small></div>
      <div class="kpi"><div class="kpi-icon blue">◇</div><span>NỘI DUNG THEO DÕI</span><strong>${fmt(project.entities)}</strong><small>Gồm nhóm vấn đề, vấn đề và tình trạng</small></div>
      <div class="kpi"><div class="kpi-icon teal">▣</div><span>ĐƠN VỊ ĐO</span><strong>${fmt(project.units)}</strong><small>${fmt(project.units)} loại trong dự án</small></div>
      <div class="kpi"><div class="kpi-icon amber">▤</div><span>ĐIỂM DỮ LIỆU</span><strong>${fmt(project.records)}</strong><small>Đã lưu, gồm cả giá trị chưa hiển thị</small></div>
    </div>` : ''}
    <div class="content-card" aria-busy="${loading}"><div class="tab-content"><div class="section-title"><div><h2>${chosenTab.label}</h2></div><span id="workspace-loading" class="loading" ${loading ? '' : 'hidden'}>Đang cập nhật biểu đồ…</span></div><div id="workspace-request-status" class="workspace-request-status" role="status" aria-live="polite" aria-atomic="true"></div><div id="tab-body"></div></div></div>`;
  renderTab();
  updateWorkspaceRequestStatus();
}

function hierarchyMarkup(trail = entityTrail(entities, state.entity)): string {
  return trail.length ? `<div class="hierarchy-context"><span class="context-label">Đang xem</span><div class="entity-breadcrumb" aria-label="Nội dung đang xem">${trail.map((entity, index) => `<span class="crumb ${index === trail.length - 1 ? 'current' : ''}">${esc(getEntityDisplayName(entity))}</span>${index < trail.length - 1 ? '<span class="crumb-separator" aria-hidden="true">›</span>' : ''}`).join('')}</div></div>` : '';
}

function updateWorkspaceChrome(): void {
  const project = currentProject();
  const heading = document.querySelector<HTMLElement>('.page-head h1');
  const subtitle = document.querySelector<HTMLElement>('.page-head p');
  if (heading) heading.textContent = state.project || 'Không gian phân tích';
  if (subtitle) subtitle.textContent = project
    ? `${fmt(project.records)} điểm dữ liệu đã lưu · ${fmt(project.chartable)} điểm có thể hiển thị trên biểu đồ`
    : bootstrapError ? 'Chưa kết nối được kho dữ liệu.' : bootstrapLoaded ? 'Chưa có tệp Excel nào được nhập.' : 'Đang kiểm tra dữ liệu…';
  const hierarchy = document.querySelector<HTMLElement>('#workspace-hierarchy');
  if (hierarchy) hierarchy.innerHTML = hierarchyMarkup();
  const messageRoot = document.querySelector<HTMLElement>('#workspace-message');
  if (messageRoot) messageRoot.innerHTML = message ? `<div class="notice">${esc(message)}</div>` : '';
}

function updateWorkspaceRequestStatus(): void {
  const card = document.querySelector<HTMLElement>('.content-card');
  card?.setAttribute('aria-busy', String(loading));
  const indicator = document.querySelector<HTMLElement>('#workspace-loading');
  if (indicator) indicator.hidden = !loading;
  const status = document.querySelector<HTMLElement>('#workspace-request-status');
  if (!status) return;
  status.classList.toggle('error', Boolean(workspaceError));
  status.innerHTML = workspaceError && workspace
    ? `<div><strong>Chưa áp dụng được bộ lọc mới.</strong> Biểu đồ vẫn hiển thị ${esc(displayedFilterLabel || 'kết quả thành công gần nhất')}. ${esc(workspaceError)}</div><button class="ghost" data-action="retry-workspace">Thử lại</button>`
    : loading && workspace
      ? `<div><strong>Đang áp dụng bộ lọc đã chọn.</strong> Trong lúc chờ, biểu đồ vẫn hiển thị ${esc(displayedFilterLabel || 'kết quả trước đó')}.</div>`
      : loading ? '<span class="sr-only">Đang cập nhật dữ liệu biểu đồ.</span>' : '';
}

function workspaceFilterLabel(value: Workspace): string {
  const selected = entities.find(item => item.entity_id === value.selectedEntity);
  const entity = displayEntityName(selected, value.selectedEntity);
  const scope = state.scope === 'children' ? getChildrenScopeLabel(selected?.entity_level).toLowerCase() : entity;
  return `${scope}, ${dateLabel(value.window.start)}–${dateLabel(value.window.end)}`;
}

function disposeCharts(root: ParentNode): void {
  root.querySelectorAll<HTMLElement>('[data-plot]').forEach(element => {
    const key = element.dataset.plot;
    if (key) chartFingerprints.delete(key);
    purgeChart(element);
  });
}
function chartPlotKey(section: string, entityId: string): string {
  return `${section}-${encodeURIComponent(entityId)}`;
}
function structuralSiblings(anchorId: string): Entity[] {
  const anchor = entities.find(item => item.entity_id === anchorId);
  if (!anchor?.parent_entity_id) return [];
  return entities.filter(item => item.parent_entity_id === anchor.parent_entity_id && item.entity_id !== anchorId);
}
function chartCard(chart: Chart, section: string): string {
  const entity = entities.find(item => item.entity_id === chart.entityId);
  const path = displayEntityPath(chart.entityId);
  const metadata = `${path}${entity?.effective_unit ? ` · Đơn vị đo: ${entity.effective_unit}` : ''}`;
  const plotKey = chartPlotKey(section, chart.entityId);
  const contextualAction = section === 'statistics' && state.scope === 'children';
  const siblingCount = structuralSiblings(chart.entityId).length;
  const action = contextualAction
    ? `<button id="compare-action-${encodeURIComponent(chart.entityId)}" class="compare-action" data-action="open-contextual-comparison" data-entity-id="${esc(chart.entityId)}" aria-haspopup="dialog" ${siblingCount ? '' : 'disabled'} title="${esc(getComparisonButtonDescription(entity?.entity_level, siblingCount > 0))}">So sánh</button>`
    : '<span class="pill">Theo bộ lọc</span>';
  return `<article class="chart-card" data-chart-key="${esc(plotKey)}"><div class="card-top"><div><h3>${esc(entityCardTitle(entity, chart.title))}</h3><span>${esc(metadata)}</span></div>${action}</div><div class="plot" data-plot="${esc(plotKey)}" aria-label="Biểu đồ ${esc(entityCardTitle(entity, chart.title))}"></div></article>`;
}
function hasSiblingCharts(charts: Chart[]): boolean {
  return state.scope === 'children' && (workspace?.scopeIds.length || 0) > 1 && charts.length > 1;
}
function statePanel(title: string, detail: string, retry = false, retryAction = 'refresh'): string {
  return `<div class="empty ${retry ? 'state-error' : ''}" role="${retry ? 'alert' : 'status'}"><h3>${esc(title)}</h3><p>${esc(detail)}</p>${retry ? `<button class="ghost" data-action="${retryAction}">Thử tải lại</button>` : ''}</div>`;
}

function statisticsReceipt(): string {
  const group = ({ day: 'ngày', week: 'tuần', month: 'tháng', quarter: 'quý' })[state.statisticsGroup];
  const calculation = ({ both: 'Tổng và trung bình/ngày', sum: 'Tổng', average: 'Trung bình/ngày' })[state.statisticsMode];
  const range = state.statisticsRange === 'all'
    ? 'Toàn bộ dữ liệu'
    : state.statisticsRange === 'custom'
      ? `${dateLabel(state.statisticsFrom)}–${dateLabel(state.statisticsTo)}`
      : `${fmt(state.statisticsCount)} kỳ gần nhất`;
  return `<div class="statistics-receipt" aria-label="Ngữ cảnh thống kê hiện tại"><span>Theo ${esc(group)}</span><span>${esc(calculation)}</span><span>${esc(range)}</span><span>${state.includeIncomplete ? 'Có kỳ chưa đầy đủ' : 'Chỉ kỳ đầy đủ'}</span></div>`;
}

function aiStatusLabel(value: AIAnalysis['status']): string {
  return ({
    ready: 'Số liệu đã được kiểm tra', insufficient_data: 'Chưa đủ dữ liệu',
    provider_unavailable: 'Tóm tắt dự phòng', rejected_output: 'Đang dùng kết quả từ số liệu', stale: 'Cần phân tích lại',
  })[value];
}

function aiGroupLabel(value: 'day' | 'week' | 'month'): string {
  return ({ day: 'ngày', week: 'tuần', month: 'tháng' })[value];
}

function aiPatternLabel(value: unknown): string {
  return ({
    consistently_increasing: 'Không có lần giảm giữa các kỳ hợp lệ', consistently_decreasing: 'Không có lần tăng giữa các kỳ hợp lệ',
    unchanged: 'Không đổi qua các kỳ', fluctuating: 'Dao động tăng giảm',
  } as Record<string, string>)[String(value)] || String(value);
}

function aiPeriodChange(point: AISeriesPoint): string {
  if (!point.change) return '<span class="ai-change baseline">Mốc đầu</span>';
  const direction = ({ increasing: 'Tăng', decreasing: 'Giảm', unchanged: 'Không đổi' })[point.change.direction];
  const absolute = point.change.absoluteDisplay.replace(/^[+-]/, '').replace(' pp', ' điểm phần trăm');
  const relative = point.change.relativePercent === null ? 'không tính được %' : point.change.relativeDisplay.replace(/^[+-]/, '');
  return `<span class="ai-change ${esc(point.change.direction)}"><strong>${esc(direction)} ${esc(absolute)}</strong><small>${esc(relative)}</small></span>`;
}

function aiSequenceText(sequence: AISequenceHighlight): string {
  return sequence.displayValues.map(value => esc(value)).join(' → ');
}

function aiChronologicalStory(analytics: AIPeriodAnalytics, label: string, history?: AIHistoricalContext): string {
  const structure = analytics.temporalStructure;
  if (!structure) return '';
  const entries = [
    ...structure.stages.map(stage => ({ index: stage.startIndex, text: stage.text })),
    ...structure.gaps.map(gap => ({ index: gap.startIndex, text: gap.text })),
  ].sort((a, b) => a.index - b.index);
  const stages = `<ol class="ai-stage-list">${entries.map(entry => `<li>${esc(entry.text)}</li>`).join('')}</ol>`;
  const milestones = [analytics.peak ? `Cao nhất ${analytics.peak.displayValue} tại ${analytics.peak.periodLabel}.` : '', analytics.lowest ? `Thấp nhất ${analytics.lowest.displayValue} tại ${analytics.lowest.periodLabel}.` : ''].filter(Boolean).join(' ');
  const changes = [analytics.largestIncrease, analytics.largestDecrease].filter((item): item is AIChangeHighlight => !!item).map(item => `<p>${item.direction === 'increasing' ? 'Tăng' : 'Giảm'} lớn nhất giữa hai kỳ: ${esc(item.fromPeriodLabel)}–${esc(item.toPeriodLabel)}, ${esc(item.fromDisplayValue)} → ${esc(item.toDisplayValue)} (${esc(item.absoluteDisplay.replace(' pp', ' điểm phần trăm'))}).</p>`).join('');
  const turns = structure.turningPoints.length ? `<details><summary>Các mốc đổi chiều</summary>${structure.turningPoints.map(turn => `<p>${esc(turn.text)}</p>`).join('')}</details>` : '';
  const historicalLabel = history?.currentPosition ? ({ above_historical_range: 'cao hơn tất cả', below_historical_range: 'thấp hơn tất cả', within_historical_range: 'nằm trong khoảng giá trị của', matches_historical_range: 'bằng mức đã ghi nhận trong' })[history.currentPosition.value] : '';
  const historical = history?.status === 'available' && historicalLabel ? `<details><summary>Bối cảnh trước khoảng đang xem</summary><p>Kỳ cuối hiện tại ${historicalLabel} ${fmt(history.observedPeriodCount)} kỳ hợp lệ liền trước được cung cấp; không phải toàn bộ lịch sử.</p></details>` : '';
  return `<section class="ai-chronology"><h4>${esc(label)}</h4>${entries.length > 8 ? `<details><summary>Diễn biến theo các giai đoạn</summary>${stages}</details>` : stages}${milestones ? `<p class="ai-evidence-note">${esc(milestones)}</p>` : ''}${changes}${turns}${historical}</section>`;
}

function aiOverviewStory(analysis: AIAnalysis): string {
  const chronology = (analysis.metrics || []).map(metric => aiChronologicalStory(metric.periodAnalytics, metric.metricDisplayName, metric.historicalContext)).join('');
  if (chronology) return `<section class="ai-story ai-overview-story" aria-labelledby="ai-story-title"><h4 id="ai-story-title">Diễn biến trong thời gian đã chọn</h4>${chronology}</section>`;
  if (analysis.comparisonBasis) {
    const basis = analysis.comparisonBasis;
    const endpoints = [basis.baseline, basis.current].filter((point): point is NonNullable<typeof point> => !!point).filter((point, index, points) => index === 0 || point.periodLabel !== points[0].periodLabel);
    const operands = endpoints.map(point => `<li><span>${esc(point.periodLabel)}</span><p>${esc(point.numeratorDisplay)} Tổng báo sai (lỗi) trên ${esc(point.denominatorDisplay)} lượng ghi nhận đủ điều kiện: <strong>${esc(point.rateDisplay)}</strong>.<small>${fmt(point.eligibleDayCount)}/${fmt(point.expectedDayCount)} ngày đủ dữ liệu tính tỷ lệ</small></p></li>`).join('');
    return `<section class="ai-story ai-overview-story" aria-labelledby="ai-story-title"><h4 id="ai-story-title">Mối quan hệ giữa các chỉ số</h4><p>${esc(basis.reason)}</p>${operands ? `<ul>${operands}</ul>` : ''}<p class="ai-evidence-note">Đây là so sánh kỳ đầu–cuối, không phải tổng của thời gian đã chọn hay kết luận chất lượng và nguyên nhân.</p></section>`;
  }
  if (!analysis.metrics?.length) return '';
  const rows = analysis.metrics.map(metric => {
    const current = metric.facts.find(fact => fact.kind === 'current');
    const delta = metric.facts.find(fact => fact.kind === 'absolute_change');
    const relative = metric.facts.find(fact => fact.kind === 'relative_change');
    const direction = metric.facts.find(fact => fact.kind === 'direction');
    const pattern = metric.facts.find(fact => fact.kind === 'trend_pattern');
    const movement = direction ? ({
      increasing: 'tăng', decreasing: 'giảm', unchanged: 'không đổi',
    } as Record<string, string>)[String(direction.value)] : 'chưa đủ dữ liệu so sánh';
    const change = delta
      ? `${movement} ${esc(String(delta.displayValue).replace(/^[-+]/, ''))}${relative ? ` (${esc(String(relative.displayValue).replace(/^[-+]/, ''))})` : ''} so với kỳ đầu`
      : movement;
    const range = metric.periodAnalytics.lowest && metric.periodAnalytics.peak
      ? `Thấp nhất ${esc(metric.periodAnalytics.lowest.displayValue)} · cao nhất ${esc(metric.periodAnalytics.peak.displayValue)}`
      : 'Chưa đủ dữ liệu xác định khoảng biến động';
    const last = metric.series.at(-1);
    return `<li class="ai-overview-metric"><div><span>${esc(metric.metricDisplayName)} · kỳ cuối ${last ? esc(last.periodLabel) : ''}</span><strong>${current ? esc(current.displayValue) : last ? esc(last.displayValue) : '—'}</strong></div><p>${esc(change)}. ${pattern ? `${esc(aiPatternLabel(pattern.value))}. ` : ''}<small>${range}</small></p></li>`;
  }).join('');
  return `<section class="ai-story ai-overview-story" aria-labelledby="ai-story-title"><div class="ai-section-heading"><h4 id="ai-story-title">Bức tranh ba chỉ số</h4><span>Cùng phạm vi · cùng thời gian</span></div><ul>${rows}</ul></section>`;
}

function aiDataStory(analysis: AIAnalysis): string {
  if (analysis.kind === 'metric_overview') return aiOverviewStory(analysis);
  const analytics = analysis.periodAnalytics;
  if (!analytics) return '';
  if (analytics.temporalStructure) return `<section class="ai-story">${aiChronologicalStory(analytics, 'Diễn biến trong thời gian đã chọn', analysis.historicalContext)}</section>`;
  const beats: string[] = [];
  if (analytics.lowest && analytics.peak) {
    beats.push(`<li><span>Mức thấp và cao</span><p>Mức thấp nhất là <strong>${esc(analytics.lowest.displayValue)}</strong> vào ${esc(analytics.lowest.periodLabel)}; mức cao nhất là <strong>${esc(analytics.peak.displayValue)}</strong> vào ${esc(analytics.peak.periodLabel)}.</p></li>`);
  }
  const changes: string[] = [];
  if (analytics.largestIncrease) {
    const item = analytics.largestIncrease;
    const relative = item.relativePercent === null ? '' : `, tương ứng ${item.relativeDisplay}`;
    changes.push(`nhịp tăng lớn nhất đi từ <strong>${esc(item.fromDisplayValue)}</strong> lên <strong>${esc(item.toDisplayValue)}</strong> (${esc(item.absoluteDisplay)}${esc(relative)})`);
  }
  if (analytics.largestDecrease) {
    const item = analytics.largestDecrease;
    const relative = item.relativePercent === null ? '' : `, tương ứng ${item.relativeDisplay}`;
    changes.push(`nhịp giảm lớn nhất đi từ <strong>${esc(item.fromDisplayValue)}</strong> xuống <strong>${esc(item.toDisplayValue)}</strong> (${esc(item.absoluteDisplay)}${esc(relative)})`);
  }
  if (changes.length) {
    const sentence = changes.map((item, index) => index ? `${item}` : `${item[0].toUpperCase()}${item.slice(1)}`).join('; ');
    beats.push(`<li><span>Biến động lớn nhất</span><p>${sentence}.</p></li>`);
  }
  const runs: string[] = [];
  if (analytics.consecutiveIncrease) runs.push(`tăng liên tiếp ${aiSequenceText(analytics.consecutiveIncrease)}`);
  if (analytics.consecutiveDecrease) runs.push(`giảm liên tiếp ${aiSequenceText(analytics.consecutiveDecrease)}`);
  if (runs.length) {
    beats.push(`<li><span>Nhịp liên tiếp</span><p>Các đoạn được ghi nhận: ${runs.join('; ')}.</p></li>`);
  }
  if (analytics.endingPlateau) {
    beats.push(`<li><span>Trạng thái cuối kỳ</span><p>Các kỳ cuối giữ nguyên ở cùng một mức: ${aiSequenceText(analytics.endingPlateau)}.</p></li>`);
  } else if (analytics.latestChange) {
    const item = analytics.latestChange;
    const alreadyCovered = [analytics.largestIncrease, analytics.largestDecrease].some(change => (
      change?.fromPeriodStart === item.fromPeriodStart && change.toPeriodStart === item.toPeriodStart
    ));
    if (!alreadyCovered) {
      const movement = item.direction === 'increasing'
        ? `tăng từ <strong>${esc(item.fromDisplayValue)}</strong> lên <strong>${esc(item.toDisplayValue)}</strong>`
        : item.direction === 'decreasing'
          ? `giảm từ <strong>${esc(item.fromDisplayValue)}</strong> xuống <strong>${esc(item.toDisplayValue)}</strong>`
          : `giữ nguyên ở <strong>${esc(item.toDisplayValue)}</strong>`;
      beats.push(`<li><span>Chuyển động gần nhất</span><p>Từ ${esc(item.fromPeriodLabel)} đến ${esc(item.toPeriodLabel)}, chỉ số ${movement}.</p></li>`);
    }
  }
  const history = analysis.historicalContext;
  if (history?.status === 'available' && history.currentPosition) {
    const label = ({
      above_historical_range: 'cao hơn tất cả',
      below_historical_range: 'thấp hơn tất cả',
      within_historical_range: 'nằm trong khoảng giá trị của',
      matches_historical_range: 'bằng mức đã ghi nhận trong',
    })[history.currentPosition.value];
    beats.push(`<li><span>Bối cảnh lịch sử</span><p>Kỳ cuối hiện tại ${label} ${fmt(history.observedPeriodCount)} kỳ hợp lệ liền trước.</p></li>`);
  }
  if (!beats.length) return '';
  const pattern = analysis.facts.find(fact => fact.kind === 'trend_pattern');
  const lead = pattern
    ? `Qua ${fmt(analysis.quality.validPeriodCount)} kỳ hợp lệ, chuỗi ${aiPatternLabel(pattern.value).toLowerCase()}.`
    : '';
  return `<section class="ai-story" aria-labelledby="ai-story-title"><div class="ai-section-heading"><h4 id="ai-story-title">Câu chuyện dữ liệu</h4><span>Từ số liệu đã kiểm chứng</span></div>${lead ? `<p class="ai-story-lead">${esc(lead)}</p>` : ''}<ul>${beats.join('')}</ul></section>`;
}

function aiReadable(text: string): string {
  return text.replaceAll('toàn khoảng', 'thời gian đã chọn').replaceAll('endpoint', 'đầu và cuối giai đoạn')
    .replaceAll('tỷ trọng trên Tổng số ghi nhận', 'tỷ lệ báo sai').replaceAll('tỷ trọng trên Tổng số', 'tỷ lệ báo sai').replaceAll('tỷ trọng', 'tỷ lệ báo sai')
    .replaceAll('; ', '. ').split('. ').map(sentence => sentence.charAt(0).toUpperCase() + sentence.slice(1)).join('. ');
}

function aiReadingStory(analysis: AIAnalysis): string {
  const reportPhases = analysis.narrative.report?.phases;
  if (reportPhases?.length) {
    const rows = reportPhases.map(phase => `<li><h5>${esc(phase.startLabel || '')} → ${esc(phase.endLabel || '')}</h5><p>${esc(aiReadable(phase.text))}</p>${phase.source === 'deterministic' && analysis.narrative.mode === 'ai' ? '<small>Tổng hợp từ số liệu</small>' : ''}</li>`);
    return `<section class="ai-reading-story"><h4>${aiShortWindow(analysis) ? 'So sánh các kỳ đã có' : 'Các chỉ số thay đổi như thế nào?'}</h4><ol class="ai-reading-phases">${rows.slice(0, 4).join('')}</ol>${rows.length > 4 ? `<details class="ai-more-phases"><summary>Xem các giai đoạn tiếp theo</summary><ol class="ai-reading-phases">${rows.slice(4).join('')}</ol></details>` : ''}${analysis.narrative.report?.omittedPhaseCount ? '<p>Còn các giai đoạn khác trong phần số liệu và nguồn.</p>' : ''}</section>`;
  }
  const phases = analysis.synthesis?.reading?.phases || [];
  if (!phases.length) return '';
  const rows = phases.map(phase => {
    const label = phase.startLabel === phase.endLabel ? phase.startLabel : `${phase.startLabel} → ${phase.endLabel}`;
    return `<li><h5>${esc(label)}</h5><p>${esc(aiReadable(phase.text))}</p>${phase.explanation ? `<p class="ai-phase-meaning">${esc(aiReadable(phase.explanation))}</p>` : ''}</li>`;
  });
  const short = aiShortWindow(analysis);
  const title = short ? (phases.length === 1 && (analysis.metrics?.[0].series.length || analysis.series?.length) === 2 ? 'So sánh hai kỳ' : 'Diễn biến các kỳ đã có') : 'Các chỉ số thay đổi như thế nào?';
  return `<section class="ai-reading-story"><h4>${title}</h4><ol class="ai-reading-phases">${rows.slice(0, 4).join('')}</ol>${rows.length > 4 ? `<details class="ai-more-phases"><summary>Xem các giai đoạn tiếp theo</summary><ol class="ai-reading-phases">${rows.slice(4).join('')}</ol></details>` : ''}</section>`;
}

function aiReportSection(analysis: AIAnalysis, section: 'relationships', title: string): string {
  const items = analysis.narrative.report?.[section] || [];
  if (!items.length) return '';
  return `<section class="ai-report-${section}"><h4>${esc(title)}</h4><ul class="ai-reading-phases">${items.map(item => `<li>${item.metricDisplayName ? `<h5>${esc(item.metricDisplayName)}</h5>` : ''}<p>${esc(aiReadable(item.text))}</p>${item.source === 'deterministic' && analysis.narrative.mode === 'ai' ? '<small>Tổng hợp từ số liệu</small>' : ''}</li>`).join('')}</ul></section>`;
}

function aiAnalyticalDetails(analysis: AIAnalysis): string {
  const sourceButtons = (ids: string[]) => ids.map(id => {
    const evidence = analysis.evidence.find(item => item.evidenceId === id);
    if (!evidence) return '';
    const metric = analysis.metrics?.find(item => item.evidence.some(source => source.evidenceId === id));
    const label = `${metric?.metricDisplayName || analysis.scope.metricDisplayName} · ${evidence.periodLabel}`;
    return `<button class="text-action" data-action="open-ai-evidence" data-evidence-id="${esc(id)}">${esc(label)}</button>`;
  }).join('');
  const selected = new Set(analysis.narrative.summary.candidateIds || []);
  const hasChronology = !!analysis.periodAnalytics?.temporalStructure || !!analysis.metrics?.some(metric => metric.periodAnalytics.temporalStructure);
  const temporal = hasChronology ? [] : analysis.insightCandidates?.filter(item => item.layer === 'temporal' && !selected.has(item.candidateId)) || [];
  const events = temporal.length ? `<section class="ai-story"><h4>Diễn biến cần chú ý</h4>${temporal.map(item => `<p>${esc(item.text)}</p><div class="ai-source-actions">${sourceButtons(item.evidenceIds)}</div>`).join('')}</section>` : '';
  const checks = analysis.inspectionChecks || [];
  const next = checks.length ? `<section class="ai-story"><h4>Đối chiếu nguồn</h4><ul>${checks.map(item => `<li><span>Đối chiếu nguồn</span><div><p>${esc(item.text)}</p><div class="ai-source-actions">${sourceButtons(item.evidenceIds)}</div></div></li>`).join('')}</ul></section>` : analysis.narrative.suggestedChecks.length ? `<section class="ai-story"><h4>Gợi ý kiểm tra</h4><ul>${analysis.narrative.suggestedChecks.map(text => `<li><p>${esc(text)}</p></li>`).join('')}</ul></section>` : '';
  if (aiShortWindow(analysis)) return next;
  const basis = analysis.comparisonBasis;
  const relationship = analysis.insightCandidates?.find(item => item.layer === 'relational');
  const supplemental = basis ? `<details class="ai-supplement"><summary>Thông tin bổ sung: so sánh đầu–cuối</summary><p>${esc(basis.reason)}</p>${relationship ? `<p>${esc(relationship.text)}</p><div class="ai-source-actions">${sourceButtons(relationship.evidenceIds)}</div>` : ''}${[basis.baseline, basis.current].filter(point => !!point).map(point => `<p>${esc(point!.periodLabel)}: ${esc(point!.numeratorDisplay)} Tổng báo sai (lỗi) trên ${esc(point!.denominatorDisplay)} lượng ghi nhận đủ điều kiện (${esc(point!.rateDisplay)}); ${fmt(point!.eligibleDayCount)}/${fmt(point!.expectedDayCount)} ngày đủ dữ liệu.</p>`).join('')}<p class="ai-evidence-note">Đầu–cuối không đại diện cho diễn biến các kỳ ở giữa, không phải kết luận chất lượng hay nguyên nhân.</p></details>` : '';
  const first = analysis.series?.[0];
  const last = analysis.series?.at(-1);
  const delta = analysis.facts.find(fact => fact.kind === 'absolute_change');
  const singleSupplement = !basis && first && last && analysis.series!.length > 1 ? `<details class="ai-supplement"><summary>Thông tin bổ sung: so sánh đầu–cuối</summary><p>Kỳ đầu ${esc(first.periodLabel)}: ${esc(first.displayValue)}; kỳ cuối ${esc(last.periodLabel)}: ${esc(last.displayValue)}.${delta ? ` Chênh lệch đầu–cuối: ${esc(delta.displayValue.replace(' pp', ' điểm phần trăm'))}.` : ''}</p><p class="ai-evidence-note">So sánh này không thay thế diễn biến các kỳ ở giữa.</p></details>` : '';
  return events + next + supplemental + singleSupplement;
}

function aiInsightEvidence(analysis: AIAnalysis): string {
  if (!analysis.synthesis) return '';
  const selectedIds = analysis.narrative.mode === 'ai' ? analysis.narrative.summary.candidateIds || analysis.synthesis.selectedCandidateIds : analysis.synthesis.selectedCandidateIds;
  const anchors = selectedIds.flatMap(id => analysis.synthesis!.candidates.find(c => c.candidateId === id)?.anchors || []).filter((anchor, index, all) => all.findIndex(item => item.factId === anchor.factId) === index);
  if (!anchors.length) return '';
  return `<section class="ai-insight-evidence"><h4>Số liệu hỗ trợ phân tích</h4><ul>${anchors.map(anchor => `<li><span>${esc(anchor.metricDisplayName)} · ${esc(anchor.periodLabel)}: <strong>${esc(anchor.displayValue)}</strong></span> <button class="text-action" data-action="open-ai-evidence" data-evidence-id="${esc(anchor.evidenceId)}" aria-label="Mở căn cứ ${esc(anchor.metricDisplayName)} · ${esc(anchor.periodLabel)}">Mở nguồn</button></li>`).join('')}</ul></section>`;
}

function aiShortWindow(analysis: AIAnalysis): boolean {
  return (analysis.metrics ? Math.max(0, ...analysis.metrics.map(metric => metric.series.length)) : (analysis.series?.length || 0)) < 4;
}

function aiCompactPeriod(point: { periodStart: string; periodEnd: string }): string {
  const [sy, sm, sd] = point.periodStart.split('-');
  const [ey, em, ed] = point.periodEnd.split('-');
  if (point.periodStart === point.periodEnd) return `${sd}/${sm}`;
  if (sy !== ey) return `${sd}/${sm}/${sy} → ${ed}/${em}/${ey}`;
  return sm === em ? `${sd}–${ed}/${em}` : `${sd}/${sm}–${ed}/${em}`;
}

function aiComparisonTable(analysis: AIAnalysis): string {
  const metrics = analysis.metrics || [{ metricDisplayName: analysis.scope.metricDisplayName, series: analysis.series || [] }];
  const points = [...new Map(metrics.flatMap(metric => metric.series).map(point => [point.periodStart, point])).values()].sort((a, b) => a.periodStart.localeCompare(b.periodStart));
  if (!points.length) return '';
  const labels = points.map((point, index) => `Kỳ ${index + 1} (${aiCompactPeriod(point)})`);
  const rows = metrics.map(metric => `<tr><th scope="row">${esc(metric.metricDisplayName)}</th>${points.map(period => {
    const point = metric.series.find(item => item.periodStart === period.periodStart && item.periodEnd === period.periodEnd);
    return `<td>${point ? `<strong>${esc(point.displayValue)}</strong> <button class="text-action" data-action="open-ai-evidence" data-evidence-id="${esc(point.evidenceId)}" aria-label="Mở nguồn ${esc(metric.metricDisplayName)} · ${esc(point.periodLabel)}">Nguồn</button>` : 'Thiếu dữ liệu'}</td>`;
  }).join('')}</tr>`).join('');
  return `<details class="ai-disclosure ai-periods ai-comparison"><summary>So sánh các KPI giữa các kỳ</summary><div class="ai-disclosure-body"><p>${esc(labels.join(' → '))}</p><p class="ai-evidence-note">Số kỳ còn ít: chỉ so sánh, chưa xác định xu hướng. Năm và phạm vi đầy đủ được ghi ở trên.</p><div class="ai-period-table"><table><thead><tr><th>Chỉ số</th>${labels.map(label => `<th scope="col">${esc(label)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div></div></details>`;
}

function aiFriendlyError(): string {
  return 'Dịch vụ phân tích tạm thời không phản hồi. Dữ liệu trên bảng điều khiển không bị ảnh hưởng; hãy thử lại.';
}

function focusAIAction(): void {
  requestAnimationFrame(() => document.querySelector<HTMLButtonElement>('[data-action="generate-ai-insight"]')?.focus());
}

function announceAI(message: string): void {
  requestAnimationFrame(() => {
    const status = document.querySelector<HTMLElement>('#ai-status-message');
    if (status) status.textContent = message;
  });
}

function renderAIInsights(rawAnalysis = aiAnalysis): string {
  const aiAnalysis = metricPresentation(rawAnalysis);
  const scopeBlocked = state.scope !== 'node';
  const statusUnavailable = aiStatus && !aiStatus.enabled;
  const notConfigured = aiStatus && !aiStatus.configured;
  const hardDisabled = !aiStatus || statusUnavailable || notConfigured || scopeBlocked || !workspace;
  const disabled = hardDisabled || aiLoading;
  const actionLabel = aiLoading ? 'Đang phân tích…' : aiAnalysis ? 'Phân tích lại' : 'Phân tích khoảng đang xem';
  const statusCopy = aiStatusError
    ? '<p id="ai-availability-note" class="ai-inline-error">Không kiểm tra được tính sẵn sàng của tính năng. Hãy tải lại trang hoặc liên hệ người vận hành.</p>'
    : !aiStatus
      ? '<p id="ai-availability-note" class="ai-muted">Đang kiểm tra tính sẵn sàng của tính năng…</p>'
      : !aiStatus.enabled
        ? '<p id="ai-availability-note" class="ai-muted">Tính năng phân tích đang tắt ở môi trường này.</p>'
        : !aiStatus.configured
          ? '<p id="ai-availability-note" class="ai-inline-error">Tính năng phân tích chưa sẵn sàng. Liên hệ người vận hành để hoàn tất cấu hình.</p>'
          : !aiStatus.externalAllowed
            ? '<p id="ai-availability-note" class="ai-privacy-note">Chế độ riêng tư đang bật: hệ thống chỉ dùng số liệu đã kiểm chứng trong máy chủ và không gọi dịch vụ trí tuệ nhân tạo bên ngoài.</p>'
            : '<p id="ai-availability-note" class="ai-trust-note">Chỉ số liệu đã chuẩn hóa và mã định danh thay thế được gửi đến dịch vụ trí tuệ nhân tạo. Tệp Excel gốc và thông tin truy vết luôn ở lại máy chủ.</p>';
  const selectedEntity = currentEntity();
  const resultRef = aiAnalysis?.scope.entityRef;
  const resultEntity = aiAnalysis ? entities.find(entity => entity.entity_id === resultRef) : selectedEntity;
  const selectedName = aiAnalysis ? displayEntityName(undefined, aiAnalysis.scope.entityLabel) : displayEntityName(selectedEntity, 'Nội dung đang xem');
  const selectedScope = getCurrentScopeLabel(selectedEntity?.entity_level);
  const scopeCopy = scopeBlocked
    ? `<div id="ai-scope-note" class="ai-scope-note"><div><strong>Mức hiển thị này chưa hỗ trợ phân tích tự động.</strong><p>Hiện tại tính năng phân tích từng nội dung. Chuyển về “${esc(selectedScope)}” để tiếp tục.</p></div><button class="ghost" data-action="use-selected-entity">Dùng nội dung đang chọn</button></div>`
    : '';
  const error = aiAnalysisError ? `<div class="ai-callout error" role="alert"><strong>Không tạo được phân tích.</strong><p>${esc(aiAnalysisError)}</p></div>` : '';
  let result = scopeBlocked
    ? `<div class="ai-empty compact"><strong>Chưa có kết quả cho mức hiển thị này.</strong><p>Biểu đồ phía trên vẫn hiển thị bình thường. Chọn “${esc(selectedScope)}” để tạo nhận xét xu hướng.</p></div>`
    : aiLoading
      ? '<div class="ai-empty compact"><strong>Đang đối chiếu các kỳ dữ liệu…</strong><p>Kết quả sẽ xuất hiện tại đây sau khi số liệu và bằng chứng được kiểm tra.</p></div>'
      : '<div class="ai-empty"><strong>Chưa có phân tích cho bộ lọc này.</strong><p>Tính năng chỉ chạy khi bạn chủ động yêu cầu; đổi bộ lọc không tự gửi dữ liệu ra ngoài.</p></div>';
  if (aiAnalysis && !scopeBlocked) {
    const stale = aiLocallyStale || aiAnalysis.status === 'stale' || aiAnalysis.dataAsOf.stale;
    const stateValue: AIAnalysis['status'] = stale ? 'stale' : aiAnalysis.status;
    const periodRows = (series: AISeriesPoint[], metricLabel = aiAnalysis!.scope.metricDisplayName) => series.map(point => {
      const evidence = aiAnalysis?.evidence.find(item => item.evidenceId === point.evidenceId);
      return `<tr><th scope="row"><strong>${esc(point.periodLabel)}</strong><small>${fmt(point.observedDayCount)}/${fmt(point.expectedDayCount)} ngày dữ liệu</small></th><td>${esc(point.displayValue)}</td><td>${aiPeriodChange(point)}</td><td>${evidence ? `<button class="text-action" data-action="open-ai-evidence" data-evidence-id="${esc(point.evidenceId)}" aria-label="Mở nguồn ${esc(metricLabel)} · ${esc(point.periodLabel)}">Nguồn</button>` : '—'}</td></tr>`;
    }).join('');
    const periods = periodRows(aiAnalysis.series ?? []);
    const limitations = [...new Set([...(aiAnalysis.quality.limitations || []), ...(aiAnalysis.narrative.limitations || [])])];
    const providerFailure = aiAnalysis.validation.errors[0];
    const providerFailureDetail = providerFailure === 'timeout'
      ? 'Mô hình không trả lời trong thời gian cho phép nên hệ thống đã dừng chờ.'
      : providerFailure === 'rate_limited'
        ? 'Dịch vụ đang giới hạn số yêu cầu và có thể sẵn sàng lại sau.'
        : 'Không kết nối được với dịch vụ diễn giải tự động.';
    const validationCategories = aiAnalysis.validation.categories || [];
    const rejectionDetail = validationCategories.includes('structure') || ['invalid_json', 'claim_schema', 'narrative_identity'].includes(providerFailure)
      ? 'Dịch vụ trả về nội dung sai định dạng nên hệ thống chưa thể sử dụng.'
      : validationCategories.includes('numerical_temporal')
        ? 'Một số giá trị hoặc ngày trong phần diễn giải không khớp với dữ liệu được trích dẫn.'
        : validationCategories.includes('grounding')
          ? 'Phần diễn giải chưa liên kết đầy đủ với dữ liệu nguồn trong phạm vi đang xem.'
          : 'Hệ thống chưa xác minh được một số nhận định trong phần diễn giải.';
    const providerNotice = aiAnalysis.status === 'provider_unavailable'
      ? `<div class="ai-callout warning"><strong>Dịch vụ phân tích tự động tạm thời không phản hồi.</strong><p>${esc(providerFailureDetail)} Kết quả bên dưới vẫn được tạo từ số liệu đã kiểm chứng.</p></div>`
      : aiAnalysis.status === 'rejected_output'
        ? `<div class="ai-callout warning"><strong>Chưa sử dụng được phần diễn giải tự động.</strong><p>${esc(rejectionDetail)} Kết quả từ số liệu đã kiểm chứng vẫn được giữ lại. Bạn có thể chọn “Phân tích lại”.</p></div>`
        : aiAnalysis.validation.status === 'partial'
          ? '<div class="ai-callout warning"><strong>Một số nhận định đã được lược bỏ.</strong><p>Các nhận định đã kiểm chứng và diễn biến từ số liệu vẫn được giữ lại.</p></div>'
        : '';
    const narrativeInsights = aiAnalysis.narrative.insights
      .map(item => `<li>${esc(item.text)}</li>`)
      .join('');
    const storyContent = aiShortWindow(aiAnalysis) ? '' : aiDataStory(aiAnalysis);
    const story = storyContent ? `<details class="ai-details"><summary>Xem chi tiết diễn biến</summary>${storyContent}</details>` : '';
    const periodDisclosure = aiShortWindow(aiAnalysis) ? aiComparisonTable(aiAnalysis) : aiAnalysis.metrics?.length
      ? `<div class="ai-metric-disclosures">${aiAnalysis.metrics.map(metric => `<details class="ai-disclosure ai-periods"><summary><span>${esc(metric.metricDisplayName)}</span><small>${fmt(metric.quality.validPeriodCount)}/${fmt(metric.quality.expectedPeriodCount)} kỳ hợp lệ · xem chi tiết</small></summary><div class="ai-disclosure-body">${metric.series.length ? `<div class="ai-period-table"><table><thead><tr><th>Kỳ</th><th>Giá trị</th><th>So với kỳ hợp lệ trước</th><th>Bằng chứng</th></tr></thead><tbody>${periodRows(metric.series, metric.metricDisplayName)}</tbody></table></div>` : '<p>Chưa có kỳ hợp lệ. Kiểm tra dữ liệu nguồn hoặc chọn khoảng khác.</p>'}</div></details>`).join('')}</div>`
      : `<details class="ai-disclosure ai-periods"><summary><span>Biến động từng ${esc(aiGroupLabel(aiAnalysis.window.groupBy))}</span><small>${fmt(aiAnalysis.series?.length ?? 0)} kỳ · mở để xem bằng chứng</small></summary><div class="ai-disclosure-body"><div class="ai-period-table"><table><thead><tr><th>Kỳ</th><th>Giá trị</th><th>So với kỳ trước</th><th>Bằng chứng</th></tr></thead><tbody>${periods}</tbody></table></div></div></details>`;
    const reading = aiAnalysis.synthesis?.reading;
    const reportOverview = aiAnalysis.narrative.report?.overview?.[0];
    const overviewText = reportOverview?.text || reading?.overview?.text || aiAnalysis.narrative.summary.text;
    const takeawayText = aiAnalysis.narrative.report ? '' : aiAnalysis.narrative.mode === 'ai' && aiAnalysis.narrative.schemaVersion === 'ai-narrative-v4'
      ? aiAnalysis.narrative.summary.text
      : reading?.overview ? (reading.takeaways || []).map(item => item.text).filter(text => !aiReadable(overviewText).includes(aiReadable(text))).join(' ') : '';
    const qualityAlert = limitations.length
      ? `<div class="ai-quality-alert"><strong>Dữ liệu cần lưu ý</strong><p>${esc(limitations[0])}${limitations.length > 1 ? ` Còn ${fmt(limitations.length - 1)} giới hạn khác trong phần chi tiết.` : ''}</p></div>`
      : '';
    result = `<div class="ai-result ${stale ? 'stale' : ''}">
      <div class="ai-result-head"><span class="ai-state ${esc(stateValue)}">${esc(aiStatusLabel(stateValue))}</span><span>${aiAnalysis.metrics ? `${fmt(aiAnalysis.metrics.filter(metric => metric.status === 'ready').length)}/${fmt(aiAnalysis.metrics.length)} chỉ số đủ dữ liệu so sánh · theo ${esc(aiGroupLabel(aiAnalysis.window.groupBy))}` : `${fmt(aiAnalysis.quality.validPeriodCount)}/${fmt(aiAnalysis.quality.expectedPeriodCount)} kỳ ${esc(aiGroupLabel(aiAnalysis.window.groupBy))} có dữ liệu hợp lệ`}</span></div>
      <dl class="ai-scope-receipt" aria-label="Mức hiển thị của kết quả phân tích"><div><dt>${esc(getEntityLevelLabel(resultEntity?.entity_level))}</dt><dd>${esc(selectedName)}</dd></div><div><dt>Khoảng ngày</dt><dd>${dateLabel(aiAnalysis.window.start)}–${dateLabel(aiAnalysis.window.end)}</dd></div><div><dt>Chỉ số</dt><dd>${esc(aiAnalysis.scope.metricDisplayName)}</dd></div><div><dt>Xem theo</dt><dd>${esc(aiGroupLabel(aiAnalysis.window.groupBy))}</dd></div></dl>
      ${stale ? '<div class="ai-callout warning"><strong>Kết quả cũ hơn dữ liệu đang xem.</strong><p>Bộ lọc hoặc dữ liệu đã nhập đã thay đổi. Kết quả cũ được giữ để đối chiếu; hãy chọn “Phân tích lại”.</p></div>' : ''}
      ${providerNotice}
      ${aiAnalysis.status === 'insufficient_data' ? qualityAlert : ''}
      <section class="ai-executive" aria-labelledby="ai-executive-title">
        <div class="ai-section-heading"><h4 id="ai-executive-title">Tổng quan trong thời gian đã chọn</h4><span>${reportOverview ? reportOverview.source === 'ai' ? 'Diễn giải tự động' : 'Tổng hợp từ số liệu' : reading?.overview ? 'Tổng hợp từ số liệu' : aiAnalysis.narrative.mode === 'ai' ? 'Diễn giải tự động' : 'Tóm tắt từ số liệu'}</span></div>
        <p>${esc(aiReadable(overviewText))}</p>
        ${narrativeInsights ? `<ul class="ai-summary-points">${narrativeInsights}</ul>` : ''}
      </section>
      ${aiAnalysis.status !== 'insufficient_data' ? qualityAlert : ''}

      ${aiReadingStory(aiAnalysis)}
      ${aiReportSection(aiAnalysis, 'relationships', 'Các chỉ số liên quan với nhau như thế nào?')}
      ${takeawayText ? `<section class="ai-takeaways"><div class="ai-section-heading"><h4>Điều cần chú ý</h4>${aiAnalysis.narrative.mode === 'ai' && aiAnalysis.narrative.schemaVersion === 'ai-narrative-v4' ? '<span>Diễn giải tự động đã kiểm chứng</span>' : ''}</div><p>${esc(aiReadable(takeawayText))}</p></section>` : ''}
      <details class="ai-verification"><summary>Xem số liệu và nguồn</summary><div class="ai-verification-body">
      ${aiInsightEvidence(aiAnalysis)}
      ${aiAnalyticalDetails(aiAnalysis)}
      ${story}
      ${periodDisclosure}
      <details class="ai-disclosure ai-quality"><summary><span>Bằng chứng &amp; chất lượng dữ liệu</span><small>${limitations.length ? `${fmt(limitations.length)} giới hạn` : 'Không có cảnh báo về độ đầy đủ'}</small></summary><div class="ai-disclosure-body">
        <p class="ai-evidence-note">Mỗi kỳ có thể mở đúng điểm dữ liệu hoặc nhóm dữ liệu nguồn trong bảng biến động.</p>
        ${limitations.length ? `<div class="ai-limitations"><h5>Giới hạn dữ liệu</h5><ul>${limitations.map(item => `<li>${esc(item)}</li>`).join('')}</ul></div>` : '<p class="ai-quality-ok">Các kỳ đang hiển thị không có cảnh báo chất lượng bổ sung.</p>'}
        <details class="ai-technical"><summary>Thông tin kỹ thuật</summary><dl class="ai-meta"><div><dt>Dữ liệu đến</dt><dd>${dateLabel(aiAnalysis.window.currentDate || aiAnalysis.window.end)}</dd></div><div><dt>Tạo lúc</dt><dd>${esc(new Date(aiAnalysis.dataAsOf.generatedAt).toLocaleString('vi-VN'))}</dd></div><div><dt>Dịch vụ</dt><dd>${esc(aiAnalysis.provider.name)}</dd></div><div><dt>Mô hình trí tuệ nhân tạo</dt><dd>${esc(aiAnalysis.provider.model)}</dd></div><div><dt>Mã phiên dữ liệu</dt><dd><code title="${esc(aiAnalysis.dataAsOf.snapshotId)}">${esc(shortHash(aiAnalysis.dataAsOf.snapshotId))}</code></dd></div></dl></details>
      </div></details>
      </div></details>
    </div>`;
  }
  return `<section id="ai-insights" class="ai-panel" aria-labelledby="ai-insights-title">
    <div class="ai-panel-head"><div><h3 id="ai-insights-title">Phân tích KPI tự động</h3><p>Giải thích mối liên hệ và diễn biến KPI; không thay đổi số liệu trên biểu đồ.</p></div></div>
    <div class="ai-controls"><label class="ai-metric">Phạm vi chỉ số<select data-field="aiMetricCode">${select([{value:'all',label:'Tất cả chỉ số · Tổng quan'},{value:'total',label:'Tổng số'},{value:'error',label:'Báo sai/Lỗi'},{value:'error_rate',label:'% báo sai'}], state.aiMetricCode)}</select></label><label class="ai-metric">Nhóm dữ liệu<select data-field="aiGroupBy">${select([{value:'day',label:'Theo ngày'},{value:'week',label:'Theo tuần'},{value:'month',label:'Theo tháng'}], state.aiGroupBy)}</select></label><button class="primary ai-generate" data-action="generate-ai-insight" aria-disabled="${disabled}" aria-describedby="ai-availability-note${scopeBlocked ? ' ai-scope-note' : ''}" ${hardDisabled ? 'disabled' : ''}>${actionLabel}</button></div>
    ${statusCopy}${scopeCopy}${error}
    <p id="ai-status-message" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></p>
    <div class="ai-output" aria-busy="${aiLoading}">${result}</div>
  </section>`;
}

function replaceInteractiveMarkup(root: HTMLElement, markup: string): void {
  const active = root.contains(document.activeElement) && document.activeElement instanceof HTMLElement
    ? { field: document.activeElement.dataset.field, action: document.activeElement.dataset.action }
    : null;
  root.innerHTML = markup;
  if (!active?.field && !active?.action) return;
  requestAnimationFrame(() => {
    const next = Array.from(root.querySelectorAll<HTMLElement>('[data-field], [data-action]')).find(item => (
      (active.field && item.dataset.field === active.field) || (active.action && item.dataset.action === active.action)
    ));
    next?.focus();
  });
}

function analyticsHost(body: HTMLDivElement, tab: Tab, preamble: string, postamble = ''): HTMLDivElement {
  if (body.dataset.workspaceTab !== tab || !body.querySelector('[data-analytics-postamble]')) {
    disposeCharts(body);
    body.innerHTML = '<div data-analytics-preamble></div><div data-chart-host></div><div data-analytics-postamble></div>';
    body.dataset.workspaceTab = tab;
  }
  const preambleRoot = body.querySelector<HTMLDivElement>('[data-analytics-preamble]')!;
  const postambleRoot = body.querySelector<HTMLDivElement>('[data-analytics-postamble]')!;
  replaceInteractiveMarkup(preambleRoot, preamble);
  replaceInteractiveMarkup(postambleRoot, postamble);
  return body.querySelector<HTMLDivElement>('[data-chart-host]')!;
}

function replaceChartCardPresentation(card: HTMLElement, markup: string): void {
  const template = document.createElement('template');
  template.innerHTML = markup.trim();
  const fresh = template.content.firstElementChild as HTMLElement;
  const currentTop = card.querySelector('.card-top');
  const freshTop = fresh.querySelector('.card-top');
  if (currentTop && freshTop) currentTop.replaceWith(freshTop);
  const plot = card.querySelector<HTMLElement>('[data-plot]');
  const freshPlot = fresh.querySelector<HTMLElement>('[data-plot]');
  if (plot && freshPlot) plot.setAttribute('aria-label', freshPlot.getAttribute('aria-label') || 'Biểu đồ');
}

function reconcileChartCollection(host: HTMLDivElement, charts: Chart[], section: 'overview' | 'statistics'): void {
  if (!charts.length) {
    disposeCharts(host);
    host.innerHTML = empty(section === 'statistics' ? 'Không có kỳ dữ liệu phù hợp.' : 'Không có dữ liệu trong khoảng thời gian đã chọn.');
    return;
  }
  let grid = host.querySelector<HTMLDivElement>(':scope > .chart-grid');
  if (!grid) {
    host.innerHTML = '<div class="chart-grid"></div>';
    grid = host.querySelector<HTMLDivElement>(':scope > .chart-grid')!;
  }
  const previousGridClass = grid.className;
  grid.className = `chart-grid ${hasSiblingCharts(charts) ? 'children-grid' : ''}`.trim();
  const wanted = new Set(charts.map(chart => chartPlotKey(section, chart.entityId)));
  grid.querySelectorAll<HTMLElement>(':scope > [data-chart-key]').forEach(card => {
    const key = card.dataset.chartKey || '';
    if (wanted.has(key)) return;
    disposeCharts(card); card.remove(); chartFingerprints.delete(key);
  });
  charts.forEach((chart, index) => {
    const key = chartPlotKey(section, chart.entityId);
    const markup = chartCard(chart, section);
    let card = Array.from(grid!.children).find(item => (item as HTMLElement).dataset.chartKey === key) as HTMLElement | undefined;
    if (!card) {
      const template = document.createElement('template'); template.innerHTML = markup.trim();
      card = template.content.firstElementChild as HTMLElement;
      grid!.insertBefore(card, grid!.children[index] || null);
    } else {
      replaceChartCardPresentation(card, markup);
      if (grid!.children[index] !== card) grid!.insertBefore(card, grid!.children[index] || null);
    }
    draw(key, chart.figure, chart.entityId);
  });
  if (previousGridClass !== grid.className) requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
}

function reconcileComparison(host: HTMLDivElement): void {
  if (!workspace?.comparison) {
    disposeCharts(host);
    const candidates = workspace?.comparisonCandidates || [];
    host.innerHTML = state.comparisonEntities.length >= 2
      ? statePanel('Không tạo được biểu đồ so sánh', 'Các nội dung được chọn cần cùng đơn vị đo và có dữ liệu cho chỉ số, khoảng thời gian hiện tại.')
      : statePanel('Chưa đủ nội dung để so sánh', candidates.length < 2 ? 'Không đủ nội dung có dữ liệu cho chỉ số và khoảng thời gian hiện tại. Hãy đổi bộ lọc.' : 'Chọn từ 2 đến 3 nội dung có cùng đơn vị đo.');
    return;
  }
  const markup = `<article class="chart-card" data-chart-key="comparison"><div class="card-top"><h3>So sánh ${escMetric(state.comparisonMetric)}</h3><span class="pill">Cùng đơn vị</span></div><div class="plot" data-plot="comparison" aria-label="Biểu đồ so sánh ${escMetric(state.comparisonMetric)}"></div></article>`;
  let grid = host.querySelector<HTMLDivElement>(':scope > .chart-grid');
  if (!grid) { host.innerHTML = '<div class="chart-grid one"></div>'; grid = host.querySelector<HTMLDivElement>(':scope > .chart-grid')!; }
  let card = grid.querySelector<HTMLElement>(':scope > [data-chart-key="comparison"]');
  if (!card) {
    const template = document.createElement('template'); template.innerHTML = markup;
    card = template.content.firstElementChild as HTMLElement; grid.replaceChildren(card);
  } else replaceChartCardPresentation(card, markup);
  const comparisonIdentity = `comparison:${state.comparisonMetric}:${[...state.comparisonEntities].sort().join(',')}`;
  draw('comparison', workspace.comparison, 'comparison', comparisonIdentity);
}

function renderTab(): void {
  const body = document.querySelector<HTMLDivElement>('#tab-body');
  if (!body) return;
  delete body.dataset.workspaceScope;
  pendingChartRenders = [];
  if (!bootstrapLoaded) { body.innerHTML = statePanel('Đang kiểm tra dữ liệu', 'Vui lòng chờ trong khi kết nối kho dữ liệu.'); return; }
  if (bootstrapError) {
    if (state.tab === 'import' && importResult) {
      renderImport(body);
      body.insertAdjacentHTML('afterbegin', statePanel('Chưa tải lại được bảng điều khiển', 'Kết quả nhập bên dưới vẫn được giữ trong thẻ này. Kiểm tra kết nối rồi thử tải lại dữ liệu.', true));
    } else body.innerHTML = statePanel('Không kết nối được kho dữ liệu', 'Máy chủ chưa phản hồi. Kiểm tra kết nối hoặc thử lại; chưa cần nhập lại tệp Excel.', true);
    return;
  }
  if (!currentProject()) {
    body.innerHTML = statePanel('Chưa có dữ liệu đã nhập', 'Mở Nhập Excel để chọn tệp đầu tiên.');
    if (state.tab === 'import') renderImport(body);
    if (state.tab === 'history') renderHistory(body);
    return;
  }
  const analyticalTab = ['overview', 'statistics', 'comparison', 'audit'].includes(state.tab);
  if (analyticalTab && workspaceView !== state.tab && !(state.tab === 'audit' && auditFocus)) {
    body.innerHTML = statePanel('Đang tải dữ liệu', 'Đang chuẩn bị dữ liệu cho khu vực vừa chọn.');
    return;
  }
  if (workspaceError && !workspace && ['overview', 'statistics', 'comparison', 'audit'].includes(state.tab)) {
    body.innerHTML = statePanel('Không tải được dữ liệu phân tích', `Bộ lọc được giữ nguyên. ${workspaceError} Thử tải lại khi máy chủ hoạt động.`, true);
    return;
  }
  if (loading && !workspace && ['overview', 'statistics', 'comparison', 'audit'].includes(state.tab)) {
    body.innerHTML = statePanel('Đang tải dữ liệu', 'Đang áp dụng dự án, nội dung theo dõi và khoảng thời gian đã chọn.');
    return;
  }
  if (state.tab === 'overview') {
    body.dataset.workspaceScope = state.scope;
    const host = analyticsHost(
      body,
      state.tab,
      `<p class="section-desc">Biểu đồ Tổng số ghi nhận, Tổng báo sai (lỗi) và Tỷ lệ báo sai theo ${state.scope === 'children' ? getChildrenScopeLabel(currentEntity()?.entity_level).toLowerCase() : getCurrentScopeLabel(currentEntity()?.entity_level).toLowerCase()}.</p>`,
      renderAIInsights(),
    );
    reconcileChartCollection(host, workspace?.overview || [], 'overview');
  } else if (state.tab === 'statistics') {
    const host = analyticsHost(body, state.tab, `<div class="control-bar"><label>Xem theo<select data-field="statisticsGroup">${select([{value:'day',label:'Ngày'},{value:'week',label:'Tuần'},{value:'month',label:'Tháng'},{value:'quarter',label:'Quý'}], state.statisticsGroup)}</select></label>
      <label>Cách tính<select data-field="statisticsMode">${select([{value:'both',label:'Tổng và trung bình/ngày'},{value:'sum',label:'Tổng'},{value:'average',label:'Trung bình/ngày'}], state.statisticsMode)}</select></label>
      <label>Khoảng thống kê<select data-field="statisticsRange">${select([{value:'recent',label:'Các kỳ gần nhất'},{value:'all',label:'Toàn bộ dữ liệu'},{value:'custom',label:'Chọn khoảng kỳ'}], state.statisticsRange)}</select></label>
      ${state.statisticsRange === 'recent' ? `<label>Số kỳ<input data-field="statisticsCount" type="number" min="1" max="60" value="${state.statisticsCount}"></label>` : ''}
      ${state.statisticsRange === 'custom' ? `<label>Từ kỳ<input data-field="statisticsFrom" type="date" value="${esc(state.statisticsFrom)}"></label><label>Đến kỳ<input data-field="statisticsTo" type="date" value="${esc(state.statisticsTo)}"></label>` : ''}
      <label class="check"><input data-field="includeIncomplete" type="checkbox" ${state.includeIncomplete ? 'checked' : ''}> Bao gồm kỳ chưa đầy đủ</label></div>
      ${statisticsReceipt()}<p class="section-desc">Kết quả tổng và trung bình mỗi ngày được tính từ toàn bộ lịch sử của ${getCurrentScopeLabel(currentEntity()?.entity_level).toLowerCase()}, độc lập với khoảng ngày ở thanh bên. ${workspace?.statisticsPeriods.length || 0} kỳ đang hiển thị.</p>`);
    reconcileChartCollection(host, workspace?.statistics || [], 'statistics');
  } else if (state.tab === 'comparison') {
    const candidates = workspace?.comparisonCandidates || [];
    const host = analyticsHost(body, state.tab, `<div class="control-bar"><label>Chỉ số<select data-field="comparisonMetric">${select(['Tổng số','Báo sai/Lỗi','% báo sai'].map(value => ({value,label:value})), state.comparisonMetric)}</select></label><div class="comparison-hint">Chọn 2–3 nội dung theo dõi có dữ liệu trong khoảng thời gian đang xem và cùng đơn vị đo.</div></div>
      <div class="entity-picks">${candidates.map(item => `<label class="entity-pick"><input type="checkbox" data-compare="${esc(item.entity_id)}" ${state.comparisonEntities.includes(item.entity_id) ? 'checked' : ''}><span>${esc(displayEntityName(entities.find(entity => entity.entity_id === item.entity_id), item.entity_label))}<small>${esc(item.effective_unit)}</small></span></label>`).join('')}</div>`);
    reconcileComparison(host);
  } else if (state.tab === 'audit') {
    const audit = workspace?.audit;
    const columns = ['date','entity_path','metric_normalized','raw_value','display_value','chart_value','value_kind','sheet_name','cell_address','validation_status'];
    const focused = auditFocus?.status === 'ready' ? auditFocus.lookup.row : null;
    const focusPanel = !auditFocus ? '' : auditFocus.status === 'loading'
      ? '<section class="audit-focus" aria-busy="true"><strong>Đang mở đúng điểm dữ liệu và phiên bản…</strong></section>'
      : auditFocus.status === 'error'
        ? `<section class="audit-focus error"><strong>Không mở được dòng đối chiếu</strong><p>${esc(auditFocus.error)}</p><button class="ghost" data-action="retry-audit-lookup">Thử lại</button><button class="ghost" data-action="return-to-chart">Quay lại biểu đồ</button></section>`
        : `<section class="audit-focus"><div><strong>Dòng đối chiếu của điểm đã chọn</strong><p>Đã mở đúng điểm dữ liệu và phiên bản nguồn của điểm biểu đồ, kể cả khi dòng này không nằm trong trang đối chiếu hiện tại.</p></div><button class="ghost" data-action="return-to-chart">Quay lại biểu đồ</button><div class="table-wrap"><table><thead><tr>${columns.map(col => `<th>${esc(auditHeaders[col])}</th>`).join('')}</tr></thead><tbody><tr id="focused-audit-row" class="focused-audit-row" tabindex="-1">${columns.map(col => `<td title="${esc(auditCell(col, focused?.[col]))}">${esc(auditCell(col, focused?.[col]))}</td>`).join('')}</tr></tbody></table></div></section>`;
    body.innerHTML = `${focusPanel}<p class="section-desc">Đối chiếu giá trị đã nhập với trang tính và ô Excel nguồn · ${fmt(audit?.total || 0)} điểm dữ liệu theo bộ lọc.</p>
      ${audit?.total ? `<div class="table-wrap"><table><thead><tr>${columns.map(col => `<th>${esc(auditHeaders[col])}</th>`).join('')}</tr></thead><tbody>${audit.rows.map(row => `<tr>${columns.map(col => `<td title="${esc(auditCell(col, row[col]))}">${esc(auditCell(col, row[col]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <div class="pager"><button data-action="audit-prev" ${!audit.offset ? 'disabled' : ''}>← Trước</button><span>${fmt(audit.offset + 1)}–${fmt(Math.min(audit.offset + audit.rows.length, audit.total))} / ${fmt(audit.total)}</span><button data-action="audit-next" ${audit.offset + audit.rows.length >= audit.total ? 'disabled' : ''}>Sau →</button></div>` : statePanel('Không có dòng đối chiếu theo bộ lọc', 'Hãy đổi nội dung theo dõi hoặc khoảng thời gian để xem dữ liệu nguồn.')}`;
  } else if (state.tab === 'import') renderImport(body);
  else renderHistory(body);
  restorePendingFocus();
}
function empty(messageText: string): string { return `<div class="empty"><div class="empty-icon">▥</div><h3>${esc(messageText)}</h3><p>Thử đổi dự án, nội dung theo dõi hoặc khoảng thời gian trong thanh bên.</p></div>`; }
function draw(key: string, figure: Figure, entityRef: string, chartIdentity = key): void {
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
  const selectedRef = selection?.origin.plotKey === key ? aggregateParent?.selection.aggregateRef || selection.aggregateRef || selection.observationRef || undefined : undefined;
  const height = element.closest('.children-grid') ? 380 : 420;
  const fingerprintStarted = performance.now();
  const fingerprint = JSON.stringify({ figure: prepared, selectedRef, height });
  const unchanged = element.classList.contains('js-plotly-plot') && chartFingerprints.get(key) === fingerprint;
  if (renderingWorkspaceTrace) recordFingerprint(renderingWorkspaceTrace, performance.now() - fingerprintStarted, !unchanged);
  if (unchanged) return;
  chartFingerprints.set(key, fingerprint);
  const render = renderChart(
    element,
    prepared,
    point => openInvestigation(key, entityRef, point),
    selectedRef,
    height,
    `${state.project}:${chartIdentity}`,
  );
  pendingChartRenders.push(render.catch(error => {
    console.error(`Không thể cập nhật biểu đồ ${key}.`, error);
  }));
}

function dataVersionKey(value: DataVersion): string {
  return value ? `${value.committedImportRef}:${value.committedAt}` : 'none';
}

function inferContextualMetric(chart: Chart | undefined): string | null {
  if (!chart) return null;
  const metrics = ['Tổng số', 'Báo sai/Lỗi', '% báo sai'].filter(metric =>
    chart.figure.data.some(trace => String(trace.name || '').includes(metric))
  );
  return metrics.length === 1 ? metrics[0] : null;
}

function defaultContextualMetric(chart: Chart | undefined): string {
  const inherited = inferContextualMetric(chart);
  if (inherited) return inherited;
  return ['Tổng số', 'Báo sai/Lỗi', '% báo sai'].includes(state.comparisonMetric)
    ? state.comparisonMetric : 'Báo sai/Lỗi';
}

function comparisonReason(reason: string | null | undefined, level?: string): string {
  return getEligibilityReasonMessage(reason, level);
}

function contextualCandidateList(session: ContextualComparison): ComparisonCandidate[] {
  if (session.response) return session.response.comparisonCandidates;
  return structuralSiblings(session.anchorId).map(item => ({
    entity_id: item.entity_id, entity_label: item.entity_label,
    effective_unit: item.effective_unit, eligible: undefined,
  }));
}

function contextualRangeLabel(context: ComparisonContext | null | undefined): string {
  if (!context?.range.start || !context.range.end) return 'Chưa có kỳ dữ liệu phù hợp';
  return `${dateLabel(context.range.start)}–${dateLabel(context.range.end)}`;
}

function contextualCalculationLabel(context: ComparisonContext | null | undefined): string {
  if (!context) return 'Theo phép tính hiện có';
  if (context.calculation === 'weighted_rate') return 'Tỷ lệ có trọng số';
  return context.calculation === 'average_per_day' ? 'Trung bình mỗi ngày' : 'Tổng trong kỳ';
}

function restoreInvestigationDrawerHost(): void {
  const drawer = document.querySelector<HTMLElement>('#investigation-drawer');
  const shell = app.querySelector<HTMLElement>('.shell');
  if (drawer && shell && drawer.closest('#contextual-comparison-dialog')) shell.appendChild(drawer);
}

function dockInvestigationDrawerInContextualDialog(): void {
  const drawer = document.querySelector<HTMLElement>('#investigation-drawer');
  const host = document.querySelector<HTMLElement>('.contextual-investigation-host');
  if (drawer && host) host.appendChild(drawer);
}

function closeContextualInvestigation(): void {
  if (investigationSelection()?.origin.plotKey !== 'contextual-comparison') return;
  investigationRequest?.abort(); investigation = { status: 'closed' };
  aggregateParent = null; revisionHistory = null; importDetail = null; investigationLiveMessage = '';
  renderInvestigation();
}

function renderContextualComparison(): void {
  const root = document.querySelector<HTMLDivElement>('#contextual-comparison-root');
  if (!root) return;
  restoreInvestigationDrawerHost();
  disposeCharts(root);
  if (!contextualComparison) { root.replaceChildren(); document.body.classList.remove('modal-open'); return; }
  const session = contextualComparison;
  const anchor = entities.find(item => item.entity_id === session.anchorId);
  if (!anchor) { closeContextualComparison(); return; }
  const response = session.response;
  const context = response?.comparisonContext;
  const terminology = getComparisonTerminology(anchor.entity_level);
  const candidates = contextualCandidateList(session);
  const stale = session.status === 'stale';
  const busy = session.status === 'loading';
  const controlsDisabled = stale;
  const atLimit = session.selected.length >= 3;
  const hasComparisonBasis = session.lens === 'statistics' || Boolean(session.metric);
  const removed = response?.comparisonSelection?.removed || [];
  const candidateMarkup = candidates.map(item => {
    const candidateEntity = entities.find(entity => entity.entity_id === item.entity_id);
    const checked = session.selected.includes(item.entity_id);
    const eligibilityKnown = typeof item.eligible === 'boolean';
    const eligible = item.eligible !== false;
    const disabled = controlsDisabled || !hasComparisonBasis || !eligible || (!checked && atLimit);
    const detail = !hasComparisonBasis
      ? 'Chọn chỉ số để kiểm tra điều kiện'
      : !eligibilityKnown ? 'Đang kiểm tra điều kiện…'
        : eligible ? `${fmt(item.comparablePeriodCount || 0)} kỳ có thể đối chiếu`
          : comparisonReason(item.reason, candidateEntity?.entity_level || anchor.entity_level);
    return `<label class="contextual-entity ${eligible ? '' : 'ineligible'}">
      <input type="checkbox" data-context-compare="${esc(item.entity_id)}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}>
      <span><strong>${esc(displayEntityName(candidateEntity, item.entity_label))}</strong><small>${esc(item.effective_unit || 'Chưa xác định đơn vị đo')} · ${esc(detail)}</small></span>
    </label>`;
  }).join('');
  const anchorEligible = context?.anchorEligible !== false;
  const statusMarkup = stale
    ? `<div class="contextual-banner warning" role="alert"><div><strong>Có dữ liệu mới hơn.</strong><p>Dữ liệu mới đã được nhập. Kết quả đang xem vẫn thuộc phiên bản trước.</p></div><button class="primary" data-action="update-contextual-data">Cập nhật dữ liệu</button></div>`
    : session.status === 'error'
      ? `<div class="contextual-banner error" role="alert"><div><strong>Không tải được phép so sánh.</strong><p>${esc(session.error)}</p></div><button class="ghost" data-action="retry-contextual-comparison">Thử lại</button></div>`
      : session.notice
        ? `<div class="contextual-banner notice" role="status">${esc(session.notice)}</div>` : '';
  let resultMarkup = '';
  if (session.lens === 'metric' && !session.metric) {
    resultMarkup = `<div class="contextual-empty"><strong>Chọn chỉ số cần so sánh</strong><p>Biểu đồ nguồn có nhiều chỉ số hoặc chuỗi dữ liệu nên hệ thống không tự suy đoán. Mức thời gian, phạm vi kỳ và đơn vị sẽ được kế thừa tự động.</p></div>`;
  } else if (context && !anchorEligible) {
    resultMarkup = `<div class="contextual-empty"><strong>${esc(terminology.anchorLabel)} chưa thể so sánh</strong><p>${esc(comparisonReason(context.anchorReason, anchor.entity_level))} ${session.lens === 'statistics' ? 'Hãy đổi cách tính hoặc kiểm tra dữ liệu nguồn.' : 'Hãy chọn chỉ số khác hoặc kiểm tra dữ liệu nguồn.'}</p></div>`;
  } else if (response?.comparison) {
    resultMarkup = `<div class="contextual-results"><div class="contextual-chart-frame"><div class="contextual-plot" data-plot="contextual-comparison" role="img" aria-label="${session.lens === 'statistics' ? 'Biểu đồ so sánh thống kê' : `Biểu đồ so sánh ${escMetric(session.metric)}`}"></div>${busy ? '<div class="contextual-loading">Đang cập nhật kết quả…</div>' : ''}</div></div>`;
  } else if (busy) {
    resultMarkup = `<div class="contextual-empty" aria-busy="true"><strong>Đang kiểm tra ${esc(terminology.candidatePlural)} có thể so sánh…</strong><p>Kết quả từ yêu cầu cũ sẽ không ghi đè kết quả mới hơn.</p></div>`;
  } else {
    resultMarkup = `<div class="contextual-empty"><strong>${esc(terminology.emptyMessage)}</strong><p>Các nội dung được chọn cần cùng đơn vị đo và có khoảng thời gian chung.</p></div>`;
  }
  const removedText = removed.length
    ? `<p class="contextual-removal-note">Đã bỏ ${removed.map(item => { const entity = entities.find(candidate => candidate.entity_id === item.entityId); return `${displayEntityName(entity, item.entityId)}: ${comparisonReason(item.reason, entity?.entity_level || anchor.entity_level)}`; }).join('; ')}.</p>`
    : '';
  const versionLabel = session.sourceDataVersion?.committedImportRef || 'Chưa có phiên bản';
  root.innerHTML = `<dialog id="contextual-comparison-dialog" class="contextual-comparison-dialog" aria-labelledby="contextual-title">
    <div class="contextual-shell">
      <header class="contextual-header"><div><span class="contextual-eyebrow">Thống kê · So sánh</span><h2 id="contextual-title">${esc(terminology.title)}</h2><p>${esc(terminology.description)}</p></div><button class="dialog-close" data-action="close-contextual-comparison" aria-label="Đóng so sánh">Đóng</button></header>
      <div class="contextual-status-slot">${statusMarkup}</div>
      <div class="contextual-lenses" role="tablist" aria-label="Cách xem so sánh"><button role="tab" aria-selected="${session.lens === 'metric'}" class="${session.lens === 'metric' ? 'active' : ''}" data-action="contextual-lens-metric">Chỉ số gốc</button><button role="tab" aria-selected="${session.lens === 'statistics'}" class="${session.lens === 'statistics' ? 'active' : ''}" data-action="contextual-lens-statistics">Thống kê</button></div>
      <div class="contextual-receipt"><span>Đang so sánh từ: <strong>${esc(getEntityDisplayName(anchor))}</strong></span><span>Theo ${esc(({ day: 'ngày', week: 'tuần', month: 'tháng', quarter: 'quý' })[state.statisticsGroup])}</span><span>${esc(contextualRangeLabel(context))}</span><span>${esc(contextualCalculationLabel(context))}</span></div>
      <div class="contextual-layout">
        <aside class="contextual-selector" aria-label="${esc(terminology.selectorLabel)}"><div class="contextual-selector-head"><div><span>${esc(terminology.selectorLabel)}</span><strong>Đã chọn ${fmt(session.selected.length)}/3 ${esc(terminology.candidatePlural)}</strong></div><p>Nội dung đang xem được giữ cố định.</p></div>
          <label class="contextual-entity anchor"><input type="checkbox" checked disabled><span><strong>${esc(getEntityDisplayName(anchor))}</strong><small>Đang xem · ${esc(anchor.effective_unit || 'Chưa xác định đơn vị đo')}</small></span></label>
          <div class="contextual-candidates">${candidateMarkup || `<p class="contextual-no-sibling">${esc(terminology.noCandidateMessage)}</p>`}</div>${removedText}
        </aside>
        <section class="contextual-main" aria-live="polite">
          <div class="contextual-basis"><div><span class="contextual-eyebrow">Cơ sở so sánh</span><strong>${session.lens === 'statistics' ? 'Chọn một cách tính' : 'Chỉ số được chọn sẵn'}</strong><small>${session.lens === 'statistics' ? 'Áp dụng cho cả Tổng số ghi nhận và Tổng báo sai (lỗi); không cần chọn lại chỉ số.' : 'Đổi chỉ số khi cần; các nội dung còn phù hợp sẽ được giữ lại.'}</small></div><div class="contextual-basis-fields ${session.lens}">${session.lens === 'statistics' ? `<label>Cách tính<select id="contextual-calculation" data-context-field="calculation" ${controlsDisabled ? 'disabled' : ''}>${select([{ value: 'sum', label: 'Tổng trong kỳ' }, { value: 'average_per_day', label: 'Trung bình mỗi ngày' }], session.calculation)}</select></label>` : `<label>Chỉ số<select id="contextual-metric" data-context-field="metric" ${controlsDisabled ? 'disabled' : ''}>${select(['Tổng số','Báo sai/Lỗi','% báo sai'].map(value => ({ value, label:value })), session.metric || 'Báo sai/Lỗi')}</select></label>`}</div></div>
          ${resultMarkup}
        </section>
        <div class="contextual-investigation-host" aria-label="Bằng chứng của điểm đang chọn"></div>
      </div>
      <footer class="contextual-footer"><span>Phiên bản dữ liệu: ${esc(shortHash(versionLabel))}</span><div><button class="primary" data-action="close-contextual-comparison">Xong</button></div></footer>
    </div>
  </dialog>`;
  const dialog = root.querySelector<HTMLDialogElement>('#contextual-comparison-dialog')!;
  dialog.showModal();
  document.body.classList.add('modal-open');
  dockInvestigationDrawerInContextualDialog();
  renderInvestigation();
  if (response?.comparison) {
    const plot = root.querySelector<HTMLElement>('[data-plot="contextual-comparison"]');
    if (plot) void renderChart(
      plot, response.comparison, point => openInvestigation('contextual-comparison', session.anchorId, point), undefined,
      Math.max(260, Math.min(380, plot.clientHeight || 380)),
      `${state.project}:contextual:${session.anchorId}:${session.lens}:${session.metric}:${session.calculation}:${session.selected.join(',')}`,
    ).catch(error => { console.error('Không thể cập nhật biểu đồ so sánh theo ngữ cảnh.', error); });
  }
  requestAnimationFrame(() => {
    const focusTarget = contextualFocusId ? document.getElementById(contextualFocusId) : null;
    contextualFocusId = '';
    (focusTarget || root.querySelector<HTMLElement>(hasComparisonBasis ? '[data-context-compare]:not(:disabled)' : '#contextual-metric') || root.querySelector<HTMLElement>('.dialog-close'))?.focus();
  });
}

function openContextualComparison(anchorId: string, sourceButtonId: string): void {
  if (!workspace || state.tab !== 'statistics' || state.scope !== 'children') return;
  if (investigation.status !== 'closed') {
    investigationRequest?.abort(); investigation = { status: 'closed' };
    aggregateParent = null; revisionHistory = null; importDetail = null; investigationLiveMessage = '';
    renderInvestigation();
  }
  const sourceChart = workspace.statistics.find(chart => chart.entityId === anchorId);
  let lens: ContextualComparison['lens'] = 'metric';
  try { lens = sessionStorage.getItem(CONTEXTUAL_LENS_KEY) === 'statistics' ? 'statistics' : 'metric'; } catch { /* Optional preference. */ }
  const inheritedMetric = defaultContextualMetric(sourceChart);
  const metric = inheritedMetric;
  contextualComparisonRequest?.abort();
  contextualComparison = {
    anchorId, sourceButtonId, sourceScrollY: window.scrollY,
    sourceDataVersion: workspace.dataVersion, latestDataVersion: workspace.dataVersion,
    lens, calculation: 'sum', metric, selected: [anchorId], status: 'loading',
    response: null, error: '', notice: '',
  };
  renderContextualComparison();
  void loadContextualComparison();
}

function closeContextualComparison(): void {
  const session = contextualComparison;
  contextualComparisonRequest?.abort(); contextualComparisonRequest = null;
  contextualComparison = null;
  restoreInvestigationDrawerHost();
  closeContextualInvestigation();
  const root = document.querySelector<HTMLDivElement>('#contextual-comparison-root');
  if (root) { disposeCharts(root); root.replaceChildren(); }
  document.body.classList.remove('modal-open');
  if (session) requestAnimationFrame(() => {
    window.scrollTo({ top: session.sourceScrollY });
    document.getElementById(session.sourceButtonId)?.focus();
  });
}

async function loadContextualComparison(): Promise<void> {
  const session = contextualComparison;
  if (!session || !workspace || (session.lens === 'metric' && !session.metric)) return;
  contextualComparisonRequest?.abort();
  const current = new AbortController(); contextualComparisonRequest = current;
  session.status = 'loading'; session.error = ''; session.notice = '';
  renderContextualComparison();
  const params = new URLSearchParams({
    view: 'comparison', mode: state.mode, count: String(state.count),
    entity: workspace.selectedEntity, scope: 'children',
    statistics_group: state.statisticsGroup, statistics_mode: state.statisticsMode,
    statistics_count: String(state.statisticsRange === 'all' ? 3660 : state.statisticsCount),
    include_incomplete: String(state.includeIncomplete),
    comparison_anchor: session.anchorId, comparison_lens: 'metric',
    comparison_calculation: session.calculation,
    comparison_metric: session.metric || 'Báo sai/Lỗi', comparison_entities: session.selected.join(','),
  });
  params.set('comparison_lens', session.lens);
  if (state.mode === 'custom' && state.start && state.end) { params.set('start', state.start); params.set('end', state.end); }
  if (state.statisticsRange === 'custom') {
    if (state.statisticsFrom) params.set('statistics_from', state.statisticsFrom);
    if (state.statisticsTo) params.set('statistics_to', state.statisticsTo);
  }
  try {
    const result = await api<Workspace>(`/projects/${encodeURIComponent(state.project)}/workspace?${params}`, { signal: current.signal });
    if (current !== contextualComparisonRequest || session !== contextualComparison) return;
    session.latestDataVersion = result.dataVersion;
    if (dataVersionKey(result.dataVersion) !== dataVersionKey(session.sourceDataVersion)) {
      session.status = 'stale'; session.response = null;
      session.notice = 'Phiên bản dữ liệu nguồn đã thay đổi trong khi đang so sánh.';
    } else {
      session.response = result;
      session.selected = result.comparisonSelection?.accepted || [session.anchorId];
      session.status = 'ready';
      const removed = result.comparisonSelection?.removed || [];
      if (removed.length) {
        const anchor = entities.find(entity => entity.entity_id === session.anchorId);
        const terms = getComparisonTerminology(anchor?.entity_level);
        session.notice = `${fmt(removed.length)} ${terms.candidatePlural} đã được bỏ vì không còn đáp ứng điều kiện so sánh.`;
      }
    }
    contextualComparisonRequest = null; renderContextualComparison();
  } catch (error) {
    if (current.signal.aborted || current !== contextualComparisonRequest || session !== contextualComparison) return;
    contextualComparisonRequest = null; session.status = 'error'; session.error = (error as Error).message;
    renderContextualComparison();
  }
}

async function updateContextualData(): Promise<void> {
  const session = contextualComparison;
  if (!session) return;
  closeContextualInvestigation();
  session.status = 'loading'; renderContextualComparison();
  await loadWorkspace(0, true);
  if (session !== contextualComparison || !workspace) return;
  session.sourceDataVersion = workspace.dataVersion;
  session.latestDataVersion = workspace.dataVersion;
  session.response = null; session.selected = [session.anchorId];
  await loadContextualComparison();
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
        title: 'Bản chụp đầy đủ · cần xác nhận bổ sung',
        body: 'Giá trị trùng khóa trong tệp Excel có thể tạo phiên bản mới, thay phiên bản hiện hành. Giá trị vắng mặt trong tệp không bị tự động xóa theo chính sách hiện tại.',
      }
    : {
        title: 'Dữ liệu bổ sung · rủi ro thấp hơn',
        body: 'Chỉ giá trị xuất hiện trong tệp Excel được thêm hoặc cập nhật. Dữ liệu hiện có nhưng không xuất hiện trong tệp vẫn được giữ nguyên.',
      };
}
function validationIssues(value: Preview): string {
  const visible = showAllIssues ? value.issues : value.issues.slice(0, 8);
  if (!visible.length) return `<p class="issue-empty">${value.errorCount + value.warningCount ? 'Có lỗi hoặc cảnh báo, nhưng máy chủ chưa trả chi tiết trong phần xem trước.' : 'Không có lỗi hoặc cảnh báo.'}</p>`;
  const rows = visible.map(issue => `<div class="issue-row"><span class="issue-severity ${issue.severity.toLowerCase()}">${esc(validationLabel(issue.severity.toLowerCase()))}</span><div><p>${escMetric(issue.message)}</p></div></div>`).join('');
  const hidden = value.issues.length - visible.length;
  return `${rows}${hidden > 0 ? `<button class="text-action" data-action="toggle-issues">Xem thêm ${fmt(hidden)} mục kiểm tra</button>` : showAllIssues && value.issues.length > 8 ? '<button class="text-action" data-action="toggle-issues">Thu gọn danh sách</button>' : ''}`;
}
function reportIsTruncated(value: Preview): boolean { return value.issues.length < value.errorCount + value.warningCount; }
function reportDownloadLabel(value: Preview): string { return reportIsTruncated(value) ? 'Tải phần kết quả đã trả về' : 'Tải kết quả kiểm tra'; }
function importOutcomeCard(result: ImportResult): string {
  const outcome = result.outcome;
  const revisionId = outcome.run_id ?? outcome.duplicate_of_run_id;
  const isCommitted = outcome.status === 'committed';
  const title = isCommitted ? 'Đã nhập tệp Excel' : outcome.status === 'duplicate' ? 'Tệp Excel đã được nhập trước đó' : 'Lần nhập đã kết thúc';
  return `<section id="import-result" class="import-result ${isCommitted ? 'success' : 'neutral'}" role="status" aria-live="polite" aria-atomic="true" tabindex="-1">
    <div class="result-heading"><div><span>Kết quả nhập dữ liệu</span><h3>${esc(title)}</h3><p>${isCommitted ? importPhase === 'committing' ? 'Dữ liệu đã được ghi. Đang tải lại biểu đồ và lịch sử nhập…' : bootstrapError || workspaceError ? 'Dữ liệu đã được ghi. Bảng điều khiển chưa tải lại được; thử làm mới khi kết nối ổn định.' : 'Dữ liệu đã được ghi vào kho nội bộ. Biểu đồ đã được tải lại.' : outcome.status === 'duplicate' ? 'Không ghi thêm dữ liệu trùng; bạn có thể xem lần nhập trước trong lịch sử.' : esc(outcome.message || 'Hãy xem lịch sử nhập để kiểm tra kết quả.')}</p></div><strong>${new Date(result.committedAt).toLocaleString('vi-VN')}</strong></div>
    <dl class="outcome-grid">
      <div><dt>Thêm mới</dt><dd>${fmt(outcome.inserted_count)}</dd></div><div><dt>Cập nhật phiên bản</dt><dd>${fmt(outcome.updated_count)}</dd></div>
      <div><dt>Giữ nguyên</dt><dd>${fmt(outcome.unchanged_count)}</dd></div><div><dt>Khôi phục</dt><dd>${fmt(outcome.restored_count)}</dd></div>
      <div><dt>Không còn hiệu lực</dt><dd>${fmt(outcome.deleted_count)}</dd></div><div><dt>Đổi nguồn tham chiếu</dt><dd>${fmt(outcome.lineage_changed_count)}</dd></div>
    </dl>
    <div class="result-context"><span><strong>Tệp Excel:</strong> ${esc(result.fileName)}</span><span><strong>Dự án:</strong> ${esc(previewDestination(result.preview))}</span><span><strong>Phạm vi:</strong> ${esc(previewDateRange(result.preview))}</span><span><strong>Mã nhận diện tệp:</strong> <code title="${esc(result.preview.manifest.source_hash)}">${esc(shortHash(result.preview.manifest.source_hash))}</code></span></div>
    <div class="result-actions">
      <button class="primary" data-action="view-revision" ${revisionId ? '' : 'disabled'}>Xem lịch sử nhập</button>
      <button class="ghost" data-action="audit-import">Xem dữ liệu đối chiếu hiện hành</button>
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
    <div id="import-live-status" class="import-live-status" role="status" aria-live="polite" aria-atomic="true">${importPhase === 'previewing' ? 'Đang đọc tệp Excel và kiểm tra dữ liệu…' : importPhase === 'committing' ? importResult ? 'Đã ghi dữ liệu. Đang tải lại biểu đồ và lịch sử nhập…' : 'Đang ghi dữ liệu và lưu phiên bản… Không đóng thẻ này.' : ''}</div>
    ${importError ? `<div class="import-error" role="alert"><strong>${lastImportAction === 'preview' ? 'Không xem trước được tệp Excel.' : 'Chưa xác nhận được kết quả nhập.'}</strong><p>${esc(importError)}</p><p>${lastImportAction === 'preview' ? 'Kiểm tra tệp .xlsx rồi thử lại. Chưa có dữ liệu nào được ghi ở bước xem trước.' : 'Hãy xem Lịch sử nhập trước khi thử ghi lại, vì yêu cầu có thể đã được máy chủ xử lý.'}</p><button class="ghost" data-action="${lastImportAction === 'preview' ? 'retry-import' : 'check-import-history'}">${lastImportAction === 'preview' ? 'Thử xem trước lại' : 'Kiểm tra lịch sử nhập'}</button></div>` : ''}
    <div class="import-layout"><div class="upload-card"><div class="upload-symbol" aria-hidden="true">↥</div><h3>Nhập tệp Excel</h3><p>Kiểm tra chất lượng trước khi ghi vào kho dữ liệu. Tệp .xlsx tối đa 50 MB.</p>
      <input id="file-input" type="file" accept=".xlsx" ${busy ? 'disabled' : ''} aria-describedby="file-constraints"/><label class="upload-button" for="file-input">Chọn tệp Excel</label><p id="file-constraints" class="field-hint">Bước xem trước chỉ đọc tệp, chưa ghi dữ liệu.</p>
      ${selectedFile ? `<div class="selected-file"><strong>${esc(selectedFile.name)}</strong><span>${fmt(Math.round(selectedFile.size / 1024))} KB</span></div>` : ''}
      <label class="field import-mode"><span>Cách nhập dữ liệu</span><select id="import-mode" ${busy ? 'disabled' : ''}>${select([{value:'incremental',label:'Chỉ dữ liệu bổ sung'},{value:'full_snapshot',label:'Bản chụp đầy đủ'}], importMode)}</select></label>
      <div class="mode-guidance ${importMode === 'full_snapshot' ? 'high-risk' : ''}"><strong>${esc(guidance.title)}</strong><p>${esc(guidance.body)}</p></div>
      <button id="preview-action" class="primary wide" data-action="preview" ${selectedFile && !busy ? '' : 'disabled'}>${preview ? 'Kiểm tra lại tệp Excel' : 'Xem trước và kiểm tra'}</button></div>
      <div class="preview-card" aria-busy="${busy}"><h3 id="preview-result-heading" tabindex="-1">Kết quả xem trước</h3>${preview ? `<div class="preview-status ${preview.valid ? 'valid' : 'invalid'}" role="${preview.valid ? 'status' : 'alert'}">${preview.valid ? 'Đạt kiểm tra · có thể xác nhận nhập' : 'Không đạt kiểm tra · chưa ghi dữ liệu'}</div>
      <dl class="preview-identity"><div><dt>Dự án đích</dt><dd>${esc(previewDestination(preview))}</dd></div><div><dt>Tệp Excel</dt><dd>${esc(selectedFile?.name || preview.manifest.source_file)}</dd></div><div><dt>Phạm vi ngày</dt><dd>${esc(previewDateRange(preview))}</dd></div><div><dt>Mã nhận diện tệp</dt><dd><code title="${esc(preview.manifest.source_hash)}">${esc(shortHash(preview.manifest.source_hash))}</code></dd></div></dl>
      <div class="preview-metrics"><div><strong>${fmt(preview.manifest.record_count)}</strong><span>Điểm dữ liệu trong tệp</span></div><div><strong>${fmt(preview.manifest.date_count)}</strong><span>Ngày có dữ liệu</span></div><div><strong>${fmt(preview.errorCount)}</strong><span>Lỗi</span></div><div><strong>${fmt(preview.warningCount)}</strong><span>Cảnh báo</span></div></div>
      <section class="impact-summary" aria-labelledby="impact-heading"><div class="subsection-heading"><h4 id="impact-heading">Tác động khi ghi</h4><span>Xác định sau khi xác nhận</span></div><dl><div><dt>Thêm mới</dt><dd>—</dd></div><div><dt>Cập nhật phiên bản</dt><dd>—</dd></div><div><dt>Giữ nguyên</dt><dd>—</dd></div><div><dt>Thay phiên bản</dt><dd>—</dd></div></dl><p>Hệ thống chưa tính được số thay đổi chính xác ở bước xem trước. Kết quả thực tế sẽ hiển thị sau khi nhập.</p></section>
      <section class="revision-behavior"><h4>Cách lưu phiên bản</h4><p>${esc(guidance.body)}</p><p>Thay đổi giá trị được lưu thành phiên bản mới; tệp Excel nguồn và lịch sử nhập vẫn được giữ để đối chiếu.</p></section>
      <section class="validation-report" aria-labelledby="validation-heading"><div class="subsection-heading"><h4 id="validation-heading">Kết quả kiểm tra</h4><button class="text-action" data-action="download-validation">${reportDownloadLabel(preview)}</button></div><div class="issue-list">${validationIssues(preview)}</div>${reportIsTruncated(preview) ? `<p class="issue-limit">Chỉ hiển thị và tải được ${fmt(preview.issues.length)} / ${fmt(preview.errorCount + preview.warningCount)} mục kiểm tra; tổng lỗi và cảnh báo ở trên vẫn đầy đủ.</p>` : ''}</section>
      ${importMode === 'full_snapshot' && preview.valid ? `<label class="snapshot-confirm"><input id="snapshot-confirm" type="checkbox" ${fullSnapshotConfirmed ? 'checked' : ''}><span><strong>Tôi xác nhận nhập bản chụp đầy đủ.</strong>Tôi hiểu giá trị trùng khóa có thể tạo phiên bản mới; giá trị vắng mặt trong tệp không bị tự động xóa theo chính sách hiện tại.</span></label>` : ''}
      <button class="primary wide commit-button" data-action="commit" ${commitDisabled ? 'disabled' : ''}>${importMode === 'full_snapshot' ? 'Xác nhận nhập bản chụp' : 'Xác nhận nhập dữ liệu bổ sung'}</button>` : '<div class="preview-placeholder"><p>Chọn tệp Excel rồi xem trước dự án đích, phạm vi ngày, mã nhận diện tệp và kết quả kiểm tra.</p><strong>Chỉ ghi dữ liệu sau khi bạn xác nhận.</strong></div>'}</div></div>
    ${importResult && showAllIssues && report ? `<section id="committed-validation" class="committed-validation" tabindex="-1"><div class="subsection-heading"><h3>Kết quả kiểm tra của tệp Excel vừa nhập</h3><button class="text-action" data-action="download-validation">${reportDownloadLabel(report)}</button></div><div class="issue-list">${validationIssues(report)}</div>${reportIsTruncated(report) ? `<p class="issue-limit">Chỉ có ${fmt(report.issues.length)} / ${fmt(report.errorCount + report.warningCount)} mục chi tiết trong bản xem trước này.</p>` : ''}</section>` : ''}`;
  restorePendingFocus();
}
function renderHistory(body: HTMLDivElement): void {
  if (historyLoading) { body.innerHTML = statePanel('Đang tải lịch sử nhập', 'Đang lấy các lần nhập gần nhất từ kho dữ liệu.'); return; }
  if (historyError) { body.innerHTML = statePanel('Không tải được lịch sử nhập', `${historyError} Dữ liệu đã nhập không bị thay đổi.`, true, 'retry-history'); return; }
  const cols = ['started_at','submitted_file_name','attempt_status','requested_mode','input_record_count','inserted_count','updated_count','unchanged_count'];
  const latestAttempt = importResult?.outcome.attempt_id;
  body.innerHTML = `<p class="section-desc">Tối đa 100 lần nhập gần nhất, gồm lần đã ghi, trùng, không đạt kiểm tra và thất bại.</p>${historyItems.length ? `<div class="table-wrap"><table><thead><tr>${cols.map(col => `<th>${esc(historyHeaders[col])}</th>`).join('')}</tr></thead><tbody>${historyItems.map(item => { const current = Number(item.attempt_id) === latestAttempt; return `<tr ${current ? 'id="latest-import-row" class="current-import" tabindex="-1" aria-current="true"' : ''}>${cols.map(col => `<td title="${esc(historyCell(col, item[col]))}">${esc(historyCell(col, item[col]))}</td>`).join('')}</tr>`; }).join('')}</tbody></table></div>` : statePanel('Chưa có lần nhập nào', 'Sau khi kiểm tra và xác nhận tệp Excel đầu tiên, kết quả sẽ xuất hiện ở đây.')}`;
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
async function loadWorkspace(debounceMs = 0, force = false): Promise<void> {
  request?.abort();
  workspaceError = '';
  if (!state.project) { workspace = null; renderSidebar(); renderMain(); return; }
  const current = new AbortController(); request = current;
  const requestedView = ['overview', 'statistics', 'comparison', 'audit'].includes(state.tab)
    ? state.tab as 'overview' | 'statistics' | 'comparison' | 'audit'
    : 'overview';
  const trace = beginWorkspaceTrace('workspace-load');
  loading = true; updateWorkspaceRequestStatus(); scheduleFeedbackPaint(trace);
  const params = new URLSearchParams({
    view: requestedView,
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
  const requestKey = `${state.project}?${params.toString()}`;
  try {
    if (debounceMs > 0) await new Promise(resolve => setTimeout(resolve, debounceMs));
    if (current.signal.aborted || current !== request) { void finishWorkspaceTrace(trace, 'aborted'); return; }
    if (!force && workspace && workspaceView === requestedView && !workspaceError && requestKey === lastWorkspaceRequestKey) {
      loading = false; request = null; updateWorkspaceRequestStatus();
      await finishWorkspaceTrace(trace, 'success'); return;
    }
    const result = await api<Workspace>(`/projects/${encodeURIComponent(state.project)}/workspace?${params}`, { signal: current.signal }, trace);
    if (current !== request) { void finishWorkspaceTrace(trace, 'aborted'); return; }
    workspace = result; workspaceProject = state.project; workspaceView = requestedView; state.entity = result.selectedEntity;
    if (requestedView === 'comparison' && !result.comparisonContext) {
      const candidateIds = new Set(result.comparisonCandidates.map(item => item.entity_id));
      const retained = state.comparisonEntities.filter(id => candidateIds.has(id)).slice(0, 3);
      if (retained.join(',') !== state.comparisonEntities.join(',')) {
        state.comparisonEntities = retained;
      }
    }
    if (contextualComparison && dataVersionKey(result.dataVersion) !== dataVersionKey(contextualComparison.sourceDataVersion)) {
      contextualComparison.latestDataVersion = result.dataVersion;
      contextualComparison.status = 'stale';
      contextualComparison.notice = 'Không gian phân tích đã nhận một phiên bản dữ liệu mới.';
      renderContextualComparison();
    }
    if (aiAnalysis && (
      aiAnalysis.scope.project !== state.project
      || aiAnalysis.scope.entityRef !== result.selectedEntity
      || aiAnalysis.window.start !== result.window.start
      || aiAnalysis.window.end !== result.window.end
    )) aiLocallyStale = true;
    displayedFilterLabel = workspaceFilterLabel(result); lastWorkspaceRequestKey = requestKey;
    workspaceError = ''; message = ''; save();
    renderSidebar(); updateWorkspaceChrome();
    const reconcileStarted = performance.now();
    renderingWorkspaceTrace = trace;
    renderTab();
    renderingWorkspaceTrace = null;
    trace.reconciliationMs = performance.now() - reconcileStarted;
    const renders = [...pendingChartRenders];
    const plotlyStarted = performance.now();
    await Promise.all(renders);
    trace.plotlyMs = performance.now() - plotlyStarted;
    if (current !== request) { void finishWorkspaceTrace(trace, 'aborted'); return; }
    loading = false; request = null; updateWorkspaceRequestStatus();
    await finishWorkspaceTrace(trace, 'success');
  } catch (error) {
    if (current.signal.aborted || current !== request) {
      void finishWorkspaceTrace(trace, 'aborted'); return;
    }
    loading = false; workspaceError = (error as Error).message; request = null;
    if (workspace) updateWorkspaceRequestStatus();
    else { renderSidebar(); renderMain(); }
    await finishWorkspaceTrace(trace, 'error', workspaceError);
  }
}
function invalidateAIAnalysis(clear = false): void {
  aiRequest?.abort(); aiLoading = false; aiAnalysisError = '';
  if (clear) { aiAnalysis = null; aiLocallyStale = false; }
  else if (aiAnalysis) aiLocallyStale = true;
}

async function loadAIStatus(): Promise<void> {
  aiStatusError = '';
  try { aiStatus = await api<AIStatus>('/ai/status'); }
  catch (error) { aiStatus = null; aiStatusError = (error as Error).message; }
  if (state.tab === 'overview') renderTab();
}

async function refreshAIAnalysisFreshness(): Promise<void> {
  if (!aiAnalysis) return;
  try {
    const refreshed = await api<AIAnalysis>(`/ai/analyses/${encodeURIComponent(aiAnalysis.analysisId)}`);
    if (refreshed.analysisId !== aiAnalysis.analysisId) return;
    aiAnalysis = refreshed;
    aiLocallyStale = refreshed.status === 'stale' || refreshed.dataAsOf.stale;
    if (state.tab === 'overview') renderTab();
  } catch { /* A transient freshness check must not break the dashboard. */ }
}

async function generateAIInsight(): Promise<void> {
  if (!workspace || !aiStatus?.enabled || !aiStatus.configured || state.scope !== 'node' || aiLoading) return;
  aiRequest?.abort();
  const current = new AbortController(); aiRequest = current;
  let completionAnnouncement = '';
  aiLoading = true; aiAnalysisError = ''; renderTab();
  announceAI('Đang phân tích dữ liệu trong khoảng đã chọn.'); focusAIAction();
  try {
    const result = await api<AIAnalysis>(`/projects/${encodeURIComponent(state.project)}/ai/trend-summary`, {
      method: 'POST', signal: current.signal, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entityRef: workspace.selectedEntity,
        metricCode: state.aiMetricCode,
        start: workspace.window.start,
        end: workspace.window.end,
        groupBy: state.aiGroupBy,
        scope: 'node',
      }),
    });
    if (current !== aiRequest) return;
    aiAnalysis = result; aiLocallyStale = false; aiAnalysisError = '';
    completionAnnouncement = `Phân tích hoàn tất. ${aiStatusLabel(result.status)}.`;
  } catch {
    if (current.signal.aborted || current !== aiRequest) return;
    aiAnalysisError = aiFriendlyError();
    completionAnnouncement = 'Không tạo được phân tích. Dữ liệu trên bảng điều khiển vẫn được giữ nguyên.';
  } finally {
    if (current === aiRequest) {
      aiLoading = false; aiRequest = null; renderTab();
      announceAI(completionAnnouncement); focusAIAction();
    }
  }
}

function openAIInsightEvidence(evidenceId: string): void {
  const evidence = aiAnalysis?.evidence.find(item => item.evidenceId === evidenceId);
  if (!evidence || aiLocallyStale && aiAnalysis?.scope.project !== state.project) return;
  const exact = evidence.target.kind === 'exact' ? evidence.target : null;
  const aggregate = evidence.target.kind === 'aggregate' ? evidence.target : null;
  const evidenceMetric = aiAnalysis?.metrics?.find(metric => (
    metric.evidence.some(item => item.evidenceId === evidenceId)
  ));
  const selection: InvestigationSelection = {
    kind: evidence.target.kind === 'exact' ? 'exact-observation' : 'aggregate',
    aggregateRef: aggregate?.aggregateRef || null,
    observationRef: exact?.observationRef || null,
    lineageRef: exact?.lineageRef || null,
    origin: {
      plotKey: 'ai-insight', tab: 'overview', entityRef: aiAnalysis?.scope.entityRef || '',
      seriesName: evidenceMetric?.metricDisplayName || aiAnalysis?.scope.metricDisplayName || 'Nhận định tự động',
      observedDate: evidence.observedDate, displayedValue: 'Dữ kiện phân tích', curveNumber: 0, pointNumber: 0,
    },
  };
  aggregateParent = null; revisionHistory = null; importDetail = null;
  void loadProvenance(selection);
}

async function refreshProject(forceWorkspace = false): Promise<void> {
  request?.abort();
  const changingProject = workspaceProject !== state.project;
  if (changingProject) {
    workspace = null; workspaceView = ''; displayedFilterLabel = ''; lastWorkspaceRequestKey = ''; workspaceError = ''; chartFingerprints.clear();
    renderSidebar(); renderMain();
  }
  try {
    await loadEntities(); await loadWorkspace(0, forceWorkspace);
    if (forceWorkspace) await refreshAIAnalysisFreshness();
  }
  catch (error) {
    workspaceError = (error as Error).message;
    if (workspace) updateWorkspaceRequestStatus(); else renderMain();
  }
}
async function refreshHistory(): Promise<void> {
  historyError = ''; historyLoading = true; if (state.tab === 'history') renderTab();
  try { historyItems = (await api<{items: Record<string, unknown>[]}>('/imports')).items; }
  catch (error) { historyError = (error as Error).message; }
  historyLoading = false; if (state.tab === 'history') renderTab();
}
app.addEventListener('change', event => {
  const interactionAt = performance.now();
  const target = event.target as HTMLInputElement | HTMLSelectElement;
  if (target.id === 'file-input' && target instanceof HTMLInputElement) {
    selectedFile = target.files?.[0] || null; preview = null; importResult = null; importError = '';
    fullSnapshotConfirmed = false; showAllIssues = false; pendingFocusId = selectedFile ? 'preview-action' : 'file-input'; renderTab(); return;
  }
  if (target.id === 'import-mode') { importMode = target.value as typeof importMode; fullSnapshotConfirmed = false; pendingFocusId = 'import-mode'; renderTab(); return; }
  if (target.id === 'snapshot-confirm' && target instanceof HTMLInputElement) { fullSnapshotConfirmed = target.checked; pendingFocusId = 'snapshot-confirm'; renderTab(); return; }
  if (target.dataset.contextField === 'metric' && contextualComparison) {
    closeContextualInvestigation();
    contextualComparison.metric = target.value || null;
    contextualComparison.response = null; contextualComparison.error = ''; contextualComparison.notice = '';
    contextualComparison.status = contextualComparison.metric ? 'loading' : 'choosing';
    contextualFocusId = 'contextual-metric';
    if (contextualComparison.metric) void loadContextualComparison(); else renderContextualComparison();
    return;
  }
  if (target.dataset.contextField === 'calculation' && contextualComparison) {
    closeContextualInvestigation();
    contextualComparison.calculation = target.value as ContextualComparison['calculation'];
    contextualComparison.response = null; contextualComparison.error = ''; contextualComparison.notice = '';
    contextualComparison.status = 'loading'; contextualFocusId = 'contextual-calculation';
    void loadContextualComparison(); return;
  }
  if (target.dataset.contextCompare && contextualComparison && target instanceof HTMLInputElement) {
    closeContextualInvestigation();
    const id = target.dataset.contextCompare;
    const selected = new Set(contextualComparison.selected);
    if (target.checked) selected.add(id); else selected.delete(id);
    if (selected.size > 3) { target.checked = false; return; }
    contextualComparison.selected = [contextualComparison.anchorId, ...[...selected].filter(value => value !== contextualComparison?.anchorId)];
    contextualFocusId = '';
    void loadContextualComparison(); return;
  }
  if (target.dataset.compare) {
    const id = target.dataset.compare;
    const selected = new Set(state.comparisonEntities);
    if (target instanceof HTMLInputElement && target.checked) selected.add(id); else selected.delete(id);
    if (selected.size > 3) { message = 'Chỉ được chọn tối đa 3 nội dung theo dõi.'; if (target instanceof HTMLInputElement) target.checked = false; renderMain(); return; }
    state.comparisonEntities = [...selected]; save();
    noteWorkspaceInteraction(`compare:${id}`, interactionAt, performance.now());
    void loadWorkspace(120); return;
  }
  const field = target.dataset.field as keyof State | undefined;
  if (!field) return;
  if (contextualComparison) closeContextualComparison();
  const value: string | number | boolean = target instanceof HTMLInputElement && target.type === 'checkbox' ? target.checked : target.type === 'number' ? Number(target.value) : target.value;
  (state as unknown as Record<string, string | number | boolean>)[field] = value;
  if (field === 'aiMetricCode' || field === 'aiGroupBy') {
    invalidateAIAnalysis(); save(); renderTab(); return;
  }
  if (['project', 'mode', 'count', 'start', 'end', 'entity', 'scope'].includes(field)) {
    invalidateAIAnalysis(field === 'project');
  }
  if (field === 'project') {
    closeContextualComparison();
    state.entity = ''; state.comparisonEntities = []; state.start = ''; state.end = '';
    investigationRequest?.abort(); investigation = { status: 'closed' }; auditFocus = null; renderInvestigation();
  }
  if (field === 'mode') { state.count = state.mode === 'month' ? 6 : 8; const p = currentProject(); state.start = p?.minDate || ''; state.end = p?.maxDate || ''; }
  if (field === 'entity') state.scope = 'node';
  if (field !== 'auditOffset') state.auditOffset = 0;
  save();
  noteWorkspaceInteraction(`field:${field}`, interactionAt, performance.now());
  const debounceMs = ['project', 'entity', 'scope'].includes(field) ? 0 : 120;
  if (field === 'project') void refreshProject(); else void loadWorkspace(debounceMs);
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
  if (element.dataset.tab) {
    closeContextualComparison();
    state.tab = element.dataset.tab as Tab; save(); renderMain();
    if (state.tab === 'history') void refreshHistory();
    else if (['overview', 'statistics', 'comparison', 'audit'].includes(state.tab) && workspaceView !== state.tab) void loadWorkspace();
    return;
  }
  const action = element.dataset.action;
  if (action === 'open-contextual-comparison' && element.dataset.entityId) {
    openContextualComparison(element.dataset.entityId, element.id); return;
  }
  if (action === 'close-contextual-comparison') { closeContextualComparison(); return; }
  if ((action === 'contextual-lens-metric' || action === 'contextual-lens-statistics') && contextualComparison) {
    const lens = action === 'contextual-lens-statistics' ? 'statistics' : 'metric';
    if (contextualComparison.lens === lens) return;
    closeContextualInvestigation();
    contextualComparison.lens = lens;
    contextualComparison.response = null; contextualComparison.error = ''; contextualComparison.notice = '';
    contextualComparison.status = 'loading';
    try { sessionStorage.setItem(CONTEXTUAL_LENS_KEY, lens); } catch { /* Optional preference. */ }
    void loadContextualComparison(); return;
  }
  if (action === 'retry-contextual-comparison') { void loadContextualComparison(); return; }
  if (action === 'update-contextual-data') { void updateContextualData(); return; }
  if (action === 'close-investigation') {
    const selection = investigationSelection();
    investigationRequest?.abort(); investigation = { status: 'closed' }; aggregateParent = null; revisionHistory = null; importDetail = null; investigationLiveMessage = '';
    if (selection) {
      const plot = document.querySelector<HTMLElement>(`[data-plot="${selection.origin.plotKey}"]`);
      if (plot) {
        clearChartSelection(plot);
      }
    }
    renderInvestigation(); return;
  }
  if (action === 'retry-provenance') {
    const selection = investigationSelection(); if (selection) void loadProvenance(selection); return;
  }
  if (action === 'use-selected-entity') {
    state.scope = 'node'; invalidateAIAnalysis(); save(); void loadWorkspace(); return;
  }
  if (action === 'generate-ai-insight') { void generateAIInsight(); return; }
  if (action === 'open-ai-evidence' && element.dataset.evidenceId) { openAIInsightEvidence(element.dataset.evidenceId); return; }
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
  if (action === 'refresh') { void bootstrap(true); return; }
  if (action === 'retry-workspace') { void loadWorkspace(); return; }
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
    message = runId ? 'Mục Đối chiếu dữ liệu hiển thị các điểm dữ liệu hiện hành sau lần nhập; đây không phải danh sách thay đổi riêng của lần đó.' : 'Mục Đối chiếu dữ liệu hiển thị các điểm dữ liệu hiện hành, không phải danh sách thay đổi riêng của lần nhập.';
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
  if (event.key === 'Escape' && contextualComparison && investigationSelection()?.origin.plotKey === 'contextual-comparison') {
    event.preventDefault();
    app.querySelector<HTMLButtonElement>('#investigation-drawer [data-action="close-investigation"]')?.click();
    return;
  }
  if (event.key === 'Escape' && contextualComparison) {
    event.preventDefault(); closeContextualComparison(); return;
  }
  if (event.key === 'Escape' && investigation.status !== 'closed') {
    event.preventDefault();
    app.querySelector<HTMLButtonElement>('#investigation-drawer [data-action="close-investigation"]')?.click();
  }
});
app.addEventListener('cancel', event => {
  if ((event.target as HTMLElement).id !== 'contextual-comparison-dialog') return;
  event.preventDefault(); closeContextualComparison();
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
    if (result.status === 'committed') invalidateAIAnalysis();
    await bootstrap(result.status === 'committed'); await refreshHistory();
    importPhase = 'idle'; fullSnapshotConfirmed = false; showAllIssues = false; pendingFocusId = 'import-result'; renderMain();
  } catch (error) {
    importPhase = 'idle'; importError = (error as Error).message; pendingFocusId = 'preview-result-heading'; renderMain();
  }
}
async function bootstrap(forceWorkspace = false): Promise<void> {
  bootstrapError = '';
  void loadAIStatus();
  try {
    projects = (await api<{projects:Project[]}>('/bootstrap')).projects;
    bootstrapLoaded = true;
    if (!projects.some(project => project.label === state.project)) state.project = projects[0]?.label || '';
    const p = currentProject();
    if (!state.start) state.start = p?.minDate || '';
    if (!state.end) state.end = p?.maxDate || '';
    save(); await refreshProject(forceWorkspace);
  } catch (error) { bootstrapLoaded = true; bootstrapError = (error as Error).message; renderSidebar(); renderMain(); }
}
renderShell(); renderSidebar(); renderMain(); void bootstrap();
