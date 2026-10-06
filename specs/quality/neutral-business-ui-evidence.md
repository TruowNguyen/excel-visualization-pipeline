# Bằng chứng triển khai phong cách 1 — giao diện nghiệp vụ trung tính

Ngày thực hiện: 05/10/2026. Áp dụng cho frontend TypeScript/Vite của Automated CX Report, không phải giao diện Streamlit legacy.

## Phạm vi đã triển khai

- Thống nhất Segoe UI/system stack giữa giao diện và Plotly; không phụ thuộc font tải từ bên ngoài. Chữ điều khiển 14px, nhãn thẻ 14px, số nghiệp vụ 28px, tiêu đề khu vực/AI 18px. Văn bản diễn giải theo ngữ cảnh 16px, dòng 1,65 và độ dài tối đa 75ch.
- Nền trắng/xám trung tính; giữ sidebar navy và tím nhận diện cho thao tác, focus, lựa chọn. Bỏ nền tím trang trí trong phần diễn giải, gradient ở dấu hiệu thương hiệu và shadow của thẻ/khung nội dung.
- Làm phẳng khung ngoài của vùng nội dung; mỗi biểu đồ giữ một container. Bốn thẻ nghiệp vụ và mục Cách đọc các chỉ số vẫn giữ dữ liệu, phạm vi và trạng thái đóng mặc định.
- Đổi icon chrome từ ký tự Unicode sang SVG trang trí cùng nét; tên truy cập vẫn nằm trên nút. Nút trên chart dùng nhãn Phân tích. Tải dữ liệu CSV dùng nút phụ để không cạnh tranh với tác vụ chính.
- Thống nhất căn lề phần AI; tăng cỡ chữ thông tin nguồn và nút trong Điều tra điểm. Giữ màu trạng thái cảnh báo, lỗi và xác nhận dữ liệu.
- Sửa cắt đáy biểu đồ: khung root 433px chứa Plotly 420px và padding dọc 13px; khung child 393px chứa Plotly 380px và cùng padding. Loại override 355px trên điện thoại, không giảm chiều cao hoặc thay dữ liệu Plotly để che lỗi. Kiểm thử đo vị trí tất cả nhãn trục thời gian bên trong card, không chỉ kiểm tra chart có mặt trong DOM.
- Áp dụng cho Tổng quan, Thống kê, AI, Nhập Excel/lịch sử, so sánh theo ngữ cảnh và điều tra nguồn. Không di chuyển bộ lọc hoặc thiết kế lại luồng nhập.

Không sửa API, database, parser, công thức, metric keys, dữ liệu trace, lineage hoặc cơ chế chống response cũ trong lượt này. Không phục hồi tab So sánh/Đối chiếu dữ liệu hay điều tra điểm bằng bàn phím. Các sửa backend và tài liệu nghiệp vụ khác trong worktree đã có từ trước, không phải phạm vi thay đổi giao diện này.

## Kiểm thử và xuất xứ bằng chứng

Kiểm thử bằng Playwright với `installApiHarness`: dữ liệu mô phỏng, không gọi provider AI, không ghi vào database thật. Browser trong ứng dụng không khả dụng tại thời điểm kiểm chứng; dùng Chrome headless qua Playwright local.

Các ảnh được tạo tại `.impeccable/review/neutral-ui/`; thư mục này được gitignore theo cấu hình hiện có. Chúng là bằng chứng kiểm thử cục bộ, không phải ảnh hoặc dữ liệu production, không phải tài nguyên raster đưa vào sản phẩm.

| Bề mặt/trạng thái | Kích thước |
| --- | --- |
| Tổng quan, Thống kê trước phân tích, AI sau phân tích | 1366×768, 1440×900, 390×844 |
| Nhập Excel chưa chọn tệp; xem trước đạt kiểm tra và lịch sử mở | 1366×768, 1440×900, 390×844 |
| So sánh chỉ số gốc; trung bình mỗi ngày; điều tra nguồn tổng hợp | 1366×768, 1440×900 |

21 ảnh: `overview-*`, `statistics-*`, `ai-*`, `import-*`, `import-history-*`, `comparison-*`, `comparison-statistics-*`, `comparison-investigation-*`.

Kiểm tra độ tương phản AA cho các nhãn quan trọng gồm breadcrumb, bộ lọc Thống kê, nhãn môi trường, marker CX, trục/legend, nguồn/validation, bảng đối chiếu và lịch sử. Đây không phải chứng nhận accessibility toàn hệ thống.

Detector Impeccable chạy một lần trên `frontend/src`: trả `[]`; lưu `detector.json`. Kết quả detector không thay thế kiểm tra ảnh và tương tác.

Rà soát độc lập lần đầu xem đủ 21 ảnh: đúng định hướng; ghi nhận một P1 là cắt trục thời gian ở điện thoại. Source đã sửa theo finding; kết luận sau sửa được ghi riêng, không xem kết quả scan rỗng là chứng cứ hết lỗi.

## Quy tắc cập nhật kiểm thử hình thức

