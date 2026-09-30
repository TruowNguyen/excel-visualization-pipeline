import { expect, test } from '@playwright/test';
import { installApiHarness } from './fixtures';
import {
  getChildrenScopeLabel,
  getComparisonTerminology,
  getCurrentScopeLabel,
  getEligibilityReasonMessage,
  getEntityDisplayName,
  getEntityLevelLabel,
  normalizeSectionDisplayLabel,
} from '../src/terminology';

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
