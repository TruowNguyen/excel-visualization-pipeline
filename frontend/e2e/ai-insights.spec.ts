import { expect, test } from '@playwright/test';
import { aiAnalysis, installApiHarness } from './fixtures';
import { formatMetricText } from '../src/terminology';

test('đỉnh và đáy nằm trong diễn giải giai đoạn, không có heading riêng', async ({ page }) => {
  const fixture = aiAnalysis({ metricCode: 'all', entityRef: 'root', start: '2026-09-07', end: '2026-09-16' }, undefined, undefined, undefined, true);
  const report = {
    policyVersion: 'analytical-report-v1', omittedPhaseCount: 0,
    overview: [{ candidateId: 'overview', text: 'Số lỗi dao động rồi tăng lên đỉnh, sau đó giảm và giữ nguyên.', factIds: [], source: 'ai' }],
    phases: [
      { candidateId: 'early', text: 'Số lỗi giảm rồi dao động. Mức thấp nhất là 8 vào 08/09 và 10/09.', factIds: [], source: 'ai', startLabel: '07/09/2026', endLabel: '10/09/2026' },
      { candidateId: 'rise', text: 'Số lỗi tăng lên 43 vào 13/09, mức cao nhất trong các kỳ có dữ liệu.', factIds: [], source: 'ai', startLabel: '12/09/2026', endLabel: '13/09/2026' },
    ], relationships: [],
  };
  await installApiHarness(page, { aiFixture: { ...fixture, narrative: { ...fixture.narrative, mode: 'ai', report } } });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.locator('.ai-reading-story')).toContainText('thấp nhất là 8 vào 08/09 và 10/09');
  await expect(panel.locator('.ai-reading-story')).toContainText('43 vào 13/09');
  await expect(panel.getByRole('heading', { name: /Đỉnh và đáy/ })).toHaveCount(0);
  await expect(panel.locator('.ai-takeaways')).toHaveCount(0);
  for (const width of [1440, 1280]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
    await panel.screenshot({ path: `../.impeccable/review/phase-extrema-${width}.png` });
  }
});

for (const state of [
  { key: 'structure', status: 'rejected_output', validationStatus: 'rejected', code: 'invalid_json', message: 'Dịch vụ trả về nội dung sai định dạng' },
  { key: 'grounding', status: 'rejected_output', validationStatus: 'rejected', code: 'unknown_fact_id', message: 'Phần diễn giải chưa liên kết đầy đủ với dữ liệu nguồn' },
  { key: 'numerical_temporal', status: 'rejected_output', validationStatus: 'rejected', code: 'numeric_period_mismatch', message: 'Một số giá trị hoặc ngày trong phần diễn giải không khớp' },
  { key: 'semantic', status: 'rejected_output', validationStatus: 'rejected', code: 'semantic_unverified', message: 'Hệ thống chưa xác minh được một số nhận định' },
  { key: 'partial', status: 'ready', validationStatus: 'partial', code: 'unsupported_meaning', message: 'Một số nhận định đã được lược bỏ.' },
]) {
  test(`validator ${state.key}: giữ phần có căn cứ và giải thích đúng lỗi`, async ({ page }) => {
    const fixture = aiAnalysis({ metricCode: 'all', entityRef: 'root', start: '2026-09-16', end: '2026-09-17' });
    fixture.status = state.status;
    fixture.validation = { status: state.validationStatus, errors: [state.code], categories: [state.key] };
    if (state.key === 'partial') {
      fixture.narrative.mode = 'ai';
      fixture.narrative.schemaVersion = 'ai-narrative-v4';
      fixture.narrative.summary.text = 'Báo sai/Lỗi tăng nhưng tỷ lệ báo sai giảm giữa hai kỳ. Tổng số tăng nhanh hơn số lỗi.';
    }
    await installApiHarness(page, { aiFixture: fixture });
    await page.goto('/');
    const panel = page.locator('.ai-panel');
    await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
    await expect(panel).toContainText(state.message);
    await expect(panel).not.toContainText('Phần diễn giải tự động không đủ căn cứ.');
    await expect(panel.locator('.ai-executive')).toBeVisible();
    await expect(panel.locator('.ai-reading-story')).toBeVisible();
    await expect(panel.locator('.ai-verification')).not.toHaveAttribute('open', '');
    if (state.key === 'partial') await expect(panel.locator('.ai-takeaways')).toContainText(formatMetricText(fixture.narrative.summary.text));
    for (const width of [1440, 1280]) {
      await page.setViewportSize({ width, height: 1000 });
      await expect(panel).toBeVisible();
      await panel.screenshot({ path: `../.impeccable/review/semantic-${state.key}-${width}.png` });
    }
  });
}

