# 03 — Đặc tả báo cáo tự động theo template

**Phiên bản đặc tả:** 2.0.0. **Trạng thái:** Đề xuất / CHƯA TRIỂN KHAI; owner phải duyệt report template thực tế đầu tiên của mentor và output format. **IDs:** `AI-RPT-*`.

## 1. Mục tiêu và ranh giới sản phẩm

Sinh **report draft có thể review**, không phải official report tự động. Hệ thống ghép deterministic KPI fact, chart và AI narrative đã duyệt vào template ổn định, có version. Human reviewer có thể chỉnh commentary và phê duyệt rõ ràng một version cụ thể trước khi export/phân phối chính thức.

Tính năng này không mặc nhiên bao gồm scheduled import, scheduled publication, gửi email, approval authority hoặc cause verification.

## 2. Mẫu MVP và danh mục ứng viên

**MVP candidate:** Weekly CX Performance Report, ưu tiên chuyển đổi từ report template thực tế của mentor. Ứng viên khác gồm Monthly CX Performance Report, Comparative Analysis Report và Investigation Summary. Việc chọn template/format là product decision, không phải năng lực as-built.

Section schema canonical được đề xuất:

| Section | Nội dung | Component chịu trách nhiệm |
|---|---|---|
| Cover/metadata | Project, window, template version, generated time, data version | Report composer |
| Executive summary | Narrative ngắn gọn có evidence | Validated AI text + reviewer |
| KPI overview | `Tổng số`, `Báo sai/Lỗi`, `% báo sai`, unit, coverage | Deterministic analytics |
| Trend analysis | Chart, absolute/relative change, data-quality note | Analytics + narrative |
| Comparison | Entity và period delta có thể so sánh đã chọn | Comparison engine + narrative |
| Key finding | Typed fact có evidence reference | Evidence builder + validated narrative |
| Follow-up check | Đề xuất kiểm tra cho con người, không phải diagnosis thiếu căn cứ | AI draft + reviewer |
| Appendix | Metric definition, scope, data ref, limitation, model/template/policy version | Composer |

## 3. Hợp đồng template

- `AI-RPT-001`: Report template MUST có version và định nghĩa required section, allowed field type, formatting rule, cùng việc section có cho phép AI-generated text hay chỉ deterministic value.
- `AI-RPT-002`: Composer MUST NOT cho LLM thay đổi metric value, chart series, calculation rule, source reference ID hoặc period boundary.
- `AI-RPT-003`: Report generation MUST dùng một pinned analysis evidence bundle. Nếu report ghép nhiều analysis, MUST giữ rõ data version của từng bundle và nêu mismatch; MVP SHOULD yêu cầu cùng snapshot.
- `AI-RPT-004`: Generated narrative MUST qua schema, fact, grounding và unsupported-cause validation trước khi chèn vào report field.
- `AI-RPT-005`: Section/data bị thiếu MUST hiển thị `not available` hoặc reviewer action rõ ràng, không bịa narrative.
- `AI-RPT-006`: Caption/metadata MUST phân biệt hypothetical, computed và manually edited text khi phù hợp.

## 4. Vòng đời báo cáo dự kiến

`draft_generated -> in_review -> approved -> exported`, cùng outcome `rejected` và `generation_failed`. `stale` là **freshness flag**, không tự động xóa hoặc reject. Version đã approved/exported là immutable. Chỉnh sửa sau approval tạo draft revision mới và phải review lại.

- `AI-RPT-010`: Khi tạo report, MUST lưu unique report ID, version, creator/action time, template ID/version, filter, pinned evidence snapshot và calculation/prompt/model/policy version deterministic.
- `AI-RPT-011`: Manual edit MUST giữ author, timestamp, original text và latest text trong revision/audit history; retention vẫn TBD.
- `AI-RPT-012`: Approval MUST gắn với exact report version, authenticated reviewer identity và thời gian trong access model đã duyệt. Vì API hiện chưa có authentication/authorization, formal approval bị chặn bởi `AI-DEC-011`; display name local hoặc browser field không đủ làm identity.
- `AI-RPT-013`: Committed import mới MUST NOT âm thầm sửa report hiện có. UI MAY đánh dấu stale và cho tạo draft mới.
- `AI-RPT-014`: Exported document MUST ghi report version, reporting period, source data snapshot và generation/review status. Nếu cho export draft chưa duyệt, file MUST có nhãn DRAFT rõ ràng.
- `AI-RPT-015`: MVP không được tự gửi hoặc tự publish report.

## 5. Yêu cầu tạo báo cáo có thể cấu hình

Các trường dự kiến: `templateId`, `templateVersion`, `project`, `entityIds` nếu phù hợp, `metricCodes`, `startDate`, `endDate`, `timeGroup`, `scope`, `compareTo`, `dataSnapshotRef`, `locale`, `sections` và optional `reviewerNotes`. `metricCodes` chỉ dùng core code `total`, `error`, `error_rate`; label là presentation metadata. Backend kiểm tra project/entity/unit và coverage thực tế; không cho LLM tự diễn giải input schema tự do.

## 6. Ví dụ định nghĩa template

```yaml
id: weekly-cx-performance
version: 1
status: proposed
locale: vi-VN
sections:
  - id: executive_summary
    type: narrative
    requires_review: true
  - id: kpi_overview
    type: deterministic_metrics
    fields: [total, error, error_rate]
  - id: trend
    type: chart_and_narrative
  - id: comparison
    type: comparison_and_narrative
    optional: true
  - id: limitations
    type: deterministic_and_narrative
  - id: sources
    type: evidence_appendix
```

Ví dụ này chỉ là đề xuất thiết kế, không phải template hoặc schema migration đã tồn tại.

## 7. Thiết kế export

Ưu tiên HTML preview. Chỉ chọn PDF và/hoặc DOCX sau khi xác nhận cách mentor thực sự chỉnh report. PDF phù hợp layout ổn định; DOCX hỗ trợ manual editing. Deterministic renderer sở hữu table/chart, pagination, font và escape/sanitization. LLM chỉ điền text field được cho phép. Lỗi export MUST NOT thay đổi approved report/evidence.

## 8. UI có con người kiểm duyệt

- Chọn template/data scope, preview deterministic fact rồi yêu cầu draft.
- Hiển thị fact, linked evidence, limitation, model-generation status và editable commentary ở các vùng tách biệt.
- Cho regenerate narrative mà không đổi data snapshot, trừ khi người dùng yêu cầu refresh rõ ràng.
- Reviewer kiểm tra numerical/grounding issue, chỉnh sửa và approve exact version.
- Export và hiển thị generation date, data-as-of, version cùng trạng thái DRAFT/APPROVED.

## 9. Kịch bản kiểm thử

Template schema sai; thiếu section; metric period incomplete; source ref invalid; LLM sửa số; unsupported cause; AI timeout và deterministic fallback; edit sau approval; import mới sau draft; cùng template khác version; unsafe HTML/prompt injection; export fidelity; retained history/evidence; không tự gửi khi chưa duyệt.

Acceptance canonical nằm trong [05-ai-evaluation-and-acceptance.md](05-ai-evaluation-and-acceptance.md), namespace `AI-ACC-RPT-*`.
