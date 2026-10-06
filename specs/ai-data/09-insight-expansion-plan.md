# 09 — Kế hoạch mở rộng AI Insight

Ngày: 04/10/2026. Trạng thái: **Đã duyệt; các luồng chức năng đã triển khai, nghiệm thu chất lượng còn giới hạn**. [As-built, quyết định endpoint/budget và phần chưa hoàn thành](10-context-insight-as-built.md); [kiểm thử](evidence/2026-10-04-context-insight-evaluation.md). Các nội dung phía dưới giữ thiết kế/exit gates gốc, không tự coi mọi gate đã đạt.

Baseline đã freeze và push: commit `daa397462059c55524370598acba2142915a1ea4`, tag `freeze-2026-10-04-ai-insights-v15` trên origin/dev. [Biên bản freeze](evidence/2026-10-04-freeze.md). Kế hoạch này được lập sau mốc freeze, không thay đổi tag hoặc runtime trong mốc đó.

## 1. Kết quả cần đạt

Người dùng CX hiểu dữ liệu đã thay đổi như thế nào, vấn đề nào đáng chú ý và những diễn biến liên quan nhau. Không phải đọc lại từng giá trị hoặc ghép nhiều report riêng. Giữ ngôn ngữ Việt dễ hiểu, câu ngắn, chủ ngữ rõ; không dùng “toàn khoảng”, không khẳng định chất lượng hoặc nguyên nhân nghiệp vụ khi thiếu căn cứ.

Phạm vi đã thống nhất:

1. Phân tích từng vấn đề, không bắt buộc đổi lựa chọn toàn dashboard.
2. AI Insight trong Thống kê, dùng đúng kỳ và cách tính của biểu đồ.
3. Phân tích kết hợp **các vấn đề đã chọn** hoặc **tất cả vấn đề trong nhóm**. Chọn một trả phân tích riêng; chọn nhiều trả bức tranh chung và chi tiết cần thiết.

Không triển khai mobile redesign, correlation, dự báo, anomaly detection, nguyên nhân nghiệp vụ, scheduled reports, export/approval hoặc thay phép tính core trong đợt này. Desktop-first, giữ hành vi responsive hiện có.

## 2. Những gì hiện có và khoảng trống

| Thành phần | Baseline | Việc cần làm |
|---|---|---|
| API trend-summary | Một entityRef, scope=node; ba KPI hoặc all; day/week/month | Thêm ngữ cảnh Thống kê và tập entity, tương thích request cũ |
| Tổng quan | AI panel cho node hiện chọn; children bị khóa | Phân tích từ một biểu đồ vấn đề và phân tích tập vấn đề |
| Thống kê | day/week/month/quarter; sum/average/both; khoảng kỳ riêng | Kết nối AI với cùng period resolver và prepared statistics |
| Engine/report | Facts, evidence, phases, extrema, liên hệ ba KPI trong node | Facts liên vấn đề và cách tính Thống kê, namespace không xung đột |
| Validator | Semantic grounding v6; salvage theo paragraph | Khóa entity/calculation/phạm vi; kiểm tra thứ tự giai đoạn; giảm false rejection có hồi quy |
| LLM adapter | Timeout/token/retry/privacy đã có | Giới hạn payload đa vấn đề, cache và đo độ trễ; không gọi từng vấn đề vô hạn |

Chú ý: API hiện đã phân tích được node vấn đề có dữ liệu riêng. Mở rộng từng vấn đề chủ yếu là luồng truy cập và khóa ngữ cảnh, không cần viết lại thuật toán từ đầu.

## 3. Chốt ngữ nghĩa trước khi code

### 3.1. Hai ngữ cảnh dữ liệu độc lập

