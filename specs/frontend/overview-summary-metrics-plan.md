# Kế hoạch thay bốn chỉ số tổng quan dự án

> **Đề xuất cũ được thay thế sau quyết định người dùng ngày 05/10/2026.** Đã duyệt và cài đặt hướng ưu tiên project + nguồn theo dõi riêng có nhãn rõ; không còn yêu cầu cả ba thẻ đều là tổng toàn dự án. Hợp đồng hiện hành: [đặc tả đã cài đặt](overview-summary-metrics.md). Các mục BLOCKED/“chưa triển khai” bên dưới ghi lại tình trạng trước quyết định này, không phải trạng thái hiện tại. Kết quả nghiệm thu thực tế: [evidence](../quality/overview-summary-metrics-evidence.md).

- Phiên bản đề xuất: **v1.2 — 05/10/2026**.
- Trạng thái: **Đã được yêu cầu triển khai; người dùng chọn Tổng số ghi nhận làm chỉ số nền; Gate 0 còn chờ quyết định cho dự án thiếu nguồn tổng, chưa thay giao diện/API**. Chỉ số nền mới có dữ liệu tại node project của SmartParking, VOL và VW Vũ Yên; ANVF, VSO và V-Pet vẫn thiếu nguồn tổng. Xem [bằng chứng Gate 0](../quality/overview-summary-gate-0.md). Các hợp đồng dưới đây chưa phải As-built.
- Phạm vi: bốn thẻ trên tab **Tổng quan** của giao diện TypeScript/FastAPI.
- Chế độ trải nghiệm: hỗ trợ nhân sự CX đọc nhanh tình hình dự án trong khoảng đang chọn; kế thừa bố cục, màu, kiểu chữ và form hiện có theo Impeccable shape.
- Lượt lập kế hoạch ban đầu chỉ cập nhật tài liệu. Lượt triển khai đã kiểm tra database ở chế độ chỉ đọc, bổ sung fixture kiểm chứng calculation hiện có và chạy hồi quy; chưa triển khai bốn thẻ.

### Điểm dừng triển khai đã xác nhận

Ngày 05/10/2026, người dùng chọn **Tổng số ghi nhận** thay cho Tổng báo sai (lỗi), vì không phải dự án nào cũng có số lỗi. Không tự cộng node con để khắc phục thiếu nguồn tổng. Với chỉ số nền mới, SmartParking, VOL và VW Vũ Yên có numeric tại project; VSO và V-Pet không có quan sát tại project; ANVF không có tổng số numeric tại project. Dữ liệu của ba dự án còn lại nằm ở các nhóm/vấn đề, chưa có quyết định ánh xạ thành tổng dự án. V-Pet có cả số theo ngày và số lũy kế, không được cộng chung.

Cần người dùng chọn trước khi tiếp tục: giữ bốn thẻ toàn dự án và chấp nhận thiếu số liệu tại các dự án này; hoặc đổi rõ phạm vi ba thẻ diễn biến sang nội dung đang chọn; hoặc cung cấp mapping nguồn tổng hợp không trùng. Không coi yêu cầu triển khai chung là quyết định thay semantics hoặc cho phép cộng descendants. Phase 1 có nguồn đếm khả thi nhưng chưa được cài đặt; Phase 2–4 chưa qua điều kiện nguồn để phát hành.

## 1. Mục tiêu và những lựa chọn chưa chốt

Thay các thẻ Dự án, Nội dung theo dõi, Đơn vị đo, Điểm dữ liệu bằng thông tin có ý nghĩa nghiệp vụ trong khoảng đang xem. Tên dự án vẫn ở tiêu đề; đơn vị vẫn có tại từng biểu đồ. Không dùng metadata toàn bộ database để giả thành kết quả của khoảng đã chọn.

Chỉ số nền đã được người dùng chọn lại. Các quyết định đếm, xếp hạng thay đổi và cách xử lý thiếu nguồn vẫn theo bảng dưới; **việc đổi chỉ số không tự cho phép cộng node con, đổi phạm vi hoặc đổi cách tính dữ liệu lũy kế**:

| Quyết định | Mặc định đề xuất | Phương án thay thế cần duyệt |
|---|---|---|
| Chỉ số nền của ba thẻ diễn biến | **Đã chọn: Tổng số ghi nhận**, khóa API `Tổng số`, metric code `total` | Không tự fallback sang báo sai hoặc tỷ lệ khi thiếu tổng số |
| Đếm vấn đề | Vấn đề riêng biệt có dữ liệu nguồn hợp lệ trong khoảng, kể cả 0 thật | Chỉ vấn đề có phát sinh báo sai > 0; phải đổi nhãn tương ứng |
| Mức thay đổi | Lần tăng/giảm lớn nhất giữa hai kỳ lịch liền nhau, xếp hạng theo độ lớn chênh lệch tuyệt đối | Chênh lệch đầu–cuối; phải ghi rõ không phải xu hướng toàn khoảng |
| Phạm vi | Toàn dự án + khoảng Tổng quan đang chọn | Theo node; nếu chọn phương án này phải đổi nhãn/phạm vi, không gọi là tổng dự án |

