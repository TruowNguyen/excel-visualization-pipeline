# 02 — Đặc tả phân tích so sánh bằng AI

**Phiên bản đặc tả:** 2.0.0. **Trạng thái:** Đề xuất / CHƯA TRIỂN KHAI; cần owner phê duyệt. **IDs:** `AI-CMP-*`.

## 1. Mục tiêu và kiểu so sánh được hỗ trợ

Dùng observation và aggregation đã được core kiểm chứng để giải thích khác biệt giữa **2–3 entity trong cùng một project**, hoặc giữa current/reference period của một entity. Hiển thị khác biệt, biến động, coverage và hướng kiểm tra có căn cứ từ observation thực tế.

**MVP mode:** (A) entity-to-entity trong cùng period; (B) period-over-period cho cùng entity. **Giai đoạn sau, cần phê duyệt:** baseline deviation và multi-project comparison sau khi chuẩn hóa metric/business definition.

## 2. Đầu vào và điều kiện hợp lệ

- `AI-CMP-001`: Entity comparison MUST dùng constraint hiện tại của core: cùng project, effective unit tương thích và chọn 2–3 entity. Chỉ so sánh khác hierarchy level khi scope/unit contract của core cho phép; không rollup parent+child ngầm.
- `AI-CMP-002`: Mọi entity MUST dùng cùng metric definition, reporting period, granularity và approved aggregation rule.
- `AI-CMP-003`: Comparison MUST công khai observed coverage có thể so sánh theo entity/kỳ. Missing, invalid hoặc incomplete period MUST được cảnh báo, không âm thầm đổi thành zero.
- `AI-CMP-004`: Input không thể so sánh MUST trả `not_comparable` kèm lý do có thể xử lý; không sinh narrative tạo cảm giác comparison hợp lệ.
- `AI-CMP-005`: Reference window được duyệt MUST có date cụ thể và business definition tương thích; cấm dùng “tháng trước” mơ hồ hoặc calendar assumption ẩn.

## 3. Đầu ra so sánh tất định

Với từng entity/kỳ, trả project/entity ID và label, metric code/unit, date range, selected scope, valid count/coverage, aggregation rule, value, evidence ref và comparison eligibility status.

Comparative fact gồm absolute difference theo native unit; relative difference chỉ khi reference khác zero và hợp lệ; với rate metric, trả absolute percentage-point difference và optional relative percent có nhãn đúng. Direction dùng **higher/lower**, không tự suy ra better/worse. `Tổng số` cao có thể chỉ phản ánh volume; `% báo sai` cao có ý nghĩa vận hành khác. Không chấm điểm hiệu suất nếu chưa có business objective và weighting được duyệt.

- `AI-CMP-010`: Arithmetic MUST đến từ deterministic analytics; LLM MUST NOT tính hoặc sửa numeric fact.
- `AI-CMP-011`: Aggregate `% báo sai` MUST dùng weighted sum của numerator/denominator đã duyệt, không dùng arithmetic mean của percentage.
- `AI-CMP-012`: Nếu có ranking/order, MUST nêu rõ numeric sort key và period; không được trình bày như đánh giá chất lượng toàn diện.
- `AI-CMP-013`: Comparison với approved baseline MUST có baseline source, value, unit, period và policy version.
- `AI-CMP-014`: Significant difference/alert cần threshold và coverage policy đã duyệt; nếu chưa có chỉ được gọi là “observed difference”.

## 4. Cấu trúc diễn giải

1. **Comparison scope:** project, entity, metric, exact period và hierarchy scope.
2. **Khác biệt đo được:** value và delta kèm evidence.
3. **Diễn biến theo thời gian:** chỉ khi hợp lệ và có thể so sánh.
4. **Quan sát đáng chú ý:** do deterministic policy chọn.
5. **Giới hạn dữ liệu:** missing date, coverage không tương thích, đổi unit, sample nhỏ.
6. **Kiểm tra đề xuất:** viết dưới dạng yêu cầu xác minh source, không khẳng định nguyên nhân.

- `AI-CMP-020`: Không được khẳng định diagnostic cause chỉ từ ba KPI hiện có.
- `AI-CMP-021`: Mọi material comparison claim MUST tham chiếu evidence/snapshot của cả hai phía, không chỉ entity được chọn hoặc có value cao.
- `AI-CMP-022`: Output MUST nêu rõ comparison unavailable thay vì điền model estimate.

## 5. Ví dụ minh họa

Entity A: 12 error trên 120 total, tương ứng 10%; entity B: 15 error trên 100 total, tương ứng 15%. Fact hợp lệ: aggregate error rate của B cao hơn A 5 percentage point trong cùng approved period, với điều kiện scope/coverage tương thích. Claim không hợp lệ: “Hệ thống B bị lỗi vì rate cao hơn.” Total/error nguồn phải được kiểm chứng và liên kết tới aggregate contributor tương ứng.

## 6. UI và trạng thái kết quả

Action tùy chọn từ core Compare workspace: **Giải thích so sánh**. Tái sử dụng entity/filter context đang chọn. Hiển thị fact và evidence trước narrative; hỗ trợ `not_comparable`, `insufficient_data`, `ready`, `stale`, `provider_unavailable`, `rejected_output`. Chart hiện tại vẫn dùng được khi AI offline. Side-by-side report phải chỉ ra data version đã đổi sau import.

## 7. Kịch bản đánh giá

Unit tương thích/không tương thích; project khác nhau; chọn 1/2/3/4 entity; parent so với child; date coverage không bằng nhau; month complete/incomplete; weighted rate; percentage-point label; reference bằng zero; thiếu baseline; provenance không resolve; provider bịa comparison; import mới làm comparison cũ stale.

Acceptance canonical: [05-ai-evaluation-and-acceptance.md](05-ai-evaluation-and-acceptance.md), namespace `AI-ACC-CMP-*`.
