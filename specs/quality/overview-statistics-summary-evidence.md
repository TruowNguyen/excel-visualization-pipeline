# Bằng chứng — bốn thẻ Thống kê và Tổng quan thu gọn

Ngày: 05/10/2026. [Contract v1.1](../frontend/overview-summary-metrics.md). Scope: mở rộng cùng bốn thẻ sang Thống kê; bỏ khối heading/thời gian/nguồn mở sẵn ở Tổng quan. Không sửa công thức/chart/Comparison/AI/import hoặc storage schema.

## Đã cài đặt

- Backend thêm `statisticsSummary` tương thích ngược. Tái sử dụng source policy, count, extrema/change và snapshot/version/cache; dữ liệu thống kê lấy đúng danh sách kỳ của chart và `prepare_period_statistics`.
- Tổng dùng `period_sum`; trung bình dùng `average_per_day`, không tự chia ngày lịch. Mode both dùng tổng trên thẻ, có nhãn/giải thích rõ; không trộn hai cách tính.
- Ngày/tuần/tháng/quý, count/khoảng/custom/incomplete được dùng theo bộ lọc Thống kê. Kỳ trống trả no_data/window null. Không nối gap lịch; zero thật khác missing/source marker.
- Renderer dùng chung, bỏ khối mở sẵn phía trên bốn thẻ. Nguồn/tên/phạm vi/chọn nguồn/cách đọc nằm trong details mặc định đóng; vẫn đổi nguồn được, giữ node/filter/chart DOM và focus.
- Lifecycle phân biệt tab và các filter Thống kê; pending/error/old API không mượn số Tổng quan hoặc giữ số cũ như kết quả mới.

## Kiểm thử

Đã chạy feature Playwright trước sửa độ nhất quán dữ liệu ảnh mô phỏng: **20 passed (54.4s)**. Sửa fixture Thống kê để kỳ, value và chênh lệch của thẻ/biểu đồ nhất quán, không sửa application calculation để đạt test.

Kiểm thử backend bổ sung: SUM/AVG/both parity; cả bốn grain; ngày thiếu/marker/coverage kế thừa/zero; selected-period issue count/calendar gap/empty; integration API average/source rejection/incomplete quarter. Kiểm thử frontend bổ sung: bốn thẻ thay metadata, cách tính/khoảng, source/Refresh/chart identity, pending/late/error, API cũ và ba captures Thống kê. Các kiểm thử Tổng quan được chỉnh để xác nhận khối thông tin không mở sẵn và disclosure vẫn thao tác được.

Full-suite ban đầu phát hiện helper lineage lấy bounding box rồi `page.mouse.click` mà không cuộn bar vào viewport. Sau thay vị trí chart theo bốn thẻ mới, click có thể nằm ngoài viewport nên không mở nguồn. Đã thêm `scrollIntoViewIfNeeded` trước lấy tọa độ, giữ nguyên click trên bar thật và toàn bộ assertions/ref provenance; không sửa ứng dụng hoặc nới assertion.

Lần full-suite tiếp theo đã qua lineage nhưng bắt race trong test đo layout AI: `boundingBox()` gọi ngay sau đổi scope khi panel đang dựng lại nên trả null. Đã thêm assertions chờ heading/selector hiện và workspace hết loading trước đo, giữ nguyên ngưỡng alignment/width và các asserts nội dung. Không thay layout/AI để né lỗi; sẽ chạy lại full suite sau ổn định test.

Lần tiếp theo có 130 passed/1 failed ở test debounce: ba vòng fill/Tab qua automation có thể dài hơn chính debounce interval trên máy bận, không còn là burst nhanh. Đã dispatch ba change trong cùng browser task, query lại input mỗi lần vì sidebar có thể dựng lại; giữ assertion chỉ một request và final count=5. Không tăng debounce của ứng dụng, thêm retries hoặc nới assertion. Đây là ổn định timing fixture, không sửa semantics tính thẻ.

