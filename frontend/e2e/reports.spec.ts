import { test, expect, type Page } from '@playwright/test';
import { installApiHarness } from './fixtures';
import { reportFigure } from '../src/report-chart';

// Explicit synthetic UI fixture. Real Engine/LLM/export evidence is separate.
function reportFixture() {
  const values = [16,8,10,8,19,43,32,22,22];
  const points = values.map((value,index) => ({ periodStart:`2026-09-${String(index+7).padStart(2,'0')}`,
    periodEnd:`2026-09-${String(index+7).padStart(2,'0')}`, periodLabel:`${String(index+7).padStart(2,'0')}/09/2026`,
    value, displayValue:String(value), factId:`fact-${index}`,evidenceId:`ev-${index}` }));
  const chart = { chartId:'chart-error',entityRef:'root',entityLabel:'Chất lượng cảnh báo - ghi nhận trên hệ thống',
    metricCode:'error',metricLabel:'Tổng báo sai (lỗi)',calculation:'sum',calculationLabel:'Tổng trong kỳ',unit:'ticket', points,
    quality:{validPeriodCount:9,expectedPeriodCount:9,limitations:[]} };
  const anchors = (indices:number[]) => indices.map(index => ({...points[index],anchorId:`anchor-${index}`,chartId:chart.chartId,
    entityRef:'root',metricCode:'error',calculation:'sum'}));
  const findings = [
    {findingId:'finding-peak',title:'Tổng báo sai (lỗi)',text:'Số lỗi tăng mạnh lên đỉnh 43, sau đó giảm liên tiếp và giữ nguyên ở 22.',
      source:'deterministic',kind:'peak_retreat',anchorType:'interval',entityRef:'root',entityLabel:chart.entityLabel,calculation:'sum',blockId:'block-phase',anchors:anchors([4,5,8])},
    {findingId:'finding-trough',title:'Tổng báo sai (lỗi)',text:'Số lỗi giảm ở đầu giai đoạn, ghi nhận mức thấp nhất 8.',
      source:'deterministic',kind:'trough_recovery',anchorType:'point',entityRef:'root',entityLabel:chart.entityLabel,calculation:'sum',blockId:null,anchors:anchors([1])},
  ];
  return {schemaVersion:'cx-report-v1',reportId:'rpt_ui_synthetic',revision:1,title:'Báo cáo CX — dữ liệu kiểm thử',createdAt:'2026-10-05T03:00:00Z',updatedAt:'2026-10-05T03:00:00Z',
    context:{project:'VSO',view:'overview',parentEntityRef:'root',selection:'node',requestedCount:1,analyzedCount:1,excluded:[],calculation:'sum'},
    window:{start:'2026-09-07',end:'2026-09-15',groupBy:'day'}, dataAsOf:{snapshotId:'as_synthetic',committedImportRef:'imp_1',generatedAt:'2026-10-05T03:00:00Z',sourceCommittedAt:'2026-10-04T03:00:00Z',checksum:'synthetic'},
    review:{status:'needs_review',publicationStatus:'draft',checkedAt:null},freshness:{newerDataAvailable:false},generation:{status:'engine_only',provider:{model:'fixture-not-a-provider'},validation:{status:'not_run',errors:[]}},
    executiveSummary:[{blockId:'block-overview',text:'Số lỗi giảm ở đầu giai đoạn, sau đó tăng lên mức cao nhất 43. Sau đỉnh, số lỗi giảm liên tiếp và giữ nguyên ở cuối chuỗi.',source:'deterministic',section:'overview'}],
    blocks:[{blockId:'block-phase',text:'Số lỗi giảm từ 16 xuống 8 rồi tăng mạnh lên đỉnh 43, chênh lệch 35. Sau đỉnh, số lỗi giảm về 22 và giữ nguyên ở kỳ cuối.',
      source:'deterministic',section:'phases',entityRef:'root',calculation:'sum',candidateId:'candidate-phase'}],charts:[chart],findings,selectedFindingIds:['finding-peak','finding-trough'],
    kpis:[{chartId:chart.chartId,entityRef:'root',entityLabel:chart.entityLabel,metricLabel:chart.metricLabel,calculationLabel:'Tổng trong kỳ',unit:'ticket',quality:chart.quality,
      value:22,displayValue:'22',periodStart:points[8].periodStart,periodEnd:points[8].periodEnd,periodLabel:points[8].periodLabel,evidenceIds:['ev-8'],change:{absoluteDisplay:'0',relativeDisplay:'0%',direction:'unchanged'}}],
    limitations:[],userNotes:'',versions:[{revision:1,createdAt:'2026-10-05T03:00:00Z',checkedAt:null}],
    evidence:points.map((p,index) => ({evidenceId:p.evidenceId,observedDate:p.periodStart,periodStart:p.periodStart,periodEnd:p.periodEnd,periodLabel:p.periodLabel,
      target:{kind:'exact',observationRef:`obs_root_${index+1}`,lineageRef:`lin_root_${index+1}`}}))};
}

