export type PendingWorkspaceInteraction = {
  trigger: string;
  interactionAt: number;
  stateUpdatedAt: number;
};

export type WorkspacePerformanceTrace = {
  id: number;
  trigger: string;
  status: 'pending' | 'success' | 'error' | 'aborted';
  interactionAt: number;
  stateUpdatedAt: number;
  feedbackPaintAt?: number;
  requestDispatchedAt?: number;
  responseHeadersAt?: number;
  responseBodyAt?: number;
  dataReadyAt?: number;
  jsonParseMs: number;
  fingerprintMs: number;
  reconciliationMs: number;
  plotlyMs: number;
  chartsRendered: number;
  chartsSkipped: number;
  finalPaintAt?: number;
  backendTiming?: string;
  error?: string;
};

type PerformanceWindow = Window & {
  __EVP_WORKSPACE_PERF__?: WorkspacePerformanceTrace[];
};

let sequence = 0;
let pendingInteraction: PendingWorkspaceInteraction | null = null;
const history: WorkspacePerformanceTrace[] = [];

export function noteWorkspaceInteraction(trigger: string, interactionAt: number, stateUpdatedAt: number): void {
  pendingInteraction = { trigger, interactionAt, stateUpdatedAt };
}

export function beginWorkspaceTrace(fallbackTrigger = 'programmatic'): WorkspacePerformanceTrace {
  const interaction = pendingInteraction;
  pendingInteraction = null;
  const now = performance.now();
  const trace: WorkspacePerformanceTrace = {
    id: ++sequence,
    trigger: interaction?.trigger || fallbackTrigger,
    status: 'pending',
    interactionAt: interaction?.interactionAt ?? now,
    stateUpdatedAt: interaction?.stateUpdatedAt ?? now,
    jsonParseMs: 0,
    fingerprintMs: 0,
    reconciliationMs: 0,
    plotlyMs: 0,
    chartsRendered: 0,
    chartsSkipped: 0,
  };
  performance.mark(`workspace-${trace.id}-interaction`, { startTime: trace.interactionAt });
  return trace;
}

export function scheduleFeedbackPaint(trace: WorkspacePerformanceTrace): void {
  requestAnimationFrame(() => {
    trace.feedbackPaintAt = performance.now();
    performance.mark(`workspace-${trace.id}-feedback-painted`);
  });
}

export function recordFingerprint(trace: WorkspacePerformanceTrace, durationMs: number, rendered: boolean): void {
  trace.fingerprintMs += durationMs;
  if (rendered) trace.chartsRendered += 1;
  else trace.chartsSkipped += 1;
}

function nextPaint(): Promise<number> {
  return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(performance.now()))));
}

export async function finishWorkspaceTrace(
  trace: WorkspacePerformanceTrace,
  status: WorkspacePerformanceTrace['status'],
  error?: string,
): Promise<void> {
  trace.status = status;
  trace.error = error;
  trace.finalPaintAt = await nextPaint();
  performance.mark(`workspace-${trace.id}-final-painted`);
  performance.measure(`workspace-${trace.id}-interaction-to-paint`, {
    start: `workspace-${trace.id}-interaction`,
    end: `workspace-${trace.id}-final-painted`,
  });
  history.push(trace);
  if (history.length > 50) history.shift();
  (window as PerformanceWindow).__EVP_WORKSPACE_PERF__ = history;
  window.dispatchEvent(new CustomEvent('cx:workspace-performance', { detail: trace }));
}
