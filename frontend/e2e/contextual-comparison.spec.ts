import { expect, test, type Locator, type Page } from '@playwright/test';
import { installApiHarness } from './fixtures';

async function clickRealBar(page: Page, plotKey: string, trace = 0, point = 0) {
  const bar: Locator = page.locator(`[data-plot="${plotKey}"] .barlayer .trace`).nth(trace).locator('.point path').nth(point);
  await expect(bar).toBeVisible();
  const box = await bar.boundingBox();
  if (!box) throw new Error(`Plotly bar ${plotKey}/${trace}/${point} has no browser bounding box`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

async function openContextualComparison(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
      project: 'VSO', entity: 'root', scope: 'children', tab: 'statistics',
      statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
    }));
  });
  await page.goto('/');
  await expect(page.locator('[data-plot="statistics-child-a"]')).toHaveClass(/js-plotly-plot/);
  const action = page.locator('#compare-action-child-a');
  await expect(action).toBeEnabled();
  await action.click();
  await expect(page.locator('#contextual-comparison-dialog')).toBeVisible();
  return action;
}

test('vertical slice 1 opens from a child chart, inherits context and restores focus', async ({ page }) => {
  const harness = await installApiHarness(page);
  const action = await openContextualComparison(page);

  await expect(page.getByText('Đang so sánh từ:')).toBeVisible();
  await expect(page.getByText('Camera 360 lỗi kết nối', { exact: true }).first()).toBeVisible();
  await expect(page.locator('#contextual-comparison-dialog').getByText('Theo tuần', { exact: true })).toBeVisible();
  await expect(page.locator('#contextual-metric')).toHaveValue('Báo sai/Lỗi');
  await expect(page.getByText('Chỉ số được chọn sẵn')).toBeVisible();
  expect(await action.evaluate(element => element.getBoundingClientRect().width)).toBeLessThan(100);

  await expect(page.locator('[data-context-compare="child-b"]')).toBeEnabled();
  await page.locator('[data-context-compare="child-b"]').check();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);

  const contextualCall = harness.calls.filter(call => call.search.includes('comparison_anchor=child-a')).at(-1);
  const params = new URLSearchParams(contextualCall?.search);
  expect(params.get('entity')).toBe('root');
  expect(params.get('scope')).toBe('children');
  expect(params.get('statistics_group')).toBe('week');
  expect(params.get('comparison_metric')).toBe('Báo sai/Lỗi');
  expect(params.get('comparison_entities')).toContain('child-a');
  expect(params.get('comparison_entities')).toContain('child-b');

  await page.getByRole('button', { name: 'Xong' }).click();
  await expect(page.locator('#contextual-comparison-dialog')).toHaveCount(0);
  await expect(action).toBeFocused();
  await expect(page.locator('[data-plot="statistics-child-a"]')).toHaveClass(/js-plotly-plot/);
});

test('metric change recomputes eligibility and a late old response cannot overwrite it', async ({ page }) => {
  await installApiHarness(page, {
    workspaceDelaysMs: [0, 220, 20],
    contextualIneligibleMetrics: ['% báo sai'],
  });
  await openContextualComparison(page);

  await page.locator('#contextual-metric').selectOption('% báo sai');
  await expect(page.locator('[data-context-compare="child-b"]')).toBeDisabled();
  await expect(page.getByText('Vấn đề này không có dữ liệu cho chỉ số đang chọn.')).toBeVisible();
  await expect(page.getByText('Chọn thêm một vấn đề trong cùng nhóm để tạo biểu đồ.')).toBeVisible();

  await page.waitForTimeout(260);
  await expect(page.locator('#contextual-metric')).toHaveValue('% báo sai');
  await expect(page.locator('[data-context-compare="child-b"]')).toBeDisabled();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveCount(0);
});

test('percentage metric remains available and keeps valid sibling selections', async ({ page }) => {
  const harness = await installApiHarness(page);
  await openContextualComparison(page);

  await expect(page.locator('[data-context-compare="child-b"]')).toBeEnabled();
  await page.locator('[data-context-compare="child-b"]').check();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);

  await page.locator('#contextual-metric').selectOption('% báo sai');
  await expect(page.locator('[data-context-compare="child-b"]')).toBeChecked();
  await expect(page.locator('[data-context-compare="child-b"]')).toBeEnabled();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);

  const contextualCall = harness.calls.filter(call => call.search.includes('comparison_anchor=child-a')).at(-1);
  const params = new URLSearchParams(contextualCall?.search);
  expect(params.get('comparison_metric')).toBe('% báo sai');
  expect(params.get('comparison_entities')).toContain('child-b');
});

