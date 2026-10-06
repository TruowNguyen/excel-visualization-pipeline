import { expect, test, type Locator } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { presentationFigure } from '../src/chart';
import type { Figure } from '../src/types';
import { installApiHarness } from './fixtures';

const evidence = '../.impeccable/review/week-labels-readable';
const weeklyFigure = (labels: string[]): Figure => ({
  data: [{ type: 'bar', x: labels, y: labels.map((_, index) => index + 1), ids: labels.map((_, index) => `point_${index}`),
    customdata: labels.map(label => [label, 0]), meta: { lineage: { contractVersion: 2, kind: 'aggregate', selectable: true, aggregateRefs: labels.map((_, index) => `agg_${index}`) } } }],
  layout: { xaxis: { type: 'category' } },
});

for (const [label, expected] of [
  ['Tuần 37/2026', '07/09 - 13/09'],
  ['Tuần 36/2026', '31/08 - 06/09'],
  ['Tuần 09/2024', '26/02 - 03/03'],
  ['Tuần 01/2026', '29/12/2025 - 04/01/2026'],
  ['Tuần 53/2020', '28/12/2020 - 03/01/2021'],
  ['Tuần 37/2026 (07/09–13/09)', '07/09 - 13/09'],
  ['Tuần 00/2026', 'Tuần 00/2026'],
  ['Tuần 54/2026', 'Tuần 54/2026'],
  ['Tuần 53/2021', 'Tuần 53/2021'],
]) {
  test(`nhãn tuần lịch: ${label}`, () => {
    expect(presentationFigure(weeklyFigure([label])).layout.xaxis?.ticktext).toEqual([expected]);
  });
}

test('biểu đồ nhiều năm giữ năm, dữ liệu và tham chiếu nguồn nguyên vẹn', () => {
  const original = weeklyFigure(['Tuần 37/2025', 'Tuần 37/2026']);
  const before = structuredClone(original);
  const styled = presentationFigure(original);
  expect(styled.layout.xaxis?.ticktext).toEqual(['08/09/2025 - 14/09/2025', '07/09/2026 - 13/09/2026']);
  expect(styled.layout.xaxis?.tickvals).toEqual(before.data[0].x);
  for (const field of ['x', 'y', 'ids', 'customdata', 'meta']) expect(styled.data[0][field]).toEqual(before.data[0][field]);
  expect(original).toEqual(before);
});

test('ngày, tháng, quý và dữ liệu trộn không bị đổi nhãn', () => {
  for (const labels of [['2026-09-07', '2026-09-08'], ['Tháng 09/2026'], ['Quý 3/2026'], ['Tuần 37/2026', '2026-09-08']]) {
    const original = weeklyFigure(labels);
    original.layout.xaxis!.ticktext = ['Nhãn sẵn có'];
    expect(presentationFigure(original).layout.xaxis).toEqual(original.layout.xaxis);
  }
});

test('chart hẹp xuống dòng và giảm nhãn, không giảm dữ liệu hoặc thông tin khi rê chuột', () => {
  const original = weeklyFigure(Array.from({ length: 8 }, (_, index) => `Tuần ${30 + index}/2026`));
  const before = structuredClone(original);
  const styled = presentationFigure(original, 380, 'compact', 327);
  expect(styled.layout.xaxis?.tickangle).toBe(0);
  expect(styled.layout.xaxis?.tickvals).toHaveLength(4);
  expect(styled.layout.xaxis?.tickvals?.[0]).toBe(original.data[0].x?.[0]);
  expect(styled.layout.xaxis?.tickvals?.at(-1)).toBe(original.data[0].x?.at(-1));
  expect(styled.layout.xaxis?.ticktext?.at(-1)).toBe('07/09<br>- 13/09');
  expect(styled.data[0].hovertext?.at(-1)).toBe('07/09 - 13/09');
  expect(styled.data[0].hovertemplate).toContain('%{hovertext}');
  for (const field of ['x', 'y', 'ids', 'customdata', 'meta']) expect(styled.data[0][field]).toEqual(before.data[0][field]);
  expect(original).toEqual(before);
});

