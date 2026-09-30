# 06 — Sổ quyết định, phụ thuộc và kế hoạch triển khai

**Phiên bản đặc tả:** 2.2.0. **Trạng thái:** Tài liệu lập kế hoạch đang đề xuất. **IDs:** `AI-DEC-*`. Đây là owner duy nhất của `AI-DEC-*`; decision xuất hiện ở đây không tự động được coi là approved.

## 1. Quyết định cần mentor/product owner chốt

| ID | Quyết định cần chốt | Lý do | Owner đề xuất |
|---|---|---|---|
| AI-DEC-001 | Duyệt việc mở rộng ngoài AI Trend Summary sang comparison và automated report | Thay đổi scope/acceptance | Mentor/PO |
| AI-DEC-002 | Cung cấp weekly/monthly report template thực tế và mandatory section | Tránh tự nghĩ ra business report format | Mentor/CX reviewer |
| AI-DEC-003 | Xác nhận audience, report language, editable/export format PDF/DOCX và approval authority | Xác định report lifecycle/output | Mentor/PO |
| AI-DEC-004 | Định nghĩa relatively stable, noteworthy movement và minimum valid coverage | Tránh threshold tùy ý và false certainty | Data owner + mentor |
| AI-DEC-005 | Định nghĩa source-percentage semantics, weighted aggregate eligibility và comparable period | Ngăn diễn giải KPI sai | Data owner + mentor |
| AI-DEC-006 | Duyệt production use của 9Router đã chọn: deployment region, allowed field, PII handling, retention/logging | Bắt buộc trước khi gửi CX data thật ra ngoài | Security/PO/maintainer |
| AI-DEC-007 | Xác định MVP entity/project scope đầu tiên và owner của gold benchmark | Giới hạn release evaluation | Mentor + data owner |
| AI-DEC-008 | Quyết định nơi lưu AI snapshot/report version và storage/retention policy | Bảo đảm reproducibility và audit | Backend/maintainer |
| AI-DEC-009 | Xác nhận issue/ticket diagnostic có thuộc scope không và ai sở hữu nguồn riêng | KPI hiện tại không chứng minh root cause | Mentor/PO |
| AI-DEC-010 | Quyết định scheduling/delivery/notification policy ở giai đoạn sau | Không đồng nghĩa với draft generation | Mentor/PO |
| AI-DEC-011 | Định nghĩa role/identity và access mechanism cho reviewer approval | Core API hiện chỉ dành cho trusted internal deployment, chưa có role-based authorization | Backend/PO |
| AI-DEC-012 | Duyệt external endpoint/UI shape, streaming mode, timeout và bounded retry policy | Bắt buộc trước khi đóng băng API/frontend behavior | Backend/Frontend/PO |
| AI-DEC-013 | Duyệt request/daily token-cost budget và golden-evaluation release threshold | Bắt buộc trước production enablement | PO/Data evaluation owner |

## 2. Các giai đoạn triển khai kỹ thuật

### Quyết định đã được xác nhận

`AI-DEC-006` được owner xác nhận cho môi trường hiện tại ngày **2026-09-25** với boundary `normalized_facts_only`. Hai gate runtime đã bật; model-catalog check, synthetic smoke và live normalized-data smoke đều pass. Approval này không tự áp dụng cho môi trường khác, comparison/reporting, raw workbook, issue text hoặc scheduled delivery.

Kế hoạch chi tiết canonical nằm tại [07-vertical-slice-implementation-plan.md](07-vertical-slice-implementation-plan.md). Không triển khai theo các horizontal layer độc lập; mỗi feature phải hoàn thành đủ backend, AI, validation, frontend và testing.