- Tổng quan: project, node/tập vấn đề, khoảng ngày và nhóm kỳ của Tổng quan.
- Thống kê: project, node/tập vấn đề, day/week/month/quarter, tổng/trung bình mỗi ngày/cả hai, các kỳ gần nhất/toàn bộ/chọn khoảng, includeIncomplete. Không lấy workspace.window của Tổng quan thay cho các kỳ Thống kê.
- Backend resolve danh sách kỳ một lần bằng logic đang dùng cho biểu đồ. Prepared data phục vụ cả chart và AI, không có công thức KPI song song.
- Tổng và trung bình là hai cách nhìn khác nhau, không gọi chênh lệch giữa chúng là thay đổi KPI. Mỗi số phải có cách tính và đơn vị rõ.
- Thống kê hiện chuẩn bị Tổng số và Báo sai/Lỗi. Không tự thêm % báo sai hoặc suy ra tỷ lệ từ các average; chỉ mở rộng nếu có contract nguồn/công thức/evidence được duyệt riêng.
- Bảo toàn `eligible_day_count`, `observed_day_count`, `calendar_day_count`, `coverage_source_entity_id`, inferred_zero và semantic_unavailable_reason theo `prepare_period_statistics`. Không chia lại tổng cho số ngày lịch hoặc tự coi missing là zero. Giữ nguyên quy tắc inherited coverage và trường hợp average unavailable.

### 3.2. Các vấn đề được chọn và tất cả

- Đề xuất MVP: danh sách **con trực tiếp** trong nhóm hiện chọn, đồng nhất với danh sách biểu đồ. Không tự lấy toàn bộ hậu duệ; phạm vi hậu duệ sâu hơn cần duyệt riêng.
- `selected`: nhận ID được chọn, loại ID trùng, kiểm tra thuộc nhóm/project và trả lỗi rõ cho ID sai; không âm thầm sửa selection.
- `all`: backend chụp toàn bộ danh sách con trong snapshot, không tin danh sách được frontend gửi như bằng chứng “tất cả”.
- Response ghi rõ số yêu cầu, số đủ dữ liệu, ID phân tích, ID không thể phân tích và lý do. Vấn đề không có dữ liệu vẫn nằm trong receipt phạm vi, không biến thành zero.
- Không chọn vấn đề nào: chưa cho tạo insight; không mặc định đổi sang all. Có một vấn đề: dùng report riêng. Có nhiều: dùng report kết hợp.
- Đổi nhóm/project/period/calculation/data version phải invalidate kết quả; không tự gọi LLM. Đổi selection giữ bản cũ kèm trạng thái không còn khớp cho đến khi người dùng tạo bản mới.

### 3.3. Liên hệ và tổng hợp có giới hạn

- Phân biệt **tổng hợp nhận định** với **cộng số liệu**. Luôn có thể trình bày diễn biến từng vấn đề; không luôn có thể tạo tổng nhóm hoặc tỷ trọng đóng góp.
- Không cộng cha và con, không cộng vấn đề có thể trùng lặp; cùng đơn vị chưa đủ chứng minh tính cộng được. Không suy ra rollup khi parent không có dữ liệu riêng.
- Nếu group total có nguồn trực tiếp, dùng nó như chuỗi riêng, không mặc định bằng tổng các child. Nếu group total unavailable, không viết “tổng lỗi của nhóm giảm”.
- Chỉ tính đóng góp/tỷ trọng khi có bằng chứng denominator, phạm vi và tính cộng được. Tập selected không đại diện mọi vấn đề trong nhóm; câu kết luận phải giới hạn đúng tập đó.
- Khác đơn vị: cho xem diễn biến riêng và cùng thời điểm; không xếp hạng độ lớn, cộng hoặc diễn giải mức chênh lệch tuyệt đối giữa các đơn vị.
- Các nhận định liên hệ cần cùng kỳ so sánh, đủ dữ liệu và đúng calculation: cùng tăng/giảm, diễn biến trái chiều, một vấn đề tăng trong khi những vấn đề khác giảm. Không gọi là correlation, tác động nhân quả hoặc chất lượng giảm.
- Tổng của kỳ ngắn hơn không đủ chứng minh hoạt động giảm. Câu diễn giải phải nêu ngay kỳ bị cắt/khác thời lượng; average chỉ dùng khi chart/core cho phép.

