# Kiểm tra AI Insight trên toàn bộ dữ liệu và bộ lọc

Ngày: 02/10/2026. Runtime: narrative/provider v5, semantic-grounding-v6, trend-summary-v15 / metric-overview-v11; resource grounded-insight-v5.md. Không thay phép tính KPI, giao diện hay phạm vi mobile.

## Kết luận

Analytics Engine vốn hỗ trợ ngày/tuần/tháng. Lỗi nằm ở diễn giải và kiểm chứng: parser còn giả định ngày, nhận nhầm tháng/năm thành số, gắn sai ngày cho cực trị; lựa chọn giai đoạn có thể bỏ phần cuối hoặc điểm rời. Đã sửa các lỗi này và kiểm tra toàn bộ entity có dữ liệu committed. Chưa thể coi chất lượng diễn giải là hoàn thiện: output vẫn nhiều số, có câu đúng bị validator loại và có giai đoạn được chấp nhận nhưng tóm tắt chưa đầy đủ thứ tự tăng/giảm.

## Thay đổi

- Provider nhận start/end/groupBy và nhãn kỳ thật. Tuần/tháng là giá trị tổng hợp của kỳ, không phải giá trị tại ngày bắt đầu kỳ. Hai kỳ chỉ so sánh, không gọi là xu hướng.
- Grounding xử lý nhãn tháng/năm, khoảng tuần, kỳ bị cắt bởi bộ lọc, nhiều ngày đồng mức cực trị và KPI đơn. Không thay nguồn, đơn vị, missing/zero hoặc quy tắc tỷ lệ.
- KPI có nhiều kỳ hợp lệ nhất làm trục chia giai đoạn. Điểm rời và dữ liệu KPI phụ không bị mất, nhưng không nối qua khoảng thiếu để suy ra xu hướng chung.
- Report giữ mọi giai đoạn. Tối đa tám giai đoạn gửi LLM, ưu tiên đầu/cuối và các mốc cực trị; giai đoạn còn lại được diễn giải bằng facts Engine. Đỉnh/đáy nằm trong giai đoạn, không thêm heading riêng.
- Sửa lỗi HTTP 422 thật ở V-Pet video: đơn vị nguồn bị NaN, không thể serialize JSON; nay trả null, không tự đặt đơn vị.
- Các sửa parser cuối có hồi quy: không nhầm tỷ lệ thiếu kỳ dạng 25/47 thành ngày; không gắn giá trị sau đảo chiều vào ngày cực trị vừa nhắc; cho phép giải thích khoảng trống bằng thiếu kỳ nếu quality facts xác nhận. Không mở quyền suy diễn nguyên nhân KPI.

## Phạm vi và kết quả

Nguồn hiện tại có 4.443 dòng, sáu dự án, 34 entity có dữ liệu trực tiếp. Hai node cấu trúc không có dữ liệu riêng không được tự động cộng các node con.

| Lớp kiểm tra | Phạm vi | Kết quả |
|---|---|---|
| Ma trận Engine/report/grounding offline | 34 entity × 3 nhóm kỳ × 4 selector × 5 cửa sổ | 2.040/2.040 đạt |
| Python sau sửa parser cuối | Toàn bộ suite, gồm hồi quy khác ngày/khác năm | 308 đạt |
| Playwright AI Insight | Tương tác/giao diện hiện có | 21 đạt |
| API ứng dụng với LLM thật | 64 request: mọi entity theo ngày; tuần/tháng mỗi dự án; đủ chín tổ hợp KPI đơn × nhóm kỳ | 30 accepted, 32 partial, 2 không đủ dữ liệu |
| Replay response thật sau sửa parser cuối | 62 response đã lưu, không gọi provider | 37 accepted, 25 partial, 0 bị loại toàn bộ |
| API thật lần cuối sau sửa code | Sáu ca đại diện, năm response provider | 2 accepted, 3 partial, 1 không đủ dữ liệu |

Năm cửa sổ offline: toàn bộ dữ liệu, mười ngày cuối, khoảng cắt hai đầu, một ngày, khoảng rỗng. Ma trận chạy trước ba sửa parser cuối; không giả nhận đây là lần chạy lại toàn ma trận sau các sửa đó. Suite Python, replay và API mới kiểm tra phiên bản cuối.

Đợt 64 request có 62 response provider thật, 314 paragraph AI và 73 paragraph Engine; không có provider_unavailable hoặc report bị loại toàn bộ. Một HTTP 422 được phát hiện, sửa rồi gọi API lại; artifact giữ receipt lỗi và kết quả retry. Độ trễ request: trung vị 6.475 ms, p95 13.322 ms, lớn nhất 22.062 ms; gồm xử lý ứng dụng, provider và kiểm chứng, không phải thời gian reasoning riêng.