Không thêm bộ chọn chỉ số cho bốn thẻ trong bản đầu. Nếu đổi mặc định ở Gate 0, chỉnh nhãn và contract cùng lúc; không để ba thẻ dùng ba chỉ số nền khác nhau.

## 2. Hiện trạng đã đối chiếu

| Source | Điều đã xác minh | Hệ quả triển khai |
|---|---|---|
| [`main.ts`](../../frontend/src/main.ts): `renderMain` | Bốn thẻ dùng `project.label/entities/units/records` từ bootstrap; không phải phép tính theo window | Cần read model tổng quan mới; không chỉ đổi nhãn |
| [`main.ts`](../../frontend/src/main.ts): `updateWorkspaceChrome`, `loadWorkspace` | Chrome chỉ cập nhật tiêu đề/ngữ cảnh; workspace được áp dụng bằng active request và giữ DOM chart | Phải cập nhật thẻ khi workspace thành công, không chỉ khi dựng toàn trang |
| [`app/api.py`](../../app/api.py): `bootstrap`, `_window`, `workspace` | Bootstrap là metadata toàn project; workspace có window, scopeIds, dataVersion và cache theo committed run | Tái sử dụng window/version; summary không lấy scopeIds node làm phạm vi toàn dự án |
| [`charts.py`](../../src/excel_visualization_pipeline/visualization/charts.py): `prepare_period_metric_summary` | SUM cho số lượng; tỷ lệ theo kỳ có trọng số; có coverage/ancestor logic | Tái sử dụng semantics đã có, kiểm chứng parity trước khi chọn adapter |
| [`ai/analytics.py`](../../src/excel_visualization_pipeline/ai/analytics.py): `_period_analytics` | Có peak/lowest, tie chọn kỳ mới nhất, largestIncrease/largestDecrease | Có thể tái sử dụng helper thuần; không gọi endpoint sinh AI để dựng thẻ |
| Cùng file: `_series`, `_build_points`, `_point` | Bỏ kỳ không hợp lệ rồi so với điểm hợp lệ trước; chỉ hỗ trợ day/week/month, giới hạn 60 kỳ; xử lý count/rate/zero riêng | Không lấy nguyên kết quả AI làm bằng chứng về kỳ lịch liền nhau; không áp giới hạn AI lên range dashboard âm thầm |
| [`workbook_parser.py`](../../src/excel_visualization_pipeline/parser/workbook_parser.py): `_apply_default_zero_rates` | Blank rate có thể được chuẩn hóa thành `default_zero_rate` và chart_value 0 | `chart_value.notna()` một mình chưa đủ chứng minh vấn đề có dữ liệu nguồn thật |
| [`date_ranges.py`](../../src/excel_visualization_pipeline/date_ranges.py) | Có ISO week, month, quarter; completeness của kỳ là boundary, không chứng minh mọi ngày có numeric | Tách kỳ chưa đầy đủ và thiếu dữ liệu trong kỳ |
| [`API contract`](../api/api-contract.md) | dataVersion chỉ nhận diện current read model; không historical workspace query | Không hứa tính lại thẻ theo revision cũ |

Các khác biệt AI/chart trên đây là rủi ro cần fixture, **chưa kết luận là lỗi calculation**. Gate 0 không được âm thầm sửa AI, Statistics, Comparison hoặc parser cho phù hợp thẻ mới.

## 3. Định nghĩa bốn thẻ đề xuất

### Thẻ 1 — Vấn đề có dữ liệu

- Giá trị là số `entity_id` cấp `item` riêng biệt có ít nhất một quan sát nguồn hợp lệ trong window của project.
- Quan sát tại `item` hoặc tình trạng `subitem` được ánh xạ về vấn đề sở hữu qua `parent_entity_id`; nhiều ngày/metric/tình trạng của một vấn đề chỉ đếm một lần.
- Không đếm project, nhóm `section`, tình trạng hoặc số lượt báo sai thành số vấn đề. Numeric tại nhóm/project không tự biến mọi vấn đề bên dưới thành có dữ liệu.
- Đề xuất nguồn hợp lệ: numeric/percentage/percentage_text đã chuẩn hóa hữu hạn, thuộc một trong ba metric chính và không bị quality gate loại. Zero thật được giữ. Gate 0 xác minh allowlist/value_kind thực tế, không suy đoán qua display text.
- Missing/NBSP/not_recorded/source_marker/text và `default_zero_rate` **không tự làm một vấn đề đủ điều kiện**. Một vấn đề có rate mặc định nhưng có numeric thật ở metric khác vẫn được đếm theo numeric thật đó.
- Không có quan sát đủ điều kiện khi dữ liệu/window đã tải thành công: hiển thị **0 vấn đề**. Nếu request lỗi/không xác định được phạm vi: `—`, không giả thành 0.
- Quan sát không ánh xạ được về `item` không được đoán theo depth hoặc chuỗi tên; loại có lý do và báo giới hạn đếm. Gate 0 lập danh sách hierarchy bất thường theo project.