## 4. Brief trải nghiệm đọc và thao tác

Áp dụng Impeccable theo hướng Read trong Operate, kế thừa giao diện hiện tại; không thay visual identity và không sửa UI trong bước planning.

- Một khu vực phân tích cho phạm vi đang xem. Chọn “Tất cả vấn đề trong nhóm” hoặc “Các vấn đề đã chọn”; danh sách có tên rõ, tìm kiếm khi dài và đếm số chọn. Thao tác phân tích riêng từ biểu đồ xác định đúng issue ID, không làm đổi bộ lọc toàn trang.
- Trước khi tạo: hiện receipt gồm nhóm, vấn đề, thời gian/kỳ, cách tính và kỳ chưa đầy đủ. Trong Thống kê không thêm bộ lọc AI riêng có thể lệch chart.
- Thứ tự đọc: **Tổng quan → Diễn biến đáng chú ý và liên hệ → Chi tiết từng vấn đề khi mở rộng → Nguồn/chất lượng thu gọn**. Đỉnh/đáy nằm trong giai đoạn, không có heading riêng. Không lặp ba thẻ KPI cho mọi vấn đề.
- “Tất cả” là phạm vi Engine xét, không phải yêu cầu overview liệt kê tất cả. Các vấn đề không nổi bật vẫn có chi tiết; danh sách thiếu dữ liệu luôn có thể kiểm tra.
- Empty/loading/partial/provider failure/stale phải có trạng thái rõ. Đổi bộ lọc trong lúc chạy không được để response cũ ghi đè; abort ở frontend không được mô tả là chắc chắn đã hủy request provider.
- Loading không khóa đọc biểu đồ. Lỗi AI không chặn dashboard. Paragraph fallback có nhãn phù hợp, không đẩy thông báo kỹ thuật lên trước câu chuyện dữ liệu.
- Điều khiển có label, bàn phím, focus và thông báo đọc màn hình; bảng/danh sách dài không làm mất phạm vi đang chọn.

## 5. Thiết kế kỹ thuật cần hoàn thành trước triển khai

1. **AnalysisContext có version**: view, project, parent/entity selection, resolved membership, explicit periods, groupBy, calculation, coverage policy và pinned data version. Giữ contract trend-summary cũ; đề xuất endpoint context-aware riêng hoặc envelope có version, quyết định sau spike compatibility.
2. **Shared data adapters**: tái sử dụng AnalyticsEngine cho Tổng quan; adapter prepared statistics cho Thống kê. Tách period resolver đang nằm trong app/api.py thành shared service nếu cần, có test parity trước/sau refactor.
3. **Fact/evidence mở rộng**: namespace gồm entity + metric + calculation + kỳ; claim liên vấn đề mang operands và period alignment. Mỗi số tổng/trung bình phải có exact/aggregate evidence và metadata phép tính, coverage/denominator đã dùng. EvidenceBuilder phải mở đúng contributor nguồn, không chỉ có một checksum của số average.
4. **Composer**: một report cấp tập vấn đề với overview, shared phases/relationships và issue details; không nối chuỗi report độc lập. Kết quả Engine cho mọi issue phải còn truy cập được dù LLM chỉ nhận các facts nổi bật.
5. **Validator version mới**: tách grounding số/ngày/metric/entity/calculation khỏi diễn giải; kiểm tra các giai đoạn được mô tả theo đúng thứ tự. Giá trị có thật nhưng gán cho vấn đề khác hoặc bỏ nhịp giảm rồi gọi toàn đoạn tăng phải bị phát hiện. Giữ scope/source/unit gates, salvage theo paragraph, không dùng hardcoded ví dụ nguồn.
6. **Prompt version mới**: định nghĩa insight và few-shot cho một/nhiều vấn đề, average vs sum, quarter, kỳ ngắn, cùng/trái chiều, missing, khác đơn vị và selected vs all. Few-shot không trở thành phép tính production hoặc template bắt model đọc hết số.
7. **Giới hạn và hiệu năng**: đo độ rộng nhóm/số kỳ/tokens trước khi đặt ngưỡng; không áp giới hạn 60 kỳ của endpoint cũ lên “toàn bộ” rồi âm thầm cắt. Với dữ liệu lớn, Engine tính đủ, nén facts và cung cấp detail phân trang; nếu vượt khả năng thực tế phải báo rõ phạm vi chưa xử lý. Không gọi LLM cho mỗi issue tự động. Ưu tiên một request summary có ngân sách; lazy detail chỉ khi người dùng yêu cầu. Cân nhắc background job nếu đo đạc chứng minh cần, không mặc định xây hàng đợi ngay.
8. **Cache/freshness/privacy**: key gồm resolved membership, view, periods, calculation, coverage policy, data version, prompt/policy/model version; không dùng chung cache selected/all hoặc sum/average. Chỉ gửi facts chuẩn hóa theo privacy gate hiện có, không gửi Excel thô. Ghi provider latency/usage/fallback/coverage, không log credentials.

