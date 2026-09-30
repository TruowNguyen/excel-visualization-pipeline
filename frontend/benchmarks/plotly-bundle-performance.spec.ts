import { expect, test, type Browser, type Page } from '@playwright/test';

type PlotlyMetric = {
  starts: number[];
  completes: number[];
  longTasks: { start: number; duration: number }[];
};

type Sample = {
  coldInitializationMs: number;
  coldReactMs: number;
  warmInitializationMs: number;
  warmReactMs: number;
  firstVisibleChartMs: number;
  coldMainThreadMs: number;
  coldScriptMs: number;
  warmMainThreadMs: number;
  plotlyResourceMs: number;
  plotlyTransferBytes: number;
  plotlyDecodedBytes: number;
};

const projectState = {
  project: 'VSO',
  entity: '1-1-chat-luong-canh-bao-ghi-nhan-tren-he-thong-ba6898fb1d78',
  scope: 'children',
  mode: 'recent',
  count: 8,
  tab: 'overview',
};

async function installMetrics(page: Page): Promise<void> {
  await page.addInitScript(state => {
    sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify(state));
    const metric: PlotlyMetric = { starts: [], completes: [], longTasks: [] };
    (window as typeof window & { __PLOTLY_BUNDLE_PERF__?: PlotlyMetric }).__PLOTLY_BUNDLE_PERF__ = metric;
    document.addEventListener('cx:plotly-render-start', () => metric.starts.push(performance.now()));
    document.addEventListener('cx:plotly-render-complete', () => metric.completes.push(performance.now()));
    new PerformanceObserver(list => {
      for (const entry of list.getEntries()) metric.longTasks.push({ start: entry.startTime, duration: entry.duration });
    }).observe({ type: 'longtask', buffered: true });
  }, projectState);
}

async function measure(browser: Browser): Promise<Sample> {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Performance.enable');
  const readMetric = async (name: string): Promise<number> => {
    const result = await cdp.send('Performance.getMetrics');
    return result.metrics.find(metric => metric.name === name)?.value || 0;
  };
  const taskBefore = await readMetric('TaskDuration');
  const scriptBefore = await readMetric('ScriptDuration');
  await installMetrics(page);
  await page.goto('/');
  await expect(page.locator('[data-plot^="overview-"]')).toHaveCount(9, { timeout: 120_000 });
  await expect.poll(async () => page.evaluate(() => (
    (window as typeof window & { __PLOTLY_BUNDLE_PERF__?: PlotlyMetric }).__PLOTLY_BUNDLE_PERF__?.completes.length || 0
  )), { timeout: 120_000 }).toBeGreaterThan(0);
  await expect.poll(async () => page.evaluate(() => (
    (window as typeof window & { __EVP_WORKSPACE_PERF__?: { status: string }[] }).__EVP_WORKSPACE_PERF__?.some(trace => trace.status === 'success') || false
  )), { timeout: 120_000 }).toBe(true);

  const cold = await page.evaluate(() => {
    const metric = (window as typeof window & { __PLOTLY_BUNDLE_PERF__: PlotlyMetric }).__PLOTLY_BUNDLE_PERF__;
    const firstStart = metric.starts[0];
    const firstComplete = metric.completes.at(-1)!;
    const workspaceTrace = (window as typeof window & {
      __EVP_WORKSPACE_PERF__: { status: string; plotlyMs: number }[];
    }).__EVP_WORKSPACE_PERF__.find(trace => trace.status === 'success')!;
    const resource = performance.getEntriesByType('resource')
      .map(entry => entry as PerformanceResourceTiming)
      .find(entry => /plotly[^/]*\.js(?:$|\?)/.test(entry.name));
    return {
      coldInitializationMs: workspaceTrace.plotlyMs,
      coldReactMs: firstComplete - firstStart,
      firstVisibleChartMs: firstComplete,
      plotlyResourceMs: resource?.duration || 0,
      plotlyTransferBytes: resource?.transferSize || 0,
      plotlyDecodedBytes: resource?.decodedBodySize || 0,
      completeCount: metric.completes.length,
    };
  });
  const taskAfterCold = await readMetric('TaskDuration');
  const scriptAfterCold = await readMetric('ScriptDuration');

  const traceCount = await page.evaluate(() => (
    (window as typeof window & { __EVP_WORKSPACE_PERF__?: unknown[] }).__EVP_WORKSPACE_PERF__?.length || 0
  ));
  await page.locator('[data-field="mode"]').selectOption('week');
  await expect.poll(async () => page.evaluate(count => (
    (window as typeof window & { __PLOTLY_BUNDLE_PERF__: PlotlyMetric }).__PLOTLY_BUNDLE_PERF__.completes.length
  ), cold.completeCount), { timeout: 120_000 }).toBeGreaterThan(cold.completeCount);
  await expect(page.locator('#workspace-loading')).toBeHidden({ timeout: 120_000 });
  await expect.poll(async () => page.evaluate(count => (
    (window as typeof window & { __EVP_WORKSPACE_PERF__?: unknown[] }).__EVP_WORKSPACE_PERF__?.length || 0
  ), traceCount), { timeout: 120_000 }).toBeGreaterThan(traceCount);
  const warm = await page.evaluate(({ completeCount, traceCount }) => {
    const metric = (window as typeof window & { __PLOTLY_BUNDLE_PERF__: PlotlyMetric }).__PLOTLY_BUNDLE_PERF__;
    const traces = (window as typeof window & {
      __EVP_WORKSPACE_PERF__: { status: string; plotlyMs: number }[];
    }).__EVP_WORKSPACE_PERF__;
    return {
      warmInitializationMs: traces.slice(traceCount).find(trace => trace.status === 'success')!.plotlyMs,
      warmReactMs: metric.completes.at(-1)! - metric.starts[completeCount],
    };
  }, { completeCount: cold.completeCount, traceCount });
  const taskAfterWarm = await readMetric('TaskDuration');
  await context.close();
  return {
    ...cold,
    ...warm,
    coldMainThreadMs: (taskAfterCold - taskBefore) * 1000,
    coldScriptMs: (scriptAfterCold - scriptBefore) * 1000,
    warmMainThreadMs: (taskAfterWarm - taskAfterCold) * 1000,
  };
}

test('measure cold and warm Plotly initialization on VSO child charts', async ({ browser }) => {
  const samples: Sample[] = [];
  for (let index = 0; index < 3; index += 1) samples.push(await measure(browser));
  console.log(`PLOTLY_BUNDLE_PERF ${JSON.stringify(samples)}`);
});