| Phase | Vertical slice | Shared component được tạo/mở rộng |
|---|---|---|
| 0 | Chốt decision và readiness gate | Chưa viết feature code |
| 1 | Trend Summary hoàn chỉnh | Tạo bản đầu của Analytics Engine, Evidence Builder, LLM Adapter, Output Validator |
| 2 | Comparative Insight hoàn chỉnh | Thêm strategy/policy/schema, tái sử dụng toàn bộ shared pipeline |
| 3 | Report Draft theo template | Thêm Report Composer/Template Registry, tái sử dụng snapshot/evidence/adapter/validator |
| 4 | Review, Approval và Export | Thêm identity, audit và export gate; không để LLM tham gia approval |
| 5 | Production hardening và rollout | Hardening các component hiện có, không thêm feature nghiệp vụ mới |

## 2.1. Baseline an toàn đã dùng cho Phase 1

Các lựa chọn dưới đây là baseline đã dùng để hoàn thiện implementation; trạng thái hiện tại được ghi riêng cho từng decision:

| Decision | Baseline Phase 1 | Trạng thái production |
|---|---|---|
| `AI-DEC-004` stable/noteworthy | Phân loại monotonic deterministic từ mọi delta từng kỳ; không phát claim relatively-stable/anomaly | Threshold stable/noteworthy vẫn cần data owner duyệt |
| `AI-DEC-005` metric semantics | Dùng nguyên core: count daily value; rate weighted, `0/0 -> 0%`, missing khác zero | Đã khóa cho ba metric hiện có |
| `AI-DEC-006` privacy/provider | Payload chỉ có token giả danh, canonical metric, date window, deterministic fact/series, coverage và logical evidence ID; không raw workbook, label entity/project hay opaque core ref | **Approved cho môi trường hiện tại**; môi trường mới vẫn default-off và cần approval riêng |
| `AI-DEC-007` scope/evaluation | Một project, một entity (`scope=node`), ba metric; synthetic fixture trong CI | Gold business fixture/human sign-off vẫn cần duyệt |
| `AI-DEC-008` persistence | Snapshot in-memory tối đa 100/process; không persist provider prompt/response; không thêm migration | Retention/reproducibility dài hạn vẫn cần quyết định trước report |
| `AI-DEC-012` API/operation | JSON non-streaming; timeout mặc định 20 giây; tối đa 1 retry cho timeout/429/5xx; không retry 401/403 | Có thể điều chỉnh bằng env sau operational review |
| `AI-DEC-013` cost/release | Không auto-call theo filter; chỉ user action; real smoke opt-in | Daily/token budget và production threshold vẫn cần PO duyệt |

Feature flag `EVP_AI_ENABLED` và privacy gate `EVP_AI_EXTERNAL_ALLOWED` độc lập, đều mặc định `false` trong `.env.example`; `.env` của môi trường hiện tại đã bật cả hai sau approval. Có API operator check model nhưng không tự chạy khi mở dashboard.

## 3. Phân công trách nhiệm đề xuất

- **Data/Evaluation:** metric/coverage gold fixture, kiểm chứng calculation, insight factuality và model evaluation.
- **Backend/Platform:** read-only adapter, analysis snapshot, ref, provider boundary, persistence, versioning và error.
- **Frontend/Product:** analyst workflow, insight evidence, report editing/preview, stale/unavailable state.
- **Mentor/PO:** report vocabulary/template, scope, threshold, decision và sign-off.

## 4. Truy vết khởi đầu

| Nhu cầu sản phẩm | Contract chính | Acceptance |
|---|---|---|
| Trend narrative | `AI-TR-001`–`AI-TR-052` | `AI-ACC-TR-*`, `AI-ACC-CON-*` |
| Entity comparison | `AI-CMP-001`–`AI-CMP-022` | `AI-ACC-CMP-*` |
| Evidence và provider control | `AI-CON-001`–`AI-CON-035` | `AI-ACC-CON-*` |
| Template/review/export | `AI-RPT-001`–`AI-RPT-015` | `AI-ACC-RPT-*` |

Các mapping với core requirement hiện tại đã được cập nhật trong [traceability-matrix.md](../quality/traceability-matrix.md). Proposal ID không được đăng ký là `Covered`.