## 6. Thứ tự triển khai và exit gates

Mỗi slice đi hết Backend → AI → Validation → Frontend → Testing rồi mới chuyển slice kế tiếp. Không đồng nhất đây với các phase comparison/reporting khác của roadmap cũ.

| Slice | Công việc | Điều kiện hoàn thành |
|---|---|---|
| 0 — Nền tảng và chất lượng | Inventory hierarchy/units/coverage; contract context; hồi quy thứ tự giai đoạn và kỳ ngắn; golden output để đánh giá | Không bỏ nhịp trung gian như case VSO; scope/chart parity được chứng minh; negative tests không bị nới mất |
| 1 — Từng vấn đề | Luồng gọi từ biểu đồ; entity identity; report riêng; stale/cancel/fallback | Không đổi selection toàn trang; số và evidence đúng issue; dữ liệu thiếu không thành zero |
| 2 — Thống kê | Shared periods + prepared data; sum/average/both; quarter; riêng từng vấn đề trước | Mọi số AI bằng chart; đúng denominator ngày/coverage; không lệch sidebar; quarter và partial kỳ có tests |
| 3 — Tập vấn đề | selected/all, snapshot membership, cross-issue facts, composer; hỗ trợ cả Tổng quan và Thống kê | Engine xét đủ scope; không cộng sai/trùng; selected không bị diễn giải thành toàn nhóm; detail đủ coverage |
| 4 — Nghiệm thu cuối | Toàn suite, ma trận dữ liệu, performance và LLM API thật; đọc đánh giá output | Evidence lưu rõ cấu hình/phạm vi/raw-vs-validated; đạt tiêu chí ở mục 7; cập nhật docs trước bàn giao |

Người dùng đã duyệt triển khai ngày 04/10. Các luồng được kiểm tra theo slice; các khoảng trống cache/composer/semantic coverage được ghi trong as-built, không tự nâng thành hoàn tất production.

## 7. Ma trận test và tiêu chí nghiệm thu

### Kiểm thử xác định

