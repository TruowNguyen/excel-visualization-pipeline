# AI Insight nhóm vấn đề và Thống kê — đánh giá output thật sau sửa

Ngày 04/10/2026. Phạm vi ưu tiên: selected/all con trực tiếp và Thống kê. Không đổi công thức KPI, không thêm correlation hoặc kết luận nhân quả. Không thay provider, privacy gates, retry/timeout hoặc thiết kế mobile.

## Kết luận sản phẩm

Output sau sửa dễ đọc và cụ thể hơn: người đọc thấy diễn biến của vấn đề ở phần tổng quan, không cần mở chi tiết mới tìm được câu chuyện. Liên hệ giữa các vấn đề có thể nêu thời điểm cao nhất khác nhau và những giai đoạn cùng/trái chiều; không dùng một mốc của một vấn đề làm mốc cả nhóm. Thống kê không để số lỗi luôn bằng 0 che mất biến động Tổng số, phân biệt tổng trong kỳ với trung bình/ngày, và giữ giới hạn số ngày ghi nhận.

**Đã cải thiện, chưa nghiệm thu chất lượng production tổng quát.** Tổng quan cấp tập vẫn là composer ghép các đoạn riêng đã kiểm chứng và các quan hệ Engine, chưa phải một narrative LLM tự do phân tích sâu toàn nhóm. Một số câu còn phóng đại/lặp caveat; validator vẫn loại nhầm một số cách nói toán học đúng. Không diễn giải tác động nghiệp vụ khi dữ liệu không chứng minh.

## Runtime và bằng chứng

- Gọi POST endpoint ứng dụng qua FastAPI TestClient, **adapter/provider thật**, không replay hoặc mock response. Đây là kiểm thử API/diễn giải, không phải screenshot browser live.
- Model cấu hình `ag/gemini-3.7-flash-low`; provider trả `gemini-3.7-flash-tiered` qua9Router. Không xuất credentials/raw Excel.
- Prompt mới `context-insight-v2.md`, policy context-insight-v2, semantic-grounding-v8. Input/output schemas vẫn ai-context-provider-input-v1 / ai-context-narrative-v1 / ai-context-v1.
- [Trước sửa](2026-10-04-context-quality-before.json), [lượt sau sửa trung gian](2026-10-04-context-quality-after.json), [lượt cuối](2026-10-04-context-quality-final.json). Lượt cuối giữ providerInput, rawNarrative, report hiển thị, toàn bộ period series và sourceChecks; các fact/evidence bundles trùng lặp trong body được bỏ ở chế độ compact. ProviderInput chỉ chứa candidates/facts chuẩn hóa, không raw workbook/nguồn truy vết.
- Có một lượt kiểm tra cuối bị dừng trước case3 do metadata của landmark không có differentDirections. Đã sửa lookup, thêm hồi quy endpoint và chạy lại **toàn bộ14 ca**. Lượt lỗi không được tính là lượt cuối thành công.
- Không sửa production code sau lượt cuối thành công; không commit/push trong yêu cầu này. Freeze commit/tag cũ vẫn giữ nguyên. Shared reading focus và semantic validator có thay đổi được ghi rõ, không tuyên bố legacy reading hoàn toàn bất biến.

SHA256 runtime lượt cuối:

| File | SHA256 |
|---|---|
| context.py | 3B315C63025A089128DE2D8012D4EE9BFDB082FCAAA379B0972859C897AE3A0E |
| semantic.py | 4DADF97A2286B6DA1B73ED33D44FC5AE342B1714DE2E39CD0F191C63955A1A19 |
| reading.py | A18643BA29B9B9E727084F291F86B4E7653B79A861D36BD8719028C6F312AEB7 |
| context-insight-v2.md | C163D5610E8C4AF2A261BDB1ED8CF8B2C333A99CEE05EBFB37A856986EF23512 |

## So sánh trước/sau

| Chỉ tiêu trên cùng manifest | Trước sửa | Lượt cuối |
|---|---:|---:|
| Request ứng dụng |14|14|
| Request thực sự gọi LLM |13|13|
| Validation accepted |5|10|
| Validation partial |8|3|
| Không chạy LLM vì chưa đủ kỳ |1|1|
| Claim được giữ / claim trả về |58/70|75/80|
| Điểm chuỗi đối chiếu canonical chart |313|313|
| Lấy mẫu aggregate provenance |94|94|
| Chart/source mismatch |0|0|
| Request median có gọi provider |7.639s|6.827s|
| Request min/max có gọi provider |3.652/14.757s|3.771/15.600s|

