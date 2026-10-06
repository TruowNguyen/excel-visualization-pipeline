# Đồng nhất AI Insight giữa các phạm vi — 04/10/2026

## Kết luận

Đã chạy lại API LLM thật và đọc output gốc lẫn report sau validation. Thống kê trong nhóm vấn đề đã chọn dùng cùng cấu trúc diễn giải với node và tất cả vấn đề: tổng quan → liên hệ có căn cứ → diễn biến của từng vấn đề/cách tính → số liệu và nguồn thu gọn. Mỗi vấn đề chỉ có một disclosure, không nhân đôi vấn đề khi chọn Tổng và trung bình/ngày.

Impeccable được dùng để giữ thứ tự đọc, nhóm thông tin theo vấn đề thay vì calculation và thống nhất nhãn giai đoạn với Tổng quan; giữ nhận diện, highlight và chiều rộng desktop hiện có. Không thiết kế lại mobile, thay công thức KPI hoặc nới validator trong đợt này.

## Nguyên nhân và thay đổi

- API report cố ý giữ từng entity/calculation độc lập. Renderer trước đây coi mỗi variant là một vấn đề, nên both tạo hai khối có cùng tên, đồng thời một vấn đề bị hiển thị như nhiều vấn đề. Nay nhóm bằng entityRef, bên trong tách Trung bình/ngày trước Tổng trong kỳ; dữ liệu, evidence và hành động mở nguồn vẫn độc lập.
- Context phase trước đây chỉ có đoạn văn, trong khi Tổng quan legacy có nhãn kỳ riêng. Nay dùng chung `renderInsightPhase` và `renderInsightParagraph`; một kỳ không thêm mũi tên trùng nhãn, nội dung/nhãn đều escape trước khi hiển thị. Không ép nội dung Statistics phải có tỷ lệ như Overview.
- Tên metric Statistics trước đây chứa ` · Tổng trong kỳ` hoặc ` · Trung bình/ngày`, làm prompt và fallback lặp nhãn. Tên sum nay giữ tên KPI, average giữ hậu tố `trung bình/ngày`; calculation/unit/schema/fact namespace không đổi.
- Prompt mới `context-insight-v4.md` thống nhất tên chủ ngữ, quantitative anchor, cách viết chênh lệch, ranh giới kỳ và lời giới hạn. Sau lượt thử đầu, thêm few-shot cho ba kỳ, hai tháng và số ngày ghi nhận khác nhau; không dùng nhãn tháng cho candidate theo ngày, không nối lời giải thích bằng “do”, dùng câu ngắn “Hai kỳ chỉ đủ so sánh”.

## Chạy API thật

Provider cấu hình hiện tại: 9Router, `gemini-3.7-flash-tiered`. Request qua endpoint ứng dụng bằng FastAPI TestClient và adapter thật, không mock generation. Bộ manifest chứa 10 ca; mỗi lượt có 9 request LLM thật và một ca quý chỉ có một kỳ nên chủ động không gọi LLM.

| Ca | Phạm vi | Bộ lọc | Trước | Xác nhận cuối |
|---|---|---|---|---|
| 1 | VSO, Thống kê, 2 vấn đề đã chọn | Ngày, both, 07–16/09 | partial | accepted |
| 2 | VSO, Thống kê, 2 vấn đề đã chọn | Tuần, sum, all | partial | accepted |
| 3 | VSO, Thống kê, 2 vấn đề đã chọn | Tháng, both, all | accepted | accepted |
| 4 | SmartParking, Thống kê, node | Tuần, both, all | accepted | accepted |
| 5 | V-Pet, Thống kê, tất cả vấn đề | Tuần, average, all | partial | accepted |
| 6 | V-Pet, Thống kê, tất cả vấn đề | Tháng, both, all | accepted | accepted |
| 7 | VSO, Tổng quan, 2 vấn đề đã chọn | Ngày, all metrics | accepted | accepted |
| 8 | VSO, Tổng quan, node nhóm | Ngày, all metrics | accepted | accepted |
| 9 | VSO, Tổng quan, tất cả vấn đề | Ngày, all metrics | accepted | accepted |
| 10 | VW Vũ Yên, Thống kê, tất cả vấn đề | Quý, both, all | not_run | not_run |

- Baseline: 6 accepted, 3 partial, 1 not_run; 54/61 claim được giữ.
- Lượt sửa đầu: 5 accepted, 4 partial, 1 not_run; 59/66 claim được giữ. Không coi lượt này là cải thiện hoàn tất: còn nhãn tháng ngoài anchors và cách phủ định xu hướng bị hiểu sai.
- Xác nhận sau few-shot: 9 accepted, 1 not_run; 67/67 claim được giữ, không lỗi validation. Đây là kết quả một lượt thực nghiệm, không bảo đảm mọi lần generation đều accepted.
- 233 điểm được so với chart computation, 80 aggregate boundary source checks: không phát hiện mismatch. Đây là lấy mẫu nguồn ở đầu/cuối chuỗi, không audit mọi contributor.
- Tất cả requested member được ghi nhận là analyzed hoặc excluded; không trùng fact ID. Average/sum được so độc lập với canonical prepared statistics.
- Request latency ở 9 ca cuối: 5,405–14,465 ms; trung bình 8,194 ms. Thời gian đo endpoint bao gồm generation và kiểm chứng trong ứng dụng, không bao gồm các source checks chạy sau response; không phải SLA. Chưa thêm cache hoặc background job.

