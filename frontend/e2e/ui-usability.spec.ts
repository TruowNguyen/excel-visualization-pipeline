import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { aiAnalysis, installApiHarness } from './fixtures';

const evidence = '../.impeccable/review/compact-ui/usability';
const longText = 'Số lỗi tăng từ 10 lên 14, chênh lệch +4 (+40%). Cần xem từng kỳ và nguồn dữ liệu trước khi kết luận về xu hướng. '.repeat(12) + 'Kết thúc phần diễn giải dài.';

async function expectFitsViewport(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
}

async function expectFullParagraph(paragraph: Locator) {
  const bounds = await paragraph.evaluate(element => ({
    width: element.getBoundingClientRect().width,
    parentWidth: element.parentElement!.clientWidth,
    maxWidth: getComputedStyle(element).maxWidth,
    overflow: getComputedStyle(element).overflow,
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(bounds.maxWidth).toBe('none');
  expect(bounds.width).toBeGreaterThan(bounds.parentWidth * 0.95);
  expect(bounds.overflow).not.toBe('hidden');
  expect(bounds.scrollHeight).toBeLessThanOrEqual(bounds.clientHeight + 1);
}

for (const viewport of [
  { width: 1366, height: 768 }, { width: 1440, height: 900 },
  { width: 1024, height: 768 }, { width: 820, height: 900 }, { width: 390, height: 844 },
]) {
  test(`đọc đủ AI và thao tác toàn giao diện ${viewport.width}×${viewport.height}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    const fixture = aiAnalysis({ metricCode: 'all' });
    fixture.narrative.summary.text = longText;
    fixture.narrative.report = { overview: [{ text: longText, source: 'ai' }], phases: [], relationships: [] };
    const harness = await installApiHarness(page, { aiFixture: fixture });
    await page.goto('/');
    const panel = page.locator('#ai-insights');
    await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
    const summary = panel.locator('.ai-executive > p');
    await expect(summary).toContainText('Kết thúc phần diễn giải dài.');
    await expectFullParagraph(summary);
    await expectFitsViewport(page);

    // Open an exact source while the single-node controls have less available width.
    const bar = page.locator('[data-plot="overview-root"] .barlayer .trace').first().locator('.point path').first();
    await bar.scrollIntoViewIfNeeded();
    const point = await bar.boundingBox();
    await page.mouse.click(point!.x + point!.width / 2, point!.y + point!.height / 2);
    const drawer = page.locator('#investigation-drawer');
    await expect(drawer).toHaveAttribute('aria-hidden', 'false');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole('heading', { name: /Tổng số ghi nhận/ })).toBeVisible();
    const close = drawer.getByRole('button', { name: 'Đóng', exact: true });
    if (viewport.width <= 760) {
      const position = await close.boundingBox();
      expect(position!.y + position!.height).toBeLessThanOrEqual(viewport.height);
      await page.screenshot({ path: `${evidence}/source-${viewport.width}.png`, animations: 'disabled' });
    } else {
      const controls = await panel.locator('.ai-controls').evaluate(element => ({ width: element.clientWidth, contentWidth: element.scrollWidth }));
      expect(controls.contentWidth).toBeLessThanOrEqual(controls.width + 1);
    }
    await expectFitsViewport(page);
    await close.click();

    await page.locator('select[data-field="scope"]').selectOption('children');
    await panel.getByLabel('Phạm vi vấn đề').selectOption('selected');
    await panel.getByLabel('Camera 360 lỗi kết nối', { exact: true }).check();
    await panel.locator('[data-action="generate-context-insight"]').click();
    await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
    await expectFullParagraph(panel.locator('.ai-report-section > p').first());
    await panel.screenshot({ path: `${evidence}/ai-children-${viewport.width}.png`, animations: 'disabled' });
    await expectFitsViewport(page);

    await page.locator('[data-tab="statistics"]').click();
    await expect(page.locator('[data-plot="statistics-child-a"]')).toHaveClass(/js-plotly-plot/);
    await panel.locator('[data-action="generate-context-insight"]').click();
    await expect(panel.getByText('Đã hoàn tất phân tích.', { exact: true })).toBeVisible();
    await expectFullParagraph(panel.locator('.ai-report-section > p').first());
    await expectFitsViewport(page);
    if ([1366, 390].includes(viewport.width)) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `${evidence}/statistics-${viewport.width}.png`, fullPage: true, animations: 'disabled' });
    }

    await page.locator('[data-tab="import"]').click();
    await page.locator('#file-input').setInputFiles({ name: 'bao-cao-cx-ten-tep-dai.xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('fixture') });
    await page.locator('#preview-action').click();
    await expect(page.locator('.preview-status')).toContainText('Đạt kiểm tra');
    await page.locator('#open-import-history').click();
    await expect(page.locator('#history-row-2')).toBeVisible();
    await expectFitsViewport(page);
    if ([1366, 820, 390].includes(viewport.width)) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `${evidence}/import-${viewport.width}.png`, fullPage: true, animations: 'disabled' });
    }
    expect(errors).toEqual([]);
    expect(harness.calls.some(call => call.method === 'POST' && call.pathname.endsWith('/imports'))).toBeFalsy();
  });
}

for (const viewport of [{ width: 390, height: 844 }, { width: 820, height: 900 }, { width: 1093, height: 614 }]) {
  test(`so sánh không cắt vùng thao tác khi thu hẹp ${viewport.width}×${viewport.height}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize(viewport);
    await installApiHarness(page);
    await page.addInitScript(() => sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
      project: 'VSO', entity: 'root', scope: 'children', tab: 'statistics', statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
    })));
    await page.goto('/');
    const launch = page.locator('#compare-action-child-a');
    await launch.click();
    const dialog = page.locator('#contextual-comparison-dialog');
    await page.locator('[data-context-compare="child-b"]').check();
    await expect(dialog.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);
    const chart = await dialog.locator('.contextual-chart-frame').boundingBox();
    const boundary = await dialog.boundingBox();
    expect(chart!.x + chart!.width).toBeLessThanOrEqual(boundary!.x + boundary!.width + 1);
    const footer = await dialog.getByRole('button', { name: 'Xong' }).boundingBox();
    expect(footer!.y + footer!.height).toBeLessThanOrEqual(viewport.height);
    const bar = dialog.locator('[data-plot="contextual-comparison"] .barlayer .trace').first().locator('.point path').first();
    await bar.scrollIntoViewIfNeeded();
    const point = await bar.boundingBox();
    await page.mouse.click(point!.x + point!.width / 2, point!.y + point!.height / 2);
    await expect(dialog.locator('#investigation-drawer')).toBeVisible();
    const close = dialog.locator('#investigation-drawer').getByRole('button', { name: 'Đóng', exact: true });
    const position = await close.boundingBox();
    expect(position!.x + position!.width).toBeLessThanOrEqual(viewport.width);
    expect(position!.y + position!.height).toBeLessThanOrEqual(viewport.height);
    // A visible close button alone does not prove that the source pane stays in the popup.
    const sourceBounds = await dialog.locator('#investigation-drawer').boundingBox();
    const workingBounds = await dialog.locator('.contextual-layout').boundingBox();
    expect(sourceBounds!.x).toBeGreaterThanOrEqual(workingBounds!.x - 1);
    expect(sourceBounds!.y).toBeGreaterThanOrEqual(workingBounds!.y - 1);
    expect(sourceBounds!.x + sourceBounds!.width).toBeLessThanOrEqual(workingBounds!.x + workingBounds!.width + 1);
    expect(sourceBounds!.y + sourceBounds!.height).toBeLessThanOrEqual(workingBounds!.y + workingBounds!.height + 1);
    for (const action of [dialog.locator('.contextual-header button'), dialog.getByRole('button', { name: 'Xong' })]) {
      await expect(action).toBeVisible();
      expect(await action.evaluate(element => {
        const box = element.getBoundingClientRect();
        const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return hit !== null && element.contains(hit);
      })).toBeTruthy();
    }
    await page.screenshot({ path: `${evidence}/comparison-source-${viewport.width}.png`, animations: 'disabled' });
    await close.click();
    await page.screenshot({ path: `${evidence}/comparison-${viewport.width}.png`, animations: 'disabled' });
    await dialog.getByRole('button', { name: 'Xong' }).click();
    await expect(launch).toBeFocused();
  });
}
