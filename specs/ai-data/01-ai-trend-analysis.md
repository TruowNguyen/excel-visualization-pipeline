# 01 — Đặc tả phân tích xu hướng bằng AI

**Phiên bản đặc tả:** 2.4.0. **Trạng thái:** Phase 1 as-built cho scope `node`, chuỗi kỳ `day|week|month`, period-level analytics và bối cảnh tối đa 12 kỳ liền trước; stable/anomaly/report vẫn chưa triển khai. **Contract IDs:** `AI-TR-*`.

## 1. Mục tiêu

Giải thích chuyển động KPI theo thời gian trong project/entity/metric/khoảng thời gian người dùng chọn, thay vì chỉ hiển thị chart. Nêu các thay đổi có căn cứ dữ liệu, so sánh giữa các kỳ, quan sát đáng chú ý và giới hạn chất lượng dữ liệu.

**Metric core hiện có:** `Tổng số`, `Báo sai/Lỗi`, `% báo sai`. Metric khác chỉ được tham gia khi đã có metadata, aggregation rule và semantic definition rõ ràng.

## 2. Đầu vào và ranh giới

| Trường | Ý nghĩa / validation |
|---|---|
| project / entity | Phải tồn tại trong committed data; entity phải thuộc project |
| metric | Phải được analytics contract hỗ trợ; kiểm tra unit và metric semantics |
| scope | Dùng đúng `node` hoặc `children` của core; không tạo hierarchy rollup ngầm |
| time window | Start/end inclusive hoặc core time mode; date boundary và calendar/timezone phải hợp lệ |
| group | Runtime Phase 1 nhận `day`, `week`, `month`; aggregation dùng rule hiện có |
| comparison baseline | Kỳ trước có thể so sánh, approved fixed baseline hoặc none |
| data snapshot | Import/read-model version đã khóa cùng value, coverage và evidence ref chính xác |
| analysis policy version | Xác định rule về stable/change, period eligibility và noteworthy-point selection |

- `AI-TR-001`: Chỉ phân tích dữ liệu committed và đã khóa; filter đã chọn và observed coverage thực tế MUST xuất hiện trong output.
- `AI-TR-002`: MUST giữ nguyên unit và value type của metric. Không diễn giải percentage và count như cùng một đại lượng.
- `AI-TR-003`: MUST tái sử dụng effective-unit, hierarchy, missing-value và grouping rule của core; LLM không được tự triển khai lại.

## 3. Sự kiện phân tích tất định

### 3.1. Chuỗi thời gian

Trả ordered period key, observed value, valid observation count, expected/comparable coverage nếu đã định nghĩa và missing marker. Không tự tạo intermediate value hoặc coi ngày vắng mặt là zero.

- `AI-TR-010`: Với count metric, dùng approved SUM/AVG rule phù hợp view; output MUST nêu rõ rule đã dùng.
- `AI-TR-011`: Aggregate error rate MUST tính bằng `SUM(valid error) / SUM(valid total) * 100` khi denominator và coverage hợp lệ theo approved pair rule. MUST NOT lấy trung bình cộng daily percentage để suy ra period rate.
- `AI-TR-012`: Giữ nguyên aggregation rule của core: denominator dương dùng `error / total * 100`; `total = 0` và `error = 0` trả `0%`; `total = 0` nhưng error khác zero, missing hoặc invalid trả unavailable/null kèm lý do. Numerator bằng zero với denominator dương cũng là zero rate hợp lệ.
- `AI-TR-013`: Ở daily grain, giữ source percentage và ý nghĩa gốc; chỉ aggregate theo weighted contract đã duyệt. Không thay numerator/denominator bằng source percentage.

### 3.2. Chuyển động từng kỳ và toàn khoảng

Với mỗi cặp kỳ hợp lệ liên tiếp có value `a`, `b`, và với cặp kỳ hợp lệ đầu–cuối của toàn khoảng:

- Absolute change: `delta = b - a` theo unit của metric.
- Relative change: `(b - a) / abs(a) * 100` chỉ khi baseline khác zero, hợp lệ và cách diễn giải đã được duyệt. Với KPI không âm chuẩn, công thức tương đương `(b-a)/a * 100`.
- Khi baseline zero/null/không thể so sánh, relative change là `null` kèm lý do; không báo infinite percent.
- Với percentage metric, absolute difference MUST được ghi là **percentage point (pp)**, không phải percent.

