# Định lượng diễn giải AI Insight — 04/10/2026

## Đánh giá và thay đổi

V2 kể được cấu trúc chuỗi nhưng prompt yêu cầu overview không cần số; report candidates chủ yếu dẫn period values và extrema, không dẫn đủ period_change facts. Người đọc thấy tăng/giảm nhưng khó biết quy mô. Đây là vấn đề cấp dữ liệu diễn giải và prompt, không phải thiếu công thức KPI core.

V3 bổ sung quantitativeEvidence vào overview/phase: tối đa một nhịp tăng và một nhịp giảm đáng chú ý của một metric biến động, chọn theo độ lớn chênh lệch trong chính metric đó. Có kỳ trước/sau, display mức trước/sau, chênh lệch có dấu, unit, relativeDisplay nullable và các factIds nguồn. Không tính lại chênh lệch; không nối qua gap; không dùng delta giữa hai kỳ làm mức thay đổi cả giai đoạn. Ưu tiên số lỗi biến động rồi metric khác; không xếp độ lớn giữa unit khác nhau.

Prompt `context-insight-v3.md` yêu cầu lồng định lượng vào nhận định, không tạo heading bằng chứng mới; không đọc mọi cặp ngày. Overview kể câu chuyện trước, dùng nhịp tiêu biểu; phase giải thích một nhịp trong giai đoạn. Engine fallback phase cũng có một nhịp định lượng khi đủ dữ liệu. Không sửa frontend hoặc công thức KPI. Registry legacy prompt vẫn giữ nguyên; report builder và semantic validator dùng chung có thay đổi.

Semantic v8 phân biệt explicit “chênh lệch” với giá trị tại ngày, yêu cầu số đó có period_change fact phù hợp metric/unit; không gán mức sau cho ngày đứng trước từ “đến”. Nhận diện thêm “chưa đủ kết luận/xác lập xu hướng”. Đây là parser giới hạn, không chứng nhận mọi phát biểu tự do hoặc mọi cách gán delta vào giai đoạn.

## Kiểm thử API thật và đối chiếu

Chạy lại cùng 14 ca đại diện trên 6 dự án: node/selected/all, ngày/tuần/tháng/quý, sum/average/both, recent/all/custom, includeIncomplete. Adapter/provider thật qua endpoint FastAPI TestClient, không mock/replay. Cấu hình provider không thay.

- [Baseline v2](2026-10-04-context-quality-final.json).
- [Lượt định lượng đầu](2026-10-04-context-quantified-final.json): phát hiện date parser hiểu nhầm chênh lệch/mức sau; đây **không phải kết quả nghiệm thu cuối**, dù tên artifact có “final”.
- [Lượt kiểm chứng cuối sau sửa parser](2026-10-04-context-quantified-verified.json): rawNarrative, providerInput, report và sourceChecks để đọc lại.

| Chỉ tiêu | V2 | V3 lượt kiểm chứng cuối |
|---|---:|---:|
| Request ứng dụng | 14 | 14 |
| Gọi LLM thật | 13 | 13 |
| Accepted / partial | 10 / 3 | 6 / 7 |
| Claims giữ / trả về | 75 / 80 | 67 / 76 |
| Paragraph overview có cụm “chênh lệch” / tổng | 0 / 33 | 18 / 33 |
| Canonical period points đối chiếu | 313 | 313 |
| Lấy mẫu aggregate provenance | 94 | 94 |

Cả hai lượt không có canonical/source mismatch. Một ca quý chỉ có một kỳ nên không gọi LLM. Tất cả 13 ca có LLM cuối trả ready; các đoạn bị loại dùng Engine fallback. Độ trễ request lớn nhất lượt cuối 15.954 giây; không tuyên bố tăng tốc. 18/33 là đếm cụm từ trong overview, bao gồm paragraph cảnh báo/basis; không phải điểm chất lượng chuyên gia. Acceptance giảm khi tăng lượng số và cấu trúc câu cần kiểm chứng; không che giấu điều này hoặc dùng acceptance làm thước đo duy nhất.

## Đọc output cuối

- VSO 3 KPI: overview AI nêu nhịp số lỗi 19→43, chênh lệch +24 (+126.32%) ngày 12–13/09; sau đó 43→32, -11 (-25.58%) ở ngày 14/09. Insight có quy mô đối chiếu được, không chỉ nói tăng/giảm. Câu cuối vẫn có thể cô đọng hơn và tránh “tăng mạnh”.
- Selected hai vấn đề: Camera có mức tăng 11→17 (+6; +54.55%) và nhịp giảm 11→3 (-72.73%) với đúng kỳ. Overview Đèn pha bị loại do model nhắc ngày thiếu ngoài anchors nên Engine thay thế; phase vẫn có số đối chiếu. Định lượng chưa phủ đều mọi headline.
- SmartParking tuần/both: overview average nêu lỗi 38.5→68, +29.5 Lượt/ngày (+76.62%), rồi 68→46, -22 (-32.35%) tại đúng hai cặp tuần. Sum vẫn riêng, cảnh báo số ngày khác nhau giữ nguyên. Một phase bị date parser loại.
- V-Pet tháng/both: Cư dân average 12.82→15.33, +2.51 (+19.59%); Cảnh báo average 48.08→75.8, +27.72 (+57.65%). Sum detail nói 359→230, -129 (-35.93%) và nêu số ngày khác nhau. Playback overview vẫn Engine vì model viết phủ định xu hướng ngoài grammar; không diễn giải sum decrease như hoạt động giảm.

Mức đã đạt: người đọc có thể thấy nhận định, nhãn kỳ và độ lớn thay đổi ngay trong nhiều đoạn chính, không cần tự trừ số. Nội dung vẫn giải thích chuỗi và đỉnh/đáy bên trong giai đoạn, không tạo bảng chênh lệch từng ngày.

Giới hạn: 9 claims bị loại; date binding phức tạp, chủ ngữ ghép, số trong ngoặc và câu phủ định trend vẫn có false rejection. Một số paragraph lặp nhịp giữa overview/phase; model còn dùng “tăng mạnh/tăng vọt”. Tổng quan fallback chưa luôn có delta. Không có phép tính deterministic mức giảm cả giai đoạn nhiều kỳ mới: nhịp định lượng chỉ là cặp kỳ được ghi rõ. Không có correlation/causality hoặc score mức nghiêm trọng nghiệp vụ. Grounding bằng parser không xác minh toàn bộ diễn giải tự do; source checks không audit độc lập mọi ô Excel.

## Hồi quy

Full Python suite: **342 tests pass**, 19 deprecation warnings. Bộ ngày/tuần/tháng và report/semantic/context pass; regression mới kiểm tra metadata và fact dependencies, zero-base không có relative %, không qua gaps, số chênh lệch bịa và số kỳ bị dùng sai vai trò. Assertion bổ sung chạy riêng cũng pass. `git diff --check` pass (chỉ cảnh báo chuẩn hóa LF/CRLF của Windows). Không chạy browser screenshot mới, không thay layout, không commit/push.

Không sửa production code sau lượt API thật kiểm chứng cuối; chỉ thêm assertion kiểm thử và cập nhật tài liệu.
