# Diễn giải theo giai đoạn, lồng đỉnh/đáy — 02/10/2026

## Kết quả triển khai

Report mới có overview, phases và relationships; không tạo heading hoặc claim extrema riêng. Mỗi phase nhận `semanticSpec.phaseExtrema` từ periodAnalytics của Engine, gồm KPI, vai trò, giá trị và các ngày đồng mức nằm trong phase. Phạm vi cực trị là các kỳ có dữ liệu trong thời gian được chọn, không phải lịch sử hoặc riêng hai đầu phase. Không thêm phép tính KPI, correlation, suy đoán chất lượng hay nguyên nhân nghiệp vụ. Với ít hơn bốn kỳ hợp lệ hoặc chuỗi không đổi, không tạo extrema.

Đỉnh ở ranh giới hai phase có thể được nhắc lại để nối câu chuyện tăng → giảm. Không lặp thành bảng extrema riêng. Fallback giữ mô tả phase và mốc Engine khi AI thiếu/bị loại, ghi nguồn deterministic; UI không trình bày fallback như lời AI. Hiển thị bốn phase trước, các phase tiếp theo ở disclosure, planning giới hạn tám phase và bốn quan hệ.

Registry: trend-summary-v14 / metric-overview-v10; resource grounded-insight-v5.md; provider/narrative v5; semantic-grounding-v5. Token budget report riêng mặc định 2400, tối đa 3000 (`EVP_AI_REPORT_MAX_OUTPUT_TOKENS`); timeout/retry/privacy gates không đổi. Cấu trúc public overview/trend envelope không thay thế; `narrative.report` là bổ sung, snapshot cũ vẫn đọc được.

## Validator

Giữ kiểm tra số, đơn vị, KPI, kỳ và phạm vi, hướng chuyển động và citations. Phase có thể nêu một cực trị đã được chứng minh bằng ít hơn bốn điểm trong phase nếu cửa sổ chọn có ít nhất bốn kỳ hợp lệ; điều này không cho phép gọi hai điểm là xu hướng. Kiểm tra từng ngày đồng mức, kể cả ngày thứ hai nối bằng “và”. Không gán ngày đỉnh cho bước giảm tiếp theo; giá trị ở bước tăng/giảm giữa phase không bị bắt buộc phải là điểm cuối phase. Có regression tests cho hai lỗi loại nhầm phát hiện qua API thật.

## Kiểm thử thực tế

[Bản ghi API thật](2026-10-02-phase-extrema-report.json), provider 9Router, response model gemini-3.7-flash-tiered, dữ liệu VSO committed. Không lưu credential, raw Excel hoặc lineage target. Không đổi model.

- 07–16/09: lần cuối sau các sửa prompt/validator, ready/accepted, 9/9 đoạn nhận, request 9862 ms. Có một overview, bốn phase và bốn quan hệ. Không có extrema section, không mất phase. Đáy số lỗi 8 ở 08/09 và 10/09, đỉnh 43 ở 13/09; Tổng số thấp nhất 71 ở 07/09, cao nhất 657 ở 15/09; tỷ lệ cao nhất 22.54% ở 07/09, thấp nhất 1.76% ở 08/09. Đầu ra đối chiếu đúng facts và ngày đã ghi.
- 12–13/09: ready/accepted, 5579 ms; Tổng số giảm, số lỗi và tỷ lệ tăng. Không gọi là trend, không tạo extrema. Call dùng revision prompt ngay trước lần cuối, không phải cùng revision tuyệt đối.
- 15–16/09: ready/accepted, 6350 ms; số lỗi 22 không đổi, Tổng số 657→420, tỷ lệ 3.35%→5.24%. Nêu tỷ lệ tăng không có nghĩa thêm lỗi. Có warning wording `relation_not_expressed` nhưng số/chiều đúng. Call dùng revision prompt ngay trước lần cuối.

Các lần đầu có partial: model nêu ngày thiếu không có trong cited facts, bỏ mốc hoặc dùng câu nguyên nhân, và validator gán nhầm giá trị giữa đoạn. Các lỗi không được giấu bằng nới source gates; prompt được làm rõ, hai lỗi parsing có regression riêng. Một mẫu accepted không chứng minh mọi lần gọi đều accepted.

## Đánh giá theo yêu cầu

Đạt: không dùng đầu–cuối thay câu chuyện; nhìn thấy giảm/dao động → tăng lên đỉnh → giảm liên tiếp → giữ nguyên; có ngày đồng đáy; đỉnh/đáy nằm trong giai đoạn; giải thích số lỗi khác tỷ lệ ở cuối chuỗi; kỳ thiếu không thành 0.

Chưa hoàn thiện: overview vẫn có từ chung chung “biến động đa chiều”; phase đầu dành nhiều câu cho extrema hơn diễn biến Tổng số; phần quan hệ đôi lúc lặp số của phase; model vẫn dùng “tỷ trọng”, UI chuyển sang từ dễ hiểu nhưng chưa đảm bảo văn phong tự nhiên mọi trường hợp. Warning “mạnh/nhẹ” chưa có ngưỡng đánh giá định lượng. Semantic parser vẫn có giới hạn, không phải bộ chứng minh ngôn ngữ tổng quát. Không kết luận đã xác định nguyên nhân chất lượng hoặc đã kiểm chứng toàn bộ quan hệ nhân quả.

## Giao diện và phạm vi

21 AI Playwright tests passed, gồm ca mới xác nhận extrema nằm trong `.ai-reading-story`, không có heading riêng, không có takeaway lặp và không tràn ngang tại 1440/1280. Build passed; còn cảnh báo Plotly chunk cũ. Screenshot `.impeccable/review/phase-extrema-{1440,1280}.png` dùng fixture, không phải ảnh output live. Đã xem ảnh 1440: tổng quan → giới hạn dữ liệu → giai đoạn → nguồn thu gọn. Không thay CSS/design identity, không tối ưu mobile. Impeccable ảnh hưởng thứ tự đọc và giữ thông tin nguồn ở disclosure; không có independent review/SHIP mới.

Python sau sửa parsing cuối: toàn bộ 281 tests passed; subset report/semantic 107 passed. Có 18 cảnh báo deprecation FastAPI đã tồn tại. `git diff --check` passed (cảnh báo chuyển LF/CRLF trên Windows, không có lỗi whitespace).
