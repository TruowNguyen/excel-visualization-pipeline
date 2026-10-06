import { test, expect } from '@playwright/test';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { installApiHarness } from './fixtures';

// Diagnostic replay of real endpoint output. Dashboard scaffolding is synthetic;
// report numbers/prose are the unmodified evaluation response. No provider calls here.
// Explicit opt-in: these captures replay a dated evaluation, not fresh provider
// output, and should not silently run in the ordinary regression suite.
const enabled = process.env.EVP_REPORT_AUDIT === '1';
const evidence = enabled
  ? JSON.parse(readFileSync(process.env.EVP_REPORT_AUDIT_INPUT || '../specs/ai-data/evidence/2026-10-06-report-audit-verified.json', 'utf8')) : [];
const output = process.env.EVP_REPORT_AUDIT_OUTPUT || '../.impeccable/review/reports-audit-2026-10-06';
if (enabled && process.env.EVP_REPORT_AUDIT_FINAL_INPUT) {
  const latest = JSON.parse(readFileSync(process.env.EVP_REPORT_AUDIT_FINAL_INPUT, 'utf8'));
  evidence[0] = latest[0]; evidence[3] = latest[1];
}

const cases = process.env.EVP_REPORT_AUDIT_CASES?.split(',').map(Number) || [0, 3, 6];
for (const index of cases) {
  test(`audit real report response ${index + 1}: layout and chart template`, async ({ page }) => {
    test.skip(!enabled, 'Set EVP_REPORT_AUDIT=1 to replay the dated real report evidence.');
    const document = evidence[index].body;
    await installApiHarness(page, { weeklyCharts: true });
    await page.route('**/api/projects/*/reports**', async route => {
      const path = new URL(route.request().url()).pathname;
      await route.fulfill({ json: route.request().method() === 'GET' && path.endsWith('/reports')
        ? { items: [] } : document });
    });
    await page.goto('/');
    await page.locator('[data-tab="report"]').click();
    await page.getByRole('button', { name: 'Tạo báo cáo mới', exact: true }).click();
    await page.getByRole('button', { name: 'Chuẩn bị bản nháp', exact: true }).click();
    await expect(page.locator('[data-report-chart-ready="true"]')).toHaveCount(document.storyPanels?.length || document.charts.length);
    await expect(page.locator('.report-workspace')).toHaveAttribute('aria-busy', 'false');
    const measurements = await page.evaluate(() => {
      const top = (selector: string) => document.querySelector(selector)!.getBoundingClientRect().top + window.scrollY;
      return {
        viewportHeight: window.innerHeight,
        documentHeight: window.document.documentElement.scrollHeight,
        storyTop: top('#report-story'), findingsTop: top('#report-findings'),
        exportTop: top('[data-report-action="export"]'),
        issueStoryCount: document.querySelectorAll('.report-issue-story').length,
        paragraphCount: document.querySelectorAll('.report-paragraph').length,
        setupCollapsed: !document.querySelector<HTMLDetailsElement>('.report-setup')!.open,
        overflow: window.document.documentElement.scrollWidth > window.innerWidth + 1,
        charts: [...document.querySelectorAll('[data-report-chart]')].map(element => {
          const plot = element as unknown as { _fullData: any[]; _fullLayout: any };
          return { width: element.clientWidth, traces: plot._fullData.map(trace => ({
            type: trace.type, color: trace.line?.color ?? trace.marker?.color,
          })), tickLabels: plot._fullLayout.xaxis.ticktext,
          hovermode: plot._fullLayout.hovermode, showlegend: plot._fullLayout.showlegend };
        }),
      };
    });
    expect(measurements.overflow).toBe(false);
    if (document.storyPanels) {
      expect(await page.locator('.report-issue-story').count()).toBe(document.storyPanels.length);
      expect(await page.locator('.report-chart-analysis [data-report-block]').count()).toBe(document.storyPanels.flatMap((p:any) => [...p.blockIds, ...(p.readings || [])]).length);
      for (const panel of document.storyPanels) {
        const container = page.locator(`#report-panel-${panel.panelId}`);
        expect(await container.evaluate(el => !!(el.querySelector('[data-report-chart]')!.compareDocumentPosition(el.querySelector('.report-chart-analysis')!) & Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true);
      }
      if (document.template?.version === '1.3') {
        const visible = new Set(document.storyPanels.flatMap((p:any) => p.blockIds));
        const supplemental = document.blocks.filter((b:any) => b.section === 'phases' && !visible.has(b.blockId));
        if (supplemental.length) {
          await expect(page.locator('.report-supplemental')).toBeVisible();
          await expect(page.locator('.report-supplemental')).not.toHaveAttribute('open');
          for (const block of supplemental) {
            await expect(page.locator(`[data-report-block="${block.blockId}"]`)).toHaveCount(1);
          }
        }
        const texts = await page.locator('.report-chart-analysis [data-report-block] > p').allTextContents();
        expect(new Set(texts).size).toBe(texts.length);
      }
    }
    mkdirSync(output, { recursive: true });
    writeFileSync(`${output}/case-${index + 1}.json`, JSON.stringify({
      reportId: document.reportId, generation: document.generation,
      reportData: 'real endpoint response', dashboardScaffolding: 'synthetic fixture', ...measurements,
    }, null, 2));
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${output}/case-${index + 1}-top.png` });
    // Viewport captures avoid stitched element screenshots moving sticky chrome
    // into the middle of a long story. Center the actual chart in the viewport.
    await page.locator('[data-report-chart]').first().scrollIntoViewIfNeeded();
    await page.locator('[data-report-chart]').first().evaluate(el => el.scrollIntoView({block:'center'}));
    await page.screenshot({ path: `${output}/case-${index + 1}-story.png` });
    if (document.storyPanels?.some((p:any) => p.kind === 'metric')) {
      const detail = document.storyPanels.find((p:any) => p.kind === 'metric');
      await page.locator(`#report-panel-${detail.panelId}`).evaluate(el => el.scrollIntoView({block:'start'}));
      await page.screenshot({path:`${output}/case-${index + 1}-metric.png`});
    }
    if (index === 0 && document.selectedFindingIds.length) {
      const findingId = document.selectedFindingIds[0];
      const finding = page.locator(`[data-report-finding="${findingId}"]`);
      await finding.locator('input[type=checkbox]').uncheck();
      await finding.locator('[data-report-action="locate"]').click();
      const chartId = document.findings.find((f:any) => f.findingId === findingId).anchors[0].chartId;
      const panelId = document.storyPanels.find((p:any) => p.chartIds.includes(chartId)).panelId;
      const chart = page.locator(`[data-report-chart="${panelId}"]`);
      await expect.poll(() => chart.evaluate(el => (el as any)._fullLayout.annotations.some((a:any) => a.text === 'Đang xem'))).toBe(true);
      await expect(finding.locator('input[type=checkbox]')).not.toBeChecked();
      await chart.evaluate(el => el.scrollIntoView({block:'center'}));
      await page.screenshot({path:`${output}/deselected-finding.png`});
    }
    if (index === 1) {
      await page.setViewportSize({width:390,height:1000});
      await page.locator('[data-report-chart]').first().evaluate(el => el.scrollIntoView({block:'center'}));
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({path:`${output}/weekly-390.png`});
    }
  });
}