Build TypeScript/Vite: **đạt (11.39s)**, còn cảnh báo chunk Plotly hiện có. Full backend `python -m pytest`: **401 passed, 19 warnings in 292.35s** (warnings deprecation FastAPI/asyncio hiện có).

Full frontend cuối, sau ba sửa helper/timing kể trên:

```text
cd frontend
npx playwright test
131 passed (5.5m)
```

Không dùng retry hoặc chỉ rerun failed case để thay full-suite verdict. Bao gồm 20 cases vùng bốn thẻ và các suite AI/Comparison/lineage/Import/freshness/terminology/contrast/performance. Performance giữ chart DOM: figure không đổi có 0 render starts/0 removed; figure đổi có 1 start/1 complete. Các lần 130 passed/1 failed trước đó được giữ rõ trong báo cáo, không coi là pass.

## Kiểm chứng dữ liệu thật — sáu dự án

Đọc `data/local/analytics.sqlite3` bằng SQLite `mode=ro`, một transaction cho observations/hierarchy của `cx_report_master`; không gọi API ghi lineage hoặc hàm khởi tạo/migration database. Dùng `_statistics_period_window` trên dữ liệu từng dự án, ba kỳ gần nhất, có kỳ chưa đầy đủ, rồi gọi pure `build_statistics_summary` với policy hiện tại.

Kết quả: **48 tổ hợp** = 6 dự án × ngày/tuần/tháng/quý × tổng/trung bình. ANVF, SmartParking, V-Pet, VOL, VSO, VW Vũ Yên đều tính được; JSON serialization `allow_nan=False` đạt, cả 48 `peak.status=ready`. Kiểm tra này không khẳng định mọi cặp kỳ đều đủ để tính thay đổi, mọi ngày đều có dữ liệu hoặc là screenshot production. Lần in kết quả toàn lịch sử ban đầu gặp lỗi encoding console cp1252 ở tên có dấu, không phải lỗi calculation; lần kiểm chứng ba kỳ chạy với UTF-8 và trả exit 0.

## Giao diện cuối

Main đã mở bảy full-page captures trong hai vòng kiểm tra: Tổng quan 1440/1366/1200/390, Thống kê 1440/1366/390. Khối heading/source mở sẵn đã biến mất, bốn thẻ cùng style, không crop/tràn ngang. Nhãn calculation ở Thống kê hiện rõ. Các ảnh là dữ liệu Playwright mô phỏng, không chứng minh dữ liệu production. Vòng đầu phát hiện fixture chưa nhất quán kỳ/chênh lệch với biểu đồ; đã sửa fixture và mở cả bảy ảnh cuối. Ảnh Thống kê có tuần 37/38 = 7/14, chênh lệch +7 = +100%, khớp chart.

Ảnh Tổng quan: `.impeccable/review/overview-summary-{desktop,user-1366,user-1200,mobile}.png`. Ảnh Thống kê: `.impeccable/review/statistics-summary-{desktop,user-1366,mobile}.png`.

Detector chạy một lần trên renderer/main: `[]`. Fresh reviewer `statistics_summary_finish_review` đã mở cả bảy ảnh và đối chiếu source/contract, trả **disposition: ship**, không có material fixes cho vùng bốn thẻ/mục thu gọn. Verdict không chứng nhận dữ liệu production hoặc thay kết quả runtime.

Fresh documenter đã hoàn tất append bằng chứng tiếng Việt trong `.impeccable/surfaces/frontend-src-main-ts.md`, mở cả bảy ảnh, giữ nguyên nội dung trước phần append. Không sửa drift DESIGN.md/design.json có từ trước. Full frontend 131 passed đã được cập nhật vào evidence và surface brief sau handoff; không mở lại vòng polishing.

## Giới hạn giữ nguyên

Nguồn riêng không là tổng toàn dự án; không SUM hierarchy, không tính phát sinh từ lũy kế. Không historical query/migration. Chưa commit/push/deploy. Không gọi model hoặc gửi thêm dữ liệu ra AI trong task này.
