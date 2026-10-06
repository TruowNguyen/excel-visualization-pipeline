import { expect, test, type Locator } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { installApiHarness } from './fixtures';

const evidence = '../.impeccable/review/compact-ui';
async function expectUncroppedTimeAxis(plot: Locator) {
  const bounds = await plot.evaluate(element => {
    const card = element.closest('.chart-card')!.getBoundingClientRect();
    const axis = [...element.querySelectorAll('.xtick text')].map(tick => tick.getBoundingClientRect());
    return { bottom: card.bottom, axis: axis.map(tick => ({ top: tick.top, bottom: tick.bottom })) };
  });
  expect(bounds.axis.length).toBeGreaterThan(0);
  for (const tick of bounds.axis) expect(tick.bottom).toBeLessThanOrEqual(bounds.bottom - 1);
}
const source = { entityRef: 'root', label: 'Chất lượng cảnh báo - ghi nhận trên hệ thống', scope: 'source', effectiveUnit: 'Cảnh báo', eligible: true, reason: null };
const period = (day: number) => ({ start: `2026-09-${day}`, end: `2026-09-${day}`, label: `${day}/09/2026`, complete: true, observedDayCount: 1, expectedDayCount: 1 });
const summary = {
  schemaVersion: 1, policyVersion: 'overview-total-v1', project: 'VSO', grain: 'day',
  metricKey: 'Tổng số', metricDisplayName: 'Tổng số ghi nhận', scope: 'source', source, sourceChoices: [source],
  window: { start: '2026-09-16', end: '2026-09-17' },
  issueCount: { status: 'ready', value: 7, excludedCount: 0, reason: null },
  peak: { status: 'ready', value: 14, unit: 'Cảnh báo', tieCount: 1, period: period(17) },
  lowest: { status: 'ready', value: 10, unit: 'Cảnh báo', tieCount: 1, period: period(16) },
  largestChange: { status: 'ready', absolute: 4, relativePercent: 40, direction: 'increasing', unit: 'Cảnh báo', tieCount: 1,
    from: { value: 10, period: period(16) }, to: { value: 14, period: period(17) } },
  limitations: [], validPeriodCount: 2, expectedPeriodCount: 2,
};

