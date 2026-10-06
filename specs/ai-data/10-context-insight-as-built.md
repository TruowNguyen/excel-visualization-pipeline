# 10 — AI Insight theo ngữ cảnh: triển khai 04/10/2026

Mở rộng theo [kế hoạch đã duyệt](09-insight-expansion-plan.md). Các luồng chức năng đã triển khai; không đồng nghĩa nghiệm thu toàn bộ chất lượng diễn giải hoặc SLA production. Baseline freeze v15 không bị thay đổi. Không thay công thức KPI core hoặc thiết kế mobile.

## Phạm vi chức năng

### Cập nhật insight liên kết v5

- Sửa hiển thị nhãn lặp: giữ nguyên template; các đoạn liên tiếp cùng entity/cách tính chỉ giữ tiền tố ở đoạn đầu. Khi chuyển vấn đề hoặc cách tính, giữ nhãn để không mất ngữ cảnh; trong chi tiết có tiêu đề sẵn thì bỏ tiền tố dư. Chỉ xử lý tiền tố khớp metadata, không cắt câu phân tích, không sửa payload, prompt, validator hoặc nguồn. Đã replay output API ghi sẵn của Thống kê tuần/tháng và kiểm tra chuyển ngữ cảnh bằng E2E.
- Prompt context-insight-v5 và synthesis-v5 ưu tiên ý nghĩa của diễn biến, sau đó số trước/sau và chênh lệch. Không lấy endpoint làm đại diện cả chuỗi.
- Thống kê phân tích liên hệ Tổng số/Số lỗi trong cùng cách tính, cùng hai kỳ liền nhau; tối đa hai nhịp đại diện, không liệt kê mọi ngày. Chỉ nêu cùng/trái chiều đã quan sát, không suy diễn chất lượng, tỷ lệ hay tác động nhân quả.
- Composer đối chiếu tổng và trung bình/ngày của cùng entity/metric/kỳ, đưa khác biệt đáng chú ý lên trước chi tiết. Mỗi phép tính giữ facts/evidence riêng; không cộng hoặc trừ hai cách tính với nhau.
- Quan hệ KPI được đưa lên phần mở đầu; so sánh hai kỳ không lặp lại ở overview và phases. Các hạn chế dữ liệu được gom một lần cho mỗi vấn đề. Đỉnh/đáy vẫn ở trong giai đoạn, không thêm heading riêng.
- Semantic-grounding-v9 sửa các cách diễn đạt đúng về phép tính tỷ lệ, metric giữ nguyên và liên kết ngày–giá trị. Đây vẫn là parser tiếng Việt có giới hạn, không phải bộ kiểm chứng ngữ nghĩa tổng quát. Các trường hợp còn bị loại nhầm được ghi trong báo cáo kiểm thử, không tăng tỷ lệ accepted bằng cách bỏ cổng kiểm chứng.
- Cách trình bày tiếp tục desktop-first. Kỹ thuật distill từ skill impeccable được dùng để giảm nội dung lặp và ưu tiên insight trước chi tiết; không đổi thiết kế mobile.

[Output API thật và đánh giá chi tiết](evidence/2026-10-04-linked-insight-review.md).

- Nút AI Insight trên biểu đồ mở phân tích riêng đúng entity, không đổi bộ lọc toàn trang.
- Tổng quan hỗ trợ một nội dung, các con trực tiếp được chọn hoặc tất cả con trực tiếp. Chọn rỗng không được tạo; all do backend resolve. Không lấy mọi hậu duệ hoặc cộng cha/con.
- Thống kê dùng cùng period resolver và `prepare_period_statistics` với biểu đồ: ngày/tuần/tháng/quý, tổng/trung bình mỗi ngày/cả hai, gần nhất/toàn bộ/custom, includeIncomplete. Không lấy khoảng ngày sidebar thay khoảng kỳ Thống kê. Chỉ Tổng số và Báo sai/Lỗi; không tự tạo tỷ lệ.
- Mỗi metric/calculation/entity có facts và evidence riêng. Trung bình giữ đúng float canonical của chart và denominator/coverage nguồn. Missing không tự thành zero; inferred zero chỉ theo core. Mở nguồn dùng exact/aggregate reference đã chụp.
- Liên hệ giữa các vấn đề là diễn biến cùng kỳ, cùng/trái chiều. Không correlation, nhân quả, rollup hoặc tỷ trọng. Không xếp hạng độ lớn giữa đơn vị khác nhau. Tổng hai kỳ khác số ngày không dùng làm cross-issue activity comparison.
- Đổi nhóm/project/kỳ/cách tính/lựa chọn/version làm kết quả stale và hủy chờ ở frontend; không tự gọi lại LLM, không tuyên bố provider đã bị hủy. Response cũ không ghi đè context mới.

## Contract API

`POST /api/projects/{project}/ai/context-insight`, schemaVersion mặc định `ai-context-request-v1`.

