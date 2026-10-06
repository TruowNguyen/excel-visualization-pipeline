# Khôi phục phân nhóm giao diện — 05/10/2026

Người dùng đã chọn lấy lại bố cục/điểm nhấn của giao diện cũ, giữ font dễ đọc, thẻ số nổi bật và các sửa lỗi. Đây là chỉnh phần trình bày, không rollback tính năng hoặc dữ liệu. Định hướng được triển khai; việc chấp nhận thẩm mỹ cuối cùng vẫn thuộc người dùng.

## Đã hoàn thành

| Yêu cầu | Thay đổi | Bằng chứng |
| --- | --- | --- |
| Phân nhóm rõ như hướng cũ | Tab chọn có nền tím nhạt; khung làm việc trắng có viền; sidebar có vùng ghi chú riêng | `overview-1366.png`, `overview-390.png`; assertion màu/viền của test giao diện |
| Bốn thẻ vẫn nổi bật | Giữ nhãn 14px/600, số có dữ liệu 32px/700 và navy; số 0 khác dữ liệu chưa có | `metric-highlight-overview-1366.png`, `metric-highlight-statistics-1366.png`; test phân biệt 0 và dấu gạch |
| AI có phân cấp, bớt khoảng trống | Tiêu đề/tổng hợp nền nhạt, nội dung trắng; inset 20px, khoảng giữa phần 20px, đoạn 12px | `ai-1366.png`, `ai-390.png`; assertion header/tổng hợp/gap |
| Đọc đủ AI | Giữ toàn chiều rộng báo cáo, xuống dòng dài; không giới hạn chiều cao, không ellipsis/lược bỏ nội dung | `ui-usability.spec.ts` kiểm tra câu cuối của diễn giải dài, kích thước nội dung và mở nguồn |
| Giữ form nhập gọn | Không thêm khung ngoài cho vùng chọn tệp/xem trước/lịch sử đã phân nhóm | `import-history-1366.png`, `import-390.png`; assertion border ngoài bằng 0 |
| Popup không mất thao tác | Giữ footer ngoài cuộn; nguồn trong vùng làm việc; tách selector CSS của bảng nguồn dashboard khỏi bảng nguồn popup | Test đo nguồn nằm trong `.contextual-layout` và hit-test cả nút đóng header/nút Xong khi nguồn mở tại 390, 820 và 1093px |

Source thay đổi trong lượt này: `frontend/src/style.css`. Test cập nhật: `frontend/e2e/neutral-business-ui.spec.ts`, `frontend/e2e/ui-usability.spec.ts`. Hồ sơ thiết kế được hợp nhất ở `DESIGN.md`, `.impeccable/design.json` và brief; các quyết định không liên quan được giữ nguyên.

Không sửa renderer, output AI, backend, API, database hoặc phép tính trong lượt này. Không khôi phục tab So sánh/Đối chiếu đã ẩn, không khôi phục điều tra điểm bằng bàn phím. Các thay đổi sẵn có ngoài phạm vi trong worktree được giữ nguyên.

## Kiểm chứng

- Build source cuối: `npm run build` **PASS** — TypeScript + Vite, 4,88 giây. Plotly vẫn có cảnh báo chunk >500KB.
- Frontend regression source cuối: `npx playwright test --reporter=line` **145/145 PASS**, 4,6 phút, một worker. Bao gồm 6 test giao diện/điểm nhấn, 8 test khả năng sử dụng và 3 test tương phản trên các phần chữ được chọn; không phải chứng nhận WCAG toàn sản phẩm.
- Lượt đầy đủ trước sửa selector bảng nguồn tablet: **145/145 PASS**, 4,5 phút. Đây không phải kết quả source cuối; ảnh đã phát hiện lỗ hổng kiểm thử và dẫn đến assertion containment/hit-test mới.
- Lượt kiểm thử hẹp ban đầu: 14/17 PASS, ba lỗi cùng nguyên nhân selector dùng `.workspace[data-import-workspace]` trong khi attribute thực tế ở `#workspace`. Đã sửa CSS, giữ assertion, không nới test để bỏ qua lỗi.
- Detector layout chạy một lần trên `frontend/src`, trả `[]`; đây không phải bằng chứng UI đẹp hoặc WCAG toàn diện.
- `git diff --check` không có lỗi whitespace; sidecar JSON parse được. Cảnh báo Git chuyển LF/CRLF không phải lỗi kiểm thử.

Fixture Chrome headless, không gọi provider AI thật hoặc ghi database thật. Bộ kiểm thử kiểm tra import/refresh/stale-response, nhưng request được harness mô phỏng; không chứng minh hệ thống production hoặc chất lượng AI thật.

## Ảnh và phạm vi rà soát

Ảnh nằm trong `.impeccable/review/compact-ui/` (ignored, giữ trong workspace). Các ảnh tự sinh còn có phiên bản 1440px và bảng nguồn/chi tiết; tập trực tiếp rà soát gồm:

- `overview-1366.png`, `overview-390.png`: toàn trang, thẻ và khung làm việc.
- `ai-1366.png`, `ai-390.png`: vùng AI theo ngữ cảnh, phạm vi và chi tiết.
- `comparison-investigation-1366.png`: Statistics và nguồn docked cùng popup.
- `import-history-1366.png`, `import-390.png`: form/lịch sử, không khung ngoài thừa.
- `usability/ai-children-1366.png`, `usability/statistics-390.png`: AI theo vấn đề được chọn và Thống kê.
- `usability/comparison-source-{390,820,1093}.png`: đã đọc lại ảnh source cuối sau sửa selector tablet; nguồn nằm trong vùng làm việc, header và nút Xong còn thấy. 1093px vẫn có chart/nguồn cùng lúc, 390/820px dùng nguồn thay vùng làm việc khi mở.