async function harness(page: Page, delay = 0, ai = false) {
  const baseCalls = await installApiHarness(page);
  const calls: {url:string;body:any;method:string}[] = [];
  let deleted = false;
  let current = reportFixture();
  if (ai) {
    current.blocks[0].source = 'ai';
    current.generation.status = 'ready';
  }
  const versions = new Map<number, typeof current>();
  versions.set(1, structuredClone(current));
  await page.route('**/api/projects/*/reports**', async route => {
    const url = new URL(route.request().url());
    const body = route.request().postDataJSON();
    calls.push({url:url.pathname,body,method:route.request().method()});
    if (route.request().method() === 'DELETE') {
      deleted = true;
      await route.fulfill({json:{reportId:current.reportId,status:'deleted'}}); return;
    }
    if (route.request().method() === 'GET' && url.pathname.endsWith('/reports')) {
      await route.fulfill({json:{items: !deleted && calls.some(c => c.body?.context) ? [{...current}] : []}});return;
    }
    if (route.request().method() === 'GET') {
      const revision = Number(url.pathname.split('/revisions/')[1]);
      await route.fulfill({json:{...(versions.get(revision) || current), versions:current.versions}});return;
    }
    if (url.pathname.endsWith('/regenerate')) {
      if (delay) await new Promise(resolve => setTimeout(resolve,delay));
      current = {...current,revision:current.revision+1,generation:{...current.generation,status:'provider_unavailable'}};
    } else if (url.pathname.endsWith('/check')) {
      current = {...current,review:{...current.review,status:'checked',checkedAt:'2026-10-05T04:00:00Z'}};
    } else if (url.pathname.endsWith('/revisions')) {
      current = {...current,revision:current.revision+1,title:body.title,userNotes:body.userNotes,selectedFindingIds:body.selectedFindingIds,
        review:{...current.review,status:'needs_review',checkedAt:null}};
    } else if (url.pathname.endsWith('/exports')) {
      // Only UI download plumbing. These bytes are not real-export evidence.
      await route.fulfill({contentType:'application/pdf',body:'%PDF-UI-synthetic-fixture'});return;
    }
    current.versions = [...current.versions.filter(v => v.revision !== current.revision),{revision:current.revision,createdAt:current.createdAt,checkedAt:current.review.checkedAt}];
    versions.set(current.revision, structuredClone(current));
    await route.fulfill({json:current});
  });
  await page.goto('/');
  return {calls,baseCalls};
}

async function prepare(page: Page) {
  await page.locator('[data-tab="report"]').click();
  await page.getByRole('button',{name:'Tạo báo cáo mới',exact:true}).click();
  await page.getByRole('button',{name:'Chuẩn bị bản nháp',exact:true}).click();
  await expect(page.locator('.report-document')).toBeVisible();
  await expect(page.locator('.report-workspace')).toHaveAttribute('aria-busy','false');
  await expect(page.locator('[data-report-chart-ready="true"]')).toHaveCount(1);
}