Các test cũ yêu cầu đoạn diễn giải theo ngữ cảnh chiếm toàn chiều rộng. Phong cách mới đặt giới hạn 75ch để đọc thuận tiện trên màn hình lớn. Assertion được thay bằng phép đo 75ch theo font thực tế và bảo đảm chiều rộng bằng `min(parent, 75ch)`, không cắt chữ hoặc che nội dung. Báo cáo AI kiểu cũ theo một node vẫn giữ đoạn tổng hợp toàn chiều rộng. Các assertion số liệu, nội dung, source, request scope, selection và response supersession được giữ.

Kiểm thử mới: `frontend/e2e/neutral-business-ui.spec.ts`. Kiểm thử liên quan: `contrast.spec.ts`, `context-insights.spec.ts`, `insight-reading.spec.ts`, cùng toàn bộ frontend regression suite.

## Kết quả cuối

- `npm run build`: TypeScript và Vite **PASS**, lần cuối 9,81 giây. Cảnh báo Plotly chunk lớn có từ trước vẫn còn; không coi là lỗi build.
- `npx playwright test --reporter=line,json`: **136/136 PASS**, không skip, không flaky, khoảng 5 phút. Báo cáo máy đọc: `.impeccable/review/neutral-ui/tests-final.json`.
- Kiểm thử mới: **5/5 PASS** cho typography/khung phẳng/icon, bốn thẻ và disclosure, không tràn ngang, trục thời gian không bị cắt, xem trước/lịch sử và so sánh/điều tra/focus return.
- Kiểm thử tương phản: **3/3 PASS** tại 1366×768, 1440×900 và 1920×1080.
- Ba kiểm thử freshness tiếp tục PASS: nhập thành công cập nhật dashboard không reload toàn trang; Refresh fetch lại cùng bộ lọc; response cũ không ghi đè response mới.
- Rà soát hoàn thiện độc lập: disposition ban đầu **FIX** với một P1; Verdict Pass xác nhận **P1 Resolved**, chuyển **SHIP** trong phạm vi phong cách đã duyệt. Báo cáo cục bộ: `.impeccable/review/neutral-ui/finish-review.md`. Verdict chỉ xác nhận finding đã liệt kê, không phải chứng nhận toàn hệ thống.

Full run đầu có 130 pass và 6 failure do assertion cũ đòi đoạn diễn giải contextual full-width. Sau cập nhật assertion theo contract 75ch: kiểm thử đọc 10/10 PASS; full run cuối 136/136 PASS. Không bỏ test hoặc nới assertion số liệu để đạt kết quả.

Source của lượt này: `frontend/src/style.css`, `main.ts`, `chart.ts`, file mới `ui-icons.ts`. Hồ sơ quy chuẩn as-built: `DESIGN.md` và `.impeccable/design.json`. Các ảnh/báo cáo trong `.impeccable` giữ local theo gitignore hiện tại; không tự commit hoặc đẩy lên Git.

### Xác nhận hồ sơ thiết kế

Hai file quy chuẩn đã được tạo theo source thực tế. Agent ghi tài liệu bị gián đoạn sau khi ghi file; bước documenter được hoàn tất trực tiếp bằng kiểm tra lại tài liệu và source, không thay đổi định hướng hoặc UI sau verdict.

- Palette: trắng/xám trung tính, sidebar navy, tím cho hành động/focus/lựa chọn; màu validation giữ ngữ nghĩa.
- Typography: Segoe UI/system cùng Plotly; UI 14px, tiêu đề khu vực 18px, thẻ số 28px, prose contextual 16px/1,65/75ch.
- Layout: khung nội dung ngoài phẳng, một container cho chart, bốn thẻ giữ contract và disclosure nguồn đóng mặc định.
- Quy tắc: Action Accent, Reading Measure và Flat Surface ghi đúng cách áp dụng đã triển khai.
- Sidecar: schemaVersion 2, 9 component HTML/CSS độc lập, tham chiếu token hợp lệ và SVG inline; không phụ thuộc runtime hoặc ảnh từ bên ngoài.

Không chuẩn hóa các hạn chế legacy thành quy tắc mới: metadata 10–11px vẫn là giới hạn hiện có, không phải chuẩn chữ mới; đoạn tổng hợp single-node legacy và popup điện thoại được ghi rõ ngoại lệ/phạm vi. Không sửa lại drift nghiệp vụ, API hoặc bộ lọc ngoài yêu cầu.

## Giới hạn kiểm chứng

- Chỉ xác minh bằng fixture và Chrome local, không tuyên bố kiểm thử provider thật, backend thật, mọi dự án/dataset hoặc mọi trình duyệt.
- Không thiết kế lại cửa sổ so sánh cho điện thoại trong lượt chỉnh phong cách này.
- Sidebar trên điện thoại vẫn mở theo trạng thái hiện có; không đổi vị trí hay cơ chế lưu bộ lọc.
- Cảnh báo bundle Plotly lớn hơn 500KB có từ trước, không xử lý bằng thay đổi kiến trúc tải trong lượt này.
