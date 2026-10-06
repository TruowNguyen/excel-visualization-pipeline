import { test, expect } from '@playwright/test';
import { installApiHarness } from './fixtures';

const project = (label: string) => ({label, records:12, chartable:12, entities:4, units:1, minDate:'2026-09-16', maxDate:'2026-09-17'});

for (const savedProject of ['', 'ANVF']) {
  test(`opens VSO instead of the first project or saved ${savedProject || 'empty'} selection`, async ({page}) => {
    const { calls } = await installApiHarness(page);
    await page.route('**/api/bootstrap', route => route.fulfill({json:{projects:[project('ANVF'), project('VSO')]}}));
    if (savedProject) await page.addInitScript(() => {
      sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({project:'ANVF',entity:'anvf-only',start:'2020-01-01',end:'2020-01-02',tab:'overview'}));
    });
    await page.goto('/');
    await expect(page.locator('[data-field="project"]')).toHaveValue('VSO');
    await expect.poll(() => calls.some(call => call.pathname === '/api/projects/VSO/workspace')).toBe(true);
    const workspace = calls.find(call => call.pathname === '/api/projects/VSO/workspace')!;
    expect(workspace.search).not.toContain('anvf-only');
    expect(workspace.search).not.toContain('2020-01');
    await expect(page.locator('[data-field="project"] option')).toHaveText(['ANVF','VSO']);
  });
}

test('uses an available project when VSO is absent', async ({page}) => {
  await installApiHarness(page);
  await page.route('**/api/bootstrap', route => route.fulfill({json:{projects:[project('ANVF')]}}));
  await page.route('**/api/projects/ANVF/entities', route => route.fulfill({json:{entities:[]}}));
  await page.route('**/api/projects/ANVF/workspace**', route => route.fulfill({status:503,json:{detail:'Synthetic unavailable workspace'}}));
  await page.goto('/');
  await expect(page.locator('[data-field="project"]')).toHaveValue('ANVF');
});
