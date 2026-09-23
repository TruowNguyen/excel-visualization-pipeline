import { expect, test, type Locator, type Page } from '@playwright/test';
import { installApiHarness } from './fixtures';

async function openApp(page: Page) {
  await page.goto('/');
  await expect(page.locator('[data-plot="overview-root"].js-plotly-plot')).toBeVisible();
}

async function clickRealBar(page: Page, plotKey: string, trace = 0, point = 0) {
  const bar: Locator = page.locator(`[data-plot="${plotKey}"] .barlayer .trace`).nth(trace).locator('.point path').nth(point);
  await expect(bar).toBeVisible();
  const box = await bar.boundingBox();
  if (!box) throw new Error(`Plotly bar ${plotKey}/${trace}/${point} has no browser bounding box`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

test('Overview uses the real Plotly point, ignores the transparent helper trace, and resolves exact refs', async ({ page }) => {
  const harness = await installApiHarness(page, { provenanceDelayMs: 150 });
  await openApp(page);
  await page.locator('[data-plot="overview-root"] + .chart-keyboard summary').click();
  await expect(page.locator('[data-plot-key="overview-root"][data-chart-point]')).toHaveCount(2);
  await clickRealBar(page, 'overview-root');
  await expect(page.getByText('Đang xác minh nguồn dữ liệu…')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Tổng số 14/ })).toBeVisible();
  expect(harness.calls.some(call => call.pathname.includes('/observations/obs_overview_2/provenance') && call.search.includes('lineageRef=lin_overview_2'))).toBeTruthy();
});

test('keyboard point opens the same drawer and close restores point focus and selection feedback', async ({ page }) => {
  await installApiHarness(page);
  await openApp(page);
  await page.locator('[data-plot="overview-root"] + .chart-keyboard summary').click();
  const point = page.locator('[data-plot-key="overview-root"][data-chart-point]').first();
  await point.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: /Tổng số 10/ })).toBeVisible();
  await expect(point).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Đóng' }).click();
  await expect(point).toBeFocused();
  await expect(point).toHaveAttribute('aria-pressed', 'false');
  await page.keyboard.press('Space');
  await expect(page.getByRole('heading', { name: /Tổng số 10/ })).toBeVisible();
});

test('Statistics, Comparison, and child-node surfaces dispatch real Plotly point identities', async ({ page }) => {
  const harness = await installApiHarness(page);
  await openApp(page);

  await page.getByRole('button', { name: /Thống kê/ }).click();
  await expect(page.locator('[data-plot="statistics-root"].js-plotly-plot')).toBeVisible();
  await clickRealBar(page, 'statistics-root');
  await expect(page.getByRole('heading', { name: /Tổng số 14/ })).toBeVisible();
  await page.getByRole('button', { name: 'Đóng' }).click();

  await page.getByRole('button', { name: /So sánh/ }).click();
  await page.locator('[data-compare="child-a"]').check();
  await page.locator('[data-compare="child-b"]').check();
  await expect(page.locator('[data-plot="comparison"].js-plotly-plot')).toBeVisible();
  await clickRealBar(page, 'comparison');
  await expect(page.getByRole('heading', { name: /Tổng số 10/ })).toBeVisible();
  await page.getByRole('button', { name: 'Đóng' }).click();

  await page.getByRole('button', { name: /Tổng quan/ }).click();
  await page.locator('[data-field="scope"]').selectOption('children');
  await expect(page.locator('[data-plot="overview-child-b"].js-plotly-plot')).toBeVisible();
  await clickRealBar(page, 'overview-child-b');
  await expect(page.getByRole('heading', { name: /Tổng số 14/ })).toBeVisible();

  const paths = harness.calls.filter(call => call.pathname.includes('/provenance')).map(call => call.pathname);
  expect(paths).toContain('/api/projects/VSO/observations/obs_statistics_2/provenance');
  expect(paths).toContain('/api/projects/VSO/observations/obs_comparison_a_1/provenance');
  expect(paths).toContain('/api/projects/VSO/observations/obs_child_b_2/provenance');
});

