# Đặc tả AI/Data — Automated CX Report

## Tab Báo cáo đã triển khai — 05/10/2026

[As-built và hướng dẫn](12-report-workspace-as-built.md): bản nháp năm phần, snapshot/revision durable, diễn giải có kiểm chứng, chọn/bỏ điểm đề xuất và xuất **PDF/DOCX** theo exact revision. Người dùng đã xác nhận hai định dạng và quyền chọn điểm. Template `cx-period-report` 1.0 là bản draft; mẫu cuối và authenticated approval vẫn chưa có. [Kế hoạch gốc](11-report-workspace-plan.md), [đánh giá LLM thật và kiểm chứng export](evidence/2026-10-05-reports-review.md). Không thay prompt/context policy hiện có.

## Mở rộng theo ngữ cảnh — 04/10/2026

Mốc mới nhất: `context-insight-v5`, `grounded-synthesis-v5`, `semantic-grounding-v9`. Thống kê có fact liên hệ Tổng số/Số lỗi cùng kỳ; Tổng quan chuyển đủ comparisonBasis; phần mở đầu nêu khác biệt giữa tổng và trung bình/ngày khi chúng đổi chiều khác nhau. Gom hạn chế dữ liệu và tránh lặp so sánh hai kỳ. Không thay công thức KPI, không tính correlation hoặc suy diễn nguyên nhân nghiệp vụ. [Đánh giá triển khai và API thật](evidence/2026-10-04-linked-insight-review.md). Các mốc v4/v3/v2 bên dưới là lịch sử.

Đồng nhất template mới nhất: `context-insight-v4.md` / policy context-insight-v4. Thống kê gom theo vấn đề, tách Trung bình/ngày và Tổng trong kỳ bên trong; Tổng quan và Thống kê dùng chung renderer nhãn giai đoạn/đoạn văn. Không đổi phép tính KPI, schema v1 hoặc validator. [Chạy lại API thật và đánh giá template](evidence/2026-10-04-template-scope-review.md). Các mốc v3/v2 bên dưới là lịch sử.

Cập nhật mới nhất: prompt `context-insight-v3.md` bổ sung số đầu/sau và chênh lệch đã tính sẵn vào các nhịp đáng chú ý. Provider candidates có `quantitativeEvidence`, không tự tính mức thay đổi của giai đoạn dài. [Đánh giá định lượng trên API thật](evidence/2026-10-04-context-quantified-review.md). Đoạn dưới mô tả mốc v2 trước cập nhật này.

Đã triển khai phân tích riêng từ biểu đồ, AI trong Thống kê và tập vấn đề selected/all con trực tiếp. Contract context-v1 giữ nguyên; prompt hiện là context-insight-v2, semantic policy dùng chung v8; registry legacy v15/v11 giữ nguyên. [As-built và giới hạn](10-context-insight-as-built.md), [đánh giá API thật trước/sau cải thiện](evidence/2026-10-04-context-quality-review.md). Chưa có cache mới hoặc nghiệm thu chất lượng narrative production tổng quát. Các phần có ngày cũ bên dưới là lịch sử, không ghi đè trạng thái này.

## Freeze và kế hoạch mở rộng — 04/10/2026

Baseline đã đóng băng tại commit `daa3974`, tag `freeze-2026-10-04-ai-insights-v15`, đã push lên origin/dev. [Biên bản freeze](evidence/2026-10-04-freeze.md) ghi kiểm thử và giới hạn. [Kế hoạch mở rộng](09-insight-expansion-plan.md) sau đó đã được người dùng duyệt triển khai; mốc freeze vẫn giữ nguyên.

## Kiểm tra mọi bộ lọc và dữ liệu committed — 02/10/2026

Runtime mới nhất dùng provider/narrative v5, `semantic-grounding-v6`, registry `trend-summary-v15` / `metric-overview-v11`, resource `grounded-insight-v5.md`. Ngày/tuần/tháng và KPI đơn/tổng hợp dùng đúng phạm vi, nhãn kỳ và facts của request; không gán giá trị tuần/tháng cho một ngày. Report giữ mọi giai đoạn, kể cả điểm rời do thiếu dữ liệu; chỉ giới hạn tối đa tám giai đoạn gửi LLM, phần còn lại dùng Engine. Đỉnh/đáy tiếp tục nằm trong diễn giải giai đoạn, không có heading riêng. Kiểm tra 2.040 tổ hợp trên 34 entity có dữ liệu thuộc sáu dự án; đánh giá API thật và những hạn chế còn lại được ghi tại [báo cáo kiểm thử toàn dữ liệu](evidence/2026-10-02-all-data-filter-evaluation.md). Các mục phiên bản bên dưới là lịch sử triển khai.

