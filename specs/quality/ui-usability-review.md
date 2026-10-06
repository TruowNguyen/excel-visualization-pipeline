# Rà soát khả năng sử dụng UI — 05/10/2026

> Cập nhật tiếp nối: người dùng đã chọn lấy lại phân nhóm/điểm nhấn cũ, giữ font/thẻ nổi bật và sửa lỗi. Hướng này đã được triển khai; xem `compact-ui-restoration-evidence.md` cho source và kiểm thử mới. Các trạng thái “chưa chốt”, số test và verdict bên dưới là biên bản vòng trước, không phải kết luận hiện tại.

Trạng thái: **chưa chốt thiết kế thẩm mỹ**. Người dùng phản hồi giao diện mới xấu hơn giao diện cũ trong lúc rà soát. Dừng chỉnh thêm về thẩm mỹ, giữ các sửa lỗi và chờ lựa chọn hướng nhìn. Đây không phải biên bản nghiệm thu toàn bộ UI.

## Kết quả đánh giá

Phạm vi: frontend TypeScript/Vite, gồm Tổng quan, Thống kê, AI theo node/nhóm, Nhập Excel/lịch sử, nguồn dữ liệu và so sánh theo ngữ cảnh. Không sửa Streamlit legacy, backend, API, database, công thức hay nội dung phân tích AI.

| Phát hiện | Mức độ | Tác động và xử lý |
| --- | --- | --- |
| Diễn giải AI theo ngữ cảnh bị giới hạn `75ch` | P2 | Không có bằng chứng mất chữ; nội dung xuống dòng nhưng chỉ dùng một phần vùng báo cáo, gây cảm giác bị cắt hẹp. Đã bỏ giới hạn theo yêu cầu. Dòng dài hơn là một đánh đổi về khả năng đọc, không mặc định là đẹp hơn. |
| Điều khiển và các cột dựa vào viewport thay vì workspace khi mở nguồn | P1 | Vùng còn lại có thể hẹp dù màn hình lớn. Đã thêm container query cho điều khiển AI, thẻ số, header và vùng nhập để tự xuống dòng/xếp cột. |
| Popup so sánh dùng cột biểu đồ tối thiểu 640px trên điện thoại | P1 | Kiểm thử trước sửa tại 390px đo mép phải chart khoảng 964px, vượt mép popup khoảng 367px. Đã xếp selector/chart theo chiều dọc ở màn hình hẹp; giữ footer ngoài vùng cuộn. |
| Nguồn dữ liệu trên điện thoại không có bố cục chuyên biệt | P1 | Đã dùng bảng nguồn cố định toàn màn hình khi mở từ dashboard; khi mở trong so sánh, nguồn nằm trong vùng làm việc của popup, không phủ header/footer. |
| Giá trị nguồn dài và vùng bấm nhỏ | P2 | Giá trị trong luồng nguồn được xuống dòng thay vì dấu ba chấm; tăng vùng thao tác trên điện thoại, không phục hồi tính năng điều tra điểm bằng bàn phím đã bỏ. |
| Bản mới quá phẳng, ít phân nhóm và nhiều khoảng trống | P1 về nghiệm thu thiết kế | Người dùng chưa chấp nhận thẩm mỹ. Nền/thẻ/AI gần nhau về sắc độ; phân tích có nhiều khoảng tách nhưng thiếu phân cấp nhóm. Chưa tiếp tục thay đổi hoặc ghi nhận bản này thành chuẩn thiết kế. |

Đánh giá kỹ thuật không thay thế đánh giá thẩm mỹ. Chưa chấm điểm WCAG/toàn hệ thống vì không có kiểm chứng đầy đủ bằng screen reader, mọi browser và dữ liệu thật. Theme tối không nằm trong yêu cầu hiện tại. Plotly vẫn có cảnh báo chunk lớn, là giới hạn hiệu năng chưa xử lý trong lượt sửa bố cục này.

## Phương án đề xuất, chưa triển khai

Lấy lại sự cô đọng và phân nhóm của giao diện cũ; giữ font dễ đọc, điểm nhấn cho bốn thẻ và các sửa lỗi cắt nội dung/che nút. Phần AI cần tổ chức như một báo cáo: điều khiển gọn, tổng hợp dẫn đầu, chi tiết có phân nhóm rõ; không chỉ đổi màu toàn bộ nền hoặc tăng khoảng trống. Chờ người dùng chọn lấy lại phong cách cũ hay giữ phong cách mới nhưng điều chỉnh mật độ/điểm nhấn trước khi tiếp tục.

## Thay đổi và bằng chứng kiểm thử