test('drawer error can retry and keeps the exact observation and lineage references', async ({ page }) => {
  const harness = await installApiHarness(page, { provenanceFailures: 1 });
  await openApp(page);
  await page.locator('[data-plot="overview-root"] + .chart-keyboard summary').click();
  await page.locator('[data-plot-key="overview-root"][data-chart-point]').first().click();
  await expect(page.locator('.lineage-state strong').getByText('Không tải được nguồn dữ liệu', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Thử tải lại nguồn' }).click();
  await expect(page.getByRole('heading', { name: /Tổng số 10/ })).toBeVisible();
  const calls = harness.calls.filter(call => call.pathname.endsWith('/obs_overview_1/provenance'));
  expect(calls).toHaveLength(2);
  expect(calls.every(call => call.search.includes('lineageRef=lin_overview_1'))).toBeTruthy();
});

test('keyboard legacy point opens the safe unavailable state without guessing provenance', async ({ page }) => {
  const harness = await installApiHarness(page, { legacyUnavailable: true });
  await openApp(page);
  await page.locator('[data-plot="overview-root"] + .chart-keyboard summary').click();
  const legacy = page.locator('[data-lineage-unavailable="true"]');
  await expect(legacy).toContainText('chưa có nguồn truy vết');
  await legacy.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Chưa truy vết được điểm này')).toBeVisible();
  expect(harness.calls.some(call => call.pathname.includes('/provenance'))).toBeFalsy();
});

test('exact Audit navigation and return preserve viewport, selected point, and keyboard focus', async ({ page }) => {
  const harness = await installApiHarness(page);
  await openApp(page);
  await page.locator('[data-plot="overview-root"] + .chart-keyboard summary').click();
  const point = page.locator('[data-plot-key="overview-root"][data-chart-point]').nth(1);
  await page.locator('[data-plot="overview-root"]').evaluate((plot: HTMLElement & { layout?: { xaxis?: { range?: string[] } } }) => {
    if (plot.layout?.xaxis) plot.layout.xaxis.range = ['2026-09-16T06:00:00', '2026-09-17T00:00:00'];
  });
  await point.click();
  await expect(page.getByText(/phiên bản tại thời điểm chọn/)).toBeVisible();
  await page.getByRole('button', { name: 'Xem các phiên bản của giá trị này' }).click();
  await expect(page.locator('.revision-item strong')).toContainText('Đã được thay thế');
  await page.getByRole('button', { name: 'Mở đúng dòng Audit' }).click();
  await expect(page.locator('#focused-audit-row')).toBeFocused();
  await expect(page.locator('#focused-audit-row')).toContainText('D7');
  const auditCall = harness.calls.find(call => call.pathname.endsWith('/audit/lookup'));
  expect(auditCall?.search).toContain('observationRef=obs_overview_2');
  expect(auditCall?.search).toContain('lineageRef=lin_overview_2');
  await page.getByRole('button', { name: 'Quay lại biểu đồ' }).click();
  const restoredPoint = page.locator('[data-plot-key="overview-root"][data-point-key="0:1"]');
  await expect(restoredPoint).toHaveAttribute('aria-pressed', 'true');
  await expect(restoredPoint).toBeFocused();
  const range = await page.locator('[data-plot="overview-root"]').evaluate((plot: HTMLElement & { layout?: { xaxis?: { range?: unknown[] } } }) => plot.layout?.xaxis?.range);
  expect(range).toEqual(['2026-09-16T06:00:00', '2026-09-17T00:00:00']);
});

test('full snapshot remains blocked until explicit confirmation', async ({ page }) => {
  await installApiHarness(page);
  await openApp(page);
  await page.getByRole('button', { name: /Nhập Excel/ }).click();
  await page.locator('#import-mode').selectOption('full_snapshot');
  await page.locator('#file-input').setInputFiles({ name: 'snapshot.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('fixture') });
  await page.locator('#preview-action').click();
  await expect(page.getByText('Đạt kiểm tra · có thể xác nhận nhập')).toBeVisible();
  const commit = page.getByRole('button', { name: 'Xác nhận nhập snapshot' });
  await expect(commit).toBeDisabled();
  await page.getByLabel(/Tôi xác nhận nhập snapshot đầy đủ/).check();
  await expect(commit).toBeEnabled();
});