test('phase 2 shows only the chart and renders daily averages as solid lines', async ({ page }) => {
  const harness = await installApiHarness(page);
  await openContextualComparison(page);

  await page.locator('[data-context-compare="child-b"]').check();
  await page.locator('#contextual-metric').selectOption('% báo sai');
  await page.getByRole('tab', { name: 'Thống kê' }).click();

  await expect(page.getByRole('tab', { name: 'Thống kê' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('[data-context-compare="child-b"]')).toBeChecked();
  await expect(page.locator('#contextual-metric')).toHaveCount(0);
  await expect(page.locator('#contextual-calculation')).toHaveValue('sum');
  await expect(page.getByText('Áp dụng cho cả Tổng số ghi nhận và Tổng báo sai (lỗi); không cần chọn lại chỉ số.')).toBeVisible();
  await expect(page.locator('.contextual-table')).toHaveCount(0);
  await expect(page.getByText('Bảng số liệu', { exact: true })).toHaveCount(0);
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);

  await page.locator('#contextual-calculation').selectOption('average_per_day');
  await expect(page.locator('[data-context-compare="child-b"]')).toBeChecked();
  await expect(page.getByText('Trung bình mỗi ngày', { exact: true }).first()).toBeVisible();
  const lineStyles = await page.locator('[data-plot="contextual-comparison"]').evaluate(
    (plot: HTMLElement & { data?: { type?: string; line?: { dash?: string; width?: number }; marker?: { size?: number } }[] }) =>
      (plot.data || []).filter(trace => trace.type === 'scatter').map(trace => ({
        dash: trace.line?.dash, width: trace.line?.width, markerSize: trace.marker?.size,
      })),
  );
  expect(lineStyles.length).toBeGreaterThan(0);
  expect(lineStyles.every(style => style.dash === 'solid' && style.width === 3 && style.markerSize === 8)).toBeTruthy();
  const call = harness.calls.filter(item => item.search.includes('comparison_lens=statistics')).at(-1);
  const params = new URLSearchParams(call?.search);
  expect(params.get('comparison_calculation')).toBe('average_per_day');
  expect(params.get('comparison_entities')).toContain('child-b');

  await page.getByRole('tab', { name: 'Chỉ số gốc' }).click();
  await expect(page.locator('#contextual-metric')).toHaveValue('% báo sai');
});

test('Statistics evidence opens inside the popup without covering the chart', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await installApiHarness(page);
  await openContextualComparison(page);
  await page.locator('[data-context-compare="child-b"]').check();
  await page.getByRole('tab', { name: 'Thống kê' }).click();
  const dialog = page.locator('#contextual-comparison-dialog');
  await expect(dialog.locator('.chart-keyboard, [data-chart-point]')).toHaveCount(0);
  await clickRealBar(page, 'contextual-comparison');

  await expect(dialog).toHaveClass(/contextual-investigation-open/);
  await expect(dialog.locator('#investigation-drawer')).toBeVisible();
  await expect(dialog.getByText('Nguồn dữ liệu tổng hợp')).toBeVisible();
  const chart = await dialog.locator('.contextual-chart-frame').boundingBox();
  const drawer = await dialog.locator('#investigation-drawer').boundingBox();
  expect(chart?.width).toBeGreaterThanOrEqual(520);
  expect((chart?.x || 0) + (chart?.width || 0)).toBeLessThanOrEqual((drawer?.x || 0) + 1);

  await dialog.locator('#investigation-drawer').getByRole('button', { name: 'Đóng' }).click();
  await expect(dialog).not.toHaveClass(/contextual-investigation-open/);
  await expect(dialog.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);

  await page.setViewportSize({ width: 1440, height: 900 });
  await clickRealBar(page, 'contextual-comparison');
  await expect(dialog).toHaveClass(/contextual-investigation-open/);
  await expect(dialog.locator('#investigation-drawer')).toBeVisible();
  const wideChart = await dialog.locator('.contextual-chart-frame').boundingBox();
  const wideDrawer = await dialog.locator('#investigation-drawer').boundingBox();
  expect(wideChart?.width).toBeGreaterThanOrEqual(520);
  expect((wideChart?.x || 0) + (wideChart?.width || 0)).toBeLessThanOrEqual((wideDrawer?.x || 0) + 1);
  await page.keyboard.press('Escape');
  await expect(dialog).toBeVisible();
  await expect(dialog).not.toHaveClass(/contextual-investigation-open/);
});