```json
{
  "view": "statistics",
  "parentEntityRef": "ID nhóm hiện chọn",
  "selection": "selected",
  "entityRefs": ["ID con trực tiếp"],
  "metricCode": "all",
  "groupBy": "week",
  "calculation": "both",
  "rangeMode": "all",
  "includeIncomplete": true,
  "expectedImportRef": "version đã hiển thị"
}
```

`selection=node` dùng parentEntityRef như entity phân tích; node/all không nhận entityRefs. Overview cần start/end, groupBy day/week/month, calculation=sum. Statistics hỗ trợ day/week/month/quarter, calculation sum/average_per_day/both, rangeMode recent/all/custom, periodCount 1–3660; custom cần periodFrom hoặc periodTo. Các trường overview date không quyết định window Thống kê. Rate trong Thống kê và ID không thuộc đúng nhóm/project trả 422; feature tắt trả 409.

Response `ai-context-v1`: context chứa requested/analyzed membership, counts, exclusions, resolved periods/cách tính; window thực tế; dataAsOf import/snapshot/checksum/stale; report gồm overview, relationships, issue details và relationshipDetails; facts/evidence typed; provider/validation receipts. Không có dữ liệu riêng hoặc kỳ hợp lệ được ghi lý do rõ, không biến thành zero. API trend-summary và snapshot GET cũ vẫn tương thích.

## Generation, grounding và hiệu năng

Mốc hiện tại: `context-insight-v4.md`, policy context-insight-v4; schema v1 và semantic-grounding-v8 giữ nguyên. Prompt thống nhất lối kể node/selected/all, tên KPI sum/average, cách ghi chênh lệch và nhãn kỳ; bổ sung ví dụ ba kỳ, hai tháng và tổng của kỳ khác số ngày để hạn chế date binding mơ hồ và từ “xu hướng” thiếu căn cứ. Nhãn metric sum không còn ghép tên calculation; average giữ `trung bình/ngày`. [Đánh giá template bằng API thật](evidence/2026-10-04-template-scope-review.md). Đoạn v3 dưới đây là lịch sử.

Cập nhật mới nhất: `context-insight-v3.md` và policy context-insight-v3. Candidates thêm tối đa hai `quantitativeEvidence` cho nhịp tăng/giảm tiêu biểu đã có period_change facts; prompt yêu cầu mức trước/sau và chênh lệch ngay trong diễn giải. Fallback phase giữ một nhịp định lượng, không tạo khối riêng. Không gọi endpoint change là thay đổi cả giai đoạn khi diễn biến bên trong khác. Semantic v8 phân biệt explicit “chênh lệch” với giá trị tại ngày, chặn số đóng sai vai trò, và nhận diện thêm câu “chưa đủ kết luận xu hướng”. [Báo cáo định lượng](evidence/2026-10-04-context-quantified-review.md). Phần v2 tiếp theo là mốc trước cập nhật.

Prompt resource/version `context-insight-v2.md`; provider input `ai-context-provider-input-v1`, response `ai-context-narrative-v1`. Legacy tiếp tục registry trend-summary-v15 / metric-overview-v11 và grounded-insight-v5.md. Semantic policy dùng chung hiện là `semantic-grounding-v8`: overview được mô tả giai đoạn con trong ranh giới facts; giá trị trung gian được đối chiếu với bước chuyển thực tế thay vì bắt buộc là điểm cuối. Phase vẫn khóa ranh giới; kiểm chứng số, đơn vị, nguồn, thiếu kỳ và nguyên nhân nghiệp vụ giữ nguyên. Không phải NLI tổng quát.

Một request provider cho mỗi lần người dùng tạo report, tối đa 12 candidate/100.000 byte và tối đa 8 paragraph. Ưu tiên round-robin overview/relationships/phases; LLM không gọi riêng vô hạn cho từng vấn đề. Claim khóa slot issue/calculation và fact dependencies; salvage theo paragraph. Markdown JSON fence được bỏ trước strict JSON parsing. Đo provider latency/attempts; không ghi credentials hoặc raw Excel. Raw response chỉ lưu khi chạy script đánh giá có chủ đích.

Engine xét mọi member trong request; facts/series và report vẫn truy cập được khi candidate không gửi LLM. UI báo rõ ưu tiên generation và gắn nhãn phần Engine. Quá 20.000 period × member × metric × calculation cells hoặc lịch sử Thống kê trên 3.660 kỳ trả lỗi rõ, không âm thầm cắt. Gate budget Thống kê chạy trước chuẩn bị chart/evidence. Feature/privacy gates và version freshness giữ nguyên.

## Trải nghiệm đọc và giới hạn chưa hoàn thành

Template hiện tại: mỗi entity chỉ có một disclosure, kể cả calculation=both. Bên trong là các section calculation độc lập, Trung bình/ngày trước Tổng trong kỳ, không cộng/chuyển số giữa hai cách tính. Số entity duy nhất quyết định nhãn chi tiết và tự mở khi chỉ có một vấn đề; không dùng số variants làm số vấn đề. Tổng quan legacy và context dùng chung `renderInsightPhase`/`renderInsightParagraph`: nhãn kỳ trước, đoạn diễn giải sau, nguồn Engine theo provenance của đoạn. Hai kỳ có thể hiển thị phần so sánh và nguồn, không bị ép thành template xu hướng. Giữ bố cục desktop và highlight an toàn đã có.

