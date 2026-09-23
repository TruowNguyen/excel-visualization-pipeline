import { expect, test, type Page } from '@playwright/test';

type Trace = {
  id: number; trigger: string; status: string; interactionAt: number; stateUpdatedAt: number;
  feedbackPaintAt?: number; requestDispatchedAt?: number; responseHeadersAt?: number;
  responseBodyAt?: number; dataReadyAt?: number; jsonParseMs: number; fingerprintMs: number;
  reconciliationMs: number; plotlyMs: number; chartsRendered: number; chartsSkipped: number;
  finalPaintAt?: number; backendTiming?: string;
};

async function traces(page: Page): Promise<Trace[]> {
  return page.evaluate(() => (window as typeof window & { __EVP_WORKSPACE_PERF__?: Trace[] }).__EVP_WORKSPACE_PERF__ || []);
}

async function act(page: Page, action: () => Promise<void>): Promise<Trace[]> {
  const before = (await traces(page)).length;
  await action();
  await expect.poll(async () => (await traces(page)).length, { timeout: 120_000 }).toBeGreaterThan(before);
  return (await traces(page)).slice(before);
}

test('measure real VSO filter lifecycle', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('[data-field="project"]')).toBeVisible();
  await expect.poll(async () => (await traces(page)).some(trace => trace.status === 'success'), { timeout: 60_000 }).toBe(true);

  const measured: { scenario: string; traces: Trace[] }[] = [];
  measured.push({ scenario: 'project-selection', traces: await act(page, () => page.locator('[data-field="project"]').selectOption('VSO')) });
  measured.push({ scenario: 'entity-selection', traces: await act(page, () => page.locator('[data-field="entity"]').selectOption('1-1-chat-luong-canh-bao-ghi-nhan-tren-he-thong-ba6898fb1d78')) });
  measured.push({ scenario: 'scope-to-children', traces: await act(page, () => page.locator('[data-field="scope"]').selectOption('children')) });
  await expect(page.locator('[data-plot^="overview-"]')).toHaveCount(9, { timeout: 120_000 });
  measured.push({ scenario: 'mode-week', traces: await act(page, () => page.locator('[data-field="mode"]').selectOption('week')) });
  measured.push({ scenario: 'child-statistics-view', traces: await act(page, () => page.locator('[data-tab="statistics"]').click()) });
  await expect(page.locator('[data-plot^="statistics-"]')).toHaveCount(9, { timeout: 120_000 });
  measured.push({ scenario: 'return-child-overview', traces: await act(page, () => page.locator('[data-tab="overview"]').click()) });
  await expect(page.locator('[data-plot^="overview-"]')).toHaveCount(9, { timeout: 120_000 });

  for (const count of ['7', '8', '7', '8', '7']) {
    measured.push({ scenario: `week-count-${count}`, traces: await act(page, async () => {
      await page.locator('[data-field="count"]').fill(count);
      await page.locator('[data-field="count"]').press('Tab');
    }) });
  }
  measured.push({ scenario: 'reapply-unchanged-count', traces: await act(page, async () => {
    await page.locator('[data-field="count"]').press('ArrowUp');
    await page.locator('[data-field="count"]').press('ArrowDown');
  }) });

  const beforeRapid = (await traces(page)).length;
  await page.locator('[data-field="count"]').fill('6'); await page.locator('[data-field="count"]').press('Tab');
  await page.locator('[data-field="count"]').fill('5'); await page.locator('[data-field="count"]').press('Tab');
  await page.locator('[data-field="count"]').fill('4'); await page.locator('[data-field="count"]').press('Tab');
  await expect.poll(async () => (await traces(page)).length, { timeout: 120_000 }).toBeGreaterThan(beforeRapid);
  await expect(page.locator('#workspace-loading')).toBeHidden({ timeout: 120_000 });
  measured.push({ scenario: 'rapid-count', traces: (await traces(page)).slice(beforeRapid) });

  measured.push({ scenario: 'mode-custom', traces: await act(page, () => page.locator('[data-field="mode"]').selectOption('custom')) });
  measured.push({ scenario: 'date-start', traces: await act(page, () => page.locator('[data-field="start"]').fill('2026-09-01')) });
  measured.push({ scenario: 'date-end', traces: await act(page, () => page.locator('[data-field="end"]').fill('2026-09-15')) });

  console.log(`REAL_FILTER_PERF ${JSON.stringify(measured)}`);
});
