# Bằng chứng hoàn thành Contextual Comparison — Vertical Slice 1

- Ngày xác minh: **2026-09-29**
- Trạng thái: **Đã triển khai và xác minh lại**
- Quyết định Gate 0 đầu vào: **GO**
- Đối chiếu dữ liệu toàn bộ 6 dự án: [contextual-comparison-all-project-audit.md](contextual-comparison-all-project-audit.md)

## 1. Phạm vi đã hoàn thành

| Hạng mục | Kết quả |
|---|---|
| Entry point từ Statistics child chart | Có; CTA chỉ xuất hiện khi `scope=children`, anchor là chart đang mở |
| Large modal và focus lifecycle | Có; native modal, Escape/Đóng, trả focus và scroll về CTA nguồn |
| Kế thừa chỉ số | Có; tự kế thừa nếu chỉ có một chỉ số, nếu có nhiều chuỗi thì chọn sẵn chỉ số So sánh dùng gần nhất hoặc `Báo sai/Lỗi` |
| Context inheritance | Có; giữ grain, Statistics range, include-incomplete, parent scope và effective unit |
| True sibling | Có; backend quyết định bằng same project + same non-null parent ID |
| Điều kiện theo chỉ số | Có; tính lại sau đổi chỉ số, giữ lựa chọn còn hợp lệ và loại lựa chọn không hợp lệ kèm mã lý do |
| Missing/zero | Có; numeric zero hợp lệ, missing không tạo comparable point |
| Selection | Anchor khóa, tối đa ba entity tính cả anchor |
| Original metric | Tổng số, Báo sai/Lỗi, % báo sai |
| Time grain | Day exact; week/month/quarter period summary |
| Calculation | Count dùng SUM; tỷ lệ dùng ratio-of-sums có trọng số |
| Mẫu số tỷ lệ node con | Kế thừa `Tổng số` từ tổ tiên gần nhất cùng đơn vị; không gán giả `Tổng số` cho node con |
| Stale request | Có AbortController và active-request identity riêng cho modal |
| Data version | Khác `committedImportRef` thì khóa controls; chỉ cho cập nhật current data hoặc đóng |
| Legacy Comparison | Giữ nguyên khi request không có `comparison_anchor` |
| Desktop layout | Đã kiểm tra 1366×768 và 1440×900; chart frame tối thiểu 640×340 |

## 2. Contract API đã triển khai

Request additive dùng endpoint workspace hiện có:

```text
view=comparison
entity=<parent đang chọn>
scope=children
comparison_anchor=<child chart anchor>
comparison_lens=metric
comparison_metric=<một trong ba metric gốc>
comparison_entities=<anchor,sibling...>
statistics_group=<day|week|month|quarter>
statistics_count|statistics_from|statistics_to
include_incomplete=<true|false>
```

Response additive:

- `comparisonContext`: anchor, metric, calculation, grain, range và trạng thái anchor;
- `comparisonSelection`: `accepted`, `removed`, `limit`;
- `comparisonCandidates`: thêm `eligible`, `reason`, `comparablePeriodCount` trong contextual mode;
- `dataVersion`: snapshot identity dùng để chặn mixed-revision rendering.

Backend vẫn là nguồn quyết định eligibility. Frontend chỉ hiển thị và gửi lựa chọn; không tự suy diễn sibling hoặc calculation để thay thế response server.

## 3. Source/module đã thay đổi

- `app/api.py`: contextual query/response, shared Statistics period window, eligibility, selection normalization, cache key.
- `visualization/charts.py`: tỷ lệ theo kỳ dùng mẫu số node hiện tại hoặc tổ tiên gần nhất cùng đơn vị; dữ liệu tổng hợp mang nguồn mẫu số rõ ràng.
- `app/aggregate_lineage.py`: provenance tỷ lệ tổng hợp lấy mẫu số từ đúng node tổ tiên đã dùng trong phép tính.
- `frontend/src/main.ts`: CTA, modal state machine, request isolation, dataVersion barrier, focus restoration.
- `frontend/src/style.css`: compact CTA và large-modal layout.
- `frontend/e2e/fixtures.ts`: contextual API harness và dataVersion fixtures.
- `tests/test_api.py`, `tests/test_charts.py`: backend contract, quarter và backward compatibility.
- `frontend/e2e/contextual-comparison.spec.ts`: acceptance theo vertical slice.

## 4. Acceptance evidence

| Acceptance | Test |
|---|---|
| Mở từ chart con, anchor khóa, context kế thừa, CTA gọn | `vertical slice 1 opens from a child chart...` |
| Chart nhiều chỉ số không tạo bước chặn | cùng test; popup mở với `Báo sai/Lỗi` được chọn sẵn và tải điều kiện ngay |
| Selection sibling tạo chart và giữ context query | cùng test; assert parent/scope/grain/metric/entity IDs |
| Đổi chỉ số tính lại điều kiện và giữ lựa chọn hợp lệ | `metric change recomputes eligibility...`; `percentage metric remains available and keeps valid sibling selections` |
| Response cũ hoàn thành muộn không ghi đè | cùng test với delay 220 ms/20 ms |
| Revision mới không bị trộn với snapshot cũ | `new committed data version blocks...` |
| Focus quay về chart nguồn khi đóng | test đầu tiên |
| Kích thước chart tại hai viewport chuẩn | hai test `large dialog preserves...` |
| True sibling, unit, max 3, invalid anchor, legacy API | `test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api` |
| Quarter và weighted rate | `test_multi_entity_quarter_view_reuses_weighted_rate_semantics` |
| Node con chỉ có lỗi, node cha có Tổng số | `test_grouped_error_rate_inherits_nearest_parent_total_without_filling_child_total`; API contextual fixture theo cấu trúc VSO |
| Contract API So sánh cũ giữ tương thích | API contextual regression; lối vào giao diện được ẩn sau khi Phase 2 hoàn thành kiểm tra tương đương |

## 5. Kết quả regression

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **88 passed**, 18 FastAPI/Python 3.14 deprecation warnings |
| `npm run build` | **PASS**; TypeScript và Vite production build thành công |
| `npx playwright test` | **46 passed** |
| Chỉ kiểm thử So sánh theo ngữ cảnh | **10 passed**, gồm `% báo sai`, thiếu tử số, giữ lựa chọn và viewport thấp 1200×650 để khóa footer |

Vite còn cảnh báo Plotly basic bundle lớn hơn 500 kB. Đây là performance warning đã tồn tại quanh dependency Plotly, không phải functional regression của slice.

## 6. Ranh giới còn giữ nguyên

- Chưa có Statistics lens đa entity; đây là Vertical Slice 2.
- Chưa có Investigation/Audit round-trip bên trong modal.
- Không thêm contributor drilldown hoặc exact Excel-cell promise cho aggregate point.
- Không có historical workspace calculation theo `importRef`; modal không cho đổi metric/range trên snapshot cũ.
- Tại thời điểm hoàn thành Slice 1, tab So sánh cũ chưa được migration hoặc xóa. Gate này đã được giải quyết sau kiểm tra tương đương Phase 2: tab bị ẩn nhưng contract API cũ vẫn được giữ.

## 7. Kết luận

**Vertical Slice 1 hoàn thành.** Có thể chuyển sang Slice 2 sau khi chốt contract multi-entity Statistics và lineage mapper riêng; không cần xây lại same-parent helper, period window, eligibility shell, dataVersion barrier hoặc modal lifecycle.