### Nguồn cho thẻ 2–4 — một chuỗi cấp dự án hợp lệ

Ưu tiên chuỗi nguồn có thẩm quyền ở node cấp `project`, được xác định bằng ID và cấu trúc thực tế, không bằng tên hiển thị hoặc node mà UI tình cờ chọn.

Cả ba thẻ dùng metric `Tổng số` (nhãn **Tổng số ghi nhận**), không phụ thuộc việc có báo sai hay không. Thẻ đếm vấn đề vẫn xét dữ liệu nguồn hợp lệ ở cả ba metric theo định nghĩa riêng; không đổi thành đếm các vấn đề có tổng số numeric mà loại các vấn đề chỉ có số lỗi.

Không trộn số phát sinh theo ngày với số dư/lũy kế, dù chúng cùng có khóa `Tổng số`. Với nguồn lũy kế được đề xuất bổ sung sau này, phải khóa semantics trước khi chấp nhận vào tổng dự án hoặc aggregate tuần/tháng; không tự lấy hiệu để suy ra số phát sinh, không cộng snapshot các ngày như các lượt độc lập. Bản đầu chưa có mapping nguồn như vậy.

Không SUM mọi node để dựng chuỗi tổng dự án. Cùng effective unit chưa chứng minh các tập nghiệp vụ độc lập; có thể trùng cha/con hoặc nhiều nhóm theo dõi cùng tập cảnh báo. Không tự chuyển sang node có số lớn nhất, cộng các sheet hoặc dùng descendant thay nguồn project khi nguồn bị missing.

Gate 0 phải xác minh nguồn này cho **mọi project hiện có**, không chỉ VSO. Nếu project thiếu chuỗi có thẩm quyền:

1. Thẻ đếm vẫn hoạt động độc lập nếu đủ dữ liệu.
2. Ba thẻ diễn biến trả unavailable, ghi **Chưa có số liệu tổng hợp cấp dự án**.
3. Nếu muốn dùng tổng từ các thành phần, cần bảng ánh xạ phạm vi không trùng, đơn vị tương thích và quyết định nghiệp vụ riêng. Không tự thêm công thức trong đợt này.
4. Nếu nhiều project không thể có ba thẻ hữu ích, dừng duyệt phát hành để chọn nguồn/đổi hướng thẻ với người dùng; unavailable là hành vi an toàn, không phải bằng chứng đã đáp ứng giá trị nghiệp vụ.

### Thẻ 2 — Ghi nhận cao nhất

- Max trên các giá trị hợp lệ của chuỗi **Tổng số ghi nhận** cấp dự án trong window, theo grain đang hiển thị.
- Kèm ngày/kỳ, đơn vị và cảnh báo coverage nếu cần; không gọi tổng cả tháng là đỉnh một ngày.
- Nhiều kỳ cùng giá trị: chọn kỳ mới nhất, phù hợp policy tieBreak hiện có; tooltip nói rõ có đồng hạng.
- Một kỳ hợp lệ vẫn có đỉnh; không cần hai kỳ. Không có kỳ hợp lệ: `—` với lý do, không 0.

### Thẻ 3 — Ghi nhận thấp nhất

- Min trên cùng chuỗi và tập kỳ với thẻ cao nhất. Missing/marker không được đưa vào phép min như 0.
- Zero nguồn hợp lệ có thể là đáy. Calculation `total_sum` hiện dùng `sum(min_count=1)` và không suy ra zero cho tổng số missing; không tái sử dụng quy tắc inferred zero của báo sai cho chỉ số này. Giữ trường `inferredZero` trong draft contract cho khả năng mở rộng, nhưng không tự gắn true khi tổng số nguồn missing.
- Tie chọn kỳ mới nhất. Chuỗi hằng số có thể có đỉnh bằng đáy; không diễn giải thành chất lượng tốt/xấu.

### Thẻ 4 — Thay đổi lớn nhất