Accepted chỉ là kết quả các checks hiện có, không chứng nhận insight hay mọi paraphrase đều đúng. Candidate selection và số claims thay đổi, LLM cũng có biến thiên; đây không phải benchmark thống kê hoặc bằng chứng nhân quả về tốc độ. Max latency vẫn hơn15s, không có SLA/cache/background job mới.

### Các ca cuối

| # | Project / phạm vi | Group / calculation | Validation | Request s |
|---|---|---|---|---:|
|1|VSO nhóm có dữ liệu riêng / node|ngày / sum|partial|7.685|
|2|VSO Camera / node toàn lịch sử|ngày / sum|partial|7.147|
|3|VSO hai vấn đề selected|ngày / sum|accepted|6.827|
|4|VSO all chín vấn đề|ngày / sum|accepted|15.600|
|5|SmartParking node|tuần / both|accepted|5.743|
|6|V-Pet all ba vấn đề|tuần / average|accepted|6.933|
|7|ANVF Đăng ký bus / node recent|ngày / sum|accepted|4.799|
|8|VOL node|tháng / sum|accepted|3.771|
|9|VW Vũ Yên all bốn vấn đề|quý / both|not_run|1.103|
|10|SmartParking all năm vấn đề, kỳ đầy đủ|tuần / average|accepted|7.408|
|11|VSO selected/custom|ngày / average|accepted|6.687|
|12|VSO node|tháng / sum|accepted|5.592|
|13|VSO node toàn lịch sử|tuần / sum|accepted|11.147|
|14|V-Pet all|tháng / both|partial|5.808|

Ca4:9 yêu cầu,7 có giá trị, hai vấn đề không có kỳ dùng được vẫn ở exclusions. Năm vấn đề có overview nhiều kỳ; tổng quan nêu ba trong số đó, các vấn đề còn lại giữ chi tiết/nguồn. Ca9 có giá trị nhưng chỉ một kỳ quý: không gọi LLM, không tạo trend. Không tuyên bố live narrative nhiều quý đã được kiểm định; hồi quy quý/đổi năm dùng synthetic.

## Đọc output thực tế theo yêu cầu sản phẩm

### Nhóm selected — có diễn biến và liên hệ cụ thể

Trước sửa, phần đầu chỉ nói các vấn đề có những nhịp tăng/giảm khác nhau. Sau sửa, hai overview AI mô tả Camera giảm, giữ nguyên, tăng lên mức cao nhất rồi giảm; Đèn pha giữ nguyên, biến động rồi tăng lên mức cao nhất và giảm cuối kỳ. Các đoạn được đưa lên tổng quan, không lặp nguyên văn trong chi tiết.

Quan hệ Engine ghi rõ Camera cao nhất13/09/2026, Đèn pha cao nhất15/09/2026; ngày13–15 Camera giảm trong khi Đèn pha tăng, ngày15–16 cả hai giảm. Đây là insight về **thời điểm và khác biệt diễn biến**, không phải hai chuỗi “tương quan” hoặc tác động lẫn nhau. Landmark đối chiếu tất cả ngày đồng mức; nếu có chung kỳ cao nhất thì không nói hai mốc không trùng.

### All nhiều vấn đề — bớt chìm trong chi tiết nhưng còn giới hạn

Ca4 có ba overview AI ở đầu, nêu các cấu trúc khác nhau và kỳ thiếu dữ liệu. Engine chọn một landmark và hai giai đoạn liên hệ; không đọc mọi cặp ngày. Tất cả requested membership vẫn được accounted for; không cộng vấn đề thành tổng nhóm.

Giới hạn: lựa chọn overview dựa trên độ phức tạp cấu trúc, không phải mức độ nghiêm trọng nghiệp vụ; không xếp hạng tuyệt đối giữa unit khác nhau. Quan hệ cấp tập vẫn deterministic. Những giai đoạn có pattern khác nhau không được gộp cưỡng bức chỉ để rút ngắn câu.

### Thống kê tuần — hai cách tính rõ ràng

