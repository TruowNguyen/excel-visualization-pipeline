import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { installApiHarness } from './fixtures';

async function firstOverviewValue(page: Page): Promise<number | undefined> {
  return page.locator('[data-plot="overview-root"]').evaluate(
    (element: HTMLElement & { data?: { y?: number[] }[] }) => element.data?.[0]?.y?.[0],
  );
}

test('successful import refreshes dashboard data without a full-page reload', async ({ page }) => {
  const harness = await installApiHarness(page, {
    workspaceValuesByRequest: [[10, 14], [30, 34]],
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({ project: 'VSO', entity: 'root' }));
  });
  await page.goto('/');
  await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);
  expect(await firstOverviewValue(page)).toBe(10);
  await page.evaluate(() => { (window as typeof window & { __dashboardSession?: string }).__dashboardSession = 'same-document'; });

  await page.getByRole('button', { name: /Nhập Excel/ }).click();
  await page.locator('#file-input').setInputFiles({
    name: 'update.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: Buffer.from('fixture'),
  });
  await page.locator('#preview-action').click();
  await expect(page.getByText('Đạt kiểm tra · có thể xác nhận nhập')).toBeVisible();
  await page.getByRole('button', { name: 'Xác nhận nhập dữ liệu bổ sung' }).click();

  await expect(page.locator('#import-result')).toContainText('Biểu đồ đã được tải lại.');
  await expect.poll(() => harness.workspaceRequestCount()).toBe(2);
  const workspaceCalls = harness.calls.filter(call => call.pathname.endsWith('/workspace'));
  expect(workspaceCalls[1].search).toBe(workspaceCalls[0].search);
  expect(await page.evaluate(() => (window as typeof window & { __dashboardSession?: string }).__dashboardSession)).toBe('same-document');

  await page.getByRole('button', { name: /Tổng quan/ }).click();
  await expect.poll(() => firstOverviewValue(page)).toBe(30);
});

test('manual refresh fetches workspace again with the same project and filters', async ({ page }) => {
  const harness = await installApiHarness(page, {
    workspaceValuesByRequest: [[10, 14], [40, 44]],
  });
  await page.addInitScript(() => {
    sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({ project: 'VSO', entity: 'root' }));
  });
  await page.goto('/');
  await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);
  expect(await firstOverviewValue(page)).toBe(10);
  const initialWorkspaceCall = harness.calls.find(call => call.pathname.endsWith('/workspace'));

  await page.getByRole('button', { name: /Làm mới dữ liệu/ }).click();

  await expect.poll(() => harness.workspaceRequestCount()).toBe(2);
  await expect.poll(() => firstOverviewValue(page)).toBe(40);
  const workspaceCalls = harness.calls.filter(call => call.pathname.endsWith('/workspace'));
  expect(workspaceCalls[1].search).toBe(initialWorkspaceCall?.search);
});

test('a superseded request that finishes late cannot overwrite the newer workspace', async ({ page }) => {
  const harness = await installApiHarness(page, {
    workspaceDelaysMs: [0, 220, 20],
    workspaceValuesByRequest: [[10, 14], [100, 104], [20, 24]],
  });
  await page.goto('/');
  await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);

  await page.locator('[data-field="mode"]').selectOption('week');
  await expect.poll(() => harness.workspaceRequestCount()).toBe(2);
  await page.locator('[data-field="mode"]').selectOption('month');

  await expect.poll(() => harness.workspaceRequestCount()).toBe(3);
  await expect(page.locator('#workspace-loading')).toBeHidden();
  await expect(page.locator('.range-note')).toContainText('1/9/2026');
  await expect.poll(() => firstOverviewValue(page)).toBe(22);

  await page.waitForTimeout(260);
  expect(await firstOverviewValue(page)).toBe(22);
  await expect(page.locator('.range-note')).toContainText('1/9/2026');
});
