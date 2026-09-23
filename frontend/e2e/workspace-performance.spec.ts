import { expect, test } from '@playwright/test';
import { installApiHarness } from './fixtures';

test('workspace filter rendering keeps chart DOM stable and avoids unchanged Plotly work', async ({ page }) => {
  await installApiHarness(page, { workspaceDelayMs: 140 });
  await page.goto('/');
  await page.getByRole('button', { name: /Thống kê/ }).click();
  const plot = page.locator('[data-plot="statistics-root"]');
  await expect(plot).toHaveClass(/js-plotly-plot/);

  await page.evaluate(() => {
    const target = document.querySelector('[data-plot="statistics-root"]');
    (window as typeof window & { __workspacePerf?: Record<string, unknown> }).__workspacePerf = {
      target,
      renderStarts: 0,
      removed: 0,
      startedAt: performance.now(),
    };
    document.addEventListener('cx:plotly-render-start', () => {
      const perf = (window as typeof window & { __workspacePerf: { renderStarts: number } }).__workspacePerf;
      perf.renderStarts += 1;
    });
    const observer = new MutationObserver(records => {
      const perf = (window as typeof window & { __workspacePerf: { target: Node; removed: number } }).__workspacePerf;
      for (const record of records) {
        for (const node of record.removedNodes) {
          if (node === perf.target || (node instanceof Element && node.contains(perf.target))) perf.removed += 1;
        }
      }
    });
    observer.observe(document.querySelector('#workspace')!, { childList: true, subtree: true });
    (window as typeof window & { __workspaceObserver?: MutationObserver }).__workspaceObserver = observer;
  });

  await page.locator('[data-field="statisticsMode"]').selectOption('sum');

  await expect(page.locator('.loading')).toBeHidden({ timeout: 5_000 });
  await expect(page.locator('[data-plot="statistics-root"]')).toHaveClass(/js-plotly-plot/);
  const result = await page.evaluate(() => {
    const win = window as typeof window & { __workspacePerf: { target: Node; renderStarts: number; removed: number; startedAt: number }; __workspaceObserver?: MutationObserver };
    win.__workspaceObserver?.disconnect();
    return {
      sameNode: document.querySelector('[data-plot="statistics-root"]') === win.__workspacePerf.target,
      renderStarts: win.__workspacePerf.renderStarts,
      removed: win.__workspacePerf.removed,
      durationMs: performance.now() - win.__workspacePerf.startedAt,
    };
  });
  console.log(`WORKSPACE_PERF ${JSON.stringify(result)}`);
  expect(result.sameNode).toBe(true);
  expect(result.renderStarts).toBe(0);
  expect(result.removed).toBe(0);
});

test('loading is separate from charts and changed data updates the existing Plotly node once', async ({ page }) => {
  await installApiHarness(page, { workspaceDelaysMs: [0, 180] });
  await page.goto('/');
  const plot = page.locator('[data-plot="overview-root"]');
  await expect(plot).toHaveClass(/js-plotly-plot/);
  const dragSurface = plot.locator('.nsewdrag');
  const dragBox = await dragSurface.boundingBox();
  if (!dragBox) throw new Error('Plotly zoom surface has no browser bounding box');
  await page.mouse.move(dragBox.x + dragBox.width * .2, dragBox.y + dragBox.height * .45);
  await page.mouse.down();
  await page.mouse.move(dragBox.x + dragBox.width * .78, dragBox.y + dragBox.height * .55, { steps: 8 });
  await page.mouse.up();
  const viewportBefore = await plot.evaluate((element: HTMLElement & { _fullLayout?: { xaxis?: { range?: unknown[] } } }) => element._fullLayout?.xaxis?.range);
  expect(viewportBefore).toHaveLength(2);
  await page.evaluate(() => {
    const target = document.querySelector('[data-plot="overview-root"]');
    const metrics = { target, starts: 0, completes: 0, startedAt: performance.now(), completedAt: 0 };
    (window as typeof window & { __changedPerf?: typeof metrics }).__changedPerf = metrics;
    document.addEventListener('cx:plotly-render-start', () => { metrics.starts += 1; });
    document.addEventListener('cx:plotly-render-complete', () => { metrics.completes += 1; metrics.completedAt = performance.now(); });
  });

  await page.locator('[data-field="mode"]').selectOption('week');
  await expect(page.locator('#workspace-loading')).toBeVisible();
  await expect(plot).toBeVisible();
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await expect(plot.locator('.barlayer .point')).toHaveCount(2);
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __changedPerf?: { completes: number } }).__changedPerf?.completes)).toBe(1);
  const result = await page.evaluate(() => {
    const metrics = (window as typeof window & { __changedPerf: { target: Node; starts: number; completes: number; startedAt: number; completedAt: number } }).__changedPerf;
    return { sameNode: document.querySelector('[data-plot="overview-root"]') === metrics.target, starts: metrics.starts, completes: metrics.completes, durationMs: metrics.completedAt - metrics.startedAt };
  });
  console.log(`WORKSPACE_CHANGED_PERF ${JSON.stringify(result)}`);
  expect(result).toMatchObject({ sameNode: true, starts: 1, completes: 1 });
  const viewportAfter = await plot.evaluate((element: HTMLElement & { _fullLayout?: { xaxis?: { range?: unknown[] } } }) => element._fullLayout?.xaxis?.range);
  expect(viewportAfter).toEqual(viewportBefore);
});

