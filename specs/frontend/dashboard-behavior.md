# Dashboard behavior

AI narrative v4: preserve engine overview/shared phases; show accepted AI prose in “Điều cần chú ý” with its own label and anchors from accepted candidate IDs. Partial rejection keeps survivors; failure copy distinguishes malformed output, source grounding, numbers/dates and semantic verification. Source disclosure remains closed. See [runtime/evaluation](../ai-data/evidence/2026-10-02-semantic-validator-and-live-evaluation.md). Desktop scope unchanged.

- Trạng thái: **As-built, có gap được ghi rõ**
- Contract IDs: `DASH-*`

## Nhãn ba chỉ số chính

Nhãn dùng thống nhất trong bộ chọn, chú giải, tooltip, So sánh, phân tích AI và màn hình nguồn dữ liệu:

| Khóa dữ liệu/API (giữ nguyên) | Nhãn hiển thị |
|---|---|
| `Tổng số` | Tổng số ghi nhận |
| `Báo sai/Lỗi` | Tổng báo sai (lỗi) |
| `% báo sai` | Tỷ lệ báo sai |

Biến thể `%báo sai` cũng hiển thị là **Tỷ lệ báo sai**. Đây chỉ là thay đổi ngôn ngữ hiển thị, không đổi công thức, đơn vị, mã chỉ số AI hoặc tham số API. Các khóa cũ trong quy tắc tính bên dưới vẫn là định danh kỹ thuật, không phải nhãn dành cho người dùng.

## Khởi tạo và trạng thái

- `DASH-001`: Dashboard MUST tải project từ `/api/bootstrap`; database rỗng hiển thị empty state, không tự import workbook demo.
- `DASH-002`: Bộ lọc MUST lưu trong `sessionStorage` theo tab/origin, không đưa vào URL.
- `DASH-003`: Reload khôi phục bộ lọc hợp lệ; file upload không được tự khôi phục.
- `DASH-004`: Nếu project/entity cũ không còn hợp lệ, UI MUST chọn fallback an toàn.
- `DASH-005`: Loading/error của request mới không được xóa workspace thành công gần nhất một cách gây hiểu nhầm.

## Điều hướng dữ liệu

- Chọn project trước, sau đó entity và phạm vi `node`/`children`.
- Nếu chưa chọn entity, chọn entity nông nhất có dữ liệu số trong khoảng hiện tại.
- `children` chỉ lấy node con trực tiếp; nếu không có con thì dùng node hiện tại.
- Unit đến từ entity; không có unit dropdown sửa nghĩa nguồn.

## Thời gian

| Mode | Hành vi |
|---|---|
| Recent | 10 ngày phân biệt có dữ liệu gần nhất |
| Week | Các tuần ISO độc lập; count tối đa 60 |
| Month | Các tháng lịch độc lập; count tối đa 60 |
| Custom | Khoảng ngày hợp lệ trong biên dữ liệu project |

- `DASH-006`: Count metric theo kỳ là tổng.
- `DASH-007`: `% báo sai` theo kỳ là tỷ lệ có trọng số `SUM(error)/SUM(total)×100`.
- `DASH-008`: Missing MUST không hiển thị như zero.

## Các workspace

### Tổng quan

- Mỗi entity có chart riêng; tối đa hai chart mỗi hàng.
- `Tổng số` và `Báo sai/Lỗi` là bar; `% báo sai` là line trên secondary axis.
- Legend hỗ trợ click ẩn/hiện và double-click isolate series.

### Thống kê

- Nhóm theo ngày/tuần/tháng/quý.
- Hỗ trợ SUM, AVG/ngày hoặc cả hai.
- Có thể gồm/loại kỳ chưa đầy đủ.
- `SUM` chỉ cộng numeric value. Kỳ `Tổng số` toàn missing/source marker MUST giữ missing, không thành `0`.
- `Báo sai/Lỗi` trống MAY được suy ra `0` chỉ khi có ngày coverage `Tổng số` hợp lệ; source marker không được suy ra `0`.
- `AVG/ngày = SUM / eligible_day_count`; eligible day lấy từ ngày có `Tổng số` numeric và loại ngày source marker của metric đang tính.
- Coverage MAY kế thừa ancestor gần nhất có `Tổng số`; trường hợp này chỉ hỗ trợ mẫu số cho `Báo sai/Lỗi`, không được làm `Tổng số` missing thành zero.
- Kỳ chưa đầy đủ dùng boundary đã clip theo data window và chia theo eligible day, không chia mặc định cho toàn bộ số ngày lịch.

### So sánh theo ngữ cảnh