## Báo cáo theo giai đoạn và mốc đỉnh/đáy — 02/10/2026

Runtime generation hiện dùng provider/narrative v5, `semantic-grounding-v5`, registry `trend-summary-v14` / `metric-overview-v10`, resource `grounded-insight-v5.md`. Report gồm overview, phases và relationships. Đỉnh/đáy từ Engine được lồng trong giai đoạn chứa mốc qua `semanticSpec.phaseExtrema`, không có section hoặc heading extrema riêng. Giữ tất cả ngày đồng mức trong giai đoạn; không tạo extrema khi chưa có bốn kỳ hợp lệ hoặc KPI không đổi. Paragraph thiếu/bị loại dùng facts Engine và đánh dấu nguồn deterministic, không loại cả report. Desktop-first; không mở rộng tối ưu mobile. [Kiểm thử và đánh giá API thật](evidence/2026-10-02-phase-extrema-report.md).

## Cập nhật validator và prompt — 02/10/2026

Narrative v4 hiện dùng `semantic-grounding-v4`, prompt registry `trend-summary-v13` / `metric-overview-v9`. Validator chấp nhận value hoặc displayValue do Engine cung cấp, tách ngày phạm vi khỏi ngày điểm dữ liệu và giải quyết chủ ngữ trong từng câu. Prompt và selection guidance ưu tiên quan hệ ba KPI hơn lệch ngày đạt đỉnh. Giữ source/unit/scope/contradiction gates; không đổi UI hoặc phép tính KPI. [Chi tiết và kết quả kiểm thử cuối bằng API thật](evidence/2026-10-02-validator-v4-and-prompt-evaluation.md). [Chính sách v3 trước đó](evidence/2026-10-02-data-first-validator.md) và các ghi nhận v2/v3 bên dưới là lịch sử triển khai.

- Phiên bản đặc tả: **2.2.0**
- Ngày phát hành: **2026-09-25**
- Trạng thái runtime: **PHASE 1 ĐÃ TRIỂN KHAI; external provider đã bật và kiểm thử cho môi trường hiện tại; môi trường mới mặc định tắt**

## Cập nhật analytical overview — 02/10/2026

`metricCode=all` giữ `ai-overview-v2`, single-metric giữ `ai-trend-v3`. Runtime mới dùng provider input/narrative v3, prompt registry `trend-summary-v8` / `metric-overview-v4`, cùng resource `grounded-insight-v3.md`. Layer `grounded-synthesis-v1` nhóm facts thành tối đa hai nhận định: diễn biến chính và quan hệ KPI đủ căn cứ. Không bắt model sao chép nguyên đoạn canonical; validator cho phép diễn đạt tương đương trong grammar có giới hạn, khóa metric, chiều, phạm vi và citations. UI ưu tiên summary, anchors, limitation đã gom và kiểm tra liên quan; toàn bộ chronology/extrema/turns/history/endpoint ở phần thu gọn. Xem [bằng chứng triển khai synthesis](evidence/2026-10-02-grounded-analytical-insights.md). Không thay core KPI hoặc weighted pair rule hiện có. `AI-TR-013` về daily source percentage cần được làm rõ trước khi mở rộng sang source-rate khác rule hiện tại.

UI desktop-first: tổng quan → cơ sở quan hệ → diễn biến → kiểm tra → chi tiết; material limitations đặt trước kết luận. Không mở rộng tối ưu mobile, report approval/export, turning point, peak alignment hoặc anomaly trong MVP này. Rule complete aligned endpoints là baseline bảo thủ của implementation, không phải threshold đáng kể/chất lượng được suy đoán. Xem [contract](04-ai-data-and-output-contracts.md) và [nghiệm thu](05-ai-evaluation-and-acceptance.md).
- Tương thích: thay thế bộ contract nháp `AI-*` / `ACC-AI-*` bằng các namespace module rõ ràng.