Viewport kiểm thử khả năng sử dụng: 1366×768, 1440×900, 1024×768, 820×900, 390×844; popup thêm 1093×614. Kích thước 1093×614 chỉ mô phỏng vùng CSS bị thu hẹp tương đương 1366×768 ở 125%, không phải browser zoom thật. Trên màn hình nhỏ, bảng nguồn thay vùng làm việc khi mở, không hứa chart và nguồn luôn đồng thời nhìn thấy.

Ảnh/CSS cũ được đối chiếu trước sửa: `git show HEAD:frontend/src/style.css`, `ui-review-20261005-a-overview.png`, `ui-review-20261005-b-fixture-ai-1440.png`. Đây là tham chiếu hướng nhìn, không phải bằng chứng source hiện tại hoặc rollback về HEAD.

## Giới hạn

Rà soát hoàn thiện và ghi nhận quy chuẩn được thực hiện trực tiếp thay agent hỗ trợ bị gián đoạn, không phải đánh giá độc lập. Chưa xác nhận mọi browser, screen reader, thiết bị thật hoặc dữ liệu thật. Metadata legacy 10–11px và kích thước bundle Plotly chưa được xử lý trong lượt này. Vùng đọc toàn chiều rộng được giữ theo yêu cầu; dòng desktop dài hơn là đánh đổi về khả năng đọc.

## Rà soát hoàn thiện trực tiếp

disposition: ship

Refinement code-led của giao diện hiện có; không có comp hoặc QUALITY BAR mới. Căn cứ là phản hồi đã duyệt, ảnh/CSS cũ, brief và ảnh source cuối; không suy ra một phiên bản pixel-identical với ảnh cũ.

### persistence

PRODUCT.md, brief và DESIGN.md hiện có. DESIGN.md/sidecar đã hợp nhất quyết định đã duyệt: khung làm việc, nền chọn tab, phân nhóm AI, thẻ nhấn và responsive. Sidecar parse được; ba named rules và toàn bộ guardrails khớp văn bản DESIGN.md. Giữ nguyên các quyết định ngoài phạm vi.

### fidelity

| Thành phần | Kết quả | Căn cứ |
| --- | --- | --- |
| TYPE | adaptation | Giữ Segoe UI thay font cũ theo hướng đã được chọn; số/nhãn thẻ nhấn, diễn giải vẫn đọc đủ. Không phục hồi chữ điều khiển nhỏ từ CSS cũ. |
| MATERIAL | match | Bề mặt trắng, viền mảnh, nền nhạt và SVG; không giả chất liệu, gradient hoặc shadow mới. |
| GROUND | match | Khôi phục canvas lạnh nhẹ theo CSS cũ; sidebar navy và accent tím được giữ, không đổi sang nhận diện khác. |
| Phân nhóm/mật độ | match | Tab có nền chọn, khung trắng bao vùng phân tích; AI có phần dẫn đầu nền nhạt và nhịp 20/12px; không có card mới cho từng đoạn. |
| Vùng đọc AI | adaptation | Toàn chiều rộng theo yêu cầu tránh cảm giác crop; không cắt chữ, giữ disclosure nguồn/chi tiết. |
| Nhập Excel | adaptation | Không thêm khung ngoài form/xem trước đã phân nhóm; giữ import-first và lịch sử phụ. |
| Popup/nguồn | adaptation | Giữ desktop docked; màn hình hẹp mở nguồn trong vùng làm việc. Ảnh cuối và assertion containment/hit-test xác nhận header/footer không bị che. |

### ceiling

Đạt trong phạm vi refinement đã duyệt: lấy lại phân nhóm và mật độ cũ, giữ readability và các sửa thao tác. Không bổ sung trang trí hoặc thay cấu trúc/tính năng để tạo khác biệt. Đây không phải tuyên bố người dùng đã nghiệm thu thẩm mỹ cuối hoặc đã kiểm chứng mọi môi trường.

### material_fixes

Không còn lỗi cần sửa trong tập bằng chứng của lượt này. Lỗi selector Nhập Excel và selector bảng nguồn tablet đã sửa; ảnh cuối xác nhận containment tại 390/820/1093px. Không mở thêm vòng đánh bóng giao diện.

### keep

Giữ số liệu/công thức, privacy, session filters, chống response cũ, bốn thẻ, nguồn/chi tiết và những chức năng người dùng đã yêu cầu bỏ; không thay frontend flow hoặc mở rộng backend.

## Ghi nhận quy chuẩn

Paths written: `DESIGN.md`, `.impeccable/design.json`; hợp nhất chứ không thay toàn bộ hệ thống.

Palette: trắng/xám lạnh nhẹ, navy, tím thao tác và nền phân tích nhạt.
Type: Segoe UI; nhãn thẻ 14px/600, số có dữ liệu 32px/700, diễn giải 16px/1,65.
Action Accent: tím cho thao tác/focus/lựa chọn; chữ báo cáo trung tính.
Reading Measure: toàn vùng báo cáo theo yêu cầu, xuống dòng tự nhiên; không cắt chữ hoặc bảng nguồn.
Flat Surface: viền/nền/tiêu đề phân nhóm; không thêm shadow ngoài lớp nổi hiện có.

Không canonize hoặc sửa ngoài phạm vi: metadata legacy 10–11px, bundle Plotly lớn, giới hạn browser/thiết bị thật; bằng chứng fixture không trở thành chứng nhận production.
