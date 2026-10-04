# Validator v4 và prompt ưu tiên liên kết KPI — 02/10/2026

## Thay đổi

- `semantic-grounding-v4`; provider input/output vẫn v4, public API vẫn ai-trend-v3 / ai-overview-v2.
- So sánh số với `value` hoặc `displayValue` do Engine cung cấp, đúng fact/KPI/unit. Không có tolerance, không tự tính hoặc tự làm tròn. Các cặp số–ngày và vai trò cực trị vẫn được kiểm tra với chính điểm/fact được dẫn.
- Ngày trong “từ A đến B” là scope, không được gán B cho số đứng sau. Ngày của câu trước không được gán sang câu tiếp theo. Ngày điểm rõ ràng nhưng sai giá trị vẫn bị chặn.
- Chủ ngữ chỉ được giải quyết trong câu đang xét. Tên rút gọn “tỷ lệ”, “lượng ghi nhận” và chủ ngữ ghép được nhận diện. “Số lỗi và tỷ lệ đều tăng” phải đúng chiều của cả hai, không chỉ KPI cuối.
- Ngữ cảnh “cuối chuỗi” chỉ áp dụng cho mệnh đề tương ứng, không biến mọi động từ trong cùng câu thành khẳng định về kỳ cuối.
- Với quan hệ Engine xác nhận số lỗi không đổi, cho phép diễn giải Tổng số thay đổi làm tỷ lệ thay đổi. Điều kiện kiểm chứng dựa vào đúng chiều, đúng KPI và phía nguyên nhân/kết quả trong câu; không buộc lặp một câu mẫu hoặc số lỗi trong từng câu. Không cho phép đảo chiều nguyên nhân, gán quy trình/nhân sự là nguyên nhân hoặc áp dụng phép giải thích này khi số lỗi thay đổi.
- Không trở lại whitelist câu/từ; chưa giải quyết được wording vẫn là cảnh báo. Vẫn chặn scope/ref/source, unit, sai số/ngày, mâu thuẫn đã nhận diện, business cause/quality/forecast thiếu căn cứ và prompt injection. Không phải bộ chứng minh mọi câu tiếng Việt.
- Prompt registry `trend-summary-v13` / `metric-overview-v9`, resource `grounded-insight-v4.md`: giải thích diễn biến chính rồi quan hệ Tổng số–Báo sai/Lỗi–tỷ lệ. Với hai kỳ chỉ so sánh, không gọi xu hướng hoặc nêu extrema. Thêm few-shot lỗi tăng khi lượng ghi nhận giảm và số lỗi giữ nguyên khi tỷ lệ thay đổi. Chỉ dùng số của input, không lấy số ví dụ làm dữ liệu thật.
- Selection guidance ưu tiên candidate có `relationshipDescription` trước peak_offset khi có quan hệ ba KPI phù hợp; peak_offset vẫn có trong input và vẫn có thể kiểm chứng. Không đổi phép tính KPI, model, timeout, privacy gate hoặc UI/mobile.

Hướng viết prompt dùng chỉ dẫn rõ, ví dụ và kiểm thử đầu ra theo [hướng dẫn prompt chính thức](https://developers.openai.com/api/docs/guides/prompt-engineering). Không dùng hướng dẫn model-specific OpenAI để khẳng định khả năng của Gemini/9Router.

## Kiểm chứng

Regression bao gồm các câu provider thực tế bị loại nhầm, displayValue đúng/sai, %/điểm phần trăm, số đúng nhưng ngày sai, range header, chủ ngữ rút gọn/ghép, đúng số nhưng sai chiều và scope thiếu dữ liệu. Lần kiểm thử cuối gọi provider thật bằng `scripts/evaluate_ai_runtime.py --live` qua FastAPI TestClient trên read model SQLite đã committed; không dùng response giả hoặc replay cho nghiệm thu cuối.

Toàn bộ Python suite sau sửa cuối: **269 passed**, 18 cảnh báo deprecation FastAPI/Python có sẵn; compileall và diff check đạt. Không sửa frontend nên không chạy lại browser/build suite trong đợt này.

Vòng live đầu phát hiện câu đúng “Tổng số giảm ... khiến tỷ lệ tăng ...” vẫn bị chặn vì chỉ cho phép một cách nói và buộc nhắc số lỗi trong cùng câu. Đã sửa kiểm chứng theo quan hệ Engine/cause–effect metrics, bổ sung regression và chạy lại toàn bộ suite trước vòng cuối.

## Kết quả cuối bằng API LLM thật

| Dữ liệu VSO, tất cả KPI | Provider / tổng request | Kết quả |
|---|---|---|
| 07–16/09/2026 | 4.738 / 6.718 giây | ready/accepted, hai claim |
| 12–13/09/2026 | 4.074 / 5.645 giây | ready/accepted, một claim |
| 15–16/09/2026 | 3.573 / 5.222 giây | ready/accepted, một claim |

Cả ba dùng prompt metric-overview-v9, policy semantic-grounding-v4, response model gemini-3.7-flash-tiered qua route 9Router đang cấu hình. Mỗi request một provider attempt, không fallback ở vòng cuối. [Raw narrative, receipt và normalized series](2026-10-02-validator-v4-and-prompt-evaluation.json) lưu nguyên câu provider để đối chiếu.

### Đánh giá so với yêu cầu

- **Đúng dữ liệu:** cả bốn claim cuối khớp nguồn; tỷ lệ 22.54%, 1.76%, 3.69%, 20.09%, 3.35%, 5.24% là Engine displayValue, không phải phép tính hoặc làm tròn tự do. Giữ đối chiếu KPI/unit/source và ngày điểm.
- **Hiểu diễn biến:** overview nói rõ lên đỉnh 43 ngày 13/09, giảm liên tiếp rồi giữ 22 ở cuối. Không dùng đầu–cuối thay cả chuỗi và không nối qua ngày thiếu 11/09.
- **Liên kết KPI:** overview chọn Tổng số tăng 71→454 trong khi số lỗi giảm 16→8 và tỷ lệ giảm, không chỉ liệt kê lệch ngày đạt đỉnh. Case 12–13 nêu lỗi/tỷ lệ cùng tăng khi Tổng số giảm. Case 15–16 giải thích tỷ lệ tăng khi Tổng số giảm nhưng số lỗi vẫn 22.
- **Hai kỳ:** cả hai response riêng tránh xu hướng/cao nhất/thấp nhất. Case 15–16 kết luận tỷ lệ cao hơn không có nghĩa số lỗi tăng, đúng quan hệ phép tính và không suy đoán chất lượng.
- **Chưa đạt đầy đủ:** overview AI vẫn giới hạn hai claim, tập trung đoạn đỉnh/cuối và 07–08; chưa diễn giải sâu 09–10 hoặc đưa quan hệ 12–13 vào hai claim này. Các phases deterministic của API vẫn cung cấp giai đoạn đó. Một số câu còn dùng “tỷ trọng”, lặp lại ý số lỗi/tỷ lệ cùng tăng/giảm; chưa đạt độ tự nhiên tối đa.

Kết luận: đã sửa các false rejection tái hiện được và cải thiện lựa chọn/diễn giải liên kết KPI trong ba case thực tế. Không coi ba request accepted là nghiệm thu chất lượng mọi chuỗi, production pass rate hoặc chứng minh ngữ nghĩa tổng quát. Chưa kiểm tra live browser, không đổi layout/mobile trong đợt này.
