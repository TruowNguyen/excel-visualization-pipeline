# Đánh giá insight liên kết — 04/10/2026

## Kết luận

Đã triển khai đủ các hướng được duyệt: bổ sung liên hệ hai KPI cho Thống kê, chuyển comparisonBasis cho Tổng quan, ưu tiên insight có ý nghĩa trước chi tiết, đối chiếu tổng/trung bình mỗi ngày, giảm nội dung lặp và sửa các false rejection đã có regression test. Không thay công thức KPI, không tính correlation, không khẳng định nhân quả nghiệp vụ.

Output tốt hơn rõ nhất ở Thống kê tháng và nhóm đang chọn: người đọc thấy **tổng lỗi giảm nhưng lỗi trung bình/ngày tăng**, thay vì đọc hai bảng rồi tự ghép. Tổng quan theo ngày kể các giai đoạn, có đỉnh/đáy trong diễn giải và chênh lệch cụ thể. Chưa nên gọi đây là hoàn tất chất lượng production: validator vẫn có false rejection, chi tiết của nhiều vấn đề còn dài và LLM không diễn giải tất cả candidates trong mỗi request.

## Phiên bản và thay đổi

- Context prompt/policy: context-insight-v5.
- Synthesis policy: grounded-synthesis-v5.
- Validator: semantic-grounding-v9, dùng chung với legacy.
- Registry legacy trend-summary-v15 / metric-overview-v11 không đổi.
- Context/schema v1 không đổi; comparisonPromoted là cờ tùy chọn chống lặp hiển thị.
- Hai KPI chỉ được ghép khi periodStart/periodEnd trùng nhau và các kỳ liền nhau. Không bắc cầu qua missing. Tối đa hai nhịp đại diện.
- comparisonBasis lấy từ build_overview hiện có, không tự tạo numerator/denominator mới.
- calculation_contrast dùng mức và chênh lệch Engine riêng của sum và average_per_day; không trừ/cộng hai cách tính với nhau.
- Quan hệ được ưu tiên ở mở đầu. So sánh hai kỳ đã đưa lên trước không lặp lại thành phase; giữ facts, nguồn và chi tiết cách tính còn lại.
- Gom hạn chế dữ liệu một lần cho mỗi entity. Kỹ thuật distill từ skill impeccable giúp giảm khối lặp và ưu tiên thứ tự đọc trên desktop; không mở rộng thiết kế mobile.

## Vòng cuối với API thật

Provider cấu hình thực tế: **9Router / gemini-3.7-flash-tiered**. Đây là gọi thật bằng --live, không dùng mock. Mỗi ca tạo service riêng và gọi endpoint ứng dụng qua TestClient.

Bằng chứng đầy đủ, gồm raw narrative, kết quả đã kiểm chứng, provider input, facts/evidence và source checks:

- [14 ca context cuối](2026-10-04-linked-insight-confirmed.json)
- [2 ca legacy cuối](2026-10-04-linked-insight-legacy-confirmed.json)
- [Manifest phạm vi](2026-10-04-linked-insight-manifest.json)

| Ca | Phạm vi | Nhóm kỳ/cách tính | Kết quả validator | Claim nhận/tổng |
|---|---|---|---|---|
| 1 | VSO Tổng quan nhóm đang chọn | Ngày, 3 KPI | partial | 6/7 |
| 2 | VSO Thống kê nhóm đang chọn | Tuần, cả hai | accepted | 5/5 |
| 3 | VSO Thống kê nhóm đang chọn | Tháng, cả hai | accepted | 4/4 |
| 4 | SmartParking Thống kê nhóm đang chọn | Tuần, cả hai | accepted | 8/8 |
| 5 | VSO Thống kê 2 vấn đề được chọn | Ngày, cả hai | accepted | 6/6 |
| 6 | VSO Thống kê 2 vấn đề được chọn | Tuần, tổng | accepted | 8/8 |
| 7 | VSO Thống kê 2 vấn đề được chọn | Tháng, cả hai | accepted | 4/4 |
| 8 | V-Pet Thống kê tất cả vấn đề | Tuần, trung bình/ngày | partial | 7/8 |
| 9 | V-Pet Thống kê tất cả vấn đề | Tháng, cả hai | accepted | 8/8 |
| 10 | VSO Tổng quan 2 vấn đề được chọn | Ngày | accepted | 7/7 |
| 11 | VSO Tổng quan tất cả vấn đề con | Ngày | accepted | 8/8 |
| 12 | VW Vũ Yên Thống kê tất cả vấn đề | Quý, cả hai | insufficient_data / not_run | 0/0 |
| 13 | VSO Thống kê Số lỗi | Tuần, trung bình/ngày | accepted | 3/3 |
| 14 | VSO Thống kê Tổng số | Tuần, trung bình/ngày | accepted | 3/3 |
| Legacy all | VSO nhóm đang chọn, 3 KPI | Ngày | partial | 7/9 |
| Legacy error | VSO nhóm đang chọn, Số lỗi | Ngày | accepted | 5/5 |

