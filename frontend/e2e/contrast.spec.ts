import { expect, test, type Locator, type Page } from '@playwright/test';
import { installApiHarness } from './fixtures';

type Rgba = [number, number, number, number];

function parseColor(value: string): Rgba {
  const parts = value.match(/[\d.]+/g)?.map(Number) ?? [];
  return [parts[0] ?? 0, parts[1] ?? 0, parts[2] ?? 0, parts[3] ?? 1];
}

function blend([r, g, b, alpha]: Rgba, background: Rgba): Rgba {
  return [
    r * alpha + background[0] * (1 - alpha),
    g * alpha + background[1] * (1 - alpha),
    b * alpha + background[2] * (1 - alpha),
    1,
  ];
}

function luminance([r, g, b]: Rgba) {
  const values = [r, g, b].map(channel => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
}

async function contrastRatio(locator: Locator): Promise<number> {
  const colors = await locator.evaluate(element => {
    const style = getComputedStyle(element);
    const foreground = element instanceof SVGTextElement && style.fill !== 'none' ? style.fill : style.color;
    let current: Element | null = element;
    let background = 'rgb(255, 255, 255)';
    while (current) {
      const candidate = getComputedStyle(current).backgroundColor;
      const alpha = Number(candidate.match(/[\d.]+/g)?.[3] ?? 1);
      if (candidate !== 'transparent' && alpha > 0) { background = candidate; break; }
      current = current.parentElement;
    }
    return { foreground, background };
  });
  const foreground = blend(parseColor(colors.foreground), parseColor(colors.background));
  const background = parseColor(colors.background);
  const first = luminance(foreground);
  const second = luminance(background);
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}

async function expectAa(locator: Locator, label: string) {
  await expect(locator, `${label} should be rendered`).toBeVisible();
  expect(await contrastRatio(locator), `${label} should meet WCAG AA`).toBeGreaterThanOrEqual(4.5);
}

async function openWorkspace(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await installApiHarness(page);
  await page.goto('/');
  await expect(page.locator('[data-plot="overview-root"].js-plotly-plot')).toBeVisible();
}

async function clickRealBar(page: Page, plotKey: string, trace = 0, point = 0) {
  const bar = page.locator(`[data-plot="${plotKey}"] .barlayer .trace`).nth(trace).locator('.point path').nth(point);
  await expect(bar).toBeVisible();
  await bar.scrollIntoViewIfNeeded();
  const box = await bar.boundingBox();
  if (!box) throw new Error(`Plotly bar ${plotKey}/${trace}/${point} has no browser bounding box`);
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForTimeout(120);
    if (await page.locator('#investigation-drawer').getAttribute('aria-hidden') === 'false') return;
  }
  await expect(page.locator('#investigation-drawer')).toHaveAttribute('aria-hidden', 'false');
}

for (const viewport of [
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
]) {
  test(`critical desktop text meets AA at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await openWorkspace(page, viewport.width, viewport.height);
    await expectAa(page.locator('.breadcrumb'), 'top breadcrumb');
    await expectAa(page.locator('.context-label'), 'hierarchy label');
    await expectAa(page.locator('.card-top span:not(.pill)').first(), 'chart metadata');
    await expectAa(page.locator('[data-plot="overview-root"] .xtick text').first(), 'chart axis label');
    await expectAa(page.locator('[data-plot="overview-root"] .legendtext').first(), 'chart legend');
    await expectAa(page.locator('.tab.active'), 'selected tab');

    await clickRealBar(page, 'overview-root');
    await expect(page.getByRole('heading', { name: /Tổng số ghi nhận 14/ })).toBeVisible();
    await expectAa(page.locator('.validation-line > span').last(), 'validation secondary text');
    await expectAa(page.locator('.entity-path'), 'entity path');
    await expectAa(page.locator('.entity-path span').first(), 'entity path separator');
    await expectAa(page.locator('.provenance-grid dt').first(), 'drawer metadata label');
    await page.getByRole('button', { name: 'Mở đúng dòng đối chiếu' }).click();
    await expect(page.getByText('Dòng đối chiếu của điểm đã chọn')).toBeVisible();
    await expectAa(page.locator('th').first(), 'Audit table header');
    await expectAa(page.locator('td').first(), 'Audit table cell');
    await expectAa(page.locator('.pager span'), 'Audit pager');
    await expectAa(page.locator('.pager button:disabled').first(), 'disabled pager action');

    await page.getByRole('button', { name: /Lịch sử nhập/ }).click();
    await expectAa(page.locator('th').first(), 'History table header');
    await expectAa(page.locator('td').first(), 'History table cell');

    if (viewport.width === 1440) {
      await page.getByRole('button', { name: /Nhập Excel/ }).click();
      await page.locator('#import-mode').selectOption('full_snapshot');
      await page.locator('#file-input').setInputFiles({ name: 'snapshot.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('fixture') });
      await page.locator('#preview-action').click();
      await expectAa(page.getByRole('button', { name: 'Xác nhận nhập bản chụp' }), 'disabled destructive action');
    }
  });
}
