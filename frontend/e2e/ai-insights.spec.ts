import { expect, test } from '@playwright/test';
import { installApiHarness } from './fixtures';

test('AI Insights hiển thị chuỗi kỳ, mức thay đổi và mở đúng evidence', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');

  const panel = page.locator('.ai-panel');
  await expect(panel.getByRole('heading', { name: 'Nhận định xu hướng tự động' })).toBeVisible();
  const chartBox = await page.locator('[data-plot="overview-root"]').boundingBox();
  const panelBox = await panel.boundingBox();
  expect(chartBox && panelBox && panelBox.y > chartBox.y + chartBox.height).toBeTruthy();
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();

  await expect(panel.getByText('Đã kiểm chứng', { exact: true })).toBeVisible();
  await expect(panel.getByText('Kỳ đầu', { exact: true })).toBeVisible();
  await expect(panel.getByText('Tăng liên tục', { exact: false })).toHaveCount(0);
  await expect(panel.getByText('Giảm liên tục', { exact: false })).toBeVisible();
  await expect(panel.getByRole('heading', { name: 'Tổng quan phân tích' })).toBeVisible();
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('Chất lượng cảnh báo - ghi nhận trên hệ thống');
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('16/9/2026–17/9/2026');
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('Báo sai/Lỗi');
  await expect(panel.getByLabel('Mức hiển thị của kết quả phân tích')).toContainText('ngày');
  const executiveTop = await panel.locator('.ai-executive').boundingBox();
  const factsTop = await panel.locator('.ai-facts').boundingBox();
  expect(executiveTop && factsTop && executiveTop.y < factsTop.y).toBeTruthy();

  const periodDetails = panel.locator('.ai-periods');
  await expect(periodDetails).not.toHaveAttribute('open', '');
  await periodDetails.getByText('Biến động từng ngày', { exact: true }).click();
  await expect(panel.getByText('Giảm 2', { exact: true })).toBeVisible();
  await expect(panel.getByText('25%', { exact: true })).toBeVisible();
  await expect(panel.getByText('Đã đối chiếu bằng chứng')).toBeVisible();

  await panel.getByRole('button', { name: 'Mở nguồn kỳ 16/09/2026' }).click();
  await expect(page.getByRole('heading', { name: /Tổng số|Báo sai/ })).toBeVisible();
  expect(harness.calls.some(call => call.pathname.includes('/observations/obs_ai_1/provenance'))).toBeTruthy();
});

test('người dùng chọn nhóm tuần và request giữ đúng groupBy', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');

  await panel.getByLabel('Nhóm dữ liệu').selectOption('week');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();

  await expect(panel.getByText(/2\/2 kỳ tuần có dữ liệu hợp lệ/)).toBeVisible();
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
  await expect(page.locator('[data-plot="overview-root"]')).toBeVisible();
});

test('đổi filter đánh dấu insight cũ stale và không tự gọi model', async ({ page }) => {
  const harness = await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByText('Đã kiểm chứng', { exact: true })).toBeVisible();
  const before = harness.calls.filter(call => call.pathname.endsWith('/ai/trend-summary')).length;

  await page.locator('[data-field="entity"]').selectOption('child-a');
  await expect(panel.getByText('Cần phân tích lại')).toBeVisible();
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
  await expect(panel.getByText('Đã kiểm chứng', { exact: true })).toBeVisible();
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
  await expect(panel.locator('#ai-status-message')).toHaveText('Phân tích hoàn tất. Đã kiểm chứng.');
  await expect(panel.locator('.ai-output')).toHaveAttribute('aria-busy', 'false');
});

test('CTA giữ tỷ lệ gọn trên desktop và chỉ full-width trên mobile', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await installApiHarness(page);
  await page.goto('/');
  const panel = page.locator('.ai-panel');
  const action = panel.getByRole('button', { name: 'Phân tích khoảng đang xem' });
  const desktopBox = await action.boundingBox();
  const selectBox = await panel.getByLabel('Chỉ số').boundingBox();
  expect(desktopBox?.width).toBeGreaterThanOrEqual(190);
  expect(desktopBox?.width).toBeLessThanOrEqual(220);
  expect(desktopBox && selectBox && desktopBox.width <= selectBox.width).toBeTruthy();

  await page.setViewportSize({ width: 390, height: 844 });
  const mobileBox = await action.boundingBox();
  const mobileSelectBox = await panel.getByLabel('Chỉ số').boundingBox();
  expect(mobileBox && mobileSelectBox && Math.abs(mobileBox.width - mobileSelectBox.width) <= 1).toBeTruthy();
});

test('AI Insights giữ thứ tự đọc và không tràn ngang trên viewport hẹp', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installApiHarness(page);
  await page.goto('/');

  const panel = page.locator('.ai-panel');
  await panel.scrollIntoViewIfNeeded();
  const metricBox = await panel.getByLabel('Chỉ số').boundingBox();
  const groupBox = await panel.getByLabel('Nhóm dữ liệu').boundingBox();
  expect(metricBox && groupBox && groupBox.y > metricBox.y).toBeTruthy();
  await expect(panel.getByRole('button', { name: 'Phân tích khoảng đang xem' })).toBeVisible();
  await panel.getByRole('button', { name: 'Phân tích khoảng đang xem' }).click();
  await expect(panel.getByRole('heading', { name: 'Tổng quan phân tích' })).toBeVisible();
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
});
