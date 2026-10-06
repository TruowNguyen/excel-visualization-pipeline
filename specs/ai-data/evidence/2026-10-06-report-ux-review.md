# Báo cáo — cải thiện UX/UI ngày 06/10/2026

Phạm vi: giữ hệ thống giao diện desktop và năm phần báo cáo đã thống nhất. Không sửa prompt, Analytics Engine hay validator. Không triển khai thiết kế mobile mới.

## Thay đổi

- Tab Báo cáo chỉ giữ bộ chọn dự án ở sidebar. Phạm vi, thời gian và cách tính được thiết lập riêng trong báo cáo; không lẫn với bộ lọc dashboard.
- Thiết lập và báo cáo đã lưu dùng disclosure. Thông tin phạm vi/ngày ngắn gọn, metadata đầy đủ mở khi cần.
- Lưu, kiểm tra và xuất đúng revision nằm ở đầu tài liệu, trên thanh thao tác bám khi cuộn. Chưa lưu chỉnh sửa thì chưa được sinh AI, kiểm tra hoặc xuất.
- Diễn biến: mỗi vấn đề có biểu đồ ngay trước các đoạn diễn giải tương ứng. Liên hệ giữa các vấn đề đặt sau các cụm riêng, có liên kết tới biểu đồ.
- Các KPI cùng vấn đề dùng biểu đồ kết hợp theo quy ước dashboard: tổng là cột, trung bình/ngày hoặc tỷ lệ là đường; đơn vị khác nhau giữ trục riêng. Không gộp ba đơn vị vào hai trục. Diễn giải dùng chiều rộng vùng báo cáo theo thiết kế đã chốt.
- Nhãn đánh dấu mặc định gộp theo kỳ để giảm chồng nhau; chọn nhận định thì focus vào anchors tương ứng. Điểm chưa chọn vẫn được định vị bằng nhãn tạm “Đang xem”, không tự chọn để xuất và không gọi API. Canonical chart/fact/evidence identity không đổi.
- Template mới `cx-period-report` 1.1, renderer v2; PDF/DOCX mới dùng chung thứ tự biểu đồ → diễn giải. Không ghi đè bytes của file đã xuất/lưu trước đó. Template 1.0 còn giữ renderer tương thích riêng.

## Kiểm thử LLM thật

Đã được người dùng cho phép gửi facts và tên/phạm vi tới API cấu hình. Không gửi workbook hay API key trong payload. Script chạy trên bản sao SQLite, không thêm report test vào DB đang dùng.

[Ma trận tám phạm vi](2026-10-06-report-ux-live.json): 7 cuộc gọi provider, cả 7 `accepted`; một phạm vi thiếu dữ liệu không gọi provider. 166 điểm và 200 anchors đối chiếu nguồn không có mismatch. 16 lần xuất PDF/DOCX thành công, snapshot giữ nguyên.

[Hai ca xác nhận cuối](2026-10-06-report-ux-final.json):

| Ca | Thời gian sinh | Validator | Điểm / anchors đúng nguồn | Xuất |
|---|---:|---|---|---|
| Tổng quan một nội dung, theo ngày | 7.858 giây | accepted | 27 / 49 | PDF + DOCX thành công |
| Thống kê một nội dung, theo tuần, tổng + trung bình/ngày | 6.545 giây | accepted | 32 / 43 | PDF + DOCX thành công |

Model cấu hình `ag/gemini-3.7-flash-low`, response `gemini-3.7-flash-tiered`. Prompt vẫn `context-insight-v5`. Các thay đổi cuối về heading PDF/DOCX được kiểm tra bằng render lại từ response đã lưu, không gửi thêm dữ liệu.

Đánh giá nội dung: diễn giải đã có bằng chứng định lượng (ví dụ số lỗi 19 → 43, +24; sau đỉnh 43 → 32, -11). Thống kê phân biệt tổng giảm 104 → 76 với trung bình/ngày tăng 17.33 → 25.33; không suy ra hoạt động giảm từ tổng của kỳ ngắn. Quan hệ giữa KPI là đối chiếu diễn biến, không correlation hay kết luận nguyên nhân nghiệp vụ.

Hạn chế còn lại: một số câu cảnh báo “hai kỳ chỉ đủ so sánh” và nhãn nguồn vẫn lặp; Summary nhiều vấn đề chọn ý đại diện, chưa xếp hạng ưu tiên nghiệp vụ. `accepted` chứng minh qua kiểm chứng hiện tại, không đồng nghĩa mọi câu đều là insight tốt nhất. Không nới validator để giải quyết bố cục.

## Regression và bằng chứng UI

- TypeScript typecheck và production build đạt. Plotly lazy chunk vẫn có cảnh báo dung lượng >500 kB có sẵn.
- Full Playwright: 174 đạt, 3 diagnostic opt-in bỏ qua; một test mất tệp trace do hai lần chạy dùng chung thư mục. Chạy lại độc lập: đạt. Sau sửa theo review: 14 test báo cáo đạt, gồm định vị điểm chưa chọn không tự chọn/không gọi API. Lượt dùng output tùy chỉnh trong frontend gặp Vite watch EBUSY trên file download; chuyển artifacts ra ngoài root Vite rồi chạy lại đạt.
- Diagnostic replay output thật: 3 đạt; dashboard scaffolding là synthetic, không coi đó là dữ liệu LLM.
- Full Python tại lượt chạy: 427 đạt, một setup error do sandbox không tạo lock trong thư mục temp. Chạy lại test đó ngoài sandbox: đạt. Sau bổ sung test một kỳ và chỉnh export: 28 test báo cáo/story đạt.
- Detector chạy một lần trên frontend thay đổi: `[]`.
- Ảnh desktop 1366/1440/1920 và 390px chống regression; ảnh output thật Tổng quan, Thống kê, toàn bộ vấn đề trong `.impeccable/review/reports-ux-2026-10-06`.
- PDF đã render để kiểm tra trực quan; DOCX kiểm tra cấu trúc/nội dung/ảnh, chưa kiểm tra phân trang trên Microsoft Word.

Các ca Tổng quan và Thống kê ở 1440×1000 có nút xuất tại y≈477 thay vì cuối tài liệu (trước đây y≈6111/6763). Không tràn ngang; Thống kê bốn series dùng một panel thay vì bốn biểu đồ rời. Đây là số đo trên replay có nhãn, không benchmark toàn bộ dữ liệu sản phẩm.

Review độc lập theo Impeccable: ảnh PDF Thống kê ban đầu không đúng trang, đã recapture trực tiếp bằng fitz. Review đầy đủ yêu cầu sửa chiều rộng diễn giải và định vị điểm chưa chọn; đã sửa, recapture các kích thước, rồi reviewer chấm cả hai `resolved`, disposition `ship` ở phạm vi hai sửa đổi đó. Không coi verdict này là chứng nhận hoàn hảo cho toàn tính năng.

Recapture Tổng quan/Thống kê dùng hai response API cuối; phạm vi toàn bộ vấn đề giữ response của ma trận tám ca. Có thêm ảnh `deselected-finding.png` kiểm chứng feedback tạm trên biểu đồ kết hợp. Cập nhật tài liệu theo Impeccable nằm trong surface brief và as-built.
