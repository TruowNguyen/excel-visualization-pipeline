# Đánh giá output API thật và tối ưu nội dung Report 1.3

## Phạm vi và phương pháp

Chạy API thật đã cấu hình, gửi facts/names/dates đã được người dùng đồng ý. Dùng bản sao DB, không sửa báo cáo sản xuất. Lượt trước: `2026-10-06-report-clarity-before.json`; lượt cuối: [report-clarity-confirmed.json](2026-10-06-report-clarity-confirmed.json). Phạm vi ngày, tuần, thống kê both, hai vấn đề chọn, nhóm theo tháng và nhóm theo quý. Không đổi prompt/validator hoặc code Analytics Engine.

## Vấn đề tìm được và đã sửa

- Phần chung lặp các giai đoạn sẽ kể lại trong metric prose. Phân vai theo section/candidate identity: chung giữ relations và calculation contrast; riêng giữ Engine stages. Không suy ra chủ sở hữu metric bằng từ khóa của lời AI.
- Ngày: general paragraphs **7 → 3**. Thống kê tuần: **7 → 4**, bao gồm thêm contrast tổng/TB-ngày ở vị trí đầu, không mất nhận định quan trọng.
- Metric prose trước là một đoạn dài. Nay tối đa hai stages/gaps mỗi đoạn, có subject cụ thể và mốc thời gian dễ tách; giữ mọi giai đoạn, khoảng thiếu, đỉnh/đáy. Chênh lệch dùng saved `period_change` khi có, không cộng/suy diễn số mới cho giai đoạn nhiều kỳ.
- Nhãn nguồn lặp mỗi đoạn: chỉ hiện khi đổi source/calculation; pending manual edits luôn hiện. Export giữ cùng thứ tự block IDs và source grouping như preview.
- Cảnh báo ngày **4 → 2**, tuần **4 → 2**, thống kê **5 → 2**. Gom theo exact warning và scope entity/metric/calculation; cảnh báo chỉ áp dụng một metric không bị mở rộng sang metric khác.
- Tóm tắt một vấn đề không lặp đầy đủ tên vấn đề mỗi đoạn. Thông báo chính dùng “số liệu đã kiểm chứng”, không đòi người dùng hiểu facts/Engine.
- Các đoạn giai đoạn không còn cần ở phần chính vẫn giữ nguyên trong snapshot và disclosure đọc/sửa; không lặp trong export. Manual blocks không bị ẩn khỏi phần chính.
- API thực phát hiện suffix `pp` khác canonical unit; đã chuẩn hóa thành “điểm phần trăm” một lần, có regression test.

## Kết quả lượt cuối

| Ca | Trạng thái kiểm chứng | Provider call / thời gian sinh | Points / anchors |
|---|---|---|---|
| VSO tổng quan ngày | partial; 1 claim thay bằng Engine | 1 / 7.196s | 27 / 49 |
| VSO tổng quan tuần | accepted | 1 / 3.991s | 6 / 6 |
| VSO thống kê tuần, both | accepted | 1 / 6.234s | 32 / 43 |
| VSO hai vấn đề chọn | accepted | 1 / 6.902s | 17 / 26 |
| V-Pet nhóm thống kê tháng | accepted | 1 / 5.948s | 20 / 26 |
| VW Vũ Yên nhóm thống kê quý | insufficient_data / not_run | 0 / 0.134s | 10 / 0 |

**112 points, 150 anchors, không mismatch**; snapshot/charts/facts giữ nguyên sau sinh AI. Fact IDs của mọi metric reading tồn tại trong snapshot. Cả 12 bản xuất PDF/DOCX HTTP 200, đủ năm phần, nhãn DRAFT và report identity; tổng 26 ảnh chart DOCX. Quý có một kỳ không gọi LLM và không suy thành xu hướng.

Claim `issue-0:insight-08-errors_fall_faster` bị loại với `unsupported_relative_change`. Không nới validator để làm đẹp kết quả. Phần này thay bằng Engine; báo cáo vẫn có số đúng và metric stages chứa các giá trị/chênh lệch hỗ trợ nhận định. Không mô tả cả năm ca LLM là accepted hoàn toàn.

## Đánh giá nội dung

Nhận định quan trọng được giữ: lỗi 22 không đổi nhưng tổng ghi nhận 657 → 420, tỷ lệ 3.35% → 5.24%. Tỷ lệ cao hơn ở đây không đồng nghĩa số lỗi tăng. Thống kê tuần giữ tổng lỗi 104 → 76 nhưng TB/ngày 17.33 → 25.33; số ngày có dữ liệu khác nhau, nên không kết luận hoạt động/chất lượng cải thiện chỉ từ tổng giảm. Tuần hai điểm giữ so sánh, không dùng đỉnh/đáy hay kết luận trend. Không gán quan hệ nhân quả nghiệp vụ hoặc tính correlation.

Độ dễ đọc đã cải thiện rõ về phân vai, paragraph length và repeated scaffolding. Vẫn còn giới hạn: LLM có thể lặp lời cảnh báo trong từng claim; metric prose là Engine, không phải AI riêng; chuỗi nhiều giai đoạn vẫn dài khi giữ đầy đủ thông tin. Hai cách tính cùng giữ nguyên 0 vẫn có hai đoạn vì đơn vị khác nhau. Unit nội bộ như `percent` còn xuất hiện trong trục/KPI. Chênh lệch tính từ số chưa làm tròn có thể lệch 0.01 so với phép trừ các con số đã làm tròn khi hiển thị. Không hứa tất cả output LLM sẽ accepted.

## Kiểm tra kỹ thuật và hình thức

- 37 Python report/story tests; 16 Playwright report regressions; 4 real-response replays (ngày, tuần, thống kê tuần, selected issues) pass. Replay dùng response API thật, dashboard scaffolding giả lập; không phải gọi provider trong browser.
- Build TypeScript/Vite pass; còn cảnh báo Plotly chunk lớn hiện có.
- Đã kiểm tra screenshot chung/metric/390px và render đủ 34 trang PDF bằng PyMuPDF contact sheets; không thấy text/chart crop. DOCX kiểm chứng structure/order/count, chưa visual pagination trong Word.
- Source labels và primary text không duplicate nguyên đoạn trong replay. Diễn giải bổ sung mặc định đóng và retained block IDs xuất hiện một lần.
- Impeccable clarify áp dụng trong nhận diện hiện có; type detector `[]` (một lệnh dùng scope không hợp lệ đã được sửa và chạy lại). Không đổi tokens/palette hoặc thiết kế mobile mới. Không push Git hay tự restart server.
