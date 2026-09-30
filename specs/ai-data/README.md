# Đặc tả AI/Data — Báo cáo CX tự động

- Phiên bản đặc tả: **2.2.0**
- Ngày phát hành: **2026-09-25**
- Trạng thái runtime: **PHASE 1 ĐÃ TRIỂN KHAI; external provider đã bật và kiểm thử cho môi trường hiện tại; môi trường mới mặc định tắt**
- Tương thích: thay thế bộ contract nháp `AI-*` / `ACC-AI-*` bằng các namespace module rõ ràng.

Phiên bản 2.2.0 mô tả đúng runtime Phase 1 hiện tại: dữ liệu committed đã chuẩn hóa, chuỗi kỳ ngày/tuần/tháng, evidence typed, output validation và privacy gate. Các phần comparison/reporting vẫn là đặc tả đề xuất, không phải tính năng đã triển khai.

## Quản trị trạng thái và phạm vi

| Năng lực | Trạng thái | Quan hệ với sản phẩm |
|---|---|---|
| Tóm tắt xu hướng bằng AI | **Đã triển khai Phase 1; privacy gate hiện tại đã duyệt, synthetic/live smoke pass** | `SCP-102`, `PRD-F102`, `UC-10`; bằng chứng tại [08-phase-1-runbook-and-evidence.md](08-phase-1-runbook-and-evidence.md) |
| Phân tích so sánh bằng AI | **Đề xuất, chờ phê duyệt** | `AI-SCP-002`; mở rộng từ workspace so sánh deterministic hiện có |
| Báo cáo AI theo mẫu | **Đề xuất, chờ phê duyệt** | `AI-SCP-003`; phụ thuộc quyết định về template, lưu trữ, reviewer và export |
| Sinh/gửi báo cáo theo lịch | **Cần quyết định** | `AI-SCP-101`; tách biệt với scheduled import và sinh bản nháp |
| Phân tích nguyên nhân từ issue/ticket | **Cần quyết định** | `AI-SCP-102`; cần nguồn dữ liệu có owner riêng |

Yêu cầu ở trạng thái **Đề xuất** chỉ là đầu vào thiết kế, chưa phải cam kết phạm vi. Hiện chỉ có AI Trend Summary là as-built. Comparison, report draft, approval/export và scheduling chưa được triển khai.

## Chủ sở hữu contract canonical

| Tài liệu | ID canonical |
|---|---|
| [00-ai-scope-and-roadmap.md](00-ai-scope-and-roadmap.md) | `AI-SCP-*` |
| [01-ai-trend-analysis.md](01-ai-trend-analysis.md) | `AI-TR-*` |
| [02-ai-comparative-analysis.md](02-ai-comparative-analysis.md) | `AI-CMP-*` |
| [03-automated-reporting.md](03-automated-reporting.md) | `AI-RPT-*` |
| [04-ai-data-and-output-contracts.md](04-ai-data-and-output-contracts.md) | `AI-CON-*` |
| [05-ai-evaluation-and-acceptance.md](05-ai-evaluation-and-acceptance.md) | `AI-ACC-*` |
| [06-decisions-and-delivery-plan.md](06-decisions-and-delivery-plan.md) | `AI-DEC-*` |
| [07-vertical-slice-implementation-plan.md](07-vertical-slice-implementation-plan.md) | `AI-PLAN-*` |
| [08-phase-1-runbook-and-evidence.md](08-phase-1-runbook-and-evidence.md) | Runbook, known limitation và bằng chứng Phase 1 |
| [ai-reporting-model.md](ai-reporting-model.md) | Hồ sơ triển khai v2 và bảng chuyển đổi v1; không sở hữu namespace yêu cầu riêng |

Các ID cũ `AI-001`–`AI-028` và `ACC-AI-001`–`ACC-AI-010` đã ngừng sử dụng. Thay đổi mới MUST dùng các ID canonical ở trên. Bảng ánh xạ nằm trong [ai-reporting-model.md](ai-reporting-model.md); không được tái sử dụng ID cũ với ý nghĩa mới.

## Ranh giới nguồn sự thật

Core là nguồn canonical cho Excel ingestion, parser rule, metric code, identity của entity/observation, import/revision, missing-value semantics, aggregation, current view và provenance. AI/Data chỉ đọc dữ liệu committed qua adapter read-only và MUST không diễn giải lại hoặc ghi đè KPI nguồn.