test('AI Insights tổng hợp ba metric trong một câu chuyện và vẫn mở đúng evidence', async ({ page }) => {
  const pageErrors: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const harness = await installApiHarness(page);
  await page.goto('/');

  const panel = page.locator('.ai-panel');
  await expect(panel.getByRole('heading', { name: 'Phân tích KPI tự động' })).toBeVisible();
  const chartBox = await page.locator('[data-plot="overview-root"]').boundingBox();
  const panelBox = await panel.boundingBox();
  expect(chartBox && panelBox && panelBox.y > chartBox.y + chartBox.height).toBeTruthy();
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();

  await expect(panel.getByText('Số liệu đã được kiểm tra', { exact: true })).toBeVisible();
  await expect(panel.getByRole('heading', { name: 'Tổng quan trong thời gian đã chọn' })).toBeVisible();
  await expect(panel.locator('.ai-details')).toHaveCount(0);
  await expect(panel.locator('.ai-chronology')).toHaveCount(0);
  await expect(panel.locator('.ai-executive')).not.toContainText('qua các kỳ');
  await expect(panel.locator('.ai-executive')).toContainText('giữa hai kỳ');
  await expect(panel.locator('.ai-reading-story')).toContainText('Tỷ lệ báo sai giảm');
  await expect(panel.locator('.ai-supplement')).toHaveCount(0);
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('16/9/2026–17/9/2026');
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('Tất cả chỉ số');
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('ngày');
  const executiveTop = await panel.locator('.ai-executive').boundingBox();
  const storyTop = await panel.locator('.ai-reading-story').boundingBox();
  expect(executiveTop && storyTop && executiveTop.y < storyTop.y).toBeTruthy();
  const periodDetails = panel.locator('.ai-periods').first();
  await expect(periodDetails).not.toHaveAttribute('open', '');
  await expect(panel.locator('.ai-periods')).toHaveCount(1);
  await panel.locator('.ai-verification > summary').click();
  await periodDetails.locator('summary').click();
  await expect(periodDetails).toContainText('Kỳ 1 (16/09) → Kỳ 2 (17/09)');
  await expect(periodDetails.getByRole('row')).toHaveCount(4);
  await expect(periodDetails).not.toContainText('Cao nhất');
  await expect(periodDetails).not.toContainText('Thấp nhất');
  await expect(panel.getByText('Tổng hợp từ số liệu', { exact: true })).toBeVisible();

  await periodDetails.getByRole('button', { name: 'Mở nguồn Tổng số ghi nhận · 16/09/2026' }).click();
  await expect(page.locator('#investigation-title')).toBeVisible();
  expect(harness.calls.some(call => call.pathname.includes('/observations/obs_ai_1/provenance'))).toBeTruthy();
  expect(pageErrors).toEqual([]);
});

test('người dùng chọn nhóm tuần và request giữ đúng groupBy', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');

  await panel.getByLabel('Nhóm dữ liệu').selectOption('week');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();

  await expect(panel.getByText(/3\/3 chỉ số đủ dữ liệu so sánh · theo tuần/)).toBeVisible();
  const call = harness.calls.find(item => item.pathname.endsWith('/ai/trend-summary'));
  expect(call?.body).toMatchObject({ groupBy: 'week' });
});

test('dịch vụ lỗi vẫn giữ phần dữ kiện và bảng điều khiển hoạt động', async ({ page }) => {
  await installApiHarness(page, { aiResponseStatus: 'provider_unavailable' });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByText('Tóm tắt dự phòng', { exact: true }).first()).toBeVisible();
  await expect(panel.getByText('Dịch vụ phân tích tự động tạm thời không phản hồi.')).toBeVisible();
  await expect(panel.getByText(/Mô hình không trả lời trong thời gian cho phép/)).toBeVisible();
  await expect(page.locator('[data-plot="overview-root"]')).toBeVisible();
});

test('đổi filter đánh dấu insight cũ stale và không tự gọi model', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByText('Số liệu đã được kiểm tra', { exact: true })).toBeVisible();
  const before = harness.calls.filter(call => call.pathname.endsWith('/ai/trend-summary')).length;

  await page.locator('[data-field="entity"]').selectOption('child-a');
  await expect(panel.getByText('Cần phân tích lại')).toBeVisible();
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
  const after = harness.calls.filter(call => call.pathname.endsWith('/ai/trend-summary')).length;
  expect(after).toBe(before);
});