test('library ignores the old resume pointer and new-report intent hides saved content', async ({page}) => {
  const {calls} = await harness(page);
  await page.evaluate(() => sessionStorage.setItem('cx-report.last.VSO', 'rpt_ui_synthetic'));
  await page.locator('[data-tab="report"]').click();
  await expect(page.locator('.report-document, .report-setup, [data-report-chart]')).toHaveCount(0);
  expect(calls.some(c => c.method === 'GET' && c.url.endsWith('/rpt_ui_synthetic'))).toBe(false);
  await page.getByRole('button',{name:'Tạo báo cáo mới',exact:true}).click();
  await page.getByRole('button',{name:'Chuẩn bị bản nháp',exact:true}).click();
  await expect(page.locator('.report-document')).toBeVisible();
  await page.getByRole('button',{name:'Tạo báo cáo mới',exact:true}).click();
  await expect(page.locator('.report-document, [data-report-chart]')).toHaveCount(0);
  await expect(page.locator('[data-report-title]')).toBeFocused();
  await page.getByRole('button',{name:'Về danh sách bản nháp',exact:true}).click();
  await expect(page.locator('[data-report-action="open"]')).toBeVisible();
  expect(calls.filter(c => c.body?.context)).toHaveLength(1);
});

test('draft deletion can be cancelled and removes only after confirmation', async ({page}, testInfo) => {
  const {calls} = await harness(page);
  await prepare(page);
  await page.getByRole('button',{name:'Về danh sách bản nháp',exact:true}).click();
  await expect(page.locator('[data-report-action="delete"]')).toBeVisible();
  await page.screenshot({path:testInfo.outputPath('draft-library.png'),fullPage:true});
  page.once('dialog', dialog => dialog.dismiss());
  await page.locator('[data-report-action="delete"]').click();
  expect(calls.filter(c => c.method === 'DELETE')).toHaveLength(0);
  await expect(page.locator('[data-report-action="open"]')).toBeVisible();
  page.once('dialog', async dialog => {
    expect(dialog.message()).toContain('và tất cả phiên bản');
    expect(dialog.message()).toContain('Tệp PDF/DOCX đã tải không bị xóa');
    await dialog.accept();
  });
  await page.locator('[data-report-action="delete"]').click();
  await expect(page.locator('[data-report-action="open"], .report-document')).toHaveCount(0);
  await expect(page.locator('.report-status')).toContainText('Đã xóa bản nháp');
  await expect(page.locator('[data-report-action="new"]')).toBeFocused();
  expect(calls.find(c => c.method === 'DELETE')!.body).toEqual({baseRevision:1});
  await page.screenshot({path:testInfo.outputPath('draft-library-empty.png'),fullPage:true});
});

test('failed deletion retains the open document; latest revision is used even when viewing an older one', async ({page}) => {
  const {calls} = await harness(page);
  await prepare(page);
  await page.locator('[data-report-action="generate"]').click();
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 2');
  await page.locator('[data-report-version]').selectOption('1');
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 1');
  await expect(page.locator('.report-workspace')).toHaveAttribute('aria-busy','false');
  await page.locator('.report-history > summary').click();
  await page.route('**/api/projects/*/reports/rpt_ui_synthetic', async route => {
    if (route.request().method() !== 'DELETE') { await route.fallback(); return; }
    expect(route.request().postDataJSON()).toEqual({baseRevision:2});
    await route.fulfill({status:409,json:{detail:{message:'Bản nháp đã có phiên bản mới. Mở lại trước khi xóa.'}}});
  });
  page.once('dialog', dialog => dialog.accept());
  await page.locator('[data-report-action="delete"]').click();
  await expect(page.locator('.notice.error')).toContainText('Mở lại trước khi xóa');
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 1');
  await expect(page.locator('[data-report-action="open"]')).toBeVisible();
  expect(calls.filter(c => c.method === 'DELETE')).toHaveLength(0);
});