- Source sửa lỗi: `frontend/src/style.css`. Phần nhấn thẻ ngay trước lượt này nằm trong cùng CSS và `frontend/src/overview-summary.ts`: nhãn 14px/600, số sẵn có 32px/700, viền trên navy 2px; số 0 hợp lệ vẫn được nhấn, dữ liệu chưa có dùng màu dịu. Không đổi số liệu hay cách tính.
- Test mới: `frontend/e2e/ui-usability.spec.ts`, **8/8 PASS**, 38,5 giây. Năm viewport 1366×768, 1440×900, 1024×768, 820×900, 390×844 kiểm tra diễn giải dài còn câu cuối, chiều rộng đầy đủ, mở/đóng nguồn, chọn vấn đề, Thống kê, xem trước và lịch sử, không tràn trang/không có pageerror. Ba viewport popup 390×844, 820×900, 1093×614 kiểm tra mép chart, nút Xong, mở/đóng nguồn và trả focus.
- 1093×614 mô phỏng không gian CSS bị thu hẹp tương đương 1366×768 ở 125%; **không phải** kiểm thử browser zoom thật.
- Build cuối: `npm run build` **PASS** (TypeScript + Vite 7,26 giây). Cảnh báo Plotly chunk >500KB vẫn còn.
- Suite liên quan trước lần chỉnh selector mobile cuối: 36 test PASS và 5 test mới lỗi locator. Các lỗi fixture/locator mới đã sửa: chọn chính xác `select[data-field="scope"]`, kiểm tra `aria-hidden` thay vì class không tồn tại, và dùng action selector khi nhãn đổi thành Phân tích lại. Không sửa logic sản phẩm để làm test pass. Lần chạy 8/8 cuối kiểm chứng lại các test mới và cả ba popup trên source cuối.
- Không chạy lại toàn bộ frontend regression sau thay đổi này. Kết quả 136/136 trong báo cáo phong cách 1 trước đó là lịch sử, không phải kết quả của lượt hiện tại.
- Các assertion hình thức trong `context-insights.spec.ts`, `insight-reading.spec.ts`, `neutral-business-ui.spec.ts` đổi từ 75ch sang toàn vùng báo cáo theo yêu cầu mới; assertion nội dung, số liệu, nguồn, phạm vi và chống response cũ giữ nguyên.
- Detector layout chạy một lần trên `frontend/src`, trả `[]`; không dùng kết quả này để xác nhận UI đẹp hoặc đã được người dùng duyệt.

Ảnh Chrome headless/fixture ở `.impeccable/review/usability/`: `ai-children-{1366,1440,1024,820,390}.png`, `statistics-{1366,390}.png`, `import-{1366,820,390}.png`, `source-390.png`, `comparison-{390,820,1093}.png`, `comparison-source-{390,820,1093}.png`. Thư mục ignored, ảnh không phải dữ liệu production. Không gọi provider AI thật hoặc ghi database thật.

## Rà soát hoàn thiện trực tiếp

Vai trò reviewer/documenter thực hiện trực tiếp thay cho agent hỗ trợ đã bị gián đoạn; không gọi đây là review độc lập.

disposition: fix

### persistence

PRODUCT.md và brief hiện có; brief đã ghi yêu cầu mới và trạng thái chưa chốt. Không cập nhật DESIGN.md/design.json để canonize một hướng nhìn đang bị người dùng phản đối.

### fidelity

| Thành phần | Kết quả | Căn cứ |
| --- | --- | --- |
| TYPE | adaptation | Giữ Segoe UI; thẻ nhấn theo yêu cầu. Prose toàn vùng thay 75ch theo phản hồi bị thu hẹp; cần chốt lại cách phân nhóm/độ dài dòng. |
| MATERIAL | match | Giữ bề mặt phẳng, SVG và control hiện có; không giả chất liệu/raster mới. |
| GROUND | match | Giữ trắng/xám, sidebar navy và tím thao tác; không đổi nhận diện lần nữa trong lúc người dùng chưa chọn. |
| Bố cục/điểm nhấn | contradicted | Phản hồi trực tiếp của người dùng chưa chấp nhận bản mới dù kiểm thử thao tác đạt. |
| Popup/nguồn màn hình nhỏ | adaptation | Kiểm thử và ảnh cuối cho thấy nguồn nằm trong popup, header và nút Xong còn thấy; xếp dọc là điều chỉnh để không cắt vùng làm việc. |

### ceiling

Chưa đạt: cần khôi phục mật độ và phân nhóm phục vụ đọc báo cáo CX, không thêm trang trí khi chưa chốt hướng.

### material_fixes

1. Chốt với người dùng lấy lại phong cách cũ hay giữ phong cách mới; chưa triển khai tiếp trước lựa chọn này.
2. Sau lựa chọn, chỉnh phân nhóm/mật độ/điểm nhấn và kiểm chứng lại, giữ các sửa lỗi bố cục đã có.

### keep

Giữ số liệu, nguồn, privacy, session filters, nút đóng/footer, cơ chế chống response cũ và những tính năng đã được yêu cầu bỏ.

## Ghi nhận quy chuẩn

No changes: DESIGN.md và .impeccable/design.json giữ nguyên; source/brief đã kiểm tra, chờ hướng nhìn được duyệt.

Palette: giữ trắng/xám, navy, tím thao tác.
Type: Segoe UI; điểm nhấn thẻ và vùng đọc hiện tại còn là bản đang rà soát.
Action Accent: giữ tím cho thao tác/focus/lựa chọn.
Reading Measure: chưa cập nhật rule 75ch thành chuẩn mới khi người dùng chưa chốt.
Flat Surface: giữ nguyên hồ sơ trước; không khẳng định người dùng chấp nhận mức độ làm phẳng hiện tại.

Không canonize: thay đổi thẩm mỹ chưa được chấp nhận, giới hạn metadata legacy, cảnh báo bundle và bằng chứng fixture không phải chứng nhận production.