- Chỉ so hai kỳ lịch liền nhau trong cùng chuỗi, không nối xuyên kỳ missing. Day: hai ngày liền; week: hai tuần ISO liền; month: hai tháng lịch liền.
- Cặp ứng viên phải có giá trị hợp lệ ở cả hai đầu. Chính sách completeness đề xuất: loại cặp có boundary bị clip/chưa đủ kỳ khỏi xếp hạng thay đổi; giữ chúng trên chart và cực trị với chú thích. Coverage numeric thiếu trong kỳ được báo riêng, không nhầm với boundary completeness.
- `delta = value_to - value_from`; phần trăm dùng phép tính backend đã có `delta / abs(value_from) × 100` khi mẫu số khác 0. Xác minh tolerance/rounding và không viết phép tính khác trong frontend.
- Chọn cặp có `abs(delta)` lớn nhất, **không chọn theo phần trăm lớn nhất**; phần trăm là thông tin phụ. Đồng hạng chọn cặp có kỳ kết thúc mới nhất.
- Kèm dấu tăng/giảm, hai kỳ và chênh lệch tuyệt đối của **Tổng số ghi nhận**. Mẫu số 0: giữ delta, phần trăm null với lý do **Không tính được % vì kỳ trước bằng 0**. Tất cả cặp bằng nhau: **Không thay đổi**, không “chưa đủ dữ liệu”.
- Không có cặp đủ điều kiện: **Chưa đủ hai kỳ liền nhau để so sánh**, dù extrema có giá trị.
- Cặp previous-valid của AI không tự đáp ứng điều kiện liền nhau. Cần lọc toàn bộ cặp theo lịch rồi xếp hạng lại, không lấy highlight AI lớn nhất và chỉ kiểm tra một cặp đó.
- Đây là **biến động lớn nhất**, không phải xu hướng, anomaly, quan hệ nhân quả hay đánh giá tốt/xấu.

Nếu chọn Tỷ lệ báo sai thay cho count tại Gate 0: chênh lệch tuyệt đối là **điểm phần trăm**; thay đổi tương đối là `%` với nhãn riêng. Không lấy trung bình tỷ lệ ngày để dựng tỷ lệ tuần/tháng.

## 4. Phạm vi thời gian, phiên dữ liệu và tương tác

- Recent/custom: grain ngày; tuần/tháng: cùng nhóm và window backend của Tổng quan. Recent hiện là khoảng bao 10 ngày dữ liệu gần nhất, không mặc định 10 ngày lịch. Hai biên window được tính bao gồm.
- Không đưa quarter, AVG/ngày hoặc control range của tab Thống kê vào bản đầu. Thống kê có window độc lập, không lấy số thẻ Tổng quan để giả thành summary thống kê.
- Cả bốn thẻ dùng cùng project/window/dataVersion. Đếm vấn đề không đổi theo grain khi project và window không đổi; extrema/change đổi theo grain.
- Đổi entity/scope chỉ đổi các chart; bốn thẻ cấp dự án giữ phạm vi. Dòng chung ghi **Toàn dự án · Theo ngày/tuần/tháng · từ … đến …** để không gây hiểu nhầm chúng theo node.
- Đổi project/range/grain: fetch summary cùng workspace. Không gán số project cũ dưới tiêu đề project mới; hiển thị placeholder cho phạm vi mới trong lúc tải.
- Refresh cùng filter: force-fetch như hiện tại. Import committed: cập nhật cùng workspace không reload toàn trang; duplicate không giả tạo version mới. Không tự chạy AI.
- Error ở cùng phạm vi: có thể giữ số thành công gần nhất nhưng đánh dấu **Kết quả lần tải trước**, phạm vi/version cũ và hành động thử lại. Không gọi số cũ là kết quả đã cập nhật.
- Import diễn ra trong lúc GET đang đọc: Gate 0 phải xác minh identity version/cache khớp dữ liệu thực đọc. Frontend AbortController không giải quyết được payload backend bị gắn sai version.
- Không historical query/snapshot switch cho các thẻ trong bản đầu. Không thiết kế contributor drilldown, modal hoặc exact-cell lineage mới. Ngày/kỳ và tooltip căn cứ là đủ; chỉ mở provenance khi đã có ref/backend hợp lệ.

## 5. Kiến trúc dữ liệu/API đề xuất — chưa cài đặt

```text
SQLite current views của nguồn đã commit
  → phạm vi project + window Tổng quan + committed identity
  → bộ ánh xạ vấn đề / nguồn tổng dự án được Gate 0 khóa
  → adapter chuỗi chuẩn (calculation/coverage backend hiện có)
  → tính đếm / cực trị / cặp thay đổi bằng hàm thuần
  → workspace.overviewSummary (additive)
  → renderer bốn thẻ, format tiếng Việt, không tự tính
```