Context: 13 lần gọi LLM, 11 accepted và 2 partial, nhận 77/79 claims. Ca quý có một kỳ không gọi model và không tạo xu hướng giả. Legacy: 2 lần gọi thật, nhận 12/14 claims. Không lấy tỷ lệ accepted làm tiêu chí duy nhất về chất lượng.

289 điểm context khớp biểu đồ, không mismatch. 100 mẫu aggregate provenance khớp nguồn và aggregation rule. Đây là lấy mẫu biên của mỗi chuỗi, **không phải kiểm toán mọi dòng Excel**. Unique factIds và membership requested/analyzed/excluded đúng ở cả 14 ca. Legacy lưu chuỗi và narrative để đối chiếu, không nằm trong số 289/100 này.

Thời gian request context có LLM: 5.501–41.865 giây, trung vị 11.747 giây. Provider ghi 3.708–9.014 giây; request gồm chuẩn bị dữ liệu và report. Vì vậy không thể quy toàn bộ chậm cho reasoning. Ca all nhiều vấn đề vẫn có độ trễ đáng chú ý; chưa có benchmark SLA production.

## Đánh giá nội dung theo định hướng sản phẩm

### 1. Thống kê nhóm đang chọn: insight thực sự hữu ích

Tháng 08 → 09:
- Tổng lỗi **441 → 299, giảm 142**.
- Lỗi trung bình/ngày **16.33 → 19.93, tăng 3.6**.
- Tổng số trung bình/ngày **147.11 → 255, tăng 107.89 (73.34%)**.
- Lỗi trung bình/ngày tăng **22.04%**.

Mở đầu giải thích rằng tổng giảm không đại diện cho mức ghi nhận mỗi ngày; các kỳ có số ngày ghi nhận khác nhau. Đây là câu chuyện khác hẳn “lỗi đã giảm”. Không tự suy ra tỷ lệ hoặc chất lượng từ hai KPI. Hai tháng chỉ được trình bày là so sánh, không gọi xu hướng và không thêm đỉnh/đáy vô nghĩa.

Tuần 37 → 38 cũng cho thấy lỗi tổng **104 → 76, -28**, nhưng trung bình/ngày **17.33 → 25.33, +8**. Chi tiết giữ diễn biến tăng ở những tuần đầu, giảm rồi tăng lại về cuối. Đánh giá: phần mở đầu đã đáp ứng tốt; phần chi tiết vẫn có thể rút gọn hơn.

### 2. Quan hệ giữa KPI: không chỉ đọc riêng từng số

SmartParking tuần 34 → 35:
- Tổng số trung bình/ngày **7,726.71 → 7,794.71, +68 (+0.88%)**.
- Lỗi trung bình/ngày **68 → 46, -22 (-32.35%)**.

Output giải thích hai chỉ số đổi chiều khác nhau, không dùng một chỉ số đại diện cho cả hai. Đây là liên hệ quan sát, không phải correlation và không chứng minh cải thiện chất lượng.

Tổng quan VSO: khi lỗi giữ **22**, Tổng số **657 → 420** và tỷ lệ **3.35% → 5.24%**, output legacy được chấp nhận giải thích “Tỷ lệ tăng không có nghĩa số lỗi tăng”. Đây là insight toán học có căn cứ, không suy diễn nguyên nhân vận hành.

### 3. Các vấn đề được chọn/tất cả vấn đề

Camera: lỗi đạt **17** rồi về **3**; nhịp cuối **11 → 3, -8 (-72.73%)**.
Đèn pha: **5 → 9, +4 (80%)**, sau đó **9 → 3, -6 (-66.67%)**.
Cây/lá: **4 → 22, +18 (450%)**, ngay sau đó **22 → 1, -21 (-95.45%)**.

Người đọc thấy vấn đề nào tăng đột biến và điều gì xảy ra sau đó. All phân tích đủ membership, nhưng mở đầu chỉ chọn 3/5 vấn đề có diễn biến và nói rõ các vấn đề còn lại ở chi tiết. Không cộng vấn đề thành tổng nhóm, không khẳng định chúng gây ra nhau. Một số vấn đề chỉ có Số lỗi hoặc chuỗi bị thiếu nên không đủ facts để giải thích quan hệ 3 KPI.

