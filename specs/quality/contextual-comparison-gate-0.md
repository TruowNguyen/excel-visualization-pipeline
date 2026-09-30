# Báo cáo Gate 0 — Contextual Comparison

- Ngày: **2026-09-28**
- Kết luận: **GO cho Vertical Slice 1**
- Phạm vi thực hiện: calculation, hierarchy, data version, time/metric và lineage foundation.

## 1. Kết quả xác minh giả thuyết

| Giả thuyết | Kết quả |
|---|---|
| `fillna(0).sum()` an toàn cho kỳ toàn missing | Sai; biến all-null thành numeric zero |
| Numeric zero phân biệt được với missing | Đúng ở normalized data; đã khóa tiếp bằng `numeric_value_count` và `inferred_zero` |
| Blank error có Total coverage được suy ra zero | Đúng theo contract hiện tại |
| Source marker được suy ra zero | Sai về nghiệp vụ; đã sửa để giữ missing khi không có numeric contributor khác |
| AVG/ngày dùng calendar day | Sai; dùng eligible day từ Total coverage |
| Child error-only có thể kế thừa coverage | Đúng; từ ancestor gần nhất có Total numeric |
| Sibling có thể xác định bằng depth | Sai; bắt buộc cùng exact parent và project |
| Workspace cache biết committed revision | Đúng; internal key đã có latest `run_id` |
| Workspace công khai chart data version | Trước Gate 0: chưa; sau Gate 0: có `dataVersion.committedImportRef` |
| Backend dựng lại chart theo revision lịch sử | Không hỗ trợ |
| Original daily/week/month | Hỗ trợ |
| Original quarter | Chưa hỗ trợ |
| Statistics day và daily raw có cùng value semantics | Không hoàn toàn; boundary cùng ngày nhưng Statistics có inferred blank-error zero |
| Statistics aggregate lineage dùng ngay cho multi-entity | Không; mapper hiện gắn entity theo input single-entity |

## 2. Lỗi thực sự phát hiện

### G0-CALC-001 — all-missing thành zero

`prepare_period_statistics` dùng `group["chart_value"].fillna(0).sum()`. Hậu quả:

- `Tổng số` toàn missing hiển thị SUM 0;
- `Báo sai/Lỗi` toàn source marker có thể hiển thị SUM 0;
- không phân biệt numeric zero với inferred zero.

Đã sửa calculation để:

- chỉ sum numeric contributor;
- giữ all-missing Total/source-marker Error là missing;
- chỉ infer Error zero khi có eligible Total coverage;
- xuất `numeric_value_count` và `inferred_zero` trong prepared statistics frame.

### G0-LIN-001 — mapper Statistics giả định một entity

`attach_aggregate_lineage(kind="statistics")` lấy entity đầu tiên cho mọi trace. Nếu tái sử dụng nguyên trạng với multi-entity chart, provenance có thể gắn sai entity. Đã thêm fail-closed guard; mapper đa entity thuộc Phase 2.

## 3. Thay đổi source và test

Source:

- `visualization/charts.py`: sửa missing/zero semantics và thêm metadata.
- `aggregate_lineage.py`: giữ `inferred_zero`, từ chối multi-entity Statistics mapper hiện tại.
- `entity_selection.py`: thêm helper true-sibling theo project + same parent.
- `storage/repository.py`: thêm `CommittedDataVersion` và lookup latest public import ref.
- `app/api.py`: workspace trả additive `dataVersion`.

Test:

- all missing;
- numeric zero;
- mixed missing/numeric;
- partial period;
- source marker;
- blank error inferred zero;
- inherited parent coverage;
- same parent, same-depth different-parent, parent/child, cross-project, invalid/root anchor;
- public dataVersion đổi sau committed import;
- stale exact/aggregate refs tiếp tục resolve;
- multi-entity Statistics lineage fail closed.
- inferred-zero Statistics aggregate dùng Total observations làm coverage evidence.

Không có thay đổi frontend, contextual API parameters, database schema hoặc Comparison tab.

## 4. Contract dữ liệu đã khóa

- True sibling = cùng project + cùng non-null parent ID + khác anchor.
- Missing không phải numeric zero.
- Inferred error zero phải có `inferred_zero=true`.
- AVG/ngày chỉ tồn tại khi SUM tồn tại và eligible day > 0.
- Public data version = latest opaque committed import ref.
- Historical exact/aggregate refs có thể resolve; historical workspace calculation không có.
- Unit comparison tiếp tục dùng known/equal `effective_unit`.
- Weighted rate giữ ratio-of-sums.

## 5. Giới hạn còn tồn tại

- Original comparison chưa có quarter grouping.
- Chưa có contextual eligibility API/reason code.
- Chưa có historical workspace query.
- Snapshot cũ chỉ tiếp tục hiển thị khi payload còn ở client memory.
- Multi-entity Statistics cần chart builder và lineage mapper riêng ở Phase 2.
- Contributor drilldown mới không thuộc Gate 0.

## 6. Backend regression

Full backend suite sau thay đổi: **81 passed, 18 warnings** bằng `python -m pytest` ngày 2026-09-28. Warning còn lại là deprecation warning từ FastAPI/Python 3.14, không phải regression của Gate 0. Gọi `pytest` trực tiếp trong môi trường hiện tại không đưa workspace root vào import path, vì vậy lệnh chuẩn của bằng chứng này là `python -m pytest`.

## 7. Quyết định public dataVersion

Chọn additive workspace field `dataVersion` gồm `committedImportRef` và `committedAt`. Không expose `run_id`. Field áp dụng cho mọi workspace view, nên Statistics chart và contextual request tương lai có cùng cách đối chiếu revision.

## 8. Kết luận

**GO cho Vertical Slice 1.** Các gap quarter và contextual candidate API là work item đã biết của slice, không còn là ambiguity của Gate 0. Vertical Slice 2 chưa được phép tái sử dụng trực tiếp single-entity Statistics lineage mapper.
