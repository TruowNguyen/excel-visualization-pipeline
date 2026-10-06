import { test, expect } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { installApiHarness, aiAnalysis } from './fixtures';

const liveEvidencePath = new URL('../../specs/ai-data/evidence/2026-10-04-context-quantified-verified.json', import.meta.url);
const liveEvidence = process.env.EVP_LOCAL_EVIDENCE !== '0' && existsSync(liveEvidencePath)
  ? JSON.parse(readFileSync(liveEvidencePath, 'utf8')) : null;

test('nhấn mạnh không đổi chữ/số, không thực thi HTML, không tô đậm ngày hoặc mọi phần trăm', async ({ page }) => {
  await installApiHarness(page);
  await page.goto('/');
  const result = await page.evaluate(async () => {
    const path = '/src/insight-text.ts';
    const { renderInsightText } = await import(path);
    const original = 'Số lỗi tăng rồi giảm. Ngày 12/09/2026 tăng từ 19 lên 43, chênh lệch +24 (+126.32%); sau đó giảm từ 43 xuống 32, chênh lệch -11 (-25.58%). <img src=x onerror="alert(1)">';
    const element = document.createElement('div');
    element.innerHTML = renderInsightText(original);
    return { original, text: element.textContent, tags: [...element.querySelectorAll('*')].map(node => node.tagName),
      deltas: [...element.querySelectorAll('.ai-emphasis-delta')].map(node => node.textContent),
      emphasis: [...element.querySelectorAll('strong')].map(node => node.textContent) };
  });
  expect(result.text).toBe(result.original);
  expect(result.tags.every(tag => tag === 'STRONG')).toBeTruthy();
  expect(result.deltas).toEqual(['+24', '-11']);
  expect(result.emphasis).toHaveLength(3);
  expect(result.emphasis).not.toContain('12/09/2026');
  expect(result.emphasis).not.toContain('+126.32%');
});

for (const width of [1280, 1440, 1920]) {
  for (const view of ['node', 'children', 'statistics']) {
    test(`insight đọc đủ nội dung và dùng hết vùng báo cáo ${view} ${width}`, async ({ page }) => {
      test.skip(view !== 'node' && !liveEvidence, 'Local real-data evidence is not included in Git.');
      await page.setViewportSize({ width, height: 1000 });
      const longName = 'Vấn đề có tên dài để kiểm tra xuống dòng và không bị cắt mất thông tin '.repeat(4);
      if (view === 'node') {
        const fixture = aiAnalysis({ metricCode: 'all' });
        fixture.narrative.summary.text = 'Số lỗi tăng rồi giảm, chênh lệch +24 (+126.32%).';
        await installApiHarness(page, { aiFixture: fixture });
      } else {
        await installApiHarness(page);
        await page.route('**/ai/context-insight', async route => {
          const body = structuredClone(liveEvidence[view === 'statistics' ? 13 : 2].body);
          body.dataAsOf.committedImportRef = 'imp_1';
          body.dataAsOf.stale = false;
          // The saved evaluation omits this duplicate bundle in compact mode.
          body.report.relationshipDetails = [];
          body.report.issues[0].entityLabel = longName;
          body.report.issues[0].metrics.find((metric: any) => metric.series.length).series[0].periodLabel = longName;
          await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
        });
      }
      await page.goto('/');
      if (view === 'children') await page.getByLabel('Mức hiển thị').selectOption('children');
      if (view === 'statistics') await page.locator('[data-tab="statistics"]').click();
      const panel = page.locator('#ai-insights');
      await panel.getByRole('button', { name: view === 'node' ? 'Phân tích khoảng đang xem' : 'Phân tích phạm vi đang xem' }).click();
      const paragraph = panel.locator(view === 'node' ? '.ai-executive > p' : '.ai-report-section > p').first();
      await expect(paragraph).toBeVisible();
      await expect(panel.locator('.ai-emphasis').first()).toBeVisible();
      const size = await paragraph.evaluate(element => ({ width: element.getBoundingClientRect().width,
        parent: element.parentElement!.getBoundingClientRect().width,
        maxWidth: getComputedStyle(element).maxWidth, overflow: getComputedStyle(element).overflow,
        fontSize: parseFloat(getComputedStyle(element).fontSize) }));
      expect(size.maxWidth).toBe('none');
      expect(size.width).toBeCloseTo(size.parent, 1);
      expect(size.fontSize).toBeGreaterThanOrEqual(16);
      expect(size.overflow).not.toBe('hidden');
      if (view !== 'node') {
        const issue = panel.locator('.ai-issue-detail').first();
        await issue.locator(':scope > summary').click();
        await expect(issue.locator(':scope > summary')).toHaveText(new RegExp('Vấn đề có tên dài'));
        const calculation = issue.locator('.ai-calculation-section[data-calculation="sum"]');
        await calculation.getByText('Xem số liệu và nguồn', { exact: true }).click();
        const cell = calculation.locator('tbody td').first();
        await expect(cell).toHaveText(longName);
        expect(await cell.evaluate(element => getComputedStyle(element).textOverflow)).toBe('clip');
        expect(await cell.evaluate(element => getComputedStyle(element).overflow)).toBe('visible');
      }
      expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      await panel.screenshot({ path: `../.impeccable/review/insight-reading-${view}-${width}.png` });
    });
  }
}