test('five-part report prepares without AI and does not mix dashboard KPI cards', async ({page}) => {
  const {calls} = await harness(page);
  await prepare(page);
  await expect(page.locator('.report-section > h4, .report-section-head > h4')).toHaveText([
    'Thông tin báo cáo','Tóm tắt điều hành','Tổng quan KPI','Diễn biến trong kỳ','Điểm đáng chú ý']);
  await expect(page.locator('.kpi-grid, #overview-summary')).toHaveCount(0);
  await expect(page.locator('.report-kpi-table')).toContainText('22');
  await expect(page.locator('.report-kpi-table thead th')).toHaveText(['Vấn đề / KPI','Mức được ghi nhận','Thay đổi ở kỳ cuối','Dữ liệu']);
  await expect(page.locator('.report-kpi-table tbody tr').first().locator('th, td')).toHaveCount(4);
  await expect(page.locator('.report-kpi-table')).not.toContainText('Tổng trong kỳ');
  expect(calls.filter(c => c.url.endsWith('/regenerate'))).toHaveLength(0);
  const create = calls.find(c => c.body?.context)!;
  expect(create.body.context.view).toBe('overview');
  await expect(page.locator('[data-field="mode"], [data-field="entity"], [data-field="scope"]')).toHaveCount(0);
  await page.locator('[data-tab="overview"]').click();
  await page.locator('[data-field="mode"]').selectOption('week');
  await page.locator('[data-tab="report"]').click();
  await expect(page.locator('.report-document')).toHaveCount(0);
  await page.locator('[data-report-action="open"]').click();
  await expect(page.locator('.report-kpi-table')).toContainText('22');
  await expect(page.locator('#report-metadata')).toContainText('07/09/2026 → 15/09/2026');
});

test('statistics entry clones calculation and periods without automatically generating', async ({page}) => {
  const {calls} = await harness(page);
  await page.locator('[data-tab="statistics"]').click();
  await page.locator('[data-field="statisticsGroup"]').selectOption('month');
  await page.locator('[data-field="statisticsMode"]').selectOption('average');
  await page.locator('[data-action="create-report-from-scope"]').click();
  await expect(page.locator('[data-report-field="view"]')).toHaveValue('statistics');
  await expect(page.locator('[data-report-field="calculation"]')).toHaveValue('average_per_day');
  await expect(page.locator('[data-report-field="groupBy"]')).toHaveValue('month');
  expect(calls.filter(c => c.body?.context)).toHaveLength(0);
});

test('overview report entry inherits dashboard week/month instead of AI grouping on first mount and re-entry', async ({page}) => {
  const {calls} = await harness(page);
  await page.locator('[data-field="mode"]').selectOption('week');
  await page.locator('[data-action="create-report-from-scope"]').click();
  await expect(page.locator('[data-report-field="groupBy"]')).toHaveValue('week');
  await page.getByRole('button',{name:'Chuẩn bị bản nháp',exact:true}).click();
  await expect(page.locator('.report-document')).toBeVisible();
  expect(calls.find(c => c.body?.context)!.body.context.groupBy).toBe('week');
  await page.locator('[data-tab="overview"]').click();
  await page.locator('[data-field="mode"]').selectOption('month');
  await page.locator('[data-action="create-report-from-scope"]').click();
  await expect(page.locator('[data-report-field="groupBy"]')).toBeVisible();
  await expect(page.locator('[data-report-field="groupBy"]')).toHaveValue('month');
  expect(calls.filter(c => c.body?.context)).toHaveLength(1);
});

test('explicit weekly statistics entry does not auto-restore the last report over its setup', async ({page}) => {
  const {calls} = await harness(page);
  await page.evaluate(() => sessionStorage.setItem('cx-report.last.VSO', 'previous-daily-report'));
  await page.locator('[data-tab="statistics"]').click();
  await page.locator('[data-field="statisticsGroup"]').selectOption('week');
  await page.locator('[data-field="statisticsMode"]').selectOption('both');
  await page.locator('[data-action="create-report-from-scope"]').click();
  await expect(page.locator('[data-report-field="groupBy"]')).toHaveValue('week');
  await expect(page.locator('[data-report-field="calculation"]')).toHaveValue('both');
  expect(calls.some(c => c.url.endsWith('/previous-daily-report'))).toBe(false);
});