- Không có tab So sánh cấp cao. Người dùng mở popup So sánh từ biểu đồ node con trực tiếp trong Thống kê.
- Chọn 2–3 entity cùng cha trong cùng project và cùng effective unit.
- Khác hierarchy level được phép.
- Count dùng grouped bar; percentage dùng line.
- Không tự tạo tỷ lệ dẫn xuất ngoài rule đã khai báo.

### Đối chiếu dữ liệu

- Không có tab Đối chiếu dữ liệu cấp cao. Màn hình này chỉ được mở đúng ngữ cảnh từ Điều tra điểm và có hành động quay lại biểu đồ nguồn.
- Bảng hiển thị raw/display/chart value, hierarchy, sheet/cell, number format và parser metadata.
- Pagination không làm thay đổi filter chính.
- Từ chart, **Mở đúng dòng Audit** MUST dùng exact refs, kể cả dòng không nằm ở page hiện tại.

### Import và lịch sử

- Preview luôn trước commit.
- Full snapshot cần xác nhận bổ sung.
- Sau committed import, UI gọi lại bootstrap, **force-fetch workspace** và history. Workspace mới MUST được áp dụng ngay cả khi project, view và filter không đổi; không reload toàn trang.
- Khi kết quả commit không rõ do network, UI hướng người dùng kiểm tra lịch sử trước khi thử lại.

## Lineage interaction

- Nhấn trực tiếp điểm/cột trên biểu đồ mở provenance drawer. Danh sách “Điều tra điểm bằng bàn phím” đã bị loại bỏ theo quyết định sản phẩm.
- Exact point hiển thị workbook, sheet/cell, raw/display/chart value, revision và import.
- Aggregate point hiển thị rule, result, coverage/contributors và freshness.
- Legacy point không có safe refs hiển thị unavailable state; MUST không đoán nguồn.
- Đóng drawer xóa trạng thái chọn trên biểu đồ; không cam kết trả focus về một điểm Plotly riêng lẻ.

## Refresh, cache và concurrency

- `DASH-009`: **Làm mới dữ liệu** gọi lại `/api/bootstrap` rồi force-fetch workspace, bỏ qua same-request-key optimization. Nó không tìm hoặc import file mới.
- `DASH-010`: Server MUST phân biệt cache theo latest committed run để request workspace sau run mới không nhận payload của run cũ.
- `DASH-011`: Sau import có outcome `committed`, client MUST gọi bootstrap với force-workspace để dữ liệu mới xuất hiện trong cùng document/session.
- `DASH-012`: Mỗi workspace load sở hữu một `AbortController`; chỉ request còn là active request mới được cập nhật state/render. Response cũ/superseded MUST không ghi đè response mới hơn kể cả khi hoàn thành muộn.
- Filter thay đổi nhanh được debounce/batch phù hợp.
- Chart DOM SHOULD được tái sử dụng để giữ focus, selection và giảm Plotly work.
- `DASH-013`: Plotly modebar MUST bị tắt trên mọi chart; thao tác hover, legend, chọn điểm, truy vết và responsive resize vẫn hoạt động bình thường.
- Workspace response mang `dataVersion.committedImportRef`. Đây là identity của current committed read model, không phải cam kết rằng backend có thể dựng lại workspace theo revision lịch sử.

### Resolved implementation gap: `DASH-GAP-001`

Gap same-key refresh được đóng ngày 2026-09-25. `frontend/e2e/workspace-freshness.spec.ts` khóa ba trường hợp: post-commit refresh không reload trang, manual refresh với cùng query, và response superseded hoàn thành muộn. Same-request-key optimization vẫn áp dụng cho render/filter no-op thông thường; chỉ explicit freshness actions truyền `force=true`.

## Accessibility và lỗi

- Các điều khiển ứng dụng vẫn phải dùng được bằng bàn phím. Riêng thao tác chọn điểm Plotly để Điều tra là tương tác con trỏ; không dựng danh sách điểm song song.
- Critical desktop text phải đạt WCAG AA contrast tại viewport được test.
- Error phải nói rõ hành động tiếp theo; không thay missing/error bằng số liệu giả.
- UI chỉ công bố năng lực đang có, không mô tả import là “tự động hằng ngày” khi chưa có scheduler.

## AI reporting status

Short-window refinement: dưới bốn kỳ hợp lệ, không render chronology/extrema hoặc ba period disclosures lặp template. Dùng một bảng KPI × kỳ, nhãn `Kỳ 1 (07–13/09) → Kỳ 2 (14–16/09)`; năm/phạm vi đầy đủ trong receipt, khoảng khác năm ghi đầy đủ. Panel title “Phân tích KPI tự động”. Liên hệ ba KPI nằm trong synthesis cùng anchors và kiểm tra nguồn; không có bảng hệ số hoặc cảnh báo thiếu sáu kỳ. Không significance/quality/causal judgement. Các nguồn captured vẫn mở được; mobile infrastructure giữ nguyên.