### 4. Giao diện và khả năng đọc

Đã replay output API đã ghi từ vòng verified trong browser, không gọi LLM khi chạy E2E. Ảnh tuần/tháng cho thấy tên nhóm bỏ 1.1, chữ/số không bị crop, tận dụng chiều rộng desktop và mức chênh lệch được nhấn mạnh. Không thêm heading đỉnh/đáy.

Month gọn hơn nhờ không lặp so sánh average ở detail. Week vẫn dài, một số nhãn nhóm và giới hạn dữ liệu xuất hiện nhiều lần ở các lớp tổng quan/chi tiết. Đây là phần còn cần tinh giản, không phải sai số liệu. Screenshots nằm ở .impeccable/review/linked-insight-week.png và linked-insight-month.png.

## Những câu còn bị loại và đánh giá thủ công

Vòng cuối có bốn false rejection đáng ghi nhận:

1. Context ca 1: “Do Số lỗi giảm nhanh hơn Tổng số, Tỷ lệ báo sai giảm…” đúng với 43→32, 214→209, 20.09%→15.31%, nhưng parser cause-first vẫn trả unsupported_meaning.
2. Context ca 8: Total 14.86→15, Error giữ 0. Câu kết “chưa có căn cứ đánh giá chất lượng” là phủ định suy diễn, nhưng business-word guard vẫn loại unsupported_meaning.
3. Legacy all: Error16→8, Total71→454, tỷ lệ22.54%→1.76%; câu dùng “quy mô tăng” bị direction_conflict dù mô tả đúng.
4. Legacy all: “giảm với tốc độ nhanh hơn mức giảm của Tổng số” đúng quan hệ tỷ lệ, nhưng là một biến thể parser chưa hỗ trợ.

Không nới bỏ kiểm tra số/ngày/đơn vị/phạm vi để nhận các câu trên. Các claim còn lại giữ được; đoạn bị loại hoặc chưa được model viết dùng deterministic facts và gắn nguồn tương ứng. **Không phải toàn bộ bản phân tích hiển thị đều do LLM viết.**

Các vòng trước cũng phát hiện: nhầm date của peak với giá trị giữa chuỗi đã sửa kèm test; nhiều ngày đạt cùng đỉnh trong một câu phức còn có thể bị parse sai. Output khi model dùng chủ ngữ ghép “Số lỗi và Tỷ lệ…” cho cùng một cặp số thực sự sai phải bị chặn, không coi đó là lỗi validator.

## Kiểm thử và giới hạn nghiệm thu

- Backend: **353 tests**, toàn bộ qua sau sửa production cuối.
- Frontend: **90 E2E**, toàn bộ qua; build/TypeScript thành công.
- Vòng UI đầu: 87/88 qua, một timeout click do phần tử bị detached khi đang có thay đổi/reload. Vòng xác nhận cuối không thay production UI trong lúc chạy: 90/90 qua. Không sửa test bằng force-click để che lỗi.
- Regression kiểm tra: hai KPI không giả tỷ lệ, không vượt gap/phạm vi; zero movement; comparisonBasis; chênh lệch đúng calculation; câu nguyên nhân toán học có giới hạn; sai ngày/sai chiều/nhân quả nghiệp vụ vẫn bị từ chối.
- Build còn cảnh báo Plotly bundle lớn; pytest có FastAPI/Python deprecation warning, không gây fail.

Còn hạn chế: parser chưa bao quát tiếng Việt; quota tối đa 8 đoạn giữ nhiều phần Engine, nhất là selected/all; chi tiết có chuỗi thiếu còn dễ dài như bảng kể số; dữ liệu lũy kế vẫn giữ phép tính Thống kê hiện có và không được diễn giải tổng là số phát sinh mới. Ngày/tuần/tháng được chạy thật; quý kiểm chứng nhánh thiếu dữ liệu thật chứ chưa có ca nhiều quý để nghiệm thu narrative. Không dự báo, không anomaly thống kê hoặc suy ra nguyên nhân nghiệp vụ.

Ưu tiên tiếp nếu tiếp tục tối ưu: kiểm chứng negation/causal-role có cấu trúc thay vì danh sách từ, giảm chi tiết Engine cho sparse series, benchmark phần chuẩn bị context/provenance ở scope all. Không nên chỉ nới validator để tăng accepted hoặc tăng quota LLM mặc định mà chưa đo chất lượng/độ trễ.