SmartParking both có overview AI cho trung bình/ngày; các tổng kỳ vẫn ở chi tiết. Tổng số trung bình/ngày tăng ở các tuần đầu rồi biến động; lỗi trung bình/ngày biến động và thiếu tuần cuối. V-Pet nói Cư dân tăng, giữ nguyên hai tuần gần cuối rồi tăng trở lại; lỗi0 chỉ được nhắc như trạng thái không đổi, không chiếm câu chuyện chính. Cảnh báo vi phạm và Playback có nhịp khác nhau, không suy ra chất lượng hay số đăng ký mới.

### Thống kê tháng — so sánh, không trend giả

Ca14 ưu tiên ba overview average: Cư dân và Cảnh báo tăng, Playback giảm; lỗi có dữ liệu giữ0. Engine đối chiếu đúng hai tháng cùng calculation, không tạo % báo sai. Tổng và average không bị gọi là tăng/giảm giữa hai cách tính. Cảnh báo số ngày khác nhau được giữ, dù một câu LLM có “Do số ngày…” bị validator loại ở sum detail.

### Phần chưa đạt

- Còn5 claim bị loại: ngày thiếu11/09 không phải anchor được phép; nhãn tháng09/2026 trong candidate theo ngày chưa được parser coi là một thời điểm hợp lệ; các câu ratio/coverage có “do/khiến” còn bị gate nguyên nhân chặn dù một số câu toán học đúng. Fallback bảo toàn số liệu nhưng mất một phần diễn giải tốt.
- Model đôi lúc vẫn dùng “tăng vọt”, “đột biến”, “giảm mạnh” dù prompt hướng đến ngôn ngữ trung tính. Checks wording đang là warnings; accepted không chứng minh anomaly/ý nghĩa nghiệp vụ của các từ này.
- Cảnh báo thiếu dữ liệu/số ngày khác nhau còn lặp giữa overview, limitations và detail. Một số metric có lịch sử ngắn/chắp vá nên không đủ nền để insight sâu.
- Top overview tối đa ba vấn đề; không phải bao quát hết prose mọi vấn đề. Tất cả số liệu/chi tiết vẫn giữ. Không có score CX hoặc chất lượng production được gán chỉ từ acceptance rate.

## Sửa đã thực hiện và kiểm chứng

1. Prompt v2 định nghĩa insight rõ hơn, few-shot theo cấu trúc chuỗi, overview ít số, phase tối đa hai mốc, named subject và basis rõ; yêu cầu leadOverviewCandidateIds trước để nội dung quan trọng không bị budget bỏ qua.
2. Composer đưa các overview đã kiểm chứng lên đầu; both ưu tiên average và giải thích tổng vẫn ở detail. Không lặp nguyên overview trong detail.
3. Candidate budget cân bằng overview/phases/relationships, không để overview của all monopolize payload. Một bounded provider request vẫn giữ nguyên.
4. Cross-issue transitions chỉ gộp khi cùng metric/calculation/membership/direction và thực sự liền nhau; giữ tất cả fact/evidence IDs bên trong. Thêm landmark thời điểm cao nhất, kiểm tra tất cả ties, không so độ lớn/nhân quả.
5. Reading chọn metric biến động nếu lỗi không đổi, không để constant error che mất câu chuyện Tổng số. Core canonical values không thay.
6. Semantic v8 cho window overview định vị sub-stage nằm trong anchors; phase vẫn khóa exact bounds. Mức trung gian được kiểm tra bằng bước chuyển thật, không bắt buộc là terminal value. Thêm quarter lookup tránh KeyError; không nới số giả, scope, unit, dates, chronology/gap/plateau hoặc nguyên nhân nghiệp vụ.

Full Python suite cuối: **341 passed**,19 deprecation warnings FastAPI/Python3.14. Hồi quy mới cho promotion/basis, balanced candidates, merge không qua gap, extrema ties, intermediate roles/ranges, constant-error focus và landmark metadata endpoint. Context frontend E2E chạy lại: **9 passed**, gồm layout của phạm vi con/Thống kê và response cũ không ghi đè lựa chọn mới. Frontend không sửa trong đợt chất lượng này; E2E dùng dữ liệu mô phỏng, không chứng minh chất lượng live-provider prose. Đây là ma trận đại diện14 ca, không chạy lại toàn bộ600 offline cases trong lượt này.

Canonical comparisons tái dùng adapter đang phục vụ chart;94 provenance samples là boundary samples có thể lặp, không audit độc lập mọi ô Excel hoặc contributor. Không suy từ313 points matching thành chứng nhận mọi câu LLM đúng. Bằng chứng raw/validated được giữ để có thể đọc lại từng claim.