test('multi-child charts keep stable identity, unchanged siblings, and two-column order', async ({ page }) => {
  await installApiHarness(page);
  await page.goto('/');
  await page.locator('[data-field="scope"]').selectOption('children');
  const childA = page.locator('[data-plot="overview-child-a"]');
  const childB = page.locator('[data-plot="overview-child-b"]');
  await expect(childA).toHaveClass(/js-plotly-plot/);
  await expect(childB).toHaveClass(/js-plotly-plot/);
  const before = await Promise.all([childA.boundingBox(), childB.boundingBox()]);
  expect(before[0]?.y).toBe(before[1]?.y);
  expect(before[0]?.x).toBeLessThan(before[1]?.x || 0);
  await page.locator('[data-field="mode"]').selectOption('week');
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await page.evaluate(() => {
    const targets = [document.querySelector('[data-plot="overview-child-a"]'), document.querySelector('[data-plot="overview-child-b"]')];
    (window as typeof window & { __childPerf?: { targets: (Element | null)[]; starts: number } }).__childPerf = { targets, starts: 0 };
    document.addEventListener('cx:plotly-render-start', () => { (window as typeof window & { __childPerf: { starts: number } }).__childPerf.starts += 1; });
  });
  await page.locator('[data-field="count"]').fill('4');
  await page.locator('[data-field="count"]').press('Tab');
  await expect(page.locator('#workspace-loading')).toBeHidden();
  const result = await page.evaluate(() => {
    const perf = (window as typeof window & { __childPerf: { targets: (Element | null)[]; starts: number } }).__childPerf;
    return {
      sameA: document.querySelector('[data-plot="overview-child-a"]') === perf.targets[0],
      sameB: document.querySelector('[data-plot="overview-child-b"]') === perf.targets[1],
      starts: perf.starts,
    };
  });
  expect(result).toEqual({ sameA: true, sameB: true, starts: 0 });
  const after = await Promise.all([childA.boundingBox(), childB.boundingBox()]);
  expect(after[0]?.y).toBe(after[1]?.y);
  expect(after[0]?.x).toBeLessThan(after[1]?.x || 0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});

test('repeated Plotly.react updates do not duplicate lineage click handlers', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  const plot = page.locator('[data-plot="overview-root"]');
  await expect(plot).toHaveClass(/js-plotly-plot/);
  await page.locator('[data-field="mode"]').selectOption('week');
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await page.locator('[data-field="mode"]').selectOption('month');
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await expect.poll(() => plot.evaluate((element: HTMLElement & { data?: { y?: unknown[] }[] }) => element.data?.[0]?.y?.[0])).toBe(12);
  const bar = plot.locator('.barlayer .trace').first().locator('.point path').first();
  const box = await bar.boundingBox();
  if (!box) throw new Error('Plotly bar has no browser bounding box');
  const before = harness.calls.filter(call => call.pathname.includes('/provenance')).length;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect.poll(() => harness.calls.filter(call => call.pathname.includes('/provenance')).length).toBe(before + 1);
  await expect(page.locator('#investigation-drawer').getByRole('heading', { name: /Tổng số/ }).first()).toBeVisible();
  const after = harness.calls.filter(call => call.pathname.includes('/provenance')).length;
  expect(after - before).toBe(1);
});

test('rapid numeric filter changes are batched before request dispatch', async ({ page }) => {
  const harness = await installApiHarness(page, { workspaceDelayMs: 40 });
  await page.goto('/');
  await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);
  await page.locator('[data-field="mode"]').selectOption('week');
  await expect(page.locator('#workspace-loading')).toBeHidden();
  const before = harness.calls.filter(call => call.pathname.endsWith('/workspace')).length;
  for (const count of ['7', '6', '5']) {
    await page.locator('[data-field="count"]').fill(count);
    await page.locator('[data-field="count"]').press('Tab');
  }
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await expect.poll(() => harness.calls.filter(call => call.pathname.endsWith('/workspace')).length).toBe(before + 1);
  expect(harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search).toContain('count=5');
});

test('failed and superseded requests cannot erase the last successful workspace', async ({ page }) => {
  const harness = await installApiHarness(page, { workspaceDelaysMs: [0, 50, 220, 20], workspaceFailureRequests: [2] });
  await page.goto('/');
  const plot = page.locator('[data-plot="overview-root"]');
  await expect(plot).toHaveClass(/js-plotly-plot/);
  const originalNodeIsKept = await plot.evaluate(element => {
    (window as typeof window & { __lastGoodPlot?: Element }).__lastGoodPlot = element;
    return true;
  });
  expect(originalNodeIsKept).toBe(true);

  await page.locator('[data-field="mode"]').selectOption('week');
  await expect(page.getByText('Chưa áp dụng được bộ lọc mới.')).toBeVisible();
  await expect(plot).toBeVisible();
  expect(await plot.evaluate(element => element === (window as typeof window & { __lastGoodPlot?: Element }).__lastGoodPlot)).toBe(true);

  await page.getByRole('button', { name: 'Thử lại' }).click();
  await page.locator('[data-field="mode"]').selectOption('month');
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await expect(page.locator('.range-note')).toContainText('1/9/2026');
  await expect(page.getByText('Chưa áp dụng được bộ lọc mới.')).toHaveCount(0);
  const workspaceCalls = harness.calls.filter(call => call.pathname.endsWith('/workspace'));
  expect(workspaceCalls.at(-1)?.search).toContain('mode=month');
});
