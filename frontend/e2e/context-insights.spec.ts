import { test, expect } from '@playwright/test';
import { installApiHarness } from './fixtures';
import { existsSync, readFileSync } from 'node:fs';
import { contextInsightOutput } from '../src/context-insight';
import { formatMetricText } from '../src/terminology';

// Real-data replay payloads stay local; a clean clone must still run synthetic tests.
function localEvidence(name: string): any[] {
  const path = new URL(`../../specs/ai-data/evidence/${name}`, import.meta.url);
  test.skip(process.env.EVP_LOCAL_EVIDENCE === '0' || !existsSync(path), 'Local real-data evidence is not included in Git.');
  return JSON.parse(readFileSync(path, 'utf8'));
}

for (const [index, grouping] of [[1, 'week'], [2, 'month']] as const) {
  test(`insight liên kết đã kiểm chứng nổi bật trước chi tiết và không lặp so sánh hai kỳ: ${grouping}`, async ({ page }) => {
    const runs = localEvidence('2026-10-04-linked-insight-verified.json');
    const body = runs[index].body;
    await installApiHarness(page);
    await page.route('**/ai/context-insight', route => route.fulfill({ contentType: 'application/json',
      body: JSON.stringify({ ...body, dataAsOf: { ...body.dataAsOf, committedImportRef: 'imp_1', stale: false } }) }));
    await page.goto('/');
    await page.locator('[data-tab="statistics"]').click();
    await page.locator('[data-field="statisticsGroup"]').selectOption(grouping);
    await page.locator('[data-field="statisticsMode"]').selectOption('both');
    const panel = page.locator('#ai-insights');
    await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
    const overview = panel.locator('.ai-report-section').first();
    await expect(overview.locator('p').first()).toContainText('trong kỳ giảm, nhưng mức trung bình/ngày tăng');
    await expect(overview.locator('p').first()).toContainText(grouping === 'month' ? '441 đến 299' : '104 đến 76');
    await expect(panel).not.toContainText('1.1.');
    await expect(overview.locator('.ai-emphasis-topic')).toHaveCount(1);
    if (grouping === 'month') {
      const average = panel.locator('[data-calculation="average_per_day"]');
      await expect(average.locator('.ai-reading-phases > li')).toHaveCount(0);
      await expect(average).not.toContainText('Chưa đủ kỳ hợp lệ');
    }
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
    await panel.screenshot({ path: `../.impeccable/review/linked-insight-${grouping}.png` });
  });
}

test('nhãn chỉ lặp khi chuyển vấn đề hoặc cách tính, không đổi nội dung và nguồn', async ({ page }) => {
  const runs = localEvidence('2026-10-04-linked-insight-verified.json');
  const body = structuredClone(runs[1].body);
  const label = body.report.issues[0].entityLabel;
  const other = 'Vấn đề thứ hai';
  body.report.issues.push({ ...body.report.issues.find((issue: any) => issue.calculation === 'average_per_day'),
    entityRef: 'other', entityLabel: other });
  const texts = [
    `${label} · Trung bình/ngày: Số lỗi tăng từ 10 lên 12, chênh lệch 2.`,
    `${label} · Trung bình/ngày: Tổng số tăng từ 20 lên 24, chênh lệch 4.`,
    `${other} · Trung bình/ngày: Số lỗi giữ nguyên ở 3.`,
    `${other} · Trung bình/ngày: Tổng số giữ nguyên ở 30.`,
    `${label} · Trung bình/ngày: Số lỗi giảm từ 12 xuống 10.`,
    `${label} · Tổng trong kỳ: Số lỗi giảm từ 70 xuống 60.`,
    `${label} · Tổng trong kỳ: Tổng số giảm từ 140 xuống 120.`,
  ];
  body.report.overview = texts.map(text => ({ text, source: 'deterministic' }));
  const original = JSON.stringify(body);
  await page.setContent(contextInsightOutput(body, false));
  const overview = page.locator('.ai-report-section').first();
  await expect(overview.locator('h4')).toHaveText('Tổng quan trong thời gian đã chọn');
  await expect(overview.locator('.ai-emphasis-topic')).toHaveCount(4);
  await expect(overview.locator('p')).toHaveCount(7);
  for (let index = 0; index < texts.length; index++) {
    await expect(overview.locator('p').nth(index)).toContainText(formatMetricText(texts[index].slice(texts[index].indexOf(':') + 1).trim()));
  }
  await expect(overview.locator('.ai-paragraph-source')).toHaveCount(7);
  expect(JSON.stringify(body)).toBe(original);
});