- `AI-TR-020`: Numerical fact MUST được tính trước khi gọi LLM. LLM không được thay đổi hoặc tính lại.
- `AI-TR-021`: Mỗi kỳ sau kỳ đầu MUST có `period_change`, `period_relative_change` khi baseline khác zero và `period_direction`; `insufficient_data` biểu thị chuỗi có ít hơn hai kỳ hợp lệ.
- `AI-TR-022`: Policy `period-series-v3` phân loại toàn chuỗi theo dấu của mọi delta liên tiếp: chỉ tăng/không đổi là `consistently_increasing`, chỉ giảm/không đổi là `consistently_decreasing`, toàn bộ bằng zero là `unchanged`, có cả tăng và giảm là `fluctuating`. So sánh đầu–cuối vẫn được giữ như fact tổng quan nhưng không thay cho bằng chứng toàn chuỗi.
- `AI-TR-023`: Previous-period comparison MUST nêu exact date boundary và comparability/coverage; kỳ không bằng nhau, partial hoặc missing-heavy MUST được cảnh báo. Cùng elapsed time chưa đủ nếu valid-day coverage khác đáng kể.
- `AI-TR-024`: Khoảng không có kỳ hợp lệ MUST được ghi trong limitation; hệ thống không chèn kỳ thiếu dưới dạng zero. Request tạo quá 60 kỳ MUST bị từ chối và yêu cầu chọn grain lớn hơn hoặc thu hẹp khoảng; không âm thầm cắt chuỗi.

### 3.3. Thay đổi đáng chú ý

- `AI-TR-030`: Policy `period-level-v1` MUST xác định deterministic peak/lowest, lần tăng/giảm lớn nhất, thay đổi gần nhất, chuỗi tăng/giảm liên tiếp dài nhất và plateau ở cuối chuỗi trong các kỳ hợp lệ; tie chọn chuỗi hoặc kỳ kết thúc gần nhất. Chuỗi liên tiếp cần ít nhất hai transition cùng chiều; ending plateau cần ít nhất một transition không đổi. Đây là mô tả trong window, không phải threshold hoặc anomaly detection.
- `AI-TR-031`: Phân biệt rõ “largest observed change” với “statistical anomaly”. Không được claim anomaly khi chưa có detector và calibration đã duyệt.
- `AI-TR-032`: Mỗi flagged point MUST có date/period, measured value, comparator, change, valid coverage và exact/aggregate evidence.
- `AI-TR-033`: Khi sample size hoặc coverage không đủ, trả `insufficient_data` thay vì xu hướng chắc chắn.
- `AI-TR-034`: Policy `trailing-12-periods-v1` lấy tối đa 12 kỳ hợp lệ hoàn tất ngay trước window, cùng entity/metric/grain; kỳ tự nhiên chồng lấn với window MUST bị loại.
- `AI-TR-035`: Historical context MUST cung cấp kỳ liền trước, biên thấp/cao, thay đổi từ kỳ liền trước tới kỳ đầu window và vị trí kỳ cuối hiện tại so với biên lịch sử.
- `AI-TR-036`: Narrative MUST gọi rõ đây là các kỳ lịch sử được cung cấp, không được diễn đạt thành kỷ lục toàn bộ lịch sử, anomaly hoặc significance.
- `AI-TR-037`: Mọi period-level/historical result MUST có fact ID và evidence của đúng kỳ tham gia phép so sánh.

## 4. Ranh giới mô tả và chẩn đoán

### Analytical overview MVP — 02/10/2026

- `AI-TR-038`: Cross-metric overview policy `aligned-overview-v1` MUST phân biệt relationship đầu–cuối với pattern toàn chuỗi. Relationship chỉ có khi endpoints cùng ngày/grain, đầy đủ ngày và kỳ tự nhiên, độc lập count khớp numerator/denominator của weighted rate, denominator dương và numerator không âm. Zero numerator không tạo relative-growth comparison. Không xác nhận quality/cause.
- `AI-TR-039`: Overview MUST chọn có giới hạn candidates có fact/evidence; largest observed change không là anomaly. Partial/misaligned endpoints vẫn có descriptive/temporal content với limitation; không impute missing thành zero để tạo relationship. Structured investigation step chỉ mở nguồn đã có.