async function expectWeeklyAxis(plot: Locator) {
  await expect(plot).toHaveClass(/js-plotly-plot/);
  await expect(plot.locator('.xtick text')).toHaveText(['07/09 - 13/09', '14/09 - 20/09']);
  const measurements = await plot.evaluate(element => {
    const card = element.closest('.chart-card, .contextual-chart-frame')!.getBoundingClientRect();
    return [...element.querySelectorAll('.xtick text')].map(tick => {
      const box = tick.getBoundingClientRect();
      return { left: box.left, right: box.right, bottom: box.bottom, cardLeft: card.left, cardRight: card.right, cardBottom: card.bottom };
    });
  });
  for (const tick of measurements) {
    expect(tick.left).toBeGreaterThanOrEqual(tick.cardLeft - 1);
    expect(tick.right).toBeLessThanOrEqual(tick.cardRight + 1);
    expect(tick.bottom).toBeLessThanOrEqual(tick.cardBottom - 1);
  }
}

for (const viewport of [{ width: 1366, height: 768 }, { width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`nhãn khoảng tuần dùng chung Tổng quan, Thống kê và so sánh ${viewport.width}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize(viewport);
    await installApiHarness(page, { weeklyCharts: true });
    await page.goto('/');
    await page.locator('[data-field="mode"]').selectOption('week');
    await expectWeeklyAxis(page.locator('[data-plot="overview-root"]'));
    await page.locator('[data-plot="overview-root"]').screenshot({ path: `${evidence}/overview-${viewport.width}.png` });
    await page.locator('[data-tab="statistics"]').click();
    await expectWeeklyAxis(page.locator('[data-plot="statistics-root"]'));
    await page.locator('[data-tab="overview"]').click();
    await page.locator('[data-field="scope"]').selectOption('children');
    for (const id of ['child-a', 'child-b']) await expectWeeklyAxis(page.locator(`[data-plot="overview-${id}"]`));
    await page.locator('[data-tab="statistics"]').click();
    for (const id of ['child-a', 'child-b']) await expectWeeklyAxis(page.locator(`[data-plot="statistics-${id}"]`));
    await page.locator('.chart-card').first().screenshot({ path: `${evidence}/statistics-${viewport.width}.png` });
    await page.locator('#compare-action-child-a').click();
    await page.locator('[data-context-compare="child-b"]').check();
    const dialog = page.locator('#contextual-comparison-dialog');
    await dialog.getByRole('tab', { name: 'Thống kê', exact: true }).click();
    const plot = dialog.locator('[data-plot="contextual-comparison"]');
    await expectWeeklyAxis(plot);
    const bar = plot.locator('.barlayer .trace').first().locator('.point path').first();
    await bar.scrollIntoViewIfNeeded();
    const box = await bar.boundingBox();
    await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await expect(dialog.locator('#investigation-drawer')).toContainText('7/9/2026');
    await expect(dialog.locator('#investigation-drawer')).toContainText('13/9/2026');
    await dialog.locator('#investigation-drawer').getByRole('button', { name: 'Đóng', exact: true }).click();
    await dialog.locator('[data-context-field="calculation"]').selectOption('average_per_day');
    await expectWeeklyAxis(plot);
    await dialog.locator('.contextual-main').evaluate(element => element.scrollTo(0, element.scrollHeight));
    await dialog.screenshot({ path: `${evidence}/comparison-${viewport.width}.png` });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  });
}

for (const viewport of [{ width: 1366, height: 768 }, { width: 390, height: 844 }]) {
  test(`tám tuần vẫn đọc được và không cắt nhãn ${viewport.width}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize(viewport);
    await installApiHarness(page, { weeklyCharts: true });
    await page.goto('/');
    await page.locator('[data-field="scope"]').selectOption('children');
    await page.locator('[data-tab="statistics"]').click();
    const figure = weeklyFigure(Array.from({ length: 8 }, (_, index) => `Tuần ${30 + index}/2026`));
    await page.evaluate(async input => {
      const { renderChart } = await import('/src/chart.ts');
      await renderChart(document.querySelector('[data-plot="statistics-child-a"]')!, input, undefined, undefined, 380, 'dense-weeks');
    }, figure);
    const plot = page.locator('[data-plot="statistics-child-a"]');
    await expect.poll(() => plot.locator('.xtick text').count()).toBeGreaterThan(1);
    const ticks = await plot.evaluate(element => {
      const card = element.closest('.chart-card')!.getBoundingClientRect();
      return [...element.querySelectorAll('.xtick text')].map(tick => {
        const bounds = tick.getBoundingClientRect();
        return { text: tick.textContent, left: bounds.left, right: bounds.right, bottom: bounds.bottom, cardBottom: card.bottom };
      });
    });
    expect(ticks.at(-1)?.text).toBe('07/09- 13/09');
    for (const [index, tick] of ticks.entries()) {
      expect(tick.bottom).toBeLessThanOrEqual(tick.cardBottom - 1);
      if (index) expect(tick.left).toBeGreaterThan(ticks[index - 1].right + 3);
    }
    const state = await plot.evaluate(element => {
      const graph = element as unknown as { layout: { xaxis: { tickangle: number } }; data: { x: string[]; hovertext: string[] }[] };
      return { angle: graph.layout.xaxis.tickangle, x: graph.data[0].x, hover: graph.data[0].hovertext };
    });
    expect(state.angle).toBe(0);
    expect(state.x).toEqual(figure.data[0].x);
    expect(state.hover).toHaveLength(8);
    if (viewport.width === 390) expect(ticks.length).toBeLessThan(8);
    await page.locator('.chart-card').first().screenshot({ path: `${evidence}/dense-weeks-${viewport.width}.png` });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    const hiddenTick = await plot.evaluate(element => {
      const graph = element as unknown as { layout: { xaxis: { tickvals: string[] } }; data: { x: string[]; hovertext: string[] }[] };
      const index = graph.data[0].x.findIndex(label => !graph.layout.xaxis.tickvals.includes(label));
      return { index, range: graph.data[0].hovertext[index] };
    });
    expect(hiddenTick.index).toBeGreaterThanOrEqual(0);
    const hiddenBar = plot.locator('.barlayer .point path').nth(hiddenTick.index);
    await hiddenBar.scrollIntoViewIfNeeded();
    const hiddenBox = await hiddenBar.boundingBox();
    // Plotly receives pointer events through its transparent drag layer.
    await page.mouse.move(hiddenBox!.x + hiddenBox!.width / 2, hiddenBox!.y + hiddenBox!.height / 2);
    await expect(plot.locator('.hoverlayer')).toContainText(hiddenTick.range);
    if (viewport.width === 1366) {
      await page.evaluate(async () => {
        const { selectChartPoint } = await import('/src/chart.ts');
        selectChartPoint(document.querySelector('[data-plot="statistics-child-a"]')!, 0, 1);
      });
      const selection = () => plot.evaluate(element => (element as unknown as { data: { selectedpoints: number[] }[] }).data[0].selectedpoints);
      await expect.poll(selection).toEqual([1]);
      await page.setViewportSize({ width: 390, height: 844 });
      await expect.poll(() => plot.locator('.xtick text').count()).toBeLessThan(ticks.length);
      await page.setViewportSize(viewport);
      await expect(plot.locator('.xtick text')).toHaveCount(ticks.length);
      await expect(plot.locator('.barlayer .point')).toHaveCount(8);
      expect(await selection()).toEqual([1]);
    }
  });
}
