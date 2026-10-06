# Nhãn tuần bằng khoảng ngày — 05/10/2026

> Báo cáo lịch sử lượt đầu. Sau phản hồi chart con khó đọc, quyết định cho phép xoay nhãn và verdict mật độ bên dưới đã được thay thế bởi [bản tinh chỉnh nhãn ngang](chart-week-labels-readable-evidence.md). Kết quả 161 test là của source lượt đầu, không phải kết quả chạy lại source mới.

Yêu cầu: thay `T37` khó đọc bằng **07/09 - 13/09** trên chart. Triển khai ở `presentationFigure` dùng chung; không sửa backend, API, database, cách tính hoặc nội dung AI.

## Đã thực hiện

- `frontend/src/chart.ts`: đổi nhãn trục tuần sang thứ Hai–Chủ nhật ISO, tính bằng UTC để không lệch do múi giờ. Giữ category key nguồn, dữ liệu và lineage; không thay công thức hoặc boundary thực tế của kỳ.
- Thêm năm nếu khoảng qua năm mới hoặc chart chứa nhiều năm. Tuần không hợp lệ giữ nhãn nguồn, không suy ra ngày sai. Ngày/tháng/quý và nhãn trộn giữ cấu hình cũ.
- Plotly tự chọn góc nhãn và tăng lề trục khi thiếu chỗ; không tự rút gọn trở lại T37.
- Fixture `weeklyCharts` chỉ được bật trong test mới, giúp kiểm tra chart tuần thật về hình dạng ở Tổng quan/Thống kê; không đổi fixture mặc định của các suite khác.
- Contract quan sát được cập nhật trong `specs/frontend/dashboard-behavior.md`; quy tắc áp dụng cho mọi dự án dùng chung renderer, không có nhánh riêng VSO.

Khoảng trên trục là tuần lịch đầy đủ. Kỳ chưa đầy đủ hoặc ngày thiếu vẫn có boundary/count/coverage thực tế trong tooltip và nguồn; nhãn mới không hứa mọi ngày đều có dữ liệu.

## Kiểm chứng

- Build: **PASS**, TypeScript + Vite 4,86 giây. Cảnh báo Plotly chunk >500KB vẫn còn.
- Lần kiểm thử ban đầu: **14/14 PASS**, 16,7 giây; gồm 9 trường hợp tuần, kiểm tra nhiều năm/immutability, nhãn không phải tuần và ba luồng UI.
- Source cuối giữ nguyên sau lượt build; `npx playwright test --reporter=line` **161/161 PASS**, 7,2 phút, một worker. Bao gồm 16 test nhãn tuần và toàn bộ 145 test frontend trước đó. Không chạy backend regression vì không sửa backend/cách tính trong lượt này.
- Layout detector chạy một lần trên `frontend/src/chart.ts`, trả `[]`; không thay thế kiểm tra ảnh.

Test mới: `frontend/e2e/week-labels.spec.ts`.

| Phạm vi | Kiểm chứng |
| --- | --- |
| Chuyển nhãn | Tuần 37, qua tháng, năm nhuận, tuần 1 qua năm, tuần 53 hợp lệ/không hợp lệ, tuần 0/54 |
| Dữ liệu không đổi | `trace.x/y/ids/customdata/meta`, tickvals và figure đầu vào giữ nguyên |
| Nhãn khác | Ngày, tháng, quý và dữ liệu trộn không bị đổi |
| Luồng thực tế | Tổng quan root/child, Thống kê root/child, so sánh Statistics SUM/AVG và nhấn điểm mở đúng aggregate provenance |
| Kích thước | 1366×768, 1440×900, 390×844; không tràn trang hoặc cắt nhãn trong container |
| Mật độ | 8 tuần ở chart con tại 1366/390px; nhãn cuối đúng, đủ số tick, không bị cắt phía dưới |

## Ảnh

Ảnh fixture Chrome headless nằm trong `.impeccable/review/week-labels/`, ignored nhưng giữ ở workspace:

- `overview-{1366,1440,390}.png`.
- `statistics-{1366,1440,390}.png`.
- `comparison-{1366,1440,390}.png` — AVG/ngày trong popup, phần làm việc cuộn tới trục khi cần.
- `dense-weeks-{1366,390}.png` — dữ liệu mô phỏng 8 tuần để kiểm tra mật độ.

Không gọi provider AI thật, không import hoặc ghi database thật. Không dùng ảnh fixture để xác nhận dữ liệu production. Mã category/tooltip nguồn có thể vẫn dùng “Tuần 37/2026”; đây là giữ định danh và ngữ cảnh, không phải trục còn hiển thị T37.

Rà soát ảnh và ghi nhận quy chuẩn trực tiếp thay agent hỗ trợ gián đoạn; không gọi là review độc lập. Đã đọc ảnh Tổng quan 1440, Thống kê 1366, popup mobile390 và ảnh 8 tuần 1366/390; nhãn đúng, không cắt, trục dày tự xoay. DESIGN.md/sidecar giữ nguyên vì không có token, palette, typography hoặc component mới cần ghi nhận.

## Rà soát hoàn thiện trực tiếp

disposition: ship

Refinement code-led theo yêu cầu cụ thể; không có comp hoặc QUALITY BAR mới. Căn cứ là renderer cũ, yêu cầu đã xác định, brief và ảnh fixture source cuối.

### persistence

PRODUCT.md, DESIGN.md và brief hiện có; hành vi nhãn tuần được ghi trong dashboard-behavior.md. Không sửa các quy tắc hoặc token ngoài phạm vi.

### fidelity

| Thành phần | Kết quả | Căn cứ |
| --- | --- | --- |
| TYPE | match | Giữ stack/cỡ chữ trục; chỉ thay chữ viết tắt bằng khoảng ngày đã yêu cầu. |
| MATERIAL | match | Giữ Plotly và chrome chart, không thêm khung/chất liệu/ornament. |
| GROUND | match | Giữ nền trắng và palette hiện tại, không đổi nhận diện. |
| Nhãn tuần | adaptation | `T37` thành `07/09 - 13/09` theo yêu cầu; tuần qua năm/nhiều năm có thêm năm để phân biệt. |
| Mật độ và popup | adaptation | Plotly tự xoay và tăng lề cho 8 tuần; popup mobile giữ vùng làm việc cuộn và footer ngoài cuộn. |
| Nguồn dữ liệu | match | Category và aggregate refs nguyên vẹn; nhấn bar mở đúng khoảng nguồn. |

### ceiling

Đạt trong phạm vi làm rõ nhãn: khoảng ngày trực tiếp đọc được thay mã tuần; không mở rộng redesign hoặc calculation.

### material_fixes

Không còn lỗi cần sửa trong tập ảnh/kiểm thử của lượt này; không mở thêm vòng đánh bóng. 8 tuần trên màn hình nhỏ vẫn cần đọc chữ xoay, là giới hạn mật độ được ghi nhận chứ không hứa mọi nhãn luôn ngang.

### keep

Giữ category keys, giá trị, cách tính, boundary/coverage, tham chiếu nguồn, thứ tự trace, filter và các chức năng đã được yêu cầu bỏ.

## Ghi nhận quy chuẩn trực tiếp

No changes: DESIGN.md và .impeccable/design.json; đối chiếu với chart.ts và ảnh source cuối. Hành vi nhãn được ghi ở spec frontend, không tạo token mới.

Palette: giữ trắng, navy và các màu series hiện có.
Type: giữ Segoe UI; trục dùng cỡ chữ chart hiện có.
Action Accent: không đổi màu thao tác/focus.
Reading Measure: không đổi phần đọc AI.
Flat Surface: không thêm khung hoặc elevation.

Không canonize: metadata legacy, chunk Plotly lớn, chữ xoay ở mật độ cao và giới hạn dữ liệu mô phỏng; không khẳng định WCAG/mọi browser hoặc dữ liệu production.