Grounded synthesis (02/10/2026) là desktop-first; không thêm tối ưu mobile. Giữ panel sau chart, compact controls và snapshot scope bất biến. Luồng mặc định: tối đa hai nhận định → anchors tối thiểu → limitation đã gom → kiểm tra theo insight → chi tiết thu gọn. Chỉ `insufficient_data` đưa limitation lên trước summary. Độ phủ theo từng metric, không dùng max period count khẳng định cả ba đầy đủ. Direction trung tính; rate delta là điểm phần trăm. Source check mở captured logical evidence, không tìm theo giá trị/ngày. Responsive CSS cũ không là cam kết mobile support mới.

Dashboard đã có AI Trend Summary Phase 1 trong Overview. Khu vực **Phân tích xu hướng bằng AI** MUST nằm sau KPI và biểu đồ chính để dashboard tiếp tục là nguồn định lượng ưu tiên; panel không được làm thu hẹp chart thành sidebar trên desktop. Nội dung tổng quan và xu hướng xuất hiện trước, còn bảng từng kỳ, bằng chứng, chất lượng dữ liệu và metadata kỹ thuật được mở rộng khi cần.

Kết quả chính MUST được tổ chức thành một luồng đọc “Tổng quan phân tích” → “Câu chuyện dữ liệu”, không trình bày các con số như những card rời để người dùng tự ghép nghĩa. “Câu chuyện dữ liệu” dùng trực tiếp period-level facts để kết nối peak/lowest, mức tăng/giảm lớn nhất, chuỗi tăng/giảm liên tiếp, plateau cuối chuỗi và bối cảnh lịch sử thành câu hoàn chỉnh. Cùng một transition MUST không xuất hiện đồng thời như cả “lớn nhất” và “gần nhất”. Bảng từng kỳ và metadata là progressive disclosure, không cạnh tranh với câu chuyện chính.

UI MUST luôn giữ entry point hiện diện. Với `scope=children`, CTA phân tích bị khóa, lý do và thao tác chuyển về `scope=node` phải hiển thị rõ thay vì làm biến mất tính năng. Với kết quả hợp lệ, UI MUST hiển thị biên nhận phạm vi gồm entity, exact date range, metric và grain; biên nhận vẫn giữ nguyên khi kết quả stale.

UI MUST gắn nhãn nội dung AI, chỉ gọi model sau thao tác chủ động của người dùng, giữ dashboard gốc hoạt động khi provider lỗi, phân biệt stale/unavailable và cho mở typed exact/aggregate evidence theo `AI-TR-050`–`AI-TR-052`, `AI-CON-011` và `AI-CON-033`; xem [AI/Data v2](../ai-data/README.md). Thay filter không tự gọi model và không được trình bày kết quả cũ như thể thuộc selection mới. Live region chỉ thông báo trạng thái ngắn; nội dung kết quả dài nằm ngoài live region và focus MUST quay về CTA sau khi request hoàn tất hoặc lỗi.

AI Insight ưu tiên whole-window synthesis; không dùng endpoint change đại diện chuỗi dao động. Toàn bộ giai đoạn, extrema, cả lần tăng/giảm lớn nhất, turning points và lịch sử nằm trong “Xem chi tiết diễn biến”, mặc định đóng, dữ liệu không bị cắt. Đầu–cuối ở “Thông tin bổ sung: so sánh đầu–cuối”, mặc định đóng. Numerical anchors giữ đúng ngày/đơn vị và source routing. Giữ captured scope và desktop-first; không bổ sung tối ưu mobile.

Analytical reading refinement: nội dung mở sẵn gồm “Tổng quan trong thời gian đã chọn” → “Các chỉ số thay đổi như thế nào?” (hai kỳ: “So sánh hai kỳ”) → “Điều cần chú ý” khi có nhận định riêng. Giai đoạn hiển thị chung các KPI và giải thích liên hệ có căn cứ. Trạng thái giữ nguyên suốt thời gian của metric phụ chỉ nêu một lần. Căn cứ, kiểm tra nguồn, bảng KPI và lịch sử nằm trong một mục mặc định đóng “Xem số liệu và nguồn”; cảnh báo missing vẫn cạnh kết quả. Trên bốn giai đoạn, phần tiếp theo được mở theo yêu cầu, không bỏ dữ liệu. Không bổ sung tối ưu mobile.