Thêm field optional `overviewSummary` vào GET workspace, không sửa bootstrap hoặc đổi khóa ba metric gốc. Tính cho `view=overview`/`all`; view khác có thể bỏ field/null, client cũ vẫn dùng được. Không tạo endpoint sinh AI/analysis snapshot, không cần Gemini/9Router, privacy gate hay token provider cho bốn thẻ.

Contract draft tối thiểu:

| Nhóm | Trường dự kiến | Quy tắc |
|---|---|---|
| Identity | `schemaVersion`, `policyVersion`, `project`, `window`, `grain` | Phiên bản schema/policy riêng, cùng context workspace |
| Phạm vi | `scope: project`, `sourceEntityRef`, `metricKey`, `metricDisplayName`, `effectiveUnit` | Chỉ số nền `metricKey: Tổng số`, `metricDisplayName: Tổng số ghi nhận`; nguồn có thẩm quyền; unavailable thì sourceRef null, có lý do |
| Đếm | `issueCount: {status, value, reason, excludedCount}` | Integer hoặc null; 0 chỉ khi đã xác định không có vấn đề đủ điều kiện |
| Cực trị | `peak`, `lowest` | Mỗi thẻ có status, value/unit, period, coverage, inferredZero, tieCount, reason |
| Thay đổi | `largestChange` | status, from/to periods và values, absolute, relativePercent, direction, eligiblePairCount, reason |
| Chất lượng | `validPeriodCount`, `expectedPeriodCount`, `limitations` | Phân biệt missing, coverage và clipped boundary |
| Version | `workspace.dataVersion` ở response gốc | Dùng chung, không tạo run/version giả hoặc suy ID từ tên tệp |

Status draft theo từng thẻ: ready / no_data / insufficient_data / unavailable. Request error/loading là trạng thái client, không serialize lỗi mạng thành 0. Không expose raw workbook/sheet/cell trong summary công khai.

Frontend mới gặp backend chưa có field: hiển thị **Chưa có dữ liệu tổng quan mới**, không fallback sang project.records/entities dưới nhãn nghiệp vụ mới. Triển khai backend additive trước frontend; giữ API cũ và renderer cũ đến khi đủ điều kiện đổi giao diện.

Cache gồm DB/source, committed identity, project, resolved window, grain, metric nền và policyVersion. Nếu metric/policy cố định server, chúng vẫn là identity tính toán hoặc cache phải được invalidate khi đổi cấu hình. Không cache lỗi hoặc unavailable do đang đọc giữa hai commit thành kết quả lâu dài.

Gate 0 khóa cách đọc snapshot nhất quán: `_load_source_snapshot` hiện dùng revision làm cache key nhưng vẫn đọc current SQLite, không dựng revision lịch sử. Cần kiểm tra race giữa việc lấy latest version, load hai current views và dựng response/cache. Chọn cơ chế read snapshot hoặc bounded version recheck/retry phù hợp nếu fixture chứng minh cần; không gắn version trước commit vào dữ liệu sau commit.

## 6. UX dự kiến

Giữ hàng bốn thẻ hiện có trên desktop, hai cột/ một cột theo bề rộng khả dụng. Không thiết kế lại toàn dashboard. Chỉ tab Tổng quan nhận bộ thẻ mới; không âm thầm thay semantics thẻ ở Thống kê. Tab Nhập Excel tiếp tục ẩn KPI như bản hợp nhất hiện tại.

```text
Toàn dự án · Tổng số ghi nhận · Theo tuần · [khoảng đang xem]

[Vấn đề có dữ liệu] [Ghi nhận cao nhất] [Ghi nhận thấp nhất] [Thay đổi lớn nhất]
[số vấn đề       ] [giá trị + đơn vị] [giá trị + đơn vị ] [delta + đơn vị     ]
[trong khoảng    ] [kỳ đạt đỉnh     ] [kỳ đạt đáy       ] [hai kỳ / % nếu có  ]
```

- Không thêm biểu đồ nhỏ/AI narrative hoặc bảng kiểm chứng vào từng thẻ. Thông tin tính/giới hạn trong tooltip có thể truy cập bằng focus; cảnh báo ảnh hưởng kết luận phải có chữ nhìn thấy.
- Không dùng xanh/đỏ để khẳng định tốt/xấu. Hiển thị tăng/giảm bằng chữ/dấu, màu giữ trung tính.
- Loading riêng vùng thẻ, không che chart, không phá DOM Plotly. Error phải có cách tải lại, unavailable phải giải thích thiếu nguồn/phạm vi.
- Nhãn/giải thích tiếng Việt; đơn vị đến từ backend. Giá trị dài, tên/kỳ dài xuống dòng; không crop. Không biến thẻ không tương tác thành button.
- Thiết kế trạng thái 0, missing, một kỳ, chuỗi hằng số, tie, clipped boundary, coverage thiếu, loading/error/stale và backend cũ trước khi viết renderer cuối.

