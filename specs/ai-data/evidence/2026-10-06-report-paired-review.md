# Report 1.2 — kế thừa nhóm kỳ và ghép biểu đồ/diễn giải

## Nguyên nhân và thay đổi

- Tổng quan từng lấy `state.aiGroupBy` (mặc định ngày), không lấy bộ lọc tuần/tháng dashboard.
- Setup sao chép từ dashboard có thể bị reset ở lần mount đầu hoặc đóng khi còn bản nháp cũ. Entry context giờ được giữ và setup mở; không tự khôi phục bản cũ đè lên thao tác tạo mới.
- Template 1.2 giữ năm phần. Trong Diễn biến: chung/chart + chung/prose, rồi chart + prose cho từng metric. Template 1.0/1.1 không tự nâng cấp.
- Metric prose dùng facts/stages đã lưu của Engine, không chia AI prose theo keyword hoặc sao chép cùng đoạn vào ba biểu đồ. Các đoạn AI/manual hiện có được giữ một lần cạnh chart chung. Không đổi prompt/validator.
- Thống kê both giữ hai đơn vị/trục; một metric không bị lặp chung/riêng. Finding một metric định vị chart riêng; nhiều metric định vị chart chung.

## Kiểm thử xác nhận

- 34 tests Python báo cáo/story; 16 tests Playwright báo cáo; build TypeScript/Vite thành công. Build còn cảnh báo kích thước Plotly chunk hiện có.
- 3 tests replay output API cuối, gồm thứ tự DOM chart trước diễn giải, số panel/paragraph, không tràn desktop và kiểm tra tuần ở 390px. Đây là replay output API thật trên dashboard scaffolding giả lập, không phải gọi API mới trong browser.
- Impeccable layout detector trước/sau: `[]`; không coi đây là bằng chứng chất lượng UX đầy đủ.
- Đã xem screenshot desktop chung/metric và hẹp; xem contact sheet đủ 16 trang PDF. Không đổi nhận diện/token/palette hoặc thiết kế mobile mới.

## API LLM thật — lượt cuối

Nguồn: [report-paired-confirmed.json](2026-10-06-report-paired-confirmed.json). Chạy trên bản sao DB bằng API đã cấu hình và quyền gửi facts đã được người dùng đồng ý; không gửi workbook trong nội dung. Mỗi ca gọi provider một lần.

| Ca | Nhóm kỳ | Provider/validation | Thời gian sinh | Points / anchors | Chart PDF-DOCX |
|---|---|---|---|---|---|
| Tổng quan 07–16/09 | Ngày | ready / accepted | 6.822s | 27 / 49 | 4 |
| Tổng quan 07–16/09 | Tuần | ready / accepted | 4.097s | 6 / 6 | 4 |
| Thống kê, tổng + TB/ngày | Tuần | ready / accepted | 5.536s | 32 / 43 | 3 |

67 points và 98 anchors không có mismatch; snapshot/charts/facts không đổi sau sinh AI. Cả sáu bản xuất PDF/DOCX HTTP 200, có năm phần, report identity và nhãn DRAFT. Tất cả fact IDs của diễn giải metric tồn tại trong snapshot.

Đánh giá output: tuần ngắn nêu tổng 1,847 → 1,286, chênh lệch -561; lỗi 104 → 76, -28; tỷ lệ 5.63% → 5.91%, +0.28 điểm phần trăm. Không thêm đỉnh/đáy từ hai điểm. Ca thống kê giữ khác biệt tổng lỗi giảm nhưng trung bình/ngày tăng (17.33 → 25.33) và cảnh báo số ngày có dữ liệu không bằng nhau; không suy thành chất lượng/hoạt động cải thiện chỉ từ tổng giảm. Ca ngày giữ các giai đoạn, mốc đỉnh/đáy và gap, không chỉ đầu–cuối.

Giới hạn: phần tổng quát vẫn có thể dài với nhiều giai đoạn; metric prose hiện là Engine, chưa phải diễn giải AI riêng. Kiểm thử này không chứng minh mọi lần LLM đều accepted: lượt đầu có một claim relative-change bị loại/thay bằng Engine. DOCX kiểm chứng cấu trúc/thứ tự/số ảnh, chưa có visual pagination trong Word. Không tự triển khai server hoặc đẩy Git.