Thứ tự: phạm vi và receipt → tạo phân tích → tổng quan → liên hệ → chi tiết từng vấn đề → nguồn thu gọn. Đỉnh/đáy ở trong giai đoạn, không heading riêng. Native disclosures, tìm kiếm và checkbox giữ lựa chọn; lỗi AI không chặn chart. Impeccable ảnh hưởng đến thứ tự đọc và ghi rõ phần provider không diễn giải; giữ visual identity desktop hiện có.

Không có cache mới, background jobs hoặc lazy LLM detail trong đợt này. Composer đưa tối đa ba overview đã kiểm chứng lên đầu, ghi rõ phạm vi được tóm tắt; liên vấn đề gộp các bước liền nhau cùng chiều và có thể đối chiếu thời điểm đạt mức cao nhất. Liên hệ cấp tập vẫn deterministic, chưa phải narrative LLM tổng hợp sâu cho toàn nhóm. Reading ưu tiên metric biến động nếu lỗi giữ nguyên, không đổi công thức KPI. Validator còn false rejection với diễn giải toán học có “do/khiến”, ngày thiếu ngoài anchors và nhãn tháng trong candidate theo ngày; chưa xác minh mọi paraphrase hoặc mọi thứ tự định tính. Vì vậy ready/accepted không tự chứng minh insight đạt chuyên môn; chất lượng production tổng quát vẫn cần bộ đánh giá mở rộng. Dữ liệu committed hiện chỉ có một quý; không gọi LLM để tự tạo xu hướng quý. Hồi quy nhiều quý/đổi năm dùng dữ liệu synthetic, ghi riêng với live.

Chi tiết triển khai ban đầu: [bằng chứng 04/10](evidence/2026-10-04-context-insight-evaluation.md). Lượt cải thiện prompt/composer/validator đã chạy lại 14 ca đại diện, gồm 13 request LLM thật: [đánh giá output trước/sau và giới hạn](evidence/2026-10-04-context-quality-review.md). Các exit gates chất lượng trong kế hoạch không được tự đánh dấu đạt chỉ vì test kỹ thuật pass.

### Cân chỉnh panel desktop — 04/10/2026

Cập nhật sau theo yêu cầu người dùng: bỏ giới hạn 75ch cho nội dung AI, sử dụng chiều rộng vùng làm việc; highlight có giới hạn bằng formatter frontend dùng chung cho cả legacy/node và context/Thống kê. Tên vấn đề/cách tính tách thành nhãn dễ nhận biết, body nhấn tên KPI/cụm diễn biến/chênh lệch; không đổi nhận định hoặc số. Bảng nguồn không kế thừa ellipsis của bảng chung. Đây là thay đổi presentation, không phải lượt kiểm chứng LLM mới. Mốc layout 75ch dưới đây được giữ làm lịch sử trước cập nhật.

Sau đánh giá giao diện độc lập, panel trong Tổng quan nội dung con và Thống kê dùng chung khung nội dung có lề 26 px trên desktop. Bộ lọc chỉ số/nhóm dữ liệu/phạm vi vấn đề được gom thành hàng linh hoạt, phạm vi vấn đề không còn kéo toàn chiều rộng. Ô tìm kiếm cao tối thiểu 42 px như select. Đoạn diễn giải giới hạn 75ch, có nhịp tiêu đề/đoạn văn; bảng nguồn vẫn dùng vùng rộng và cuộn khi cần. Không còn chèn bộ lọc bằng thay thế chuỗi HTML.

Receipt có nhãn riêng “Phạm vi đang chọn” và “Phạm vi đã phân tích”; receipt kết quả dùng grouping/cách tính/date/count của response đã chụp. Khi bộ lọc hoặc dữ liệu làm kết quả stale, cảnh báo nổi bật và status không còn báo hoàn tất như một kết quả hiện hành. Không sửa request/API, prompt, validator, công thức KPI hoặc nội dung nhận định nguồn.

Kiểm chứng: 9 test context pass; toàn bộ 73 test frontend pass; build pass với cảnh báo chunk Plotly đã có. Bốn case layout đo căn lề/kích thước ở 1280 và 1440 px cho hai màn hình, đồng thời kiểm tra mở nguồn, không tràn ngang và trạng thái stale. Ảnh `context-layout-{children,statistics}-{selected,result,stale}-{1280,1440}.png` trong `.impeccable/review/` dùng API mô phỏng, không chứng minh độ chính xác/latency LLM. Kiểm tra layout tự động không có finding; đã xem ảnh kết quả và stale. Impeccable ảnh hưởng đến cách nhóm điều khiển, lề chung, chiều rộng đọc và phân biệt ngữ cảnh kết quả. Giữ nhận diện hiện có và hành vi responsive, không thiết kế lại mobile hay tuyên bố kiểm định accessibility toàn diện.