## 7. Kế hoạch theo lát dọc và thứ tự phụ thuộc

Các phase sau thuộc đợt bốn thẻ, **không phải Phase 2 Contextual Comparison**. Mỗi lát phải hoàn tất backend thuần → validation/contract → frontend → test/bằng chứng trước lát tiếp theo. Không có bước gọi LLM; tái sử dụng calculation/evidence backend thay vì dựng Analytics Engine mới.

### Gate 0 — khóa semantics, nguồn và fixture

1. Chốt ba mặc định ở mục 1, scope project và nơi hiển thị.
2. Lập inventory mọi project: root/canonical source IDs, đơn vị, numeric/missing/marker, issue ancestry, ngày có dữ liệu; không giả định VSO đại diện tất cả.
3. So parity daily raw chart, period summary và AI `_point` trên zero/marker/mixed/coverage/kỳ thiếu. Chọn adapter dùng calculation Tổng quan làm chuẩn; chưa sửa công thức khi chưa có lỗi được chứng minh.
4. Khóa source project không trùng, issue allowlist + mapping và cặp lịch liền/completeness; chỉ rõ các khác biệt eligibility với AI cũ.
5. Kiểm tra version/read-cache race, range rộng vượt 60 kỳ AI, chi phí workspace và backward compatibility.
6. Viết fixture expected bằng tay và báo cáo Gate 0 dự kiến `specs/quality/overview-summary-gate-0.md`. Fixture/tests sẽ được tạo ở lượt triển khai, hiện chưa có.

Điều kiện GO: không còn ambiguity nguồn ở project hỗ trợ; mỗi project có status/giới hạn rõ; product owner duyệt giải pháp nếu thiếu nguồn tổng; contract/fixture được khóa. Chưa GO cho ba thẻ diễn biến nếu nguồn tổng chưa xác định, dù đếm vấn đề có thể triển khai độc lập sau khóa count contract.

### Phase 1 — Vấn đề có dữ liệu + hạ tầng summary

- Backend: hàm thuần đọc project data, ánh xạ ancestry và đếm distinct; response additive, policy/status/version.
- Validation: finite values, source classification, project isolation, cycle/orphan handling, không đếm default zero hoặc nhân bản ngày/metric.
- Frontend: renderer reusable một thẻ/count + context window; ba vị trí còn lại chưa công bố ready nếu chưa có tính toán. Bản dở dang chỉ dev/test, không phát hành bốn thẻ thay thế với số placeholder giả.
- Test: unit count matrix, API additive/current version, Playwright project/range change, 0 vs lỗi, API cũ.
- Gate 1: count khớp expected mọi project/fixture và không phải project.entities đổi tên.

### Phase 2 — Cặp Ghi nhận cao nhất / thấp nhất

- Tái sử dụng identity/window/status/renderer Phase 1 và period adapter Gate 0. Đây là một feature extrema, hai thẻ chung cùng chuỗi hợp lệ.
- Backend: chọn max/min của Tổng số ghi nhận, tie và coverage; tổng số missing không suy ra zero; không SUM node tree hoặc chọn fallback node.
- Frontend: ngày/kỳ, đơn vị, unavailable/partial; không cần chạy AI để có số.
- Test: missing/zero, một kỳ, constant/tie, ngày/tuần/tháng, root thiếu/cùng tên root/mixed-unit, tất cả project; đối chiếu chart hiện có.
- Gate 2: hai thẻ dùng cùng calculation/value set và source có thẩm quyền; không có min giả 0 hoặc tổng trùng.

### Phase 3 — Thay đổi lớn nhất

- Tái sử dụng chuỗi/cực trị/contract, chỉ bổ sung lọc cặp và ranking; không viết lại parser, coverage hay rate formula.
- Backend: cặp lịch liền đủ điều kiện, abs-delta ranking, dấu/%, tie và lý do null. Nếu dùng helper AI, bảo toàn policy previous-valid của AI cũ và regression cho callers đó.
- Frontend: hai kỳ so sánh, delta/%, 0 baseline, không đủ cặp, không thay đổi; không gọi highlight này là xu hướng.
- Test: tăng/giảm, zero baseline, khoảng missing, largest-by-absolute khác largest-by-percent, tie mới nhất, partial boundary và khác biệt với đầu–cuối.
- Gate 3: người dùng đọc được cặp căn cứ; kết quả không nối qua missing và không tạo % vô hạn.

### Phase 4 — freshness, parity và phát hành bộ đủ bốn thẻ