Chạy thêm API legacy `/ai/trend-summary` cho VSO node/all metrics để kiểm tra đường Tổng quan cũ: ready/partial, 8/9 claim được giữ. Một đoạn quan hệ bị loại `unsupported_meaning`, fallback từ Engine vẫn còn; prompt legacy metric-overview-v11 không đổi. Không gộp ca legacy này vào tỷ lệ accepted của context.

## Đọc và đánh giá output cuối

### Thống kê đã chọn — ngày

Camera giảm ở đầu chuỗi, tăng lên mức cao nhất rồi giảm cuối chuỗi; overview nêu nhịp 11 → 17, chênh lệch 6 (54.55%), và 11 → 3, chênh lệch -8 (-72.73%). Đèn pha tăng 5 → 9, chênh lệch 4 (80%), rồi giảm 9 → 3, chênh lệch -6 (-66.67%). Các nhịp được gắn đúng ngày, không gọi endpoint là toàn bộ diễn biến; thiếu kỳ vẫn được nêu. Đỉnh/đáy nằm trong các phase, không thêm heading riêng.

### Thống kê đã chọn — tháng/both

Output Camera phân biệt:

- Trung bình/ngày: 4.96 → 6.87, chênh lệch 1.9 (38.36%).
- Tổng trong kỳ: 134 → 103, chênh lệch -31 (-23.13%).

Đèn pha: trung bình/ngày 2.22 → 3.07, chênh lệch 0.84 (38%); tổng 60 → 46, chênh lệch -14 (-23.33%). Tổng quan ưu tiên average, giải thích các kỳ khác số ngày ghi nhận. Hai tháng chỉ là so sánh; không thể suy ra mức lỗi mỗi ngày giảm từ tổng giảm. Delta sao chép từ Engine tính trên giá trị chưa làm tròn, nên không tự trừ lại hai displayValue đã làm tròn.

### Phạm vi riêng và tất cả

SmartParking có average lỗi 38.5 → 68, chênh lệch 29.5 (76.62%), rồi 68 → 46, chênh lệch -22 (-32.35%). Các đoạn đơn lẻ do thiếu dữ liệu được giữ riêng, không nối thành chuỗi giả. V-Pet tháng giải thích trung bình/ngày của hai vấn đề tăng nhưng vấn đề playback giảm; không cộng chúng thành tổng nhóm. VSO toàn bộ chỉ ưu tiên ba trong năm vấn đề có diễn biến ở overview, đồng thời ghi rõ giới hạn và giữ tất cả chi tiết.

### Những điểm chưa hoàn hảo

- Accepted là vượt kiểm chứng, không đồng nghĩa hoàn hảo về văn phong. VSO all vẫn có từ “giảm mạnh”; SmartParking vẫn có “tăng nhẹ” dù prompt yêu cầu ưu tiên số liệu. Không sửa số hoặc phủ nhận đoạn đúng chỉ vì cách nhấn mạnh này.
- Một số phase còn lặp nhịp đã có trong overview hoặc lặp câu “Hai kỳ chỉ đủ so sánh”; cả hai calculation theo ngày có thể cho số giống nhau. UI đã nhóm chúng theo vấn đề nhưng không tự xóa calculation người dùng yêu cầu.
- Liên hệ giữa các vấn đề vẫn là tổng hợp deterministic cùng/trái chiều và lệch mốc, chưa phải LLM suy luận nghiệp vụ sâu hoặc nhân quả. Thống kê không tự sinh tỷ lệ/correlation.
- Budget tối đa tám đoạn LLM khiến một phần chi tiết dùng Engine. Template chung vẫn giữ được, nhưng chất lượng văn phong giữa phần AI và Engine chưa tuyệt đối đồng nhất.
- Dữ liệu thực chỉ có một quý: chưa thể đánh giá xu hướng nhiều quý bằng LLM thật. Ca quý trả insufficient_data, không giả lập một cuộc gọi thật.

## Kiểm thử và bằng chứng

- Python: 342 test pass; cảnh báo deprecation FastAPI đã có.
- Frontend: 43 test AI/layout trong lượt kiểm tra đầu, sau đó toàn bộ 86 test pass trong lượt xác nhận. Ba hồi quy mới kiểm tra both ở node/selected/all: một khối mỗi vấn đề, hai calculation đúng thứ tự, bảng nguồn mở riêng.
- Build frontend pass; cảnh báo chunk Plotly lớn đã có. Không thay production UI sau build/kiểm tra giao diện; lượt cuối chỉ bổ sung few-shot backend và chạy API thật.
- Đã xem ảnh `context-template-both-selected.png`; ảnh node/selected/all do API mô phỏng, không phải ảnh chứng minh generation thật. Các test đọc ở 1280/1440/1920 dùng evidence live đã lưu từ lượt trước. Kiểm chứng output mới nằm trong JSON endpoint bên dưới; không tuyên bố browser end-to-end với provider thật.
- Không commit/push trong yêu cầu này.

Artifacts:

- [Manifest](2026-10-04-template-scope-manifest.json).
- [Baseline thật](2026-10-04-template-scope-before.json).
- [Lượt sửa đầu](2026-10-04-template-scope-after.json).
- [Xác nhận cuối bằng API thật](2026-10-04-template-scope-final.json): rawNarrative, provider input, report, facts/evidence và source checks.
- [Smoke legacy Tổng quan thật](2026-10-04-template-legacy-live.json).
