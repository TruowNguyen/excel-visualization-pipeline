import { expect, test } from '@playwright/test';
import { installApiHarness } from './fixtures';
import { presentationFigure } from '../src/chart';
import type { Figure } from '../src/types';
import {
  getChildrenScopeLabel,
  getComparisonTerminology,
  getCurrentScopeLabel,
  getEligibilityReasonMessage,
  getEntityDisplayName,
  getEntityLevelLabel,
  normalizeSectionDisplayLabel,
  getMetricDisplayLabel,
  formatMetricText,
  metricPresentation,
} from '../src/terminology';

test('uses the three public metric labels without mutating keys, numbers or provenance', () => {
  expect(['Tổng số', 'Báo sai/Lỗi', '% báo sai', '%báo sai'].map(getMetricDisplayLabel)).toEqual([
    'Tổng số ghi nhận', 'Tổng báo sai (lỗi)', 'Tỷ lệ báo sai', 'Tỷ lệ báo sai',
  ]);
  expect(getMetricDisplayLabel('Chỉ số khác')).toBe('Chỉ số khác');
  const copy = 'Tổng số ghi nhận · Tổng báo sai (lỗi) · Tỷ lệ báo sai';
  expect(formatMetricText(copy)).toBe(copy);
  const figure: Figure = {
    data: [{ type: 'bar', name: 'Tổng · Báo sai/Lỗi', x: ['2026-09-16'], y: [3],
      ids: ['obs_1'], meta: { statisticsMetric: 'Báo sai/Lỗi', lineage: {
        contractVersion: 1, kind: 'exact-observation', selectable: true, lineageRefs: ['lin_1'],
      } }, customdata: [['3', 'Báo sai/Lỗi', 'ticket']],
      hovertemplate: 'Tổng số/Cảnh báo: %{y}<br>%báo sai<extra></extra>',
    }], layout: { yaxis: { title: { text: 'Tổng số' } }, yaxis2: { title: '% báo sai' } },
  };
  const original = structuredClone(figure);
  const display = presentationFigure(figure);
  expect(display.data[0].name).toBe('Tổng · Tổng báo sai (lỗi)');
  expect(display.data[0].hovertemplate).toBe('Tổng số ghi nhận: %{y}<br>Tỷ lệ báo sai<extra></extra>');
  expect(display.data[0].customdata).toEqual([['3', 'Tổng báo sai (lỗi)', 'ticket']]);
  expect(display.layout.yaxis).toEqual({ title: { text: 'Tổng số ghi nhận' } });
  expect(display.layout.yaxis2).toEqual({ title: 'Tỷ lệ báo sai' });
  expect(display.data[0].y).toEqual(original.data[0].y);
  expect(display.data[0].ids).toEqual(original.data[0].ids);
  expect(display.data[0].meta).toEqual(original.data[0].meta);
  expect(figure).toEqual(original);

  const analysis = { metricCode: 'error', metricDisplayName: 'Báo sai/Lỗi',
    narrative: { text: 'Tổng số tăng; % báo sai giảm.' },
    entityLabel: 'Tổng số', evidenceId: 'ev_1', rawValue: 'Báo sai/Lỗi',
  };
  const formatted = metricPresentation(analysis);
  expect(formatted.metricDisplayName).toBe('Tổng báo sai (lỗi)');
  expect(formatted.narrative.text).toBe('Tổng số ghi nhận tăng; Tỷ lệ báo sai giảm.');
  expect(formatted.entityLabel).toBe(analysis.entityLabel);
  expect(formatted.evidenceId).toBe(analysis.evidenceId);
  expect(formatted.rawValue).toBe(analysis.rawValue);
  expect(analysis.metricDisplayName).toBe('Báo sai/Lỗi');
});