Phiên bản 2.2.0 mô tả đúng runtime Phase 1 hiện tại: dữ liệu committed đã chuẩn hóa, chuỗi kỳ ngày/tuần/tháng, evidence typed, output validation và privacy gate. Các phần comparison/reporting vẫn là đặc tả đề xuất, không phải tính năng đã triển khai.

## Quản trị trạng thái và phạm vi

### Semantic validator và live evaluation — 02/10/2026

Generation mới dùng provider/narrative v4, registry `trend-summary-v12` / `metric-overview-v8`, resource `grounded-insight-v4.md`. Kiểm tra riêng cấu trúc, grounding, số/ngày và predicate; salvage theo claim. Legacy v3 giữ grammar cũ. Extractor ngữ nghĩa có giới hạn tiếng Việt; ba lần live trên cùng phạm vi cho thấy số/ngày đúng nhưng diễn giải chưa sâu, lần cuối `ready/partial`. Xem [audit, hợp đồng và bằng chứng live](evidence/2026-10-02-semantic-validator-and-live-evaluation.md). Các mục runtime v3 bên dưới mô tả phiên bản trước.

### Quan hệ KPI và giới hạn số kỳ — 02/10/2026

Runtime mới nhất: `grounded-synthesis-v4`, registry `trend-summary-v11` / `metric-overview-v7`, resource `grounded-insight-v3.md`, narrative v3. Hai kỳ chỉ so sánh; ba kỳ mô tả thứ tự quan sát; từ bốn kỳ liên tiếp mới cho phép ngôn ngữ xu hướng. Liên hệ ba KPI giải thích số lỗi, Tổng số và tỷ trọng trong cùng đoạn căn chỉnh; không tính Pearson, hệ số correlation hoặc áp dụng ngưỡng sáu kỳ. Không suy diễn nguyên nhân hoặc chất lượng từ tỷ lệ.

| Năng lực | Trạng thái | Quan hệ với sản phẩm |
|---|---|---|
| Tóm tắt xu hướng bằng AI | **Đã triển khai Phase 1; privacy gate hiện tại đã duyệt, synthetic/live smoke pass** | `SCP-102`, `PRD-F102`, `UC-10`; bằng chứng tại [08-phase-1-runbook-and-evidence.md](08-phase-1-runbook-and-evidence.md) |
| Phân tích so sánh bằng AI | **Đề xuất, chờ phê duyệt** | `AI-SCP-002`; mở rộng từ workspace so sánh deterministic hiện có |
| Báo cáo AI theo mẫu | **Bản nháp v1 đã triển khai; formal approval chưa có** | `AI-SCP-003`; năm phần, SQLite revisions, PDF/DOCX; template cuối/reviewer/retention vẫn cần quyết định |
| Sinh/gửi báo cáo theo lịch | **Cần quyết định** | `AI-SCP-101`; tách biệt với scheduled import và sinh bản nháp |
| Phân tích nguyên nhân từ issue/ticket | **Cần quyết định** | `AI-SCP-102`; cần nguồn dữ liệu có owner riêng |

Yêu cầu ở trạng thái **Đề xuất** chỉ là đầu vào thiết kế, chưa phải cam kết phạm vi. AI Insight theo ngữ cảnh và report draft/export nêu ở các mốc mới nhất phía trên đã as-built. AI comparative narrative, formal approval và scheduling chưa triển khai.

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
- nâng API response từng metric lên `ai-trend-v3`, tổng quan đa metric lên `ai-overview-v1`, prompt lên `trend-summary-v6`; bổ sung period-level analytics deterministic và bối cảnh tối đa 12 kỳ hợp lệ liền trước để narrative diễn giải rõ hơn mà không tự tính;
- hỗ trợ `metricCode=all`: tổng hợp `total`, `error`, `error_rate` trong một snapshot, một provider call và một narrative chung; fact/evidence được namespace theo metric;
- tối ưu latency bằng model `ag/gemini-3.7-flash-low`, prompt/payload rút gọn, output tối đa 700 token, timeout 12 giây và không retry request tương tác.

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

Cấu trúc đọc analytical-reading-v1: tổng quan → giai đoạn chung giữa các KPI → điều cần chú ý (nếu có ý mới) → một mục đóng “Xem số liệu và nguồn”. Câu ngắn, chủ ngữ rõ; không dùng “toàn khoảng”, volume, endpoint hoặc thuật ngữ toán học trong nội dung đọc. Không thêm provider call.