test('request AI lỗi có thể retry có chủ đích', async ({ page }) => {
  const harness = await installApiHarness(page, { aiFailureRequests: [1] });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByText('Không tạo được phân tích.', { exact: true })).toBeVisible();
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByText('Số liệu đã được kiểm tra', { exact: true })).toBeVisible();
  expect(harness.calls.filter(call => call.pathname.endsWith('/ai/trend-summary'))).toHaveLength(2);
});

test('phạm vi chưa hỗ trợ vẫn giữ khu vực phân tích và đưa người dùng về Đối tượng đã chọn', async ({ page }) => {
  await installApiHarness(page);
  await page.goto('/');

  await page.getByLabel('Mức hiển thị').selectOption('children');
  const panel = page.locator('.ai-panel');
  await expect(panel).toBeVisible();
  await expect(panel.getByText('Mức hiển thị này chưa hỗ trợ phân tích tự động.')).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Phân tích khoảng đang xem' })).toBeDisabled();
  await panel.getByRole('button', { name: 'Dùng nội dung đang chọn' }).click();
  await expect(page.getByLabel('Mức hiển thị')).toHaveValue('node');
  await expect(panel.getByRole('button', { name: 'Phân tích khoảng đang xem' })).toBeEnabled();
});

test('trạng thái đọc màn hình ngắn và focus quay lại CTA sau khi phân tích', async ({ page }) => {
  await installApiHarness(page, { aiDelayMs: 500 });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  const action = panel.getByRole('button', { name: 'Phân tích khoảng đang xem' });

  await action.click();
  await expect(panel.locator('#ai-status-message')).toHaveText('Đang phân tích dữ liệu trong khoảng đã chọn.');
  await expect(panel.locator('.ai-output')).toHaveAttribute('aria-busy', 'true');
  await expect(panel.locator('.ai-output')).not.toHaveAttribute('aria-live');
  await expect(panel.getByRole('button', { name: 'Đang phân tích…' })).toBeFocused();

  const completedAction = panel.getByRole('button', { name: 'Phân tích lại' });
  await expect(completedAction).toBeFocused();
  await expect(panel.locator('#ai-status-message')).toHaveText('Phân tích hoàn tất. Số liệu đã được kiểm tra.');
  await expect(panel.locator('.ai-output')).toHaveAttribute('aria-busy', 'false');
});

test('CTA giữ tỷ lệ gọn trên desktop và chỉ full-width trên mobile', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  const action = panel.getByRole('button', { name: 'Phân tích khoảng đang xem' });
  const desktopBox = await action.boundingBox();
  const selectBox = await panel.getByLabel('Phạm vi chỉ số').boundingBox();
  expect(desktopBox?.width).toBeGreaterThanOrEqual(190);
  expect(desktopBox?.width).toBeLessThanOrEqual(220);
  expect(desktopBox && selectBox && desktopBox.width <= selectBox.width).toBeTruthy();

  await page.setViewportSize({ width: 390, height: 844 });
  const mobileBox = await action.boundingBox();
  const mobileSelectBox = await panel.getByLabel('Phạm vi chỉ số').boundingBox();
  expect(mobileBox && mobileSelectBox && Math.abs(mobileBox.width - mobileSelectBox.width) <= 1).toBeTruthy();
});

test('AI Insights giữ thứ tự đọc và không tràn ngang trên viewport hẹp', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installApiHarness(page);
  await page.goto('/');

  const panel = page.locator('.ai-panel');
  await panel.scrollIntoViewIfNeeded();
  const metricBox = await panel.getByLabel('Phạm vi chỉ số').boundingBox();
  const groupBox = await panel.getByLabel('Nhóm dữ liệu').boundingBox();
  expect(metricBox && groupBox && groupBox.y > metricBox.y).toBeTruthy();
  await expect(panel.getByRole('button', { name: 'Phân tích khoảng đang xem' })).toBeVisible();
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByRole('heading', { name: 'Tổng quan trong thời gian đã chọn' })).toBeVisible();
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
});

