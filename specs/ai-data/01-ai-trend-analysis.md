# 01 — Đặc tả phân tích xu hướng bằng AI

**Phiên bản đặc tả:** 2.3.0. **Trạng thái:** Phase 1 as-built cho scope `node`, chuỗi kỳ `day|week|month` và comparison basis `period_over_period_and_first_last`; stable/anomaly/report vẫn chưa triển khai. **Contract IDs:** `AI-TR-*`.

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
- `AI-TR-022`: Policy `period-series-v2` phân loại toàn chuỗi theo dấu của mọi delta liên tiếp: chỉ tăng/không đổi là `consistently_increasing`, chỉ giảm/không đổi là `consistently_decreasing`, toàn bộ bằng zero là `unchanged`, có cả tăng và giảm là `fluctuating`. So sánh đầu–cuối vẫn được giữ như fact tổng quan nhưng không thay cho bằng chứng toàn chuỗi.
- `AI-TR-023`: Previous-period comparison MUST nêu exact date boundary và comparability/coverage; kỳ không bằng nhau, partial hoặc missing-heavy MUST được cảnh báo. Cùng elapsed time chưa đủ nếu valid-day coverage khác đáng kể.
- `AI-TR-024`: Khoảng không có kỳ hợp lệ MUST được ghi trong limitation; hệ thống không chèn kỳ thiếu dưới dạng zero. Request tạo quá 60 kỳ MUST bị từ chối và yêu cầu chọn grain lớn hơn hoặc thu hẹp khoảng; không âm thầm cắt chuỗi.

### 3.3. Thay đổi đáng chú ý

- `AI-TR-030`: Candidate change detection MUST dùng deterministic versioned policy, ví dụ largest valid day-over-day delta, approved absolute/relative threshold hoặc baseline deviation. Policy/threshold vẫn **TBD**, LLM không được tự đoán.
- `AI-TR-031`: Phân biệt rõ “largest observed change” với “statistical anomaly”. Không được claim anomaly khi chưa có detector và calibration đã duyệt.
- `AI-TR-032`: Mỗi flagged point MUST có date/period, measured value, comparator, change, valid coverage và exact/aggregate evidence.
- `AI-TR-033`: Khi sample size hoặc coverage không đủ, trả `insufficient_data` thay vì xu hướng chắc chắn.

## 4. Ranh giới mô tả và chẩn đoán

**Descriptive:** “Trong giai đoạn đã chọn, Báo sai/Lỗi tăng từ 12 lên 18; chênh lệch +6.” Câu này hợp lệ khi đã được tính và grounding.

**Diagnostic:** “Do camera xuống cấp” không được ba KPI hiện tại chứng minh và MUST NOT được khẳng định. Khi người dùng hỏi nguyên nhân, hệ thống có thể trả: “Dữ liệu KPI hiện tại chưa xác định được nguyên nhân; cần đối chiếu issue log hoặc dữ liệu kỹ thuật.” Hypothesis chỉ được hiển thị khi có nhãn rõ ràng để con người kiểm chứng, không được coi là verified cause.

- `AI-TR-040`: Narrative MUST gắn nhãn observation/fact và hypothesis; không có unsupported causal/action claim.
- `AI-TR-041`: Nêu limitation cho missing date, chuỗi quá ngắn, kỳ so sánh incomplete, unit không tương thích hoặc evidence không resolve được.

## 5. Hành vi UI dự kiến

Entry point là khu vực **Phân tích xu hướng bằng AI** nằm sau KPI và biểu đồ chính trong Overview. Dashboard giữ vai trò nguồn định lượng chính; tính năng AI là lớp diễn giải bổ sung và không thu hẹp vùng biểu đồ trên desktop. Runtime chỉ tạo phân tích cho `scope=node`; khi người dùng chọn `scope=children`, entry point vẫn hiện với CTA bị khóa, lý do dễ hiểu và thao tác chuyển về “Entity đã chọn”. Người dùng chọn metric và nhóm ngày/tuần/tháng rồi chủ động yêu cầu phân tích. Thay filter hoặc nhóm kỳ làm kết quả cũ stale cho tới khi tạo lại. UI ưu tiên tổng quan phân tích và xu hướng trước; bảng từng kỳ, bằng chứng, chất lượng dữ liệu và metadata kỹ thuật dùng cơ chế mở rộng/thu gọn. Kết quả hiển thị biên nhận phạm vi gồm entity, exact date range, metric và grain; biên nhận không đổi khi stale. Live region chỉ chứa trạng thái ngắn, không bọc toàn bộ kết quả, và focus quay về CTA sau khi request hoàn tất/lỗi. UI vẫn hiển thị data version/as-of, fact toàn khoảng, pattern toàn chuỗi, delta/% từng kỳ, evidence link, quality indicator, generation/validation state, retry và deterministic-only fallback. Không bao giờ thay số trên core chart bằng số do model sinh.

- `AI-TR-050`: Phân biệt loading, ready, insufficient data, provider unavailable, validation rejected và stale.
- `AI-TR-051`: Mỗi insight mở đúng source/evidence; legacy data không có safe ref phải hiện unavailable, không heuristic lookup.
- `AI-TR-052`: Không được hiển thị generated answer cũ như current sau khi filter hoặc committed data version thay đổi.

## 6. Ví dụ minh họa

Input theo tuần: metric `Báo sai/Lỗi`, ba kỳ hợp lệ có value `120, 105, 87`. Hai interval fact lần lượt là `-15 (-12,5%)` và `-18 (-17,14%)`; fact đầu–cuối là `-33 (-27,5%)`; pattern là `consistently_decreasing`. Narrative hợp lệ: “Báo sai/Lỗi giảm qua cả hai lần chuyển kỳ; kỳ cuối thấp hơn kỳ đầu 33 (27,5%).” Câu này không ngụ ý verified cause.

## 7. Edge case phải test

Không có data; toàn missing; valid zero; zero denominator; zero baseline; chỉ một valid period; khoảng thiếu kỳ ở giữa; chuỗi tăng liên tục/giảm liên tục/không đổi/dao động; valid-day coverage không bằng nhau; rate theo pp so với relative %; source-rate so với weighted aggregate; first/last period incomplete; quá 60 kỳ; duplicate date; stale snapshot; revision cũ vẫn trace được sau import mới; provider timeout; LLM claim sai hoặc bịa; project/entity ref ngoài scope.

## 8. Phụ thuộc và nghiệm thu

Phụ thuộc core read model, data model, time grouping, exact/aggregate lineage và privacy approval. Acceptance canonical nằm trong [05-ai-evaluation-and-acceptance.md](05-ai-evaluation-and-acceptance.md), namespace `AI-ACC-TR-*`. Không dùng stable/anomaly/coverage threshold chưa được duyệt.