Lần API cuối:

| Dữ liệu / bộ lọc | Kiểm chứng | Độ trễ |
|---|---|---|
| VSO chất lượng cảnh báo, ngày, ba KPI, 01/08–16/09 | partial: overview và cả tám giai đoạn AI được giữ; ba quan hệ dùng Engine | 11.666 ms |
| SmartParking, tuần, total, 04/08–14/09 | accepted | 4.849 ms |
| V-Pet video, ngày, ba KPI | partial: một giai đoạn dùng Engine | 7.934 ms |
| VOL cổng AC, tháng, error, khoảng bị cắt | insufficient_data: không gọi LLM | 513 ms |
| ANVF điểm danh xe ghép, ngày, total | partial: overview dùng Engine; tám giai đoạn AI được giữ | 5.971 ms |
| VW Vũ Yên, tuần, error_rate | accepted | 4.521 ms |

## Đọc và đánh giá output thật

1. **Không phụ thuộc ví dụ theo ngày cũ.** VSO với cửa sổ 01/08–16/09 nhận đúng số lỗi cao nhất 43 ngày 13/09, thấp nhất 4 ngày 27/08. ANVF có total cao nhất 2.250 ở cả 10/09 và 11/09, thấp nhất 1.066 ngày 15/08. Các mốc được đưa vào giai đoạn liên quan, không thành heading riêng.
2. **Tuần bị cắt cần giải thích kỹ hơn.** SmartParking có kỳ cuối chỉ gồm ngày 14/09, trong khi kỳ trước đủ bảy ngày. Các tổng là đúng, nhưng câu “giảm mạnh ở kỳ cuối” dễ khiến người đọc hiểu là hoạt động giảm. Warning kỳ không đủ vẫn chưa thay thế được diễn giải trực tiếp sự khác biệt thời lượng. Không được suy ra suy giảm kinh doanh từ phép so sánh tổng này.
3. **Validator vẫn còn bảo thủ về cách viết.** V-Pet có câu đặt số trước tên KPI; ANVF nhắc “tháng 8/tháng 9” không có năm. Số nguồn đúng nhưng parser chưa nhận đủ liên kết nên dùng fallback. VSO có quan hệ tỷ trọng phù hợp facts nhưng cách dùng “do/khiến” vượt grammar nhân quả hiện tại. Không nên nới bỏ source/metric/date gates để giải quyết bằng tỷ lệ accepted.
4. **Accepted không bảo đảm câu chuyện đúng thứ tự.** Một đoạn VSO 10–15/08 nén thành “tăng từ 16 lên 21 rồi giảm 18”, trong khi chuỗi thực là 16 → 12 → 11 → 17 → 21 → 18. Các giá trị có thật nhưng câu bỏ mất nhịp giảm đầu đoạn. Kiểm chứng hiện tại chưa chứng minh đầy đủ thứ tự từng chặng của câu tổng hợp.
5. **Insight chưa đủ cô đọng.** Nhiều giai đoạn vẫn lặp ba KPI và nhiều con số; quan hệ fallback còn lặp template. Cần tiếp tục ưu tiên diễn biến đáng chú ý, ý nghĩa quan hệ số lỗi–total–tỷ lệ và giải thích kỳ không đủ, thay vì chỉ tăng số câu được chấp nhận. Không sử dụng correlation hoặc khẳng định nguyên nhân nghiệp vụ từ ba KPI.

Vì vậy: hỗ trợ bộ lọc và độ phủ report đã được cải thiện; chưa kết luận rằng mọi output đều hữu ích hoặc mọi câu accepted đều diễn giải đầy đủ. Đây là đánh giá thủ công trên output thật kết hợp kiểm thử xác định, không phải điểm chất lượng do validator tự chấm.

## Bằng chứng và tái lập

- [Receipt 64 request API và raw narrative](2026-10-02-all-data-filter-evaluation.json).
- [Ma trận, replay và sáu request API cuối](2026-10-02-all-data-filter-final-checks.json). Replay được đánh dấu riêng, không cộng thành lần gọi provider.
- Scripts: scripts/evaluate_ai_filter_matrix.py; scripts/evaluate_ai_runtime.py (--live, --group-by, --metric); scripts/replay_ai_evaluation.py. Live dùng provider cấu hình hiện có, không chuyển model; không lưu credentials hoặc file Excel thô trong evidence.
- Offline xác minh fact closure/report coverage, không phải kiểm toán độc lập công thức aggregation. Node-only không suy ra subtree rollup. Live là mẫu đại diện bộ lọc và mọi entity theo ngày, không phải gọi LLM cho cả 2.040 tổ hợp.

Phương pháp tách kiểm thử xác định, edge cases và đánh giá diễn giải theo [hướng dẫn evaluation chính thức](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