test('desktop insight có bước kiểm tra trực tiếp và giữ giới hạn so sánh', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.locator('.ai-verification')).not.toHaveAttribute('open', '');
  await expect(panel.getByRole('heading', { name: 'Đối chiếu nguồn', exact: true })).not.toBeVisible();
  await expect(panel.locator('.ai-reading-story')).toBeVisible();
  await expect(panel.locator('.ai-comparison')).not.toHaveAttribute('open', '');
  await panel.screenshot({ path: '../.impeccable/review/desktop.png' });
  await page.setViewportSize({ width: 1280, height: 900 });
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await panel.screenshot({ path: '../.impeccable/review/desktop-1280.png' });
  await panel.locator('.ai-verification > summary').click();
  await panel.getByRole('button', { name: 'Tổng số ghi nhận · 16/09/2026', exact: true }).first().click();
  expect(harness.calls.some(call => call.pathname.includes('/observations/obs_ai_1/provenance'))).toBeTruthy();
});

test('desktop kể đúng toàn chuỗi chín kỳ, không dùng đầu–cuối thay xu hướng', async ({ page }) => {
  await installApiHarness(page, { aiWholeSeries: true });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  const story = panel.locator('.ai-chronology').filter({ has: page.locator('h4').filter({ hasText: /^Tổng báo sai \(lỗi\)$/ }) });
  const stages = story.locator('.ai-stage-list li');
  await expect(stages).toHaveCount(6);
  await expect(stages.nth(0)).toContainText('giảm từ 16 xuống 8');
  await expect(stages.nth(3)).toContainText('tăng liên tiếp từ 8 lên 43, đạt mức cao nhất');
  await expect(stages.nth(4)).toContainText('giảm liên tiếp từ 43 xuống 22');
  await expect(stages.nth(5)).toContainText('giữ nguyên ở 22');
  await expect(story).toContainText('Giảm lớn nhất giữa hai kỳ: 06/09/2026–07/09/2026, 43 → 32 (-11)');
  await expect(story).toContainText('Tăng lớn nhất giữa hai kỳ: 05/09/2026–06/09/2026, 19 → 43 (24)');
  await expect(panel.locator('.ai-takeaways')).toContainText('không duy trì đà tăng');
  await expect(panel.locator('.ai-executive')).not.toContainText('16 lên 22');
  await expect(panel.locator('.ai-supplement')).not.toHaveAttribute('open', '');
  await expect(story).not.toBeVisible();
  await panel.locator('.ai-verification > summary').click();
  await panel.locator('.ai-details > summary').click();
  await story.getByText('Các mốc đổi chiều', { exact: true }).click();
  await expect(story).toContainText('chuyển từ tăng sang giảm ở mức 43');
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await expect(panel.locator('.ai-source-actions').first().getByRole('button')).toHaveCount(3);
  await panel.locator('.ai-details > summary').click();
  await panel.locator('.ai-verification > summary').click();
  await panel.screenshot({ path: '../.impeccable/review/desktop-whole-series.png' });
  await page.setViewportSize({ width: 1280, height: 900 });
  await panel.screenshot({ path: '../.impeccable/review/desktop-whole-series-1280.png' });
});

test('desktop không hiển thị quan hệ tăng trưởng khi cơ sở so sánh bị giới hạn', async ({ page }) => {
  await installApiHarness(page, { aiLimitedComparison: true });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.locator('.ai-quality-alert')).toContainText('chưa kết luận quan hệ tăng trưởng');
  await expect(panel.locator('.ai-executive')).not.toContainText('tăng nhanh hơn');
  const warningBox = await panel.locator('.ai-quality-alert').boundingBox();
  const summaryBox = await panel.locator('.ai-executive').boundingBox();
  expect(warningBox && summaryBox && warningBox.y > summaryBox.y).toBeTruthy();
  await panel.screenshot({ path: '../.impeccable/review/desktop-limited.png' });
});