test('selected members preserve identity; marker toggles save a new version without AI', async ({page}) => {
  const {calls} = await harness(page);
  await page.locator('[data-tab="report"]').click();
  await page.getByRole('button',{name:'Tạo báo cáo mới',exact:true}).click();
  await page.locator('[data-report-field="selection"]').selectOption('selected');
  await page.locator('[data-report-member="child-a"]').check();
  await page.getByRole('button',{name:'Chuẩn bị bản nháp',exact:true}).click();
  await expect(page.locator('.report-document')).toBeVisible();
  expect(calls.find(c => c.body?.context)!.body.context.entityRefs).toEqual(['child-a']);
  await page.locator('[data-report-finding-select="finding-trough"]').uncheck();
  await expect(page.getByRole('button',{name:'Lưu phiên bản mới',exact:true})).toBeEnabled();
  await expect(page.locator('[data-report-action="export"]')).toBeDisabled();
  await page.getByRole('button',{name:'Lưu phiên bản mới',exact:true}).click();
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 2');
  expect(calls.find(c => c.url.endsWith('/revisions'))!.body.selectedFindingIds).toEqual(['finding-peak']);
  expect(calls.filter(c => c.url.endsWith('/regenerate'))).toHaveLength(0);
  await page.getByRole('button',{name:'Đánh dấu đã kiểm tra',exact:true}).click();
  await expect(page.locator('.report-document-header')).toContainText('Đã kiểm tra bản nháp');
  await page.locator('[data-report-version]').selectOption('1');
  await expect(page.locator('.report-document')).toContainText('Đang xem bản cũ');
  await expect(page.locator('[data-report-action="generate"]')).toBeDisabled();
});

test('finding-to-chart and chart-to-finding use canonical anchors; source opens in existing drawer', async ({page}) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const {baseCalls} = await harness(page);
  await prepare(page);
  await page.locator('[data-report-finding-id="finding-peak"]').click();
  await expect(page.locator('[data-report-finding="finding-peak"]')).toHaveAttribute('data-active','');
  await page.locator('[data-report-chart]').evaluate(element => {
    (element as unknown as {emit:(name:string,payload:unknown)=>void}).emit('plotly_click',{points:[{pointNumber:1}]});
  });
  await expect(page.locator('[data-report-finding="finding-trough"]')).toHaveAttribute('data-active','');
  await page.locator('.report-kpi-table [data-report-action="source"]').click();
  expect(errors).toEqual([]);
  await expect(page.locator('#investigation-drawer[aria-hidden="false"] #investigation-title')).toBeVisible();
  expect(baseCalls.calls.some(c => c.pathname.includes('/provenance') && c.search.includes('lin_root_9'))).toBeTruthy();
});

test('locating a deselected finding shows temporary anchors without selecting or calling AI', async ({page}) => {
  const {calls} = await harness(page);
  await prepare(page);
  const finding = page.locator('[data-report-finding="finding-peak"]');
  await finding.locator('input[type=checkbox]').uncheck();
  const callsBefore = calls.length;
  await finding.locator('[data-report-action="locate"]').click();
  await expect.poll(() => page.locator('[data-report-chart]').evaluate(el =>
    (el as any)._fullLayout.annotations.map((a:any) => a.text))).toEqual(['Đang xem','Đang xem','Đang xem']);
  await expect(finding.locator('input[type=checkbox]')).not.toBeChecked();
  await expect(page.locator('[data-report-finding="finding-trough"] input')).toBeChecked();
  expect(calls).toHaveLength(callsBefore);
  expect(calls.filter(c => c.url.endsWith('/regenerate'))).toHaveLength(0);
});

test('reload requires explicit selection; AI unavailable preserves engine content; download uses exact revision', async ({page}) => {
  const {calls} = await harness(page);
  await prepare(page);
  await page.reload();
  await expect(page.locator('.report-document')).toHaveCount(0);
  await page.locator('[data-report-action="open"]').click();
  await expect(page.locator('.report-document')).toBeVisible();
  await page.locator('[data-report-action="generate"]').click();
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 2');
  await expect(page.locator('.report-generation-note')).toContainText('nội dung đối chiếu được với số liệu');
  await expect(page.locator('.report-generation-note')).not.toContainText('Engine');
  await expect(page.locator('.report-kpi-table')).toContainText('22');
  const download = page.waitForEvent('download');
  await page.locator('[data-report-action="export"]').click();
  expect((await download).suggestedFilename()).toContain('-v2.pdf');
  expect(calls.filter(c => c.url.endsWith('/regenerate'))).toHaveLength(1);
  expect(calls.find(c => c.url.endsWith('/exports'))!.url).toContain('/revisions/2/');
});