- Khóa cập nhật cùng workspace: Refresh cùng filter, committed import, response cũ đến muộn, đổi project/range/grain; chart và thẻ không lẫn phiên/phạm vi.
- Kiểm tra bất biến: đổi entity/scope không làm thẻ toàn dự án đổi ý nghĩa; count không đổi khi grain đổi mà window giữ nguyên.
- Kiểm thử backend/API và frontend hồi quy liên quan; test mọi project theo inventory, không chỉ dữ liệu mocked VSO.
- Responsive 1440×900, 1366×768, 1200×650 và 390×844; contrast, focus tooltip, số lớn/đơn vị dài, loading/error/unavailable. Giữ chart DOM ổn định và đánh giá Server-Timing.
- Chỉ retire bốn metadata card trên Tổng quan sau parity gate; không sửa các tab khác hoặc source import trong cùng phát hành nếu không cần.
- Đồng bộ PRD/use cases, dashboard behavior, API contract, acceptance/traceability và báo cáo bằng chứng dự kiến `specs/quality/overview-summary-metrics-evidence.md`.

Gate phát hành: toàn bộ tiêu chí dưới đạt; mọi sửa calculation thật phải có regression và báo tác động; lỗi toàn dự án không được che bằng kết quả chạy lại riêng. Nếu có test không ổn định từ trước, ghi rõ baseline/rerun và quyết định phát hành riêng.

## 8. Tiêu chí nghiệm thu và ca test dự kiến

Các ID/tên dưới là checklist proposal; **test chưa được viết hoặc chạy ở lượt này**. Không thay trạng thái các acceptance As-built hiện có.

| ID | Điều kiện đạt | Test dự kiến / lát |
|---|---|---|
| OV-KPI-01 | Đếm distinct item, nhiều subitem/ngày/metric chỉ một vấn đề; không đếm section/project | `counts_distinct_owned_issues`, Phase 1 |
| OV-KPI-02 | Numeric 0 thật được đếm; missing/marker/default_zero_rate-only không đủ điều kiện; lỗi không hiển thị 0 | `distinguishes_source_zero_and_inferred_rate`, Phase 1 |
| OV-KPI-03 | Window bao hai biên, project isolation; không dùng toàn lịch sử hoặc scopeIds node | `summary_uses_project_and_resolved_window`, Phase 1 |
| OV-KPI-04 | Root thiếu không fallback cộng descendants/cùng unit hoặc node lớn nhất | `missing_project_source_is_unavailable`, Phase 2 |
| OV-KPI-05 | Một kỳ vẫn có max/min; missing không thành đáy 0; constant/tie chọn kỳ mới nhất | `extrema_missing_zero_single_constant_ties`, Phase 2 |
| OV-KPI-06 | Extrema daily/week/month khớp chart canonical; coverage và kỳ clip ghi rõ | `extrema_matches_overview_calculation`, Phase 2 |
| OV-KPI-07 | Delta lớn nhất theo abs, không theo %; có cặp căn cứ, dấu và tie mới nhất | `largest_change_ranks_absolute_delta`, Phase 3 |
| OV-KPI-08 | Không nối kỳ missing; cặp boundary chưa đầy đủ bị loại theo policy; ít cặp trả insufficient | `change_requires_adjacent_eligible_periods`, Phase 3 |
| OV-KPI-09 | Baseline 0 không % vô hạn; delta 0 có ready/unchanged; tỷ lệ nếu được duyệt dùng điểm phần trăm | `zero_baseline_and_rate_units`, Phase 3 |
| OV-KPI-10 | Cards hoạt động khi AI disabled/unconfigured/provider lỗi, không gọi route/provider AI | `summary_is_provider_independent`, các lát |
| OV-KPI-11 | Old API fields/query/defaults giữ nguyên; field mới absent/null xử lý trung thực | `additive_summary_contract`, các lát |
| OV-KPI-12 | Playwright đổi project/range, Refresh cùng filter, import committed/duplicate; dữ liệu mới không reload | `summary_refresh_and_import_freshness`, Phase 4 |
| OV-KPI-13 | Response cũ không đè số mới; không trộn chart/cards version; backend concurrent commit không cache sai identity | `summary_rejects_stale_response` + backend race fixture, Phase 4 |
| OV-KPI-14 | Đổi entity/scope không đổi phạm vi toàn dự án; change grain với window cố định không đổi count | `summary_scope_and_grain_invariants`, Phase 4 |
| OV-KPI-15 | Range dài không âm thầm cắt 60 kỳ; latency/cache hợp lý, không tăng Plotly work | `summary_long_range_and_render_stability`, Phase 4 |
| OV-KPI-16 | Tất cả project có kết quả/giới hạn đúng inventory; legacy/missing-unit/multi-sheet không đoán nguồn | `summary_project_inventory_matrix`, Gate 0–4 |
| OV-KPI-17 | 4 viewport không crop/tràn ngang; 0/missing/loading/error/partial đọc rõ, tooltip có focus | `overview_summary_responsive_states`, Phase 4 |