for (const [index, grouping] of [[1, 'week'], [2, 'month']] as const) {
  test(`tên nhóm trong output LLM đã lưu bỏ số thứ tự nhưng giữ số liệu và nguồn: ${grouping}`, async ({ page }) => {
    const runs = localEvidence('2026-10-04-selected-group-live.json');
    const body = runs[index].body;
    const original = JSON.stringify(body);
    await installApiHarness(page);
    await page.route('**/ai/context-insight', route => route.fulfill({ contentType: 'application/json',
      body: JSON.stringify({ ...body, dataAsOf: { ...body.dataAsOf, committedImportRef: 'imp_1', stale: false } }) }));
    await page.goto('/');
    await page.locator('[data-tab="statistics"]').click();
    await page.locator('[data-field="statisticsGroup"]').selectOption(grouping);
    await page.locator('[data-field="statisticsMode"]').selectOption('both');
    const panel = page.locator('#ai-insights');
    await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
    await expect(panel.locator('.ai-emphasis-topic').first()).toContainText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
    await expect(panel).not.toContainText('1.1.');
    await expect(panel.locator('.ai-issue-detail')).toHaveCount(1);
    await expect(panel.locator('.ai-issue-detail > summary')).toHaveText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
    const calculation = panel.locator('[data-calculation="average_per_day"]');
    await calculation.getByText('Xem số liệu và nguồn', { exact: true }).click();
    const metric = body.report.issues.find((issue: any) => issue.calculation === 'average_per_day').metrics[0];
    await expect(calculation.locator('tbody tr').first().locator('td').nth(1)).toHaveText(metric.series[0].displayValue);
    await expect(calculation.locator('[data-action="open-context-insight-evidence"]').first()).toHaveAttribute('data-evidence-id', metric.series[0].evidenceId);
    expect(JSON.stringify(body)).toBe(original);
    await panel.screenshot({ path: `../.impeccable/review/selected-group-label-${grouping}.png` });
  });
}

for (const selection of ['node', 'selected', 'all']) {
  test(`Thống kê both giữ một vấn đề và hai cách tính riêng: ${selection}`, async ({ page }) => {
    await installApiHarness(page);
    await page.goto('/');
    if (selection !== 'node') await page.getByLabel('Mức hiển thị').selectOption('children');
    await page.locator('[data-tab="statistics"]').click();
    await page.locator('[data-field="statisticsMode"]').selectOption('both');
    const panel = page.locator('#ai-insights');
    if (selection === 'selected') {
      await panel.getByLabel('Phạm vi vấn đề').selectOption('selected');
      await panel.getByLabel('Camera 360 lỗi kết nối', { exact: true }).check();
    }
    await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
    await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
    await expect(panel.locator('.ai-issue-detail')).toHaveCount(selection === 'all' ? 2 : 1);
    const first = panel.locator('.ai-issue-detail').first();
    if (!await first.evaluate(element => (element as HTMLDetailsElement).open)) await first.locator(':scope > summary').click();
    await expect(first.locator('.ai-calculation-title')).toHaveText(['Trung bình/ngày', 'Tổng trong kỳ']);
    await expect(first.locator('.ai-calculation-section')).toHaveCount(2);
    await expect(first.locator('.ai-reading-phases > li')).toHaveCount(2);
    await first.locator('[data-calculation="average_per_day"]').getByText('Xem số liệu và nguồn', { exact: true }).click();
    await expect(first.locator('[data-calculation="average_per_day"] table')).toBeVisible();
    await expect(first.locator('[data-calculation="sum"] table')).not.toBeVisible();
    await panel.screenshot({ path: `../.impeccable/review/context-template-both-${selection}.png` });
  });
}

