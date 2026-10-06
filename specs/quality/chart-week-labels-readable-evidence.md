# Nhãn tuần dễ đọc trong nhóm — 05/10/2026

## Phạm vi và thay đổi

Người dùng phản hồi khoảng ngày dài khó đọc ở các vấn đề trong nhóm. **Desktop là mục tiêu**, giữ bố cục hai chart mỗi hàng; không thiết kế lại hoặc cam kết hỗ trợ mobile. Ảnh và phép thử viewport hẹp chỉ là kiểm tra phụ, không phải mục tiêu sản phẩm.

- Chart rộng: khoảng ngày một dòng, nằm ngang.
- Chart hẹp: hai dòng `07/09` / `- 13/09`, không nghiêng hoặc xoay dọc.
- Nếu quá dày: chọn các nhãn cách đều, giữ đầu/cuối; giữ toàn bộ điểm dữ liệu và khoảng ngày khi rê chuột. Không quay lại mã T37.
- Khi container đổi chiều rộng: cập nhật trục, không fetch workspace hoặc thay trace/selection. Hủy ResizeObserver khi purge chart.
- Giữ category keys, giá trị, công thức, customdata và tham chiếu nguồn. Không sửa backend, API, database, nội dung AI hoặc bố cục ứng dụng.

Source: `frontend/src/chart.ts`; bổ sung khai báo `relayout` trong `frontend/src/plotly.d.ts`. Regression: `frontend/e2e/week-labels.spec.ts`. Contract: `specs/frontend/dashboard-behavior.md`.

## Bằng chứng

- Build TypeScript + Vite: PASS; Vite 9,55 giây. Cảnh báo chunk Plotly >500KB có từ trước, chưa xử lý trong phạm vi này.
- Lần đầu: 24/24 PASS (57,6 giây), gồm nhãn tuần và workspace performance.
- Lần xác nhận cuối: **31/31 PASS (1,3 phút)** — `npx playwright test e2e/week-labels.spec.ts e2e/workspace-performance.spec.ts e2e/chart-lineage.spec.ts --reporter=line`. Bao gồm hover tuần không có nhãn trục, giữ đủ 8 điểm, đổi kích thước giữ selection, nhấn điểm mở nguồn, Audit quay lại và regression workspace.
- Bước hover bổ sung ban đầu bị timeout vì locator gặp lớp drag trong suốt của Plotly. Đã đổi test sang di chuyển con trỏ thật tới tọa độ bar; không sửa source để né lỗi test. Lượt đang chạy trước đó được dừng, không tính là PASS.
- Layout detector chạy một lần trên chart.ts: `[]`; kết quả này không thay thế kiểm tra ảnh.

Ảnh fixture Chrome nằm trong `.impeccable/review/week-labels-readable/` (ignored nhưng có tại workspace): `overview-{1366,1440,390}.png`, `statistics-{1366,1440,390}.png`, `comparison-{1366,1440,390}.png`, `dense-weeks-{1366,390}.png`. Đã xem ảnh 8 tuần ở desktop 1366 và viewport hẹp: chữ ngang, hai dòng, không chồng/cắt; còn đủ 8 bar dù bớt nhãn trục.

Không chạy lại toàn bộ frontend hoặc backend trong lượt này. Không gọi AI provider thật, không ghi database thật; fixture không chứng minh dữ liệu production. Báo cáo lượt đầu 161 test được giữ dưới dạng lịch sử, không dùng làm kết quả source mới.

## Rà soát hoàn thiện trực tiếp

Thực hiện review/documenter trực tiếp theo Impeccable, không phải đánh giá độc lập. Refinement code-led, không có comp hoặc QUALITY BAR mới; không đổi token/chrome của DESIGN.md.

disposition: ship

### persistence

PRODUCT.md, DESIGN.md và brief hiện có; quy tắc mới ghi ở dashboard-behavior.md. Ưu tiên desktop theo xác nhận mới nhất của người dùng.

### fidelity

| Thành phần | Kết quả | Căn cứ |
| --- | --- | --- |
| TYPE | match | Giữ Segoe UI và cỡ chữ trục. |
| MATERIAL | match | Giữ chart Plotly và chrome hiện tại, không thêm hiệu ứng/chất liệu. |
| GROUND | match | Giữ nền trắng và màu series. |
| Bố cục | match | Không đổi hai cột desktop hoặc component/filter. |
| Mật độ nhãn | adaptation | Theo phản hồi khó đọc: chữ ngang, hai dòng và giảm nhãn khi cần. |
| Điểm và nguồn | match | Không bỏ điểm hoặc đổi refs; regression kiểm tra mở nguồn từ biểu đồ. |

### ceiling

Đạt trong phạm vi làm rõ nhãn tuần của chart con; không mở vòng redesign ứng dụng hoặc tối ưu mobile.

### material_fixes

Không còn lỗi thị giác cần sửa trong hai ảnh mật độ đã xem; verdict chỉ áp dụng refinement này, không phải audit toàn ứng dụng. Kết quả test xác nhận bổ sung được ghi riêng ở trên.

### keep

Giữ dữ liệu, calculation, boundary/coverage, category keys, lineage, lựa chọn điểm và bố cục desktop hiện có.

## Ghi nhận quy chuẩn

No changes: DESIGN.md và .impeccable/design.json; đối chiếu source chart.ts, brief và ảnh chart con. Ghi hành vi trong spec frontend, không tạo token mới.

Palette: nền trắng và màu series hiện có.
Type: Segoe UI và cỡ chữ chart hiện có.
Action Accent: giữ màu/focus thao tác.
Reading Measure: không đổi phần đọc AI.
Flat Surface: không thêm elevation/chrome.

Không canonize: chunk Plotly lớn, metadata legacy, giới hạn fixture và mobile support chưa thuộc yêu cầu. Không khẳng định WCAG hoặc mọi browser/dữ liệu production.