Backend fixture tối thiểu: toàn missing, 0 nguồn, rate 0 mặc định không numeric khác, mixed numeric+missing, source marker, parent coverage, một kỳ, constant/tie, ngày đứt đoạn, partial week/month, nhiều item/subitem, root missing, root và child có cùng dữ liệu, mixed unit/cùng unit nhưng overlap, orphan/cycle, nhiều sheet/root, hai project cùng tên vấn đề, committed revision đổi trong GET.

Playwright dùng fixture cho race/error/contract cũ và giữ metadata/API keys thật. Kiểm chứng tất cả project bằng SQLite fixture/baseline đã biết, không ghi vào DB vận hành chỉ để tạo ảnh. Evidence phân biệt ảnh mocked, backend fixtures và kiểm chứng workbook thật nếu thực sự đã chạy.

## 9. Module dự kiến thay đổi và tái sử dụng

| Module | Dự kiến | Không làm |
|---|---|---|
| `src/excel_visualization_pipeline/overview_summary.py` (mới, đề xuất) | Read model thuần: source resolver, issue mapping/count, extrema/change policy | Không chứa HTTP/provider/prompt hoặc tạo engine thứ hai |
| `visualization/charts.py`, `date_ranges.py` | Tái sử dụng prepared calculation và lịch; chỉ extract helper tối thiểu nếu cần | Không đổi SUM/AVG/rate âm thầm |
| `ai/analytics.py` | Tham khảo/tái sử dụng helper thuần khi parity đủ; giữ caller AI cũ | Không gọi AIApplicationService cho card, không phá giới hạn/privacy/provider hiện có |
| `app/api.py` | Field overviewSummary, cache/source version coherence, serialize | Không sửa POST import hoặc migration |
| `frontend/src/main.ts` | Nhận optional contract, cập nhật summary khi workspace đổi, phạm vi tab | Không dựng lại Plotly hoặc tính số trong frontend |
| `frontend/src/overview-summary.ts` (mới, đề xuất), `style.css` | Renderer/type/format trạng thái reusable và bố cục thẻ scoped | Không refactor toàn app hoặc đổi biểu đồ |
| Tests backend + `frontend/e2e/fixtures.ts`, spec mới | Count/extrema/change, API/version, UI/freshness/range | Không đổi expected để che lỗi semantics |
| `PRODUCT.md`, specs product/api/frontend/quality | Đồng bộ As-built sau gate phát hành | Không đánh dấu đã hoàn thành ngay khi mới có plan |

Đích test mới đề xuất: `tests/test_overview_summary.py`, `frontend/e2e/overview-summary.spec.ts`; hồi quy hiện có: `test_api.py`, `test_charts.py`, `test_date_ranges.py`, tests AI analytics thực tế, `workspace-freshness.spec.ts`, `workspace-performance.spec.ts`, `contrast.spec.ts`, `unified-import-workspace.spec.ts`. Gate 0 phải kiểm tra tên/path test tồn tại và dùng đúng các test đã có, không công bố lệnh chưa chạy là bằng chứng.

## 10. Quyết định triển khai tiếp theo

Đợt này chưa cần migration SQLite, prompt mới, Gemini/9Router hay AI validation mới. Tái sử dụng dữ liệu chuẩn hóa và phép tính đã kiểm chứng, thêm read model/contract cùng renderer phù hợp.

Bước tiếp theo là **Gate 0**, không viết ngay bốn số vào UI. Báo cáo cần có: ba lựa chọn đã khóa; inventory mọi project; mapping nguồn cấp dự án/issue; parity calculation; policy missing/zero/gaps/partial; read-version/cache; fixture expected; kết luận GO theo từng lát và những project chưa thể cung cấp summary trung thực.

Chỉ số nền đã chốt lại là **Tổng số ghi nhận**. Độ phủ numeric tại node project tăng từ 1/6 dự án với báo sai lên 3/6 dự án với tổng số. Cần xác nhận cách xử lý ANVF, VSO và V-Pet: giữ unavailable ở phạm vi toàn dự án, hay cung cấp mapping/duyệt đổi phạm vi rõ ràng. Chưa tự lựa chọn thay người dùng.

Nếu Gate 0 phát hiện không có nguồn tổng dự án đáng tin cậy, cần người dùng chọn nguồn hoặc thay ý nghĩa ba thẻ diễn biến trước Phase 2; không tự nới phạm vi sang aggregation liên node. Không có cam kết thời gian hoàn thành từ bản kế hoạch này.