test('mở insight riêng từ biểu đồ không đổi node hoặc phạm vi toàn trang', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  await page.getByLabel('Mức hiển thị').selectOption('children');
  await page.locator('[data-chart-key="overview-child-a"]').getByRole('button', { name: 'Phân tích', exact: true }).click();
  const panel = page.locator('#ai-insights');
  await expect(panel.getByText('Phân tích riêng:', { exact: false })).toBeVisible();
  await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
  const call = harness.calls.find(c => c.pathname.endsWith('/ai/context-insight'))!;
  expect(call.body).toMatchObject({ view: 'overview', selection: 'node', parentEntityRef: 'child-a' });
  await expect(page.getByLabel('Mức hiển thị')).toHaveValue('children');
  await expect(page.getByLabel('Nội dung theo dõi')).toHaveValue('root');
});

test('selected chỉ gửi lựa chọn, all để backend resolve; tìm kiếm không bỏ lựa chọn', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  await page.getByLabel('Mức hiển thị').selectOption('children');
  const panel = page.locator('#ai-insights');
  await panel.getByLabel('Phạm vi vấn đề').selectOption('selected');
  await expect(panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' })).toBeDisabled();
  await panel.getByLabel('Camera 360 lỗi kết nối', { exact: true }).check();
  await panel.getByLabel('Tìm vấn đề').fill('5G');
  await expect(panel.getByLabel('Camera 360 lỗi kết nối', { exact: true })).toBeHidden();
  await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
  expect(harness.calls.filter(c => c.pathname.endsWith('/ai/context-insight'))[0].body).toMatchObject({ selection: 'selected', entityRefs: ['child-a'] });
  await panel.getByLabel('Phạm vi vấn đề').selectOption('all');
  await expect(panel.getByText(/Phân tích này không còn khớp/)).toBeVisible();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toHaveCount(0);
  await expect(panel.getByText('Phạm vi đã thay đổi. Hãy phân tích lại để cập nhật kết quả.', { exact: true })).toBeVisible();
  await expect(panel.getByText('Phạm vi đang chọn:', { exact: true })).toBeVisible();
  await expect(panel.getByText('Phạm vi đã phân tích:', { exact: true })).toBeVisible();
  await panel.getByRole('button', { name: 'Phân tích lại' }).click();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
  expect(harness.calls.filter(c => c.pathname.endsWith('/ai/context-insight'))[1].body).toMatchObject({ selection: 'all', entityRefs: [] });
  await panel.getByText('Camera 360 lỗi kết nối · Tổng trong kỳ', { exact: true }).click();
  await panel.getByText('Xem số liệu và nguồn', { exact: true }).first().click();
  await panel.getByRole('button', { name: 'Mở nguồn' }).first().click();
  await expect(page.locator('#investigation-drawer')).toBeVisible();
  expect(harness.calls.some(c => c.pathname.includes('/aggregates/agg_context_1/provenance'))).toBeTruthy();
});

test('Thống kê lấy quý, cách tính và khoảng kỳ riêng, không dùng sidebar làm phạm vi', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  await page.locator('[data-tab="statistics"]').click();
  await page.locator('[data-field="statisticsGroup"]').selectOption('quarter');
  await page.locator('[data-field="statisticsMode"]').selectOption('average');
  await page.locator('[data-field="statisticsRange"]').selectOption('all');
  const panel = page.locator('#ai-insights');
  await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
  expect(harness.calls.find(c => c.pathname.endsWith('/ai/context-insight'))!.body).toMatchObject({ view: 'statistics', groupBy: 'quarter', calculation: 'average_per_day', rangeMode: 'all', metricCode: 'all' });
  await page.locator('[data-field="statisticsMode"]').selectOption('sum');
  await expect(panel.getByText(/Phân tích này không còn khớp/)).toBeVisible();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toHaveCount(0);
  await expect(panel.locator('.ai-context-result > .ai-result-receipt')).toContainText('Theo quý');
});

