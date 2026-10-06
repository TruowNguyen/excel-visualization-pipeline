import { expect, test } from '@playwright/test';
import { installApiHarness } from './fixtures';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

function summary(value = 7, peak = 14) {
  const source = { entityRef: 'root', label: 'Chất lượng cảnh báo - ghi nhận trên hệ thống', scope: 'source', effectiveUnit: 'Cảnh báo', eligible: true, reason: null };
  return {
    schemaVersion: 1, policyVersion: 'overview-total-v1', project: 'VSO', grain: 'day',
    metricKey: 'Tổng số', metricDisplayName: 'Tổng số ghi nhận', scope: 'source', source,
    sourceChoices: [source, { ...source, entityRef: 'field', label: 'Test thực địa' }],
    window: { start: '2026-09-16', end: '2026-09-17' },
    issueCount: { status: 'ready', value, excludedCount: 0, reason: null },
    peak: { status: 'ready', value: peak, unit: 'Cảnh báo', tieCount: 1, period: { start: '2026-09-17', end: '2026-09-17', label: '17/09/2026', complete: true, observedDayCount: 1, expectedDayCount: 1 } },
    lowest: { status: 'ready', value: 10, unit: 'Cảnh báo', tieCount: 1, period: { start: '2026-09-16', end: '2026-09-16', label: '16/09/2026', complete: true, observedDayCount: 1, expectedDayCount: 1 } },
    largestChange: { status: 'ready', absolute: 4, relativePercent: 40, direction: 'increasing', unit: 'Cảnh báo', tieCount: 1,
      from: { value: 10, period: { label: '16/09/2026' } }, to: { value: 14, period: { label: '17/09/2026' } } },
    limitations: [], validPeriodCount: 2, expectedPeriodCount: 2,
  };
}

test('count shows whole-project scope, not metadata, and legacy response is honest', async ({ page }) => {
  const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary()] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await expect(page.locator('[data-overview-card="issues"]')).toContainText('Toàn dự án');
  await expect(page.getByRole('heading', { name: 'Tổng quan trong khoảng đã chọn' })).toHaveCount(0);
  await expect(page.locator('.overview-source-note')).not.toBeVisible();
  await expect(page.getByLabel('Nguồn phân tích', { exact: true })).not.toBeVisible();
  await page.locator('.overview-summary-method summary').click();
  await expect(page.locator('#overview-summary')).toContainText('không phải tổng toàn dự án');
  expect(harness.calls.some(call => call.method === 'POST' && call.pathname.includes('/ai/'))).toBe(false);
});

test('old API does not relabel metadata as business values', async ({ page }) => {
  await installApiHarness(page);
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('—');
  await expect(page.locator('#overview-summary')).toContainText('Chưa có dữ liệu tổng quan mới');
});

test('extrema show source, unit and period; changing source preserves charts and filters', async ({ page }) => {
  const next = summary(7, 54); next.source.entityRef = 'field'; next.source.label = 'Test thực địa';
  const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary(), next] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('14');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('Cảnh báo');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('17/09/2026');
  await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);
  await page.locator('[data-plot="overview-root"]').evaluate(el => el.setAttribute('data-identity-check', 'same'));
  await page.locator('.overview-summary-method summary').click();
  await page.getByLabel('Nguồn phân tích', { exact: true }).selectOption('field');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('54');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await expect(page.locator('[data-plot="overview-root"]')).toHaveAttribute('data-identity-check', 'same');
  expect(harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search).toContain('overview_source=field');
  await expect(page.locator('.overview-summary-method')).toHaveAttribute('open', '');
});

test('largest movement exposes the adjacent periods and signed change', async ({ page }) => {
  await installApiHarness(page, { overviewSummaryByRequest: [summary()] });
  await page.goto('/');
  const card = page.locator('[data-overview-card="change"]');
  await expect(card).toContainText('+4');
  await expect(card).toContainText('Tăng 40%');
  await expect(card).toContainText('16/09/2026 → 17/09/2026');
});

test('refresh fetches the same source and filters; chart and summary advance together', async ({ page }) => {
  const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary(), summary(9, 34)], workspaceValuesByRequest: [[10, 14], [30, 34]], workspaceVersionsByRequest: ['imp_1', 'imp_2'] });
  await page.addInitScript(() => sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({ project: 'VSO', entity: 'root' })));
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  const first = harness.calls.find(call => call.pathname.endsWith('/workspace'))?.search;
  await page.getByRole('button', { name: /Làm mới dữ liệu/ }).click();
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('9');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('34');
  expect(harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search).toBe(first);
});

test('a stored invalid source can be reset without resetting chart filters', async ({ page }) => {
  const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary()], workspaceFailureRequests: [1] });
  await page.addInitScript(() => sessionStorage.setItem('excel_visualization_pipeline.overview-sources.v1', JSON.stringify({ VSO: 'retired' })));
  await page.goto('/');
  await page.getByRole('button', { name: 'Khôi phục nguồn mặc định' }).click();
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  expect(harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search).not.toContain('overview_source');
});

