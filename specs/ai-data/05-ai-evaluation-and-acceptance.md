# 05 — Đặc tả đánh giá và nghiệm thu AI

**Phiên bản đặc tả:** 2.2.0. **Trạng thái:** Phase 1 có automated evidence và real-provider smoke cho môi trường hiện tại; rollout rộng vẫn cần accuracy/cost threshold. **IDs:** `AI-ACC-*`.

## 1. Nguyên tắc nghiệm thu

Một model answer viết hay không đủ để nghiệm thu. Phải test riêng: (1) deterministic arithmetic và eligibility, (2) factual grounding, (3) narrative/schema safety, (4) report template integrity và versioning, (5) operational fallback và privacy. Coverage phải dựa trên assertion thực tế, không suy luận từ tên file test.

Mỗi release evidence record SHOULD ghi code commit, core spec version, workbook/config hash, frozen fixture version, calculation/prompt/model/schema/template version, command đã chạy cùng failure/limitation.

## 2. Xây dựng golden dataset

Chuẩn bị frozen fixture có expected fact và source ref được duyệt thủ công; tách business data thật khỏi synthetic edge case. Bao gồm nhiều project/entity/window nhưng không có PII chưa được duyệt trong provider payload. Human reviewer phải sign-off label, business meaning, threshold, template wording và factual example còn mơ hồ.

Các fixture class tối thiểu:

| Nhóm | Kết quả mong đợi |
|---|---|
| Positive movement hợp lệ | Đúng direction, absolute và relative delta |
| Decrease hợp lệ | Delta âm chính xác, percent đúng, không bịa nguyên nhân |
| Endpoint bằng nhau nhưng giữa kỳ biến động | Endpoint unchanged; không claim cả series phẳng |
| Toàn missing / một point | Insufficient data, không tạo trend |
| True zero và blank/marker | Phân biệt numeric/quality semantics, gồm core rule `0/0 -> 0%` |
| Baseline = 0 | Relative percent unavailable |
| Weighted error rate | Ratio of sums, không phải trung bình daily percentage |
| Percentage metric | Absolute difference có nhãn percentage point |
| Period partial/misaligned | Nêu comparison limitation hoặc not comparable |
| Khác effective unit/project | Reject entity comparison |
| Rename entity / import mới | Giữ historical evidence và stale state |
| LLM chèn số/nguyên nhân không có căn cứ | Reject output hoặc safe fallback |
| Provider timeout / invalid JSON | Deterministic-only result và state rõ ràng |
| Prompt-injection string trong source | Được coi là dữ liệu, không phải instruction |
| Report approved rồi bị edit | Tạo version mới và yêu cầu approve lại |

## 3. Nghiệm thu tất định — xu hướng

| ID | Điều kiện nghiệm thu |
|---|---|
| AI-ACC-TR-001 | Cùng approved snapshot/policy tạo numeric fact giống nhau, độc lập với LLM/provider. |
| AI-ACC-TR-002 | Đúng zero-vs-missing và baseline-zero semantics; aggregate `0/0` trả `0%`, các zero-denominator combination invalid khác trả unavailable. |
| AI-ACC-TR-003 | Weighted aggregate `% báo sai` tuân thủ numerator/denominator contract của core. |
| AI-ACC-TR-004 | Exact period, unit, comparison basis, valid coverage và provenance được mang vào result. |
| AI-ACC-TR-005 | Không có stable/anomaly claim trước khi policy/threshold tương ứng được duyệt và versioned. |
| AI-ACC-TR-006 | Một point hoặc coverage không đủ trả unavailable/insufficient-data, không trả confident trend. |
| AI-ACC-TR-007 | Import mới làm insight cũ stale nhưng không rewrite historical snapshot. |
| AI-ACC-TR-008 | Day/week/month tạo ordered period series; mỗi kỳ sau kỳ đầu có absolute/relative change và direction đúng. |
| AI-ACC-TR-009 | Pattern toàn chuỗi phân biệt tăng liên tục, giảm liên tục, không đổi và dao động; endpoint bằng nhau không bị diễn giải thành chuỗi phẳng. |
| AI-ACC-TR-010 | Kỳ thiếu không bị điền zero; giới hạn 60 kỳ và partial-period coverage được nêu trong limitation. |

## 4. Nghiệm thu tất định — so sánh

| ID | Điều kiện nghiệm thu |
|---|---|
| AI-ACC-CMP-001 | Reject comparison khác project, unit không tương thích hoặc entity count không hợp lệ. |
| AI-ACC-CMP-002 | Mọi operand dùng cùng metric definition, window và approved aggregation. |
| AI-ACC-CMP-003 | Phân biệt đúng absolute, relative và percentage-point difference. |
| AI-ACC-CMP-004 | Missing và coverage khác nhau phải hiển thị; comparison invalid là unavailable. |
| AI-ACC-CMP-005 | Cả hai phía comparison đều trace được tới captured evidence. |