for (const width of [1280, 1440]) {
  for (const view of ['children', 'statistics']) {
    test(`context layout ${view} giữ chung căn lề tại ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await installApiHarness(page);
      await page.goto('/');
      await page.getByLabel('Mức hiển thị').selectOption('children');
      if (view === 'statistics') await page.locator('[data-tab="statistics"]').click();
      const panel = page.locator('#ai-insights');
      await expect(panel.locator('h3')).toBeVisible();
      await expect(panel.locator('[data-context-insight-selection]')).toBeVisible();
      await expect(page.locator('#workspace-loading')).toBeHidden();
      const title = await panel.locator('h3').boundingBox();
      const scope = await panel.locator('[data-context-insight-selection]').boundingBox();
      expect(title).not.toBeNull();
      expect(scope).not.toBeNull();
      const firstControl = await panel.locator('.ai-context-controls select').first().boundingBox();
      expect(Math.abs(firstControl!.x - title!.x)).toBeLessThan(1);
      expect(Math.abs(scope!.y - firstControl!.y)).toBeLessThan(1);
      expect(scope!.width).toBeLessThanOrEqual(241);
      const generate = panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' });
      const action = await generate.boundingBox();
      expect(Math.abs(action!.x - title!.x)).toBeLessThan(1);
      await panel.getByLabel('Phạm vi vấn đề').selectOption('selected');
      const search = await panel.getByLabel('Tìm vấn đề').boundingBox();
      expect(search!.height).toBeGreaterThanOrEqual(42);
      await panel.getByLabel('Camera 360 lỗi kết nối', { exact: true }).check();
      await panel.screenshot({ path: `../.impeccable/review/context-layout-${view}-selected-${width}.png` });
      await generate.click();
      await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
      const heading = await panel.getByRole('heading', { name: 'Tổng quan trong thời gian đã chọn' }).boundingBox();
      expect(Math.abs(heading!.x - title!.x)).toBeLessThan(1);
      const paragraphWidth = await panel.locator('.ai-report-section > p').first().evaluate(element => ({
        width: element.getBoundingClientRect().width,
        parentWidth: element.parentElement!.getBoundingClientRect().width,
        lineHeight: parseFloat(getComputedStyle(element).lineHeight),
        fontSize: parseFloat(getComputedStyle(element).fontSize),
        maxWidth: getComputedStyle(element).maxWidth,
      }));
      expect(paragraphWidth.width).toBeLessThanOrEqual(paragraphWidth.parentWidth + 1);
      expect(paragraphWidth.maxWidth).toBe('none');
      expect(paragraphWidth.width).toBeCloseTo(paragraphWidth.parentWidth, 1);
      expect(paragraphWidth.lineHeight / paragraphWidth.fontSize).toBeCloseTo(1.65, 2);
      const firstIssue = panel.locator('.ai-issue-detail').first();
      if (!await firstIssue.evaluate(element => (element as HTMLDetailsElement).open)) await firstIssue.locator(':scope > summary').click();
      await firstIssue.getByText('Xem số liệu và nguồn', { exact: true }).first().click();
      await expect(firstIssue.getByRole('table').first()).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      await panel.screenshot({ path: `../.impeccable/review/context-layout-${view}-result-${width}.png` });
      await panel.getByLabel('Phạm vi vấn đề').selectOption('all');
      await expect(panel.locator('.ai-stale')).toBeVisible();
      await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toHaveCount(0);
      await panel.screenshot({ path: `../.impeccable/review/context-layout-${view}-stale-${width}.png` });
    });
  }
}

test('response cũ không ghi đè khi đổi lựa chọn trong lúc LLM chạy', async ({ page }) => {
  await installApiHarness(page, { aiDelayMs: 600 });
  await page.goto('/');
  await page.getByLabel('Mức hiển thị').selectOption('children');
  const panel = page.locator('#ai-insights');
  await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
  await panel.getByLabel('Phạm vi vấn đề').selectOption('selected');
  await expect(panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' })).toBeDisabled();
  await page.waitForTimeout(750);
  await expect(panel.getByText('Tổng quan trong thời gian đã chọn', { exact: true })).toHaveCount(0);
});

test('capture desktop và viewport hẹp của context insight với dữ liệu mô phỏng', async ({ page }) => {
  await installApiHarness(page);
  await page.goto('/');
  await page.getByLabel('Mức hiển thị').selectOption('children');
  const panel = page.locator('#ai-insights');
  await panel.getByRole('button', { name: 'Phân tích phạm vi đang xem' }).click();
  await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: '../.impeccable/review/context-insight-desktop.png', fullPage: true });
  await panel.getByLabel('Phạm vi vấn đề').selectOption('selected');
  await panel.getByLabel('Camera 360 lỗi kết nối', { exact: true }).check();
  await page.screenshot({ path: '../.impeccable/review/context-insight-selection.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '../.impeccable/review/context-insight-narrow.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