test('report annotation map is stable across trace layout and does not span missing data', () => {
  const doc = reportFixture();
  const original = JSON.stringify(doc);
  const figure = reportFigure(doc.charts[0],doc.findings,doc.selectedFindingIds,'finding-peak');
  expect(figure.layout.annotations.map(a => a.x)).toEqual(['2026-09-11','2026-09-12','2026-09-15','2026-09-08']);
  expect(figure.data[0].y).toEqual([16,8,10,8,19,43,32,22,22]);
  expect(JSON.stringify(doc)).toBe(original);
  const chart = structuredClone(doc.charts[0]);
  chart.points[6].value = null as unknown as number;
  expect(reportFigure(chart,doc.findings,doc.selectedFindingIds,'').layout.shapes).toHaveLength(0);
});

test('old revisions remain read-only after setup input; in-flight generation locks narrative edits', async ({page}) => {
  const {calls} = await harness(page,1500);
  await prepare(page);
  await page.locator('[data-report-action="generate"]').click();
  await expect(page.locator('[data-report-action="edit-block"]')).toBeDisabled();
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 2');
  await page.locator('[data-report-version]').selectOption('1');
  await expect(page.locator('.report-document')).toContainText('Đang xem bản cũ');
  await expect(page.locator('[data-report-action="edit-block"], [data-report-edit]')).toHaveCount(0);
  await page.locator('.report-setup > summary').click();
  await page.locator('[data-report-title]').fill('Một bản nháp mới');
  for (const action of ['save','generate','check']) await expect(page.locator(`[data-report-action="${action}"]`)).toBeDisabled();
  await expect(page.locator('[data-report-action="export"]')).toBeEnabled();
  expect(calls.filter(c => c.url.endsWith('/revisions'))).toHaveLength(0);
});

test('pending edits override AI provenance immediately and survive selection rerender', async ({page}) => {
  const {calls} = await harness(page,0,true);
  await prepare(page);
  const paragraph = page.locator('[data-report-block="block-phase"]');
  await expect(paragraph.locator('.report-source-label')).toHaveText('AI đã kiểm chứng');
  await paragraph.locator('[data-report-action="edit-block"]').click();
  await page.locator('[data-report-edit]').fill('Số lỗi tăng từ 19 lên 43, chênh lệch 24.');
  await expect(paragraph.locator('.report-source-label')).toContainText('chưa lưu, chờ kiểm chứng');
  await page.locator('[data-report-finding-select="finding-trough"]').uncheck();
  await expect(paragraph.locator('.report-source-label')).not.toContainText('AI đã kiểm chứng');
  await expect(paragraph.locator('.report-source-label')).toContainText('chưa lưu, chờ kiểm chứng');
  await page.locator('[data-report-action="save"]').click();
  await expect(page.locator('.report-document-header')).toContainText('Phiên bản 2');
  expect(calls.find(c => c.url.endsWith('/revisions'))!.body.narrativeEdits['block-phase']).toContain('chênh lệch 24');
});

test('both finding navigation directions respect reduced motion', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await harness(page); await prepare(page);
  await page.evaluate(() => {
    (window as any).__reportScroll = [];
    Element.prototype.scrollIntoView = function(options) { (window as any).__reportScroll.push(options); };
  });
  await page.locator('[data-report-finding-id="finding-peak"]').click();
  await expect(page.locator('[data-report-chart-ready="true"]')).toHaveCount(1);
  await page.locator('[data-report-chart]').evaluate(element => {
    (element as unknown as {emit:(name:string,payload:unknown)=>void}).emit('plotly_click',{points:[{pointNumber:1}]});
  });
  await expect.poll(() => page.evaluate(() => (window as any).__reportScroll.length)).toBe(2);
  expect(await page.evaluate(() => (window as any).__reportScroll.map((entry:any) => entry.behavior))).toEqual(['auto','auto']);
});

for (const [width,height] of [[1366,768],[1440,900],[1920,1080],[390,844]]) {
  test(`report layout remains readable without cropping ${width}`, async ({page}) => {
    await page.setViewportSize({width,height});
    await harness(page); await prepare(page);
    await expect(page.locator('.report-document')).not.toContainText('1.1.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth+1)).toBeTruthy();
    expect(await page.locator('.report-paragraph p').evaluate(el => el.scrollHeight <= el.clientHeight+1)).toBeTruthy();
    await page.evaluate(() => window.scrollTo(0,0));
    await page.screenshot({path:`../.impeccable/review/reports/report-${width}.png`,fullPage:true});
  });
}