test('late response cannot overwrite a newer summary and failed range cannot display old numbers', async ({ page }) => {
  const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary(), summary(100), summary(9)], workspaceDelaysMs: [0, 1500, 10], workspaceFailureRequests: [4] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await page.locator('[data-field="mode"]').selectOption('week');
  await expect.poll(() => harness.workspaceRequestCount()).toBe(2);
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('—');
  await page.locator('[data-field="mode"]').selectOption('month');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('9');
  await page.waitForTimeout(1600);
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('9');
  await page.locator('[data-field="mode"]').selectOption('recent');
  await expect(page.locator('#overview-summary')).toContainText('Chưa tải được số liệu');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('—');
});

test('committed import updates summary without reloading the document', async ({ page }) => {
  await installApiHarness(page, { overviewSummaryByRequest: [summary(), summary(9, 34)], workspaceValuesByRequest: [[10, 14], [30, 34]] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await page.evaluate(() => { (window as unknown as { proof: string }).proof = 'same-document'; });
  await page.getByRole('button', { name: /Nhập Excel/ }).click();
  await page.locator('#file-input').setInputFiles({ name: 'new.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('fixture') });
  await page.locator('#preview-action').click();
  await page.getByRole('button', { name: 'Xác nhận nhập dữ liệu bổ sung' }).click();
  await expect(page.locator('#import-result')).toContainText('Biểu đồ đã được tải lại');
  await page.getByRole('button', { name: /Tổng quan/ }).click();
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('9');
  expect(await page.evaluate(() => (window as unknown as { proof: string }).proof)).toBe('same-document');
});

test('zero baseline, missing extrema and count zero remain distinguishable', async ({ page }) => {
  const data = summary(0); data.largestChange.relativePercent = null as unknown as number;
  Object.assign(data.largestChange, { relativeReason: 'Không tính được % vì kỳ trước bằng 0.' });
  Object.assign(data.lowest, { status: 'no_data', value: null, reason: 'Chưa có dữ liệu nguồn.' });
  await installApiHarness(page, { overviewSummaryByRequest: [data] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('0');
  await expect(page.locator('[data-overview-card="lowest"] strong')).toHaveText('—');
  await expect(page.locator('[data-overview-card="change"]')).toContainText('kỳ trước bằng 0');
  await page.locator('.overview-summary-method summary').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.overview-summary-method')).toHaveAttribute('open', '');
});

test('project switch never shows the previous project numbers', async ({ page }) => {
  await installApiHarness(page, { overviewSummaryByRequest: [summary()] });
  await page.route('**/api/bootstrap', route => route.fulfill({ json: { projects: ['VSO', 'ANVF'].map(label => ({ label, records: 12, chartable: 12, entities: 4, units: 1, minDate: '2026-09-16', maxDate: '2026-09-17' })), latestImport: null, metrics: ['Tổng số', 'Báo sai/Lỗi', '% báo sai'] } }));
  await page.route('**/api/projects/ANVF/entities', route => route.fulfill({ json: { entities: [{ entity_id: 'root', entity_label: 'Đăng ký bus', entity_level: 'item', parent_entity_id: null, entity_depth: 0, effective_unit: 'Lượt', entity_path: 'ANVF / Đăng ký bus' }] } }));
  await page.route('**/api/projects/ANVF/workspace?**', async route => {
    await new Promise(resolve => setTimeout(resolve, 250));
    const data = summary(3); data.project = 'ANVF'; data.source.label = 'Đăng ký bus';
    await route.fulfill({ json: { overviewSummary: data, dataVersion: null, window: data.window, selectedEntity: 'root', scopeIds: ['root'], overview: [], statistics: [], statisticsPeriods: [], comparisonCandidates: [], comparison: null, audit: { rows: [], total: 0, offset: 0 } } });
  });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await page.locator('[data-field="project"]').selectOption('ANVF');
  await expect(page.locator('[data-overview-card="issues"] strong')).not.toHaveText('7');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('3');
});

for (const [name, width, height] of [['desktop', 1440, 900], ['user-1366', 1366, 768], ['user-1200', 1200, 650], ['mobile', 390, 844]] as const) {
  test(`responsive summary ${name} ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await installApiHarness(page, { overviewSummaryByRequest: [summary()] });
    await page.goto('/');
    await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
    await expect(page.locator('[data-plot="overview-root"]')).toHaveClass(/js-plotly-plot/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.evaluate(() => scrollTo(0, 0));
    const dir = path.resolve('../.impeccable/review'); await mkdir(dir, { recursive: true });
    await page.screenshot({ path: path.join(dir, `overview-summary-${name}.png`), fullPage: true, animations: 'disabled' });
  });
}

function statisticsData(mode: 'sum' | 'average' | 'both' = 'both', count = 7) {
  const data = summary(count, mode === 'average' ? 2 : 14);
  const unit = mode === 'average' ? 'Cảnh báo/ngày' : 'Cảnh báo';
  const from = { ...data.lowest, value: mode === 'average' ? 1 : 7, unit,
    period: { ...data.lowest.period, start: '2026-09-07', end: '2026-09-13', label: 'Tuần 37/2026', observedDayCount: 7, expectedDayCount: 7 } };
  const to = { ...data.peak, unit,
    period: { ...data.peak.period, start: '2026-09-14', end: '2026-09-20', label: 'Tuần 38/2026', observedDayCount: 7, expectedDayCount: 7 } };
  return { ...data, calculation: mode === 'average' ? 'average_per_day' : 'sum', requestedMode: mode,
    grain: 'week', window: { start: '2026-09-07', end: '2026-09-20' },
    peak: to, lowest: from,
    largestChange: { ...data.largestChange, absolute: mode === 'average' ? 1 : 7, relativePercent: 100, unit, from, to },
  };
}

test('statistics replaces metadata with four cards and follows its calculation and range', async ({ page }) => {
  const harness = await installApiHarness(page, { overviewSummaryByRequest: [summary()],
    statisticsSummaryByRequest: [statisticsData(), statisticsData(), statisticsData('average'), statisticsData('average', 3)] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await page.getByRole('button', { name: /Thống kê/ }).click();
  await expect(page.locator('[data-overview-card]')).toHaveCount(4);
  await expect(page.locator('.kpi-grid')).toHaveCount(0);
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('Tổng trong kỳ');
  await page.locator('[data-field="statisticsMode"]').selectOption('average');
  await expect(page.locator('[data-overview-card="peak"] strong')).toContainText('2');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('Trung bình mỗi ngày');
  await expect(page.locator('[data-overview-card="peak"]')).toContainText('Cảnh báo/ngày');
  await page.locator('[data-field="statisticsGroup"]').selectOption('month');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('3');
  expect(harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search).toContain('statistics_group=month');
});

test('statistics source and refresh retain chart context and hide superseded or failed values', async ({ page }) => {
  const changed = statisticsData('sum', 9); changed.source = { ...changed.source, entityRef: 'field', label: 'Test thực địa' };
  const harness = await installApiHarness(page, { statisticsSummaryByRequest: [statisticsData(), statisticsData(), changed, statisticsData('sum', 12), statisticsData('sum', 99), statisticsData('average', 5)],
    workspaceDelaysMs: [0, 0, 0, 0, 1500, 10], workspaceFailureRequests: [7] });
  await page.goto('/');
  await page.getByRole('button', { name: /Thống kê/ }).click();
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await page.locator('.overview-summary-method summary').click();
  await expect(page.locator('.overview-summary-method')).toContainText('ba thẻ diễn biến dùng tổng trong kỳ');
  await expect(page.locator('[data-plot="statistics-root"]')).toHaveClass(/js-plotly-plot/);
  await page.locator('[data-plot="statistics-root"]').evaluate(el => el.setAttribute('data-identity-check', 'same'));
  await page.getByLabel('Nguồn phân tích', { exact: true }).selectOption('field');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('9');
  await expect(page.locator('[data-plot="statistics-root"]')).toHaveAttribute('data-identity-check', 'same');
  const query = harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search;
  expect(query).toContain('overview_source=field');
  await page.getByRole('button', { name: /Làm mới dữ liệu/ }).click();
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('12');
  expect(harness.calls.filter(call => call.pathname.endsWith('/workspace')).at(-1)?.search).toBe(query);
  await page.locator('[data-field="statisticsMode"]').selectOption('sum');
  await expect.poll(() => harness.workspaceRequestCount()).toBe(5);
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('—');
  await page.locator('[data-field="statisticsMode"]').selectOption('average');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('5');
  await page.waitForTimeout(1600);
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('5');
  await page.locator('[data-field="statisticsGroup"]').selectOption('quarter');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('—');
  await expect(page.locator('#overview-summary')).toContainText('Chưa tải được số liệu');
});

test('statistics legacy and empty periods never reuse Overview numbers', async ({ page }) => {
  await installApiHarness(page, { overviewSummaryByRequest: [summary()] });
  await page.goto('/');
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
  await page.getByRole('button', { name: /Thống kê/ }).click();
  await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('—');
  await expect(page.locator('#overview-summary')).toContainText('Chưa có dữ liệu tổng quan mới');
});

for (const [name, width, height] of [['desktop', 1440, 900], ['user-1366', 1366, 768], ['mobile', 390, 844]] as const) {
  test(`responsive statistics summary ${name} ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await installApiHarness(page, { overviewSummaryByRequest: [summary()], statisticsSummaryByRequest: [statisticsData()] });
    await page.goto('/');
    await page.getByRole('button', { name: /Thống kê/ }).click();
    await expect(page.locator('[data-overview-card="issues"] strong')).toHaveText('7');
    await expect(page.locator('[data-plot="statistics-root"]')).toHaveClass(/js-plotly-plot/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: path.resolve(`../.impeccable/review/statistics-summary-${name}.png`), fullPage: true, animations: 'disabled' });
  });
}
