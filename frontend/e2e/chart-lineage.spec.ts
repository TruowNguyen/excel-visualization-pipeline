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
  await clickRealBar(page, 'overview-root');
  await expect(page.getByText('Đang xác minh nguồn dữ liệu…')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 14/ })).toBeVisible();
  expect(harness.calls.some(call => call.pathname.includes('/observations/obs_overview_2/provenance') && call.search.includes('lineageRef=lin_overview_2'))).toBeTruthy();
});

test('keyboard investigation surface is removed while direct chart investigation remains available', async ({ page }) => {
  await installApiHarness(page);
  await openApp(page);
  await expect(page.locator('.chart-keyboard, .chart-keyboard-empty, [data-chart-point]')).toHaveCount(0);
  await clickRealBar(page, 'overview-root');
  await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 14/ })).toBeVisible();
  await page.getByRole('button', { name: 'Đóng', exact: true }).click();
  await expect(page.locator('#investigation-drawer')).not.toHaveClass(/open/);
});

test('Statistics, contextual comparison, and child-node surfaces dispatch real Plotly point identities', async ({ page }) => {
  const harness = await installApiHarness(page);
  await openApp(page);

  await page.getByRole('button', { name: /Thống kê/ }).click();
  await expect(page.locator('[data-plot="statistics-root"].js-plotly-plot')).toBeVisible();
  await clickRealBar(page, 'statistics-root');
  await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 14/ })).toBeVisible();
  await page.getByRole('button', { name: 'Đóng', exact: true }).click();

  await page.locator('[data-field="scope"]').selectOption('children');
  await expect(page.locator('[data-plot="statistics-child-a"].js-plotly-plot')).toBeVisible();
  await page.locator('#compare-action-child-a').click();
  await page.locator('[data-context-compare="child-b"]').check();
  await expect(page.locator('[data-plot="contextual-comparison"].js-plotly-plot')).toBeVisible();
  await clickRealBar(page, 'contextual-comparison');
  await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 10/ })).toBeVisible();
  await page.getByRole('button', { name: 'Đóng', exact: true }).click();
  await page.getByRole('button', { name: 'Xong' }).click();

  await page.getByRole('button', { name: /Tổng quan/ }).click();
  await expect(page.locator('[data-plot="overview-child-b"].js-plotly-plot')).toBeVisible();
  await clickRealBar(page, 'overview-child-b');
  await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 14/ })).toBeVisible();

  const paths = harness.calls.filter(call => call.pathname.includes('/provenance')).map(call => call.pathname);
  expect(paths).toContain('/api/projects/VSO/observations/obs_statistics_2/provenance');
  expect(paths).toContain('/api/projects/VSO/observations/obs_comparison_a_1/provenance');
  expect(paths).toContain('/api/projects/VSO/observations/obs_child_b_2/provenance');
});

test('drawer error can retry and keeps the exact observation and lineage references', async ({ page }) => {
  const harness = await installApiHarness(page, { provenanceFailures: 1 });
  await openApp(page);
  await clickRealBar(page, 'overview-root');
  await expect(page.locator('.lineage-state strong').getByText('Không tải được nguồn dữ liệu', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Thử tải lại nguồn' }).click();
  await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 14/ })).toBeVisible();
  const calls = harness.calls.filter(call => call.pathname.endsWith('/obs_overview_2/provenance'));
  expect(calls).toHaveLength(2);
  expect(calls.every(call => call.search.includes('lineageRef=lin_overview_2'))).toBeTruthy();
});

test('legacy point click opens the safe unavailable state without guessing provenance', async ({ page }) => {
  const harness = await installApiHarness(page, { legacyUnavailable: true });
  await openApp(page);
  await clickRealBar(page, 'overview-root');
  await expect(page.getByText('Chưa truy vết được điểm này')).toBeVisible();
  expect(harness.calls.some(call => call.pathname.includes('/provenance'))).toBeFalsy();
});

test('exact Audit navigation and return preserve the chart viewport', async ({ page }) => {
  const harness = await installApiHarness(page);
  await openApp(page);
  await page.locator('[data-plot="overview-root"]').evaluate((plot: HTMLElement & { layout?: { xaxis?: { range?: string[] } } }) => {
    if (plot.layout?.xaxis) plot.layout.xaxis.range = ['2026-09-16T06:00:00', '2026-09-17T00:00:00'];
  });
  await clickRealBar(page, 'overview-root');
  await expect(page.getByText(/phiên bản tại thời điểm chọn/)).toBeVisible();
  await page.getByRole('button', { name: 'Xem các phiên bản của giá trị này' }).click();
  await expect(page.locator('.revision-item strong')).toContainText('Đã được thay thế');
  await page.getByRole('button', { name: 'Mở đúng dòng đối chiếu' }).click();
  await expect(page.locator('#focused-audit-row')).toBeFocused();
  await expect(page.locator('#focused-audit-row')).toContainText('D7');
  const auditCall = harness.calls.find(call => call.pathname.endsWith('/audit/lookup'));
  expect(auditCall?.search).toContain('observationRef=obs_overview_2');
  expect(auditCall?.search).toContain('lineageRef=lin_overview_2');
  await page.getByRole('button', { name: 'Quay lại biểu đồ' }).click();
  await expect(page.locator('[data-plot="overview-root"].js-plotly-plot')).toBeVisible();
  await expect(page.locator('[data-chart-point]')).toHaveCount(0);
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
  const commit = page.getByRole('button', { name: 'Xác nhận nhập bản chụp' });
  await expect(commit).toBeDisabled();
  await page.getByLabel(/Tôi xác nhận nhập bản chụp đầy đủ/).check();
  await expect(commit).toBeEnabled();
});
