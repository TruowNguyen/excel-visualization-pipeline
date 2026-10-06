import { expect, test, type Page } from '@playwright/test';
import { installApiHarness } from './fixtures';

type Options = NonNullable<Parameters<typeof installApiHarness>[1]>;
const file = { name: 'bao-cao-cx.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('fixture') };
const attempt = (id: number, name: string, extra = {}) => ({ attempt_id: id, submitted_file_name: name,
  attempt_status: 'committed', requested_mode: 'incremental', started_at: '2026-09-17T09:00:00Z',
  input_record_count: 12, inserted_count: 0, updated_count: 2, unchanged_count: 10, ...extra });
async function start(page: Page, options: Options = {}, tab = 'import') {
  await page.addInitScript(tab => sessionStorage.setItem('excel_visualization_pipeline.workspace.v1', JSON.stringify({ project: 'VSO', entity: 'root', tab })), tab);
  const harness = await installApiHarness(page, options);
  await page.goto('/');
  await expect(page.locator('#preview-action')).toBeVisible();
  await expect(page.locator('.kpi-grid')).toBeHidden();
  return harness;
}
async function prepare(page: Page) {
  await page.locator('#file-input').setInputFiles(file);
  await page.locator('#preview-action').click();
  await expect(page.locator('.preview-status')).toContainText('Đạt kiểm tra');
}

test('import first: history never resets the form, file or full-snapshot confirmation', async ({ page }) => {
  const harness = await start(page);
  await expect(page.locator('[data-tab="history"]')).toHaveCount(0);
  await expect(page.locator('#import-history-body')).toBeHidden();
  expect(harness.calls.filter(c => c.pathname === '/api/imports')).toHaveLength(0);
  await prepare(page);
  await page.locator('#import-mode').selectOption('full_snapshot');
  await page.locator('#snapshot-confirm').check();
  const input = await page.locator('#file-input').elementHandle();
  await page.locator('#open-import-history').click();
  await expect(page.locator('#history-row-2')).toBeVisible();
  expect(await input!.evaluate(el => el.isConnected)).toBe(true);
  await expect(page.locator('#snapshot-confirm')).toBeChecked();
  await page.locator('#history-detail-2').click();
  await expect(page.locator('#history-details-2')).toBeVisible();
  await page.locator('#history-toggle').click();
  await expect(page.locator('#history-toggle')).toBeFocused();
  await expect(page.locator('#import-history-body')).toBeHidden();
  await expect(page.locator('.selected-file')).toContainText(file.name);
  await expect(page.locator('[data-action="commit"]')).toBeEnabled();
  await page.locator('#import-mode').selectOption('incremental');
  await page.locator('#import-mode').selectOption('full_snapshot');
  await expect(page.locator('#snapshot-confirm')).not.toBeChecked();
  await expect(page.locator('[data-action="commit"]')).toBeDisabled();
});

test('legacy history session maps to the unified tab and its explicit history destination', async ({ page }) => {
  await start(page, {}, 'history');
  await expect(page.locator('[data-tab="import"]')).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#history-toggle')).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#history-row-2')).toBeVisible();
  await expect(page.locator('.history-scope')).toContainText('không lọc theo dự án');
  await page.locator('[data-tab="overview"]').click();
  await page.locator('[data-tab="import"]').click();
  await expect(page.locator('#import-history-body')).toBeHidden();
});

for (const options of [{ bootstrapEmpty: true }, { bootstrapFailure: true }]) {
  test(`can preview without an analytical workspace: ${JSON.stringify(options)}`, async ({ page }) => {
    await start(page, options); await prepare(page);
    await expect(page.locator('[data-action="commit"]')).toBeEnabled();
  });
}

test('history refresh failure preserves previous rows and does not steal form state', async ({ page }) => {
  await start(page, { historyFailureRequests: [2] }); await prepare(page);
  await page.locator('#open-import-history').click();
  await expect(page.locator('#history-row-2')).toBeVisible();
  await page.locator('#history-refresh-action').click();
  await expect(page.locator('.history-error')).toContainText('Không tải được lịch sử nhập');
  await expect(page.locator('#history-row-2')).toBeVisible();
  await expect(page.locator('#history-refresh-action')).toBeFocused();
  await expect(page.locator('.selected-file')).toContainText(file.name);
  await expect(page.locator('[data-action="commit"]')).toBeEnabled();
});

test('history detail distinguishes missing counters and zero, and escapes source text', async ({ page }) => {
  await start(page, { historyItemsByRequest: [[attempt(7, '<script>alert(1)</script>.xlsx', {
    attempt_status: 'failed', inserted_count: null, updated_count: 0, unchanged_count: null,
    failure_message: '<img src=x onerror=alert(1)>', source_hash: 'a'.repeat(64),
  })]] });
  await page.locator('#open-import-history').click();
  await expect(page.locator('#history-row-7')).toContainText('— / 0 / —');
  await page.locator('#history-detail-7').click();
  await expect(page.locator('#history-details-7')).toContainText('<img src=x onerror=alert(1)>');
  await expect(page.locator('#import-history-body script, #import-history-body img')).toHaveCount(0);
});

test('late old history response cannot overwrite a newer refresh', async ({ page }) => {
  const harness = await start(page, { historyDelaysMs: [350, 15], historyItemsByRequest: [[attempt(1, 'old.xlsx')], [attempt(9, 'new.xlsx')]] });
  await page.locator('#open-import-history').click();
  await expect.poll(() => harness.calls.filter(c => c.pathname === '/api/imports').length).toBe(1);
  await page.locator('#history-refresh-action').click();
  await expect(page.locator('#history-row-9')).toBeVisible();
  await page.waitForTimeout(400);
  await expect(page.locator('#history-row-1')).toHaveCount(0);
  await expect(page.locator('#history-row-9')).toBeVisible();
});

test('single POST and receipt survive both refresh failures; retry is GET only', async ({ page }) => {
  const harness = await start(page, { historyFailureRequests: [1], workspaceFailureRequests: [2] });
  await prepare(page);
  const post = page.waitForRequest(r => r.url().endsWith('/api/imports') && r.method() === 'POST');
  await page.locator('[data-action="commit"]').evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  const request = await post;
  for (const expected of ['name="expected_hash"', 'b'.repeat(64), 'incremental', file.name]) expect(request.postData()).toContain(expected);
  await expect(page.locator('#import-result')).toContainText('Đã nhập tệp Excel');
  await expect(page.locator('#import-result')).toContainText('Biểu đồ chưa tải lại được');
  await expect(page.locator('#import-result')).toContainText('Chưa cập nhật được lịch sử nhập');
  await expect(page.locator('.import-error')).toHaveCount(0);
  await page.locator('[data-action="view-revision"]').click();
  await expect(page.locator('#history-row-2')).toHaveAttribute('aria-current', 'true');
  await expect(page.locator('#history-row-2')).toBeFocused();
  await page.locator('[data-action="refresh-import-dashboard"]').click();
  await expect(page.locator('#import-result')).toContainText('Biểu đồ đã được tải lại');
  await page.locator('[data-action="show-validation"]').click();
  await expect(page.locator('#committed-validation')).toBeVisible();
  expect(harness.calls.filter(c => c.pathname === '/api/imports' && c.method === 'POST')).toHaveLength(1);
  await page.locator('[data-action="new-import"]').click();
  await expect(page.locator('#preview-action')).toBeDisabled();
});

test('duplicate highlights the duplicate attempt without reloading a new data version', async ({ page }) => {
  const outcome = { attempt_id: 3, status: 'duplicate', run_id: null, duplicate_of_run_id: 1,
    inserted_count: 0, updated_count: 0, unchanged_count: 0, restored_count: 0, deleted_count: 0, lineage_changed_count: 0, message: null };
  const harness = await start(page, { importOutcome: outcome, historyItemsByRequest: [[attempt(3, file.name, { attempt_status: 'duplicate', duplicate_of_run_id: 1, inserted_count: null })]] });
  await prepare(page); const before = harness.workspaceRequestCount();
  await page.locator('[data-action="commit"]').click();
  await expect(page.locator('#import-result')).toContainText('không tạo phiên dữ liệu mới');
  await page.locator('[data-action="view-revision"]').click();
  await expect(page.locator('#history-row-3')).toHaveAttribute('aria-current', 'true');
  expect(harness.workspaceRequestCount()).toBe(before);
});

test('receipt opens current audit data and returns without losing the confirmed result', async ({ page }) => {
  const harness = await start(page); await prepare(page);
  await page.locator('[data-action="commit"]').click();
  await expect(page.locator('#import-result')).toContainText('Biểu đồ đã được tải lại');
  await page.locator('[data-action="audit-import"]').click();
  await expect(page.locator('#tab-body table')).toContainText('D7');
  expect(harness.calls.filter(c => c.pathname.endsWith('/workspace')).at(-1)?.search).toContain('view=audit');
  await expect(page.locator('[data-tab="audit"]')).toHaveCount(0);
  await page.locator('[data-tab="import"]').click();
  await expect(page.locator('#import-result')).toContainText('Đã nhập tệp Excel');
  expect(harness.calls.filter(c => c.pathname === '/api/imports' && c.method === 'POST')).toHaveLength(1);
});

test('unchanged workspace version is not announced as an updated chart', async ({ page }) => {
  const version = 'imp_1';
  await start(page, { workspaceVersionsByRequest: [version, version] });
  await prepare(page); await page.locator('[data-action="commit"]').click();
  await expect(page.locator('#import-result')).toContainText('Biểu đồ chưa tải lại được');
  await expect(page.locator('#import-result')).not.toContainText('Biểu đồ đã được tải lại');
  await expect(page.locator('#import-result')).toContainText('Đã nhập tệp Excel');
});

test('unknown POST outcome stays locked even if history returns no matching attempt', async ({ page }) => {
  const harness = await start(page, { commitNetworkFailure: true, historyItemsByRequest: [[]] });
  await prepare(page); await page.locator('[data-action="commit"]').click();
  await expect(page.locator('.import-error')).toContainText('Chưa xác nhận được kết quả nhập');
  await page.locator('[data-action="check-import-history"]').click();
  await expect(page.locator('.history-empty')).toContainText('Chưa có lần nhập nào');
  await expect(page.locator('[data-action="commit"]')).toBeDisabled();
  await expect(page.locator('#file-input')).toBeDisabled();
  expect(harness.calls.filter(c => c.pathname === '/api/imports' && c.method === 'POST')).toHaveLength(1);
});

test('409 invalidates preview and retry only checks the file again', async ({ page }) => {
  const harness = await start(page, { commitFailureStatus: 409 });
  await prepare(page); await page.locator('[data-action="commit"]').click();
  await expect(page.locator('.import-error')).toContainText('Tệp đã thay đổi');
  await expect(page.locator('[data-action="commit"]')).toHaveCount(0);
  await page.locator('[data-action="retry-import"]').click();
  await expect(page.locator('.preview-status')).toContainText('Đạt kiểm tra');
  expect(harness.calls.filter(c => c.pathname === '/api/imports' && c.method === 'POST')).toHaveLength(1);
});

test('invalid preview cannot write and truncated validation is labeled honestly', async ({ page }) => {
  const harness = await start(page, { previewFixture: { valid: false, errorCount: 110, warningCount: 0,
    manifest: { source_file: file.name, source_hash: 'b'.repeat(64), projects: ['VSO'], record_count: 12, date_count: 2 },
    issues: Array.from({ length: 100 }, (_, i) => ({ severity: 'error', code: 'BAD_VALUE', message: `Lỗi dữ liệu ${i}` })),
  } });
  await page.locator('#file-input').setInputFiles(file); await page.locator('#preview-action').click();
  await expect(page.locator('[data-action="commit"]')).toBeDisabled();
  await expect(page.locator('.issue-limit')).toContainText('100 / 110');
  await expect(page.locator('[data-action="download-validation"]')).toHaveText('Tải phần kết quả đã trả về');
  expect(harness.calls.filter(c => c.pathname === '/api/imports')).toHaveLength(0);
});

test('navigation during commit preserves one POST; a reload cannot restore the file', async ({ page }) => {
  const harness = await start(page, { commitDelayMs: 250 });
  await prepare(page); await page.locator('[data-action="commit"]').click();
  await page.locator('[data-tab="overview"]').click(); await page.locator('[data-tab="import"]').click();
  await expect(page.locator('#import-result')).toContainText('Đã nhập tệp Excel');
  await page.locator('[data-action="new-import"]').click(); await prepare(page);
  await page.locator('[data-tab="overview"]').click(); await page.locator('[data-tab="import"]').click();
  await expect(page.locator('.selected-file')).toContainText(file.name);
  await expect(page.locator('[data-action="commit"]')).toBeEnabled();
  await page.reload();
  await expect(page.locator('#preview-action')).toBeDisabled();
  await expect(page.locator('.selected-file')).toHaveCount(0);
  expect(harness.calls.filter(c => c.pathname === '/api/imports' && c.method === 'POST')).toHaveLength(1);
});

for (const [width, height] of [[1440, 900], [1366, 768], [1200, 650], [390, 844]]) {
  test(`responsive idle, preview and inline history at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await start(page, { historyItemsByRequest: [[attempt(2, file.name, {
      source_hash: 'b'.repeat(64), finished_at: '2026-09-17T09:00:01Z', committed_at: '2026-09-17T09:00:01Z',
      restored_count: 0, deleted_count: 0, lineage_changed_count: 0, run_id: 2,
    })]] });
    await page.screenshot({ path: `../.impeccable/review/unified-import-idle-${width}.png`, fullPage: true });
    await prepare(page);
    await page.locator('[data-action="commit"]').scrollIntoViewIfNeeded();
    await expect(page.locator('[data-action="commit"]')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: `../.impeccable/review/unified-import-preview-${width}.png`, fullPage: true });
    await page.locator('[data-action="commit"]').click();
    await expect(page.locator('#import-result')).toContainText('Biểu đồ đã được tải lại');
    await page.locator('[data-action="view-revision"]').click();
    await expect(page.locator('#history-details-2')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: `../.impeccable/review/unified-import-result-${width}.png`, fullPage: true });
  });
}