test('Audit round trip restores the Phase 2 popup and its selection', async ({ page }) => {
  await installApiHarness(page);
  await openContextualComparison(page);
  await page.locator('[data-context-compare="child-b"]').check();
  await page.getByRole('tab', { name: 'Thống kê' }).click();
  await clickRealBar(page, 'contextual-comparison');
  await page.locator('#investigation-drawer [data-action="open-contributor"]').first().click();
  await page.getByRole('button', { name: 'Mở đúng dòng đối chiếu' }).click();

  await expect(page.getByText('Dòng đối chiếu của điểm đã chọn')).toBeVisible();
  await expect(page.locator('#contextual-comparison-dialog')).not.toBeVisible();
  await page.getByRole('button', { name: 'Quay lại biểu đồ' }).click();

  await expect(page.locator('#contextual-comparison-dialog')).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Thống kê' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('[data-context-compare="child-b"]')).toBeChecked();
  await expect(page.locator('#contextual-comparison-dialog #investigation-drawer')).toBeVisible();
});

test('grouped percentage explains when the source rate has no exact numerator', async ({ page }) => {
  await installApiHarness(page, {
    contextualIneligibleMetrics: ['% báo sai'],
    contextualIneligibleReason: 'RATE_NUMERATOR_MISSING',
  });
  await openContextualComparison(page);

  await page.locator('#contextual-metric').selectOption('% báo sai');

  await expect(page.locator('[data-context-compare="child-b"]')).toBeDisabled();
  await expect(page.getByText(
    'Có tỷ lệ nguồn nhưng thiếu Tổng báo sai (lỗi), nên chưa thể tổng hợp tỷ lệ theo kỳ một cách chính xác.',
  )).toBeVisible();
});

for (const hiddenTab of ['comparison', 'audit']) {
  test(`hidden ${hiddenTab} workspace is not restored as a top-level tab`, async ({ page }) => {
    await installApiHarness(page);
    await page.addInitScript(tab => {
      sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
        project: 'VSO', entity: 'root', scope: 'children', tab,
        comparisonMetric: 'Báo sai/Lỗi', comparisonEntities: [],
      }));
    }, hiddenTab);
    await page.goto('/');

    await expect(page.locator('[data-tab="comparison"]')).toHaveCount(0);
    await expect(page.locator('[data-tab="audit"]')).toHaveCount(0);
    await expect(page.locator('[data-tab="statistics"]')).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('[data-plot="statistics-child-a"].js-plotly-plot')).toBeVisible();
  });
}

test('new committed data version blocks mixed-snapshot comparison until update', async ({ page }) => {
  await installApiHarness(page, {
    workspaceVersionsByRequest: ['imp_1', 'imp_2', 'imp_2', 'imp_2', 'imp_2'],
  });
  await openContextualComparison(page);

  await expect(page.getByText('Có dữ liệu mới hơn.')).toBeVisible();
  await expect(page.locator('#contextual-metric')).toBeDisabled();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveCount(0);

  await page.getByRole('button', { name: 'Cập nhật dữ liệu' }).click();
  await expect(page.getByText('Có dữ liệu mới hơn.')).toHaveCount(0);
  await expect(page.locator('[data-context-compare="child-b"]')).toBeEnabled();
  await page.locator('[data-context-compare="child-b"]').check();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);
});

for (const viewport of [
  { width: 1366, height: 768, minimumChartHeight: 340 },
  { width: 1440, height: 900, minimumChartHeight: 340 },
  { width: 1920, height: 1080, minimumChartHeight: 340 },
  { width: 1200, height: 650, minimumChartHeight: 260 },
]) {
  test(`large dialog preserves the comparison chart at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await installApiHarness(page);
    await openContextualComparison(page);
    await page.locator('[data-context-compare="child-b"]').check();
    await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);
    const bounds = await page.locator('.contextual-chart-frame').boundingBox();
    const dialog = await page.locator('#contextual-comparison-dialog').boundingBox();
    expect(bounds?.width).toBeGreaterThanOrEqual(640);
    expect(bounds?.height).toBeGreaterThanOrEqual(viewport.minimumChartHeight);
    expect(dialog?.width).toBeLessThanOrEqual(viewport.width);
    expect(dialog?.height).toBeLessThanOrEqual(viewport.height);
    await expect(page.getByRole('button', { name: 'Mở mục So sánh cũ' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Xong' })).toBeVisible();
    const footer = await page.locator('.contextual-footer').boundingBox();
    expect((footer?.y || 0) + (footer?.height || 0)).toBeLessThanOrEqual((dialog?.y || 0) + (dialog?.height || 0) + 1);
  });
}