test('shows public labels in AI and comparison while sending canonical API metric keys', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
      project: 'VSO', entity: 'root', scope: 'children', tab: 'statistics',
      statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
    }));
  });
  const harness = await installApiHarness(page);
  await page.goto('/');
  await expect(page.locator('[data-plot="statistics-child-a"] .legend')).toContainText('Tổng số ghi nhận');
  await expect(page.locator('[data-plot="statistics-child-a"] .legend')).toContainText('Tổng báo sai (lỗi)');
  await page.locator('#compare-action-child-a').click();
  const metric = page.locator('#contextual-metric');
  await expect(metric.locator('option')).toHaveText(['Tổng số ghi nhận', 'Tổng báo sai (lỗi)', 'Tỷ lệ báo sai']);
  await metric.selectOption({ label: 'Tỷ lệ báo sai' });
  await page.locator('[data-context-compare="child-b"]').check();
  await expect(page.locator('[data-plot="contextual-comparison"]')).toHaveClass(/js-plotly-plot/);
  await expect(metric).toHaveValue('% báo sai');
  const request = harness.calls.filter(call => call.search.includes('comparison_anchor=child-a')).at(-1);
  expect(new URLSearchParams(request?.search).get('comparison_metric')).toBe('% báo sai');
  await page.getByRole('button', { name: 'Xong' }).click();
  await page.locator('[data-tab="overview"]').click();
  const aiSelect = page.locator('[data-field="aiMetricCode"]');
  await expect(aiSelect.locator('option[value="total"]')).toHaveText('Tổng số ghi nhận');
  await expect(aiSelect.locator('option[value="error"]')).toHaveText('Tổng báo sai (lỗi)');
  await expect(aiSelect.locator('option[value="error_rate"]')).toHaveText('Tỷ lệ báo sai');
});

test('maps every entity level to the locked CX terminology', () => {
  expect(getEntityLevelLabel('project')).toBe('Dự án');
  expect(getEntityLevelLabel('section')).toBe('Nhóm vấn đề');
  expect(getEntityLevelLabel('item')).toBe('Vấn đề');
  expect(getEntityLevelLabel('subitem')).toBe('Tình trạng');
  expect(getEntityLevelLabel('unknown')).toBe('Nội dung theo dõi');

  expect(getCurrentScopeLabel('project')).toBe('Toàn dự án');
  expect(getChildrenScopeLabel('project')).toBe('Các nhóm vấn đề trong dự án');
  expect(getCurrentScopeLabel('section')).toBe('Nhóm vấn đề đang chọn');
  expect(getChildrenScopeLabel('section')).toBe('Các vấn đề trong nhóm');
  expect(getCurrentScopeLabel('item')).toBe('Vấn đề đang xem');
  expect(getChildrenScopeLabel('item')).toBe('Các tình trạng của vấn đề');
  expect(getCurrentScopeLabel('subitem')).toBe('Tình trạng đang xem');
});

test('normalizes structural numbering only for section display labels', () => {
  const rawLabel = '1.1. Chất lượng cảnh báo - ghi nhận trên hệ thống';
  const section = { entity_label: rawLabel, entity_level: 'section' };
  expect(getEntityDisplayName(section)).toBe('Chất lượng cảnh báo - ghi nhận trên hệ thống');
  expect(section.entity_label).toBe(rawLabel);
  expect(normalizeSectionDisplayLabel('2.3.4. Kiểm soát trạng thái')).toBe('Kiểm soát trạng thái');
  expect(normalizeSectionDisplayLabel('1.')).toBe('1.');
  expect(getEntityDisplayName({ entity_label: 'Camera 360 lỗi kết nối', entity_level: 'item' })).toBe('Camera 360 lỗi kết nối');
  expect(getEntityDisplayName({ entity_label: '5G mất kết nối', entity_level: 'item' })).toBe('5G mất kết nối');
  expect(getEntityDisplayName({ entity_label: '24/7 Monitoring', entity_level: 'item' })).toBe('24/7 Monitoring');
  expect(getEntityDisplayName({ entity_label: 'Camera số 2', entity_level: 'item' })).toBe('Camera số 2');
});