for (const viewport of [{ width: 1366, height: 768 }, { width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`khung gọn và điểm nhấn cũ, giữ khả năng đọc: ${viewport.width}×${viewport.height}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary], statisticsSummaryByRequest: [summary] });
    await page.goto('/');
    await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);
    await expectUncroppedTimeAxis(page.locator('[data-plot="overview-root"]'));
    await expect(page.locator('.overview-kpi')).toHaveCount(4);
    await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
    await expect(page.locator('.overview-summary-method')).not.toHaveAttribute('open', '');
    await expect(page.locator('.content-card')).toHaveCSS('box-shadow', 'none');
    await expect(page.locator('.content-card')).toHaveCSS('border-top-width', '1px');
    await expect(page.locator('.content-card')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
    await expect(page.locator('.tab.active')).toHaveCSS('background-color', 'rgb(240, 238, 248)');
    await expect(page.locator('.chart-card').first()).toHaveCSS('box-shadow', 'none');
    await expect(page.locator('.overview-kpi h3').first()).toHaveCSS('font-size', '14px');
    await expect(page.locator('.overview-kpi h3').first()).toHaveCSS('font-weight', '600');
    await expect(page.locator('.overview-kpi strong').first()).toHaveCSS('font-size', '32px');
    await expect(page.locator('.overview-kpi strong').first()).toHaveCSS('font-weight', '700');
    await expect(page.locator('.overview-kpi').first()).toHaveCSS('border-top-color', 'rgb(16, 24, 39)');
    await page.locator('.overview-kpi-grid').screenshot({ path: `${evidence}/metric-highlight-overview-${viewport.width}.png`, animations: 'disabled' });
    expect(await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Segoe UI');
    await expect(page.locator('[data-tab="overview"] .ui-icon')).toHaveAttribute('aria-hidden', 'true');
    await expect(page.locator('[data-tab="comparison"], [data-tab="audit"], .chart-keyboard, [data-chart-point]')).toHaveCount(0);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${evidence}/overview-${viewport.width}.png`, fullPage: true, animations: 'disabled' });

    await page.locator('[data-tab="statistics"]').click();
    await expect(page.locator('[data-plot="statistics-root"]')).toHaveClass(/js-plotly-plot/);
    await expectUncroppedTimeAxis(page.locator('[data-plot="statistics-root"]'));
    await expect(page.locator('.overview-kpi strong').first()).toHaveCSS('font-size', '32px');
    await expect(page.locator('.overview-kpi').first()).toHaveAttribute('data-value-state', 'ready');
    await page.locator('.overview-kpi-grid').screenshot({ path: `${evidence}/metric-highlight-statistics-${viewport.width}.png`, animations: 'disabled' });
    await expect(page.locator('.control-bar select').first()).toHaveCSS('font-size', '14px');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${evidence}/statistics-${viewport.width}.png`, fullPage: true, animations: 'disabled' });
    const panel = page.locator('#ai-insights');
    await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
    await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
    await expect(panel.locator('h3')).toHaveCSS('font-size', '18px');
    await expect(panel.locator('.ai-panel-head')).toHaveCSS('background-color', 'rgb(250, 249, 255)');
    await expect(panel.locator('.ai-report-section').first()).toHaveCSS('background-color', 'rgb(250, 249, 255)');
    await expect(panel.locator('.ai-report-section').nth(1)).toHaveCSS('margin-top', '20px');
    const measure = await panel.locator('.ai-report-section > p').first().evaluate(element => ({
      maxWidth: getComputedStyle(element).maxWidth,
      width: element.getBoundingClientRect().width,
      expected: element.parentElement!.getBoundingClientRect().width,
    }));
    expect(measure.maxWidth).toBe('none');
    expect(measure.width).toBeCloseTo(measure.expected, 1);
    await panel.screenshot({ path: `${evidence}/ai-${viewport.width}.png`, animations: 'disabled' });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();

    await page.locator('[data-tab="import"]').click();
    await expect(page.locator('.content-card')).toHaveCSS('border-top-width', '0px');
    await expect(page.locator('#open-import-history')).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${evidence}/import-${viewport.width}.png`, fullPage: true, animations: 'disabled' });
    await page.locator('#file-input').setInputFiles({ name: 'bao-cao-cx.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('fixture') });
    await page.locator('#preview-action').click();
    await expect(page.locator('.preview-status')).toContainText('Đạt kiểm tra');
    await page.locator('#open-import-history').click();
    await expect(page.locator('#history-row-2')).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${evidence}/import-history-${viewport.width}.png`, fullPage: true, animations: 'disabled' });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    expect(harness.calls.filter(call => call.method === 'POST' && call.pathname.endsWith('/imports')).length).toBe(0);
    expect(errors).toEqual([]);
  });
}

test('nhấn mạnh số 0 hợp lệ nhưng không làm nổi bật dữ liệu chưa có', async ({ page }) => {
  const fixture = structuredClone(summary) as Record<string, any>;
  fixture.issueCount.value = 0;
  fixture.lowest = { status: 'unavailable', reason: 'Chưa có kỳ hợp lệ', value: null };
  await installApiHarness(page, { overviewSummaryByRequest: [fixture] });
  await page.goto('/');
  const zero = page.locator('[data-overview-card="issues"]');
  await expect(zero).toHaveAttribute('data-value-state', 'ready');
  await expect(zero.locator('strong')).toHaveText('0');
  await expect(zero.locator('strong')).toHaveCSS('color', 'rgb(16, 24, 39)');
  const missing = page.locator('[data-overview-card="lowest"]');
  await expect(missing).toHaveAttribute('data-value-state', 'unavailable');
  await expect(missing.locator('strong')).toHaveText('—');
  await expect(missing.locator('strong')).toHaveCSS('color', 'rgb(82, 97, 118)');
  await expect(missing).toContainText('Chưa có kỳ hợp lệ');
});

for (const viewport of [{ width: 1366, height: 768 }, { width: 1440, height: 900 }]) {
  test(`cửa sổ so sánh giữ biểu đồ và nút đóng: ${viewport.width}×${viewport.height}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize(viewport);
    await installApiHarness(page, { overviewSummaryByRequest: [summary], statisticsSummaryByRequest: [summary] });
    await page.addInitScript(() => sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
      project: 'VSO', entity: 'root', scope: 'children', tab: 'statistics', statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
    })));
    await page.goto('/');
    const launch = page.locator('#compare-action-child-a');
    await launch.click();
    const dialog = page.locator('#contextual-comparison-dialog');
    await page.locator('[data-context-compare="child-b"]').check();
    await expect(dialog.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);
    await page.screenshot({ path: `${evidence}/comparison-${viewport.width}.png`, animations: 'disabled' });
    await dialog.getByRole('tab', { name: 'Thống kê' }).click();
    await page.locator('#contextual-calculation').selectOption('average_per_day');
    await expect(dialog.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);
    const footer = await dialog.getByRole('button', { name: 'Xong' }).boundingBox();
    expect(footer!.y + footer!.height).toBeLessThanOrEqual(viewport.height);
    const plot = await dialog.locator('[data-plot="contextual-comparison"]').boundingBox();
    expect(plot!.width).toBeGreaterThanOrEqual(640);
    expect(plot!.height).toBeGreaterThanOrEqual(260);
    await page.screenshot({ path: `${evidence}/comparison-statistics-${viewport.width}.png`, animations: 'disabled' });
    await page.locator('#contextual-calculation').selectOption('sum');
    const bar = dialog.locator('[data-plot="contextual-comparison"] .barlayer .trace').first().locator('.point path').first();
    await expect(bar).toBeVisible();
    const point = await bar.boundingBox();
    await page.mouse.click(point!.x + point!.width / 2, point!.y + point!.height / 2);
    await expect(dialog.locator('#investigation-drawer')).toBeVisible();
    await expect(dialog.getByText('Nguồn dữ liệu tổng hợp')).toBeVisible();
    const chart = await dialog.locator('.contextual-chart-frame').boundingBox();
    const drawer = await dialog.locator('#investigation-drawer').boundingBox();
    expect(chart!.x + chart!.width).toBeLessThanOrEqual(drawer!.x + 1);
    await page.screenshot({ path: `${evidence}/comparison-investigation-${viewport.width}.png`, animations: 'disabled' });
    await dialog.locator('#investigation-drawer').getByRole('button', { name: 'Đóng' }).click();
    await dialog.getByRole('button', { name: 'Xong' }).click();
    await expect(launch).toBeFocused();
  });
}