Turning point/peak alignment chưa thuộc implementation MVP. Single-metric historical/period analytics giữ nguyên. Nội dung enum monotonic trên UI là “không có lần giảm/tăng giữa các kỳ hợp lệ”, không hứa strictly increasing hoặc adjacency theo lịch khi có missing.

**Descriptive:** “Trong giai đoạn đã chọn, Báo sai/Lỗi tăng từ 12 lên 18; chênh lệch +6.” Câu này hợp lệ khi đã được tính và grounding.

**Diagnostic:** “Do camera xuống cấp” không được ba KPI hiện tại chứng minh và MUST NOT được khẳng định. Khi người dùng hỏi nguyên nhân, hệ thống có thể trả: “Dữ liệu KPI hiện tại chưa xác định được nguyên nhân; cần đối chiếu issue log hoặc dữ liệu kỹ thuật.” Hypothesis chỉ được hiển thị khi có nhãn rõ ràng để con người kiểm chứng, không được coi là verified cause.

- `AI-TR-040`: Narrative MUST gắn nhãn observation/fact và hypothesis; không có unsupported causal/action claim.
- `AI-TR-041`: Nêu limitation cho missing date, chuỗi quá ngắn, kỳ so sánh incomplete, unit không tương thích hoặc evidence không resolve được.

## 5. Hành vi UI dự kiến

Entry point là khu vực **Phân tích xu hướng bằng AI** nằm sau KPI và biểu đồ chính trong Overview. Dashboard giữ vai trò nguồn định lượng chính; tính năng AI là lớp diễn giải bổ sung và không thu hẹp vùng biểu đồ trên desktop. Runtime chỉ tạo phân tích cho `scope=node`; khi người dùng chọn `scope=children`, entry point vẫn hiện với CTA bị khóa, lý do dễ hiểu và thao tác chuyển về “Entity đã chọn”. Người dùng chọn metric và nhóm ngày/tuần/tháng rồi chủ động yêu cầu phân tích. Thay filter hoặc nhóm kỳ làm kết quả cũ stale cho tới khi tạo lại. UI ưu tiên tổng quan phân tích và xu hướng trước; bảng từng kỳ, bằng chứng, chất lượng dữ liệu và metadata kỹ thuật dùng cơ chế mở rộng/thu gọn. Kết quả hiển thị biên nhận phạm vi gồm entity, exact date range, metric và grain; biên nhận không đổi khi stale. Live region chỉ chứa trạng thái ngắn, không bọc toàn bộ kết quả, và focus quay về CTA sau khi request hoàn tất/lỗi. UI vẫn hiển thị data version/as-of, fact toàn khoảng, pattern toàn chuỗi, delta/% từng kỳ, evidence link, quality indicator, generation/validation state, retry và deterministic-only fallback. Không bao giờ thay số trên core chart bằng số do model sinh.

- `AI-TR-050`: Phân biệt loading, ready, insufficient data, provider unavailable, validation rejected và stale.
- `AI-TR-051`: Mỗi insight mở đúng source/evidence; legacy data không có safe ref phải hiện unavailable, không heuristic lookup.
- `AI-TR-052`: Không được hiển thị generated answer cũ như current sau khi filter hoặc committed data version thay đổi.

### Ưu tiên toàn chuỗi — runtime 02/10/2026