## 5. Nghiệm thu LLM và bằng chứng

| ID | Điều kiện nghiệm thu |
|---|---|
| AI-ACC-CON-001 | Mọi material numeric claim khớp existing deterministic fact ID sau parse. |
| AI-ACC-CON-002 | Mọi material fact ID resolve được về valid evidence của analysis snapshot. |
| AI-ACC-CON-003 | Unsupported verified-cause statement bị reject hoặc chỉ được viết lại thành unverified hypothesis có nhãn rõ theo approved policy. |
| AI-ACC-CON-004 | Invalid JSON, extra claim, sai project/metric/period hoặc invalid ref làm validation fail và kích hoạt safe fallback. |
| AI-ACC-CON-005 | Workbook prompt-injection text không thể đổi system task, làm lộ secret hoặc kích hoạt action. |
| AI-ACC-CON-006 | Provider outage vẫn để deterministic fact/core dashboard hoạt động. |
| AI-ACC-CON-007 | Không gửi request tới external model trước khi privacy/provider contract được duyệt. |

Evaluation gồm exact-match numeric check, schema pass rate, source-reference validity, unsupported-claim count, review rubric về clarity/utility, human edit rate và latency/cost. Numeric/evidence/unsupported-cause error là **blocking** trong approved golden acceptance suite; broader pilot threshold vẫn TBD. Không tự công bố accuracy hoặc 100% coverage từ vài fixture.

## 6. Nghiệm thu báo cáo

| ID | Điều kiện nghiệm thu |
|---|---|
| AI-ACC-RPT-001 | Required section và deterministic field của template render đúng versioned schema. |
| AI-ACC-RPT-002 | LLM không thể sửa KPI value, chart data, date hoặc evidence ID trong final draft. |
| AI-ACC-RPT-003 | Generated draft có nhãn rõ và vẫn review/edit được. |
| AI-ACC-RPT-004 | Approval gắn với exact version và reviewer; edit sau approval tạo draft mới cần review. |
| AI-ACC-RPT-005 | Report cũ vẫn tái lập được sau import mới và có freshness indicator đúng. |
| AI-ACC-RPT-006 | Export giữ numeric fact, chart, metadata, unit, source note và trạng thái DRAFT/APPROVED. |
| AI-ACC-RPT-007 | Missing data, provider failure hoặc export error không tạo report approved trông có vẻ hoàn chỉnh. |
| AI-ACC-RPT-008 | MVP không có scheduled send hoặc auto-approval. |

## 7. Cổng phát hành và trạng thái bằng chứng

Status theo criterion: `Not implemented`, `Gap`, `Partial`, `Covered`, `Blocked by decision`. Một test chỉ được tính `Covered` khi thực sự assert criterion và có passing run được ghi nhận cho commit liên quan. Tách deterministic suite, model-output golden evaluation, E2E flow, privacy/security review và report-render snapshot test.

Trước khi bật AI cho người dùng: owner phải duyệt KPI/coverage rule, privacy/provider, evaluation set và release threshold phù hợp phạm vi; deterministic/critical grounding gate phải pass; fallback hoạt động; known limitation được hiển thị. Privacy/provider đã được owner xác nhận cho môi trường hiện tại ngày 2026-09-25; điều này không tự động phê duyệt rollout cho môi trường khác hoặc các feature report/comparison.

## 8. Trạng thái bằng chứng Phase 1

| Nhóm | Trạng thái | Bằng chứng |
|---|---|---|
| `AI-ACC-TR-001`–`AI-ACC-TR-010` | Covered trong Phase 1 scope | Unit + SQLite integration trong `tests/test_ai.py`; chọn group và bảng chuỗi kỳ trong `frontend/e2e/ai-insights.spec.ts` |
| `AI-ACC-CON-001`–`AI-ACC-CON-006` | Covered bằng fake provider/validator/E2E | `tests/test_ai.py`, `frontend/e2e/ai-insights.spec.ts` |
| `AI-ACC-CON-007` | Covered cho safe gate | External adapter bị thay bằng disabled adapter khi privacy gate đóng; CI không gọi provider |
| Real-provider smoke | Covered cho môi trường hiện tại | Synthetic smoke và live normalized-data smoke pass; xem evidence record ngày 2026-09-25 |
| Production accuracy/cost threshold | Decision needed | Cần gold business fixture, reviewer và budget của `AI-DEC-007`, `AI-DEC-013` |

Chi tiết command và known limitation nằm tại [08-phase-1-runbook-and-evidence.md](08-phase-1-runbook-and-evidence.md). “Covered” ở đây không đồng nghĩa production rollout đã được duyệt.