test('uses comparison and eligibility wording for the actual level without exposing codes', () => {
  expect(getComparisonTerminology('item').title).toBe('So sánh các vấn đề trong cùng nhóm');
  expect(getComparisonTerminology('subitem').title).toBe('So sánh các tình trạng của cùng vấn đề');
  expect(getComparisonTerminology('section').title).toBe('So sánh các nhóm vấn đề');
  expect(getComparisonTerminology('unknown').title).toBe('So sánh các nội dung trong cùng nhóm');

  const itemReason = getEligibilityReasonMessage('NOT_SIBLING', 'item');
  const subitemReason = getEligibilityReasonMessage('NOT_SIBLING', 'subitem');
  expect(itemReason).toBe('Vấn đề này không thuộc cùng nhóm.');
  expect(subitemReason).toBe('Tình trạng này không thuộc cùng vấn đề.');
  expect(getEligibilityReasonMessage('UNIT_MISMATCH', 'item')).not.toContain('UNIT_MISMATCH');
  expect(getEligibilityReasonMessage('NO_METRIC_VALUE', 'item')).not.toContain('NO_METRIC_VALUE');
});

test('renders normalized CX wording across sidebar, breadcrumb and comparison surfaces', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
      project: 'VSO', entity: 'root', scope: 'children', tab: 'statistics',
      statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
    }));
  });
  await installApiHarness(page);
  await page.goto('/');

  await expect(page.getByText('Bộ lọc báo cáo')).toBeVisible();
  await expect(page.getByLabel('Nội dung theo dõi')).toContainText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
  await expect(page.getByLabel('Mức hiển thị')).toContainText('Các vấn đề trong nhóm');
  await expect(page.getByLabel('Nội dung đang xem')).toContainText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
  await expect(page.getByLabel('Nội dung đang xem')).not.toContainText('1.1.');
  await expect(page.getByText('Camera 360 lỗi kết nối', { exact: true })).toBeVisible();
  await expect(page.getByText('5G mất kết nối', { exact: true })).toBeVisible();

  await page.locator('#compare-action-child-a').click();
  await expect(page.getByRole('heading', { name: 'So sánh các vấn đề trong cùng nhóm' })).toBeVisible();
  await expect(page.getByText('Đang so sánh từ:')).toBeVisible();
  await expect(page.getByText('Camera 360 lỗi kết nối', { exact: true }).first()).toBeVisible();
  await expect(page.locator('.contextual-entity.anchor')).toContainText('Đang xem');
  await expect(page.locator('#contextual-comparison-dialog')).not.toContainText('NOT_SIBLING');
  await page.getByRole('button', { name: 'Xong' }).click();

  await expect(page.locator('[data-tab="comparison"]')).toHaveCount(0);
  await expect(page.locator('[data-tab="audit"]')).toHaveCount(0);
});

for (const viewport of [
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
]) {
  test(`keeps CX terminology readable at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.addInitScript(() => {
      sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({
        project: 'VSO', entity: 'root', scope: 'children', tab: 'statistics',
        statisticsGroup: 'week', statisticsMode: 'both', statisticsRange: 'recent', statisticsCount: 8,
      }));
    });
    await installApiHarness(page);
    await page.goto('/');

    await expect(page.locator('[data-plot="statistics-child-a"].js-plotly-plot')).toBeVisible();
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.getByLabel('Nội dung theo dõi')).toBeVisible();
    await expect(page.getByLabel('Nội dung đang xem')).toBeVisible();
    await expect(page.locator('.control-bar')).toBeVisible();
    await expect(page.locator('#compare-action-child-a')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    expect(await page.locator('.control-bar').evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);

    await expect(page.locator('[data-tab="comparison"]')).toHaveCount(0);
    await expect(page.locator('[data-tab="audit"]')).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  });
}