- `AI-TR-053`: Mục tiêu cao nhất là hiểu KPI diễn biến trong toàn khoảng, không ưu tiên first/last. Thứ tự nội dung: bức tranh toàn khoảng → giai đoạn → mốc quan trọng → quan hệ có fact tương ứng → hạn chế → đầu–cuối bổ sung. Cảnh báo dữ liệu quan trọng vẫn hiển thị sớm để tránh đọc sai.
- `AI-TR-054`: `chronological-stages-v1` chia các chuyển kỳ lịch liền nhau thành đoạn tăng/giảm/giữ nguyên tối đa, giữ đúng thứ tự. Missing period ngắt đoạn và không được nối thành consecutive run. Turning point chỉ là đảo chiều tăng ↔ giảm quan sát được giữa hai đoạn kề nhau; không phải anomaly/significance. Plateau là một giai đoạn riêng.
- `AI-TR-055`: Summary ưu tiên cấu trúc toàn chuỗi, không dùng endpoint đại diện trend. Runtime có `synthesis` dùng claims v3 với relation facts và diễn đạt tương đương có giới hạn; không yêu cầu khớp nguyên văn `temporalStructure.summaryText`. Exact-copy v1/v2 chỉ giữ cho snapshot legacy không có synthesis. UI giữ đủ các đoạn ở chi tiết thu gọn.
- `AI-TR-057`: Synthesis chọn tối đa hai nhận định grounded; ưu tiên reversal, endpoint che khuất diễn biến, peak-retreat/trough-recovery và cross-metric. Thiếu insight rõ ràng phải mô tả trung tính, không tự tạo threshold hoặc significance.
- `AI-TR-058`: Quan hệ count/rate dùng mọi chuyển tiếp liền nhau trong đoạn đã căn chỉnh, cùng scope/grain và đầy đủ contributor operands; không suy ra từ endpoint. Quan hệ lệch peak yêu cầu peak duy nhất, căn cứ ranking và các kỳ hỗ trợ. Không nối qua kỳ thiếu hoặc dùng kỳ tuần/tháng không đầy đủ.
- `AI-TR-059`: Numerical/date anchors, limitations và suggested checks do backend tạo từ captured facts; model chỉ diễn đạt nhận định đã xác nhận, không tự thêm số hoặc ngày. Mỗi check gắn candidate và evidence cụ thể.
- `AI-TR-060`: Hai kỳ chỉ cho `period_comparison`, không peak/trough/sustained; ba kỳ là `short_sequence`. Ngôn ngữ xu hướng/“qua các kỳ” cần ít nhất bốn kỳ liên tiếp trong đoạn thực sự được diễn giải. Không cộng số kỳ hai phía missing để đạt ngưỡng.
- `AI-TR-061`: Liên hệ ba KPI dựa trên chiều biến động đã kiểm chứng của Tổng số, Báo sai/Lỗi và tỷ lệ trong cùng đoạn liền nhau, cùng scope/grain/contributors. Giải thích khác biệt giữa số lượng và tỷ trọng; bao gồm số lỗi không đổi nhưng tỷ lệ thay đổi, số lỗi giảm nhưng tỷ trọng tăng, và tốc độ tương đối qua phép tính tỷ lệ. Ghi operandFactIds, evidenceIds và phạm vi. Không nối gap, tính correlation, suy diễn nhân quả hoặc chất lượng.
- `AI-TR-062`: Cross-metric candidate thay thế primary ngắn/descriptive yếu khi có căn cứ, tránh lặp metric template trước insight. Primary reversal có ý nghĩa vẫn được giữ. Tương quan mô tả không tự xác nhận trend toàn khoảng.
- `AI-TR-056`: UI giữ các đoạn theo thời gian, cả largestIncrease/largestDecrease có ngày và đơn vị, extrema, turning points và historical context có sẵn. Endpoint nằm trong disclosure bổ sung. Quan hệ liên KPI hiện có vẫn là endpoint-only và phải ghi nhãn rõ; không suy diễn quan hệ theo giai đoạn nếu chưa có corresponding fact.

## 6. Ví dụ minh họa

Input theo tuần: metric `Báo sai/Lỗi`, ba kỳ hợp lệ có value `120, 105, 87`. Hai interval fact lần lượt là `-15 (-12,5%)` và `-18 (-17,14%)`; fact đầu–cuối là `-33 (-27,5%)`; pattern là `consistently_decreasing`. Narrative hợp lệ: “Báo sai/Lỗi giảm qua cả hai lần chuyển kỳ; kỳ cuối thấp hơn kỳ đầu 33 (27,5%).” Câu này không ngụ ý verified cause.

## 7. Edge case phải test

Không có data; toàn missing; valid zero; zero denominator; zero baseline; chỉ một valid period; khoảng thiếu kỳ ở giữa; chuỗi tăng liên tục/giảm liên tục/không đổi/dao động; valid-day coverage không bằng nhau; rate theo pp so với relative %; source-rate so với weighted aggregate; first/last period incomplete; quá 60 kỳ; duplicate date; stale snapshot; revision cũ vẫn trace được sau import mới; provider timeout; LLM claim sai hoặc bịa; project/entity ref ngoài scope.

## 8. Phụ thuộc và nghiệm thu

Phụ thuộc core read model, data model, time grouping, exact/aggregate lineage và privacy approval. Acceptance canonical nằm trong [05-ai-evaluation-and-acceptance.md](05-ai-evaluation-and-acceptance.md), namespace `AI-ACC-TR-*`. Không dùng stable/anomaly/coverage threshold chưa được duyệt.