Các sự thật hiện tại của core mà AI/Data phải giữ nguyên:

- metric code gồm `total`, `error`, `error_rate`; label hiển thị là metadata riêng;
- evidence exact là cặp `observationRef + lineageRef`;
- evidence aggregate là một `aggregateRef` sở hữu immutable snapshot và danh sách contributor;
- public contract dùng reference opaque như `importRef`; số nguyên `run_id` nội bộ không phải định danh public/UI;
- tỷ lệ lỗi theo kỳ dùng quy tắc chart hiện tại: mẫu số dương dùng weighted ratio; `0/0` trả `0%`; các trường hợp mẫu số 0 khác trả unavailable;
- missing khác zero và source marker vẫn là missing;
- comparison chỉ áp dụng cho entity tương thích trong cùng project và effective unit;
- chỉ dữ liệu đã commit mới được phân tích; preview data bị loại trừ.

## Luồng end-to-end Phase 1

`Committed core data -> in-memory pinned analytical snapshot -> deterministic facts -> typed evidence -> 9Router narrative tùy chọn -> kiểm tra schema/grounding -> AI Insights panel`.

Lỗi AI/provider phải fallback về deterministic facts và trạng thái unavailable rõ ràng, không được chặn import, dashboard, lineage hoặc việc export dữ liệu core hiện có.

Kế hoạch cài đặt canonical nằm tại [07-vertical-slice-implementation-plan.md](07-vertical-slice-implementation-plan.md). Shared `AnalyticsEngine`, `EvidenceBuilder`, `LLMAdapter`, `OutputValidator`, `AIApplicationService`, `PromptRegistry` và `AnalysisSnapshotRepository` đã được tạo trong Phase 1 để phase sau mở rộng, không xây lại.

## Thay đổi trong phiên bản 2.2.0

- mở rộng Trend Summary từ hai điểm sang ordered period series theo ngày/tuần/tháng;
- thêm absolute/relative change và direction cho từng cặp kỳ liên tiếp, cùng pattern tăng liên tục/giảm liên tục/không đổi/dao động cho toàn chuỗi;
- giữ so sánh kỳ đầu–cuối như fact tổng quan nhưng không dùng nó để suy diễn monotonicity;
- thêm evidence cho từng kỳ, coverage kỳ, cảnh báo kỳ thiếu và giới hạn request tối đa 60 kỳ;
- nâng API response lên `ai-trend-v2`, prompt lên `trend-summary-v2` và bổ sung bảng biến động từng kỳ trên UI.

## Thay đổi trong phiên bản 2.1.0

- triển khai Trend Summary theo vertical slice backend → AI → validation → frontend → testing;
- chỉ đọc committed normalized current view; không dùng preview/raw workbook;
- thêm exact/aggregate evidence, opaque committed import ref, checksum và stale detection;
- thêm adapter 9Router, explicit model check, timeout/retry giới hạn và deterministic fallback;
- thêm feature flag kép: `EVP_AI_ENABLED` và privacy gate `EVP_AI_EXTERNAL_ALLOWED`, đều mặc định `false`;
- lưu snapshot Phase 1 trong bộ nhớ có giới hạn, không persist prompt/response của provider;
- thêm runbook và test evidence; real-provider smoke vẫn opt-in và chưa được tính pass khi privacy gate chưa duyệt.

## Thay đổi trong phiên bản 2.0.0

- loại bỏ hai bộ ý nghĩa trùng nhau của `AI-DEC-001`–`AI-DEC-006`;
- thay ownership hỗn hợp `AI-*` và `ACC-AI-*` bằng namespace theo module;
- sửa `error_count` và ví dụ dùng display label làm code thành metric code canonical `error`;
- đồng bộ quy tắc mẫu số 0 với implementation của chart;
- thay evidence string mơ hồ bằng exact/aggregate evidence target có kiểu rõ ràng;
- thay public integer source-run watermark bằng `committedImportRef` opaque và snapshot identity;
- tách development provider đã chọn là 9Router khỏi bước phê duyệt privacy/security còn thiếu;
- giữ report persistence, reviewer approval, export và scheduling ở đúng trạng thái Đề xuất hoặc Cần quyết định.