- Tất cả project/entity có dữ liệu committed; node không có dữ liệu riêng; group không có children; selected 0/1/n và all; foreign IDs, duplicate IDs, khác đơn vị, parent/child có nguy cơ trùng.
- Tổng quan day/week/month; Thống kê day/week/month/quarter × sum/average/both × recent/all/custom × includeIncomplete bật/tắt. Dùng nhiều bộ số, đổi năm, tuần/tháng/quý giao năm; không chỉ chuỗi chín ngày cũ.
- Một/hai/ba/bốn kỳ; hai kỳ không có ngôn ngữ trend hoặc extrema thừa; missing khác zero; inferred zero chỉ theo rule canonical; rate thiếu numerator; inherited coverage/average unavailable; kỳ không cùng thời lượng.
- Long history và nhóm lớn: đủ scope/membership, report không bỏ phần cuối/đỉnh/đáy hoặc issue ít dữ liệu, giới hạn provider được công khai. Không O(n²) gửi mọi cặp khi nhóm lớn; chọn quan hệ theo policy có test.
- Negative claims: số thật nhưng sai entity/metric/calculation/date; average sai denominator; cộng sai issue; selected giả thành all; hướng đúng nhưng thứ tự giai đoạn sai; business causality thiếu fact.
- Frontend request context, source navigation, accessibility, stale/late response/cache, provider failure không phá chart. Chart/assertions dùng raw value canonical và display format hiện có, không lấy narrative làm expected source.

### API LLM thật ở lần kiểm thử cuối mỗi slice

- Chạy qua endpoint ứng dụng với provider cấu hình thật, không chỉ adapter smoke/mock. Phải là response mới sau sửa code cuối; replay tách nhãn, không tính là live.
- Các ca live đại diện mọi nhóm kỳ/cách tính/phạm vi vừa mở, ít nhất một/nhiều/tất cả vấn đề; phủ dự án và vấn đề có nguồn/coverage đặc biệt. Offline phủ tổ hợp đầy đủ trong khả năng dữ liệu, live có manifest mẫu đại diện, không nói đã gọi mọi tổ hợp nếu chưa gọi.
- Lưu request context, data snapshot/membership, Engine facts cần đối chiếu, raw output, surviving paragraphs, rejection/fallback reasons, latency/token usage khi provider cung cấp. Không chứa secrets/Excel thô.
- Đánh giá thủ công: số đúng; thứ tự diễn biến đúng; liên hệ có nghĩa và đúng phạm vi; kỳ ngắn/thiếu được giải thích ngay; câu ngắn/dễ hiểu; không fact dump hoặc lặp template. **accepted không tự động là đạt chất lượng**.
- Sai số/sai chủ thể/sai calculation/nhân quả vô căn cứ trong phần hiển thị là lỗi chặn nghiệm thu. Partial không tự động là lỗi chặn, nhưng phải đọc fallback: nội dung còn giúp hiểu dữ liệu và không lặp/che ý chính. Đặt performance budget sau baseline đo của từng slice, không hứa SLA chưa có bằng chứng.

## 8. Các quyết định cần duyệt trước implementation

Phạm vi chức năng đã được người dùng đồng ý. Các đề xuất dưới đây làm rõ implementation, không phải tính năng đã có:

- MVP “tất cả trong nhóm” = con trực tiếp hiện thuộc nhóm; không tự đi sâu mọi hậu duệ.
- Thống kê chỉ diễn giải các đại lượng thực sự đang hiển thị; không tự thêm tỷ lệ mới.
- Kết quả chọn vấn đề gắn với một context/snapshot; mở insight riêng không đổi bộ lọc toàn trang.
- Giữ contract cũ, thêm context version mới; chọn endpoint cụ thể và ngân sách runtime sau spike/đo đạc, ghi quyết định trước viết UI.
- Không tạo group total/đóng góp nếu chưa có bằng chứng cộng được; báo giới hạn thay vì tự suy ra.

## 9. Tài liệu phải cập nhật khi triển khai

04-ai-data-and-output-contracts.md; 05-ai-evaluation-and-acceptance.md; 07-vertical-slice-implementation-plan.md (liên kết phạm vi bổ sung); API contract; dashboard behavior; product use cases; prompt registry và evidence từng slice. Chỉ đổi trạng thái as-built sau khi exit gate đạt. Kế hoạch này không tự nâng các capability trong roadmap thành đã triển khai.