test('dataset hiện tại có insight, evidence tối thiểu và điều tra liên quan thay vì fact dump', async ({ page }) => {
  await installApiHarness(page, { aiCurrentDataset: true });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  const executive = panel.locator('.ai-executive');
  await expect(panel.locator('.ai-takeaways')).toContainText('không duy trì đà tăng');
  await expect(panel.locator('.ai-takeaways')).toContainText('Tổng số ghi nhận và Tổng báo sai (lỗi) không đạt mức cao nhất cùng kỳ');
  await expect(executive).toContainText('Ở các kỳ cuối, Tổng báo sai (lỗi) giữ nguyên');
  await expect(executive).not.toContainText('Cao nhất');
  await expect(panel.locator('.ai-details')).not.toHaveAttribute('open', '');
  await expect(panel.getByRole('heading', { name: 'Diễn biến trong thời gian đã chọn' })).not.toBeVisible();
  await expect(panel.locator('.ai-insight-evidence')).toContainText('Tổng báo sai (lỗi) · 13/09/2026: 43');
  await expect(panel.locator('.ai-insight-evidence')).toContainText('Tổng số ghi nhận · 15/09/2026: 657');
  await expect(panel.locator('.ai-quality-alert')).toContainText('1/10 kỳ thiếu');
  const warning = await panel.locator('.ai-quality-alert').boundingBox();
  const summary = await executive.boundingBox();
  expect(warning && summary && warning.y > summary.y).toBeTruthy();
  await expect(panel).toContainText('Kiểm tra đoạn 12/09/2026–16/09/2026, quanh đỉnh 13/09/2026');
  await expect(panel).toContainText('Đối chiếu Tổng số ghi nhận tại 15/09/2026 và Tổng báo sai (lỗi) tại 13/09/2026');
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await panel.screenshot({ path: '../.impeccable/review/desktop-current-insight.png' });
  await page.setViewportSize({ width: 1280, height: 900 });
  await panel.screenshot({ path: '../.impeccable/review/desktop-current-insight-1280.png' });
  await panel.locator('.ai-verification > summary').click();
  await panel.locator('.ai-details > summary').click();
  await expect(panel.getByRole('heading', { name: 'Diễn biến trong thời gian đã chọn' })).toBeVisible();
});

test('liên hệ ba KPI giải thích số lượng và tỷ trọng, không tính correlation', async ({ page }) => {
  await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.locator('.ai-takeaways')).toContainText('Số lỗi tăng không đồng nghĩa tỷ lệ báo sai tăng');
  await expect(panel.locator('.ai-reading-story')).toContainText('Tổng số ghi nhận tăng nhanh hơn');
  await expect(panel.locator('.ai-correlation')).toHaveCount(0);
  await expect(panel).not.toContainText('Hệ số r');
  await expect(panel).not.toContainText('sáu kỳ');
  await panel.screenshot({ path: '../.impeccable/review/desktop-kpi-links.png' });
  await page.setViewportSize({ width: 1280, height: 900 });
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await panel.screenshot({ path: '../.impeccable/review/desktop-kpi-links-1280.png' });
});

test('hai kỳ tuần dùng nhãn rõ nghĩa và một bảng chung, không có extrema', async ({ page }) => {
  const fixture = aiAnalysis({ metricCode: 'all', groupBy: 'week' });
  fixture.window = { start: '2026-09-07', end: '2026-09-16', groupBy: 'week' };
  fixture.narrative.summary.text = 'Báo sai/Lỗi tăng về số lượng nhưng tỷ lệ báo sai giảm giữa hai kỳ; Tổng số tăng nhanh hơn Báo sai/Lỗi trong phép tính tỷ lệ.';
  fixture.synthesis.selectedCandidateIds = [];
  fixture.synthesis.candidates = [];
  fixture.synthesis.reading = undefined;
  fixture.inspectionChecks = [];
  fixture.metrics.forEach((metric: any) => {
    metric.quality.validPeriodCount = 2;
    metric.quality.expectedPeriodCount = 2;
    metric.series = metric.series.slice(0, 2).map((point: any, index: number) => ({ ...point, periodStart: index ? '2026-09-14' : '2026-09-07', periodEnd: index ? '2026-09-16' : '2026-09-13', periodLabel: index ? '14/09–16/09/2026' : '07/09–13/09/2026' }));
  });
  await installApiHarness(page, { aiFixture: fixture });
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.locator('[data-field="aiGroupBy"]').selectOption('week');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.locator('.ai-details')).toHaveCount(0);
  await expect(panel.locator('.ai-periods')).toHaveCount(1);
  await panel.locator('.ai-verification > summary').click();
  await panel.locator('.ai-comparison > summary').click();
  await expect(panel.locator('.ai-comparison')).toContainText('Kỳ 1 (07–13/09) → Kỳ 2 (14–16/09)');
  await expect(panel.locator('.ai-comparison').getByRole('row')).toHaveCount(4);
  await expect(panel).not.toContainText('Cao nhất');
  await expect(panel).not.toContainText('Thấp nhất');
  await panel.screenshot({ path: '../.impeccable/review/desktop-short-weekly.png' });
  await page.setViewportSize({ width: 1280, height: 900 });
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await panel.screenshot({ path: '../.impeccable/review/desktop-short-weekly-1280.png' });
});
