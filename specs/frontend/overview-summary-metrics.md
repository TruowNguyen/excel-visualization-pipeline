# Bốn chỉ số Tổng quan theo nguồn — đặc tả đã cài đặt

Phiên bản: v1.1, 05/10/2026. Phạm vi: TypeScript/FastAPI, tab Tổng quan và Thống kê. Bằng chứng ban đầu: [triển khai Tổng quan](../quality/overview-summary-metrics-evidence.md); bổ sung hiện tại: [Thống kê và giao diện thu gọn](../quality/overview-statistics-summary-evidence.md). Thay thế đề xuất chỉ dùng nguồn project trong [plan v1.2](overview-summary-metrics-plan.md).

## 1. Phạm vi và nguồn

Thẻ **Vấn đề có dữ liệu** đếm toàn dự án trong khoảng/kỳ của tab đang xem. Ba thẻ **Ghi nhận cao nhất / Ghi nhận thấp nhất / Thay đổi lớn nhất** dùng một nguồn duy nhất, metric key `Tổng số`, tên hiển thị Tổng số ghi nhận. Không yêu cầu metric báo sai để tính các thẻ này.

Ưu tiên đúng một root `project` có tổng số nguồn numeric hợp lệ trong current history. Không đổi nguồn theo ngày thiếu, node biểu đồ hoặc scope children. Nếu không có root numeric, chỉ dùng mapping được duyệt trong `config/overview-sources.json`; không SUM cha/con, các vấn đề, nhóm hoặc sheet. Nhiều root numeric thì unavailable, không đoán root lớn nhất.

| Dự án hiện tại | Mặc định | Các nguồn có thể chọn |
|---|---|---|
| SmartParking / VOL / VW Vũ Yên | Root cấp dự án | Root |
| ANVF | Đăng ký bus | Đăng ký bus, Điểm danh xe bus, Điểm danh xe ghép |
| VSO | Chất lượng cảnh báo – ghi nhận trên hệ thống | Nhóm trên hoặc Test thực địa, xem riêng |
| V-Pet | Cảnh báo vi phạm | Nguồn phát sinh theo ngày này; không đưa số cư dân đăng ký/thú cưng lũy kế vào tổng |

Mapping dựa trên ID cụ thể và kiểm tra hierarchy/project, không match tên hiển thị. Nguồn missing/retired, ancestry sai, thiếu đơn vị hoặc unit lũy kế không được tự thay bằng nguồn khác. Có thể chọn nguồn khác đã duyệt; nguồn mặc định mất thì trả unavailable cho đến khi người dùng chọn/cập nhật mapping. Dự án mới thiếu root và mapping cũng unavailable.

## 2. Calculation

### Đếm vấn đề

Finite numeric/percentage/percentage_text của một trong ba metric nguồn, validation `valid` hoặc `warning`. Missing/text/marker/default_zero_rate không đủ điều kiện. Numeric zero thật được đếm. Distinct item: observations tại subitem quy về item sở hữu; item phải có ancestry hợp lệ tới root project. Project/section không được đếm. Cycle/orphan loại khỏi count và báo `excludedCount`; nhiều ngày/metric/subitem của một vấn đề chỉ đếm một lần. Window inclusive, không dùng bootstrap metadata.

### Chuỗi Tổng số ghi nhận và cực trị

- Day: đúng raw numeric observation của source; không suy ra total zero. Ngày trùng observation không được tự cộng thành một daily point.
- Week/month: dùng `prepare_period_metric_summary(...).total_sum`, SUM theo calculation Tổng quan hiện có; `sum(min_count=1)` giữ toàn missing là missing. Không average daily rates hoặc mượn inferred-zero của báo sai.
- Numeric source không hợp lệ được loại khỏi chuỗi summary. Coverage là số ngày numeric và số ngày lịch trong phần window đang xem; boundary completeness tính riêng theo tuần ISO/tháng tự nhiên.
- Max/min trên cùng valid value set, tie chọn kỳ mới nhất. Một kỳ vẫn có extrema, chuỗi hằng có max=min. Mỗi kết quả có đơn vị, period, tie count, coverage và boundary completeness. `inferredZero=false` với chỉ số tổng này.

### Thay đổi lớn nhất

Liệt kê cả kỳ lịch missing trước khi xét cặp. Chỉ hai kỳ lịch liền nhau đều numeric và boundary đầy đủ; không so previous-valid qua gap. Rank theo `abs(to-from)`, không theo phần trăm; tie chọn target kỳ mới nhất. `absolute=to-from`, `relativePercent=absolute/abs(from)*100`; near-zero tolerance `1e-12`, kết quả round 8 chữ số. Baseline zero giữ absolute, relative null có lý do. Delta zero là ready/unchanged, không insufficient. Không có cặp thì insufficient_data.

Kỳ có ngày numeric thiếu vẫn dùng SUM đã có; coverage và cảnh báo hiển thị rõ, không tuyên bố mọi ngày đều được ghi nhận. Loại cặp boundary bị cắt nhưng vẫn giữ extrema kỳ đó với chú thích. Không suy ra số phát sinh từ hiệu lũy kế; không bổ sung công thức/aggregation mới cho lũy kế trong đợt này.

## 3. API và version

GET workspace thêm optional `overview_source=<entityRef>`; áp dụng cho view overview/statistics/all. Response có `overviewSummary` trên overview/all và `statisticsSummary` trên statistics/all; field không thuộc view trả null. Client cũ giữ các query/chart/metric key cũ. Public `dataVersion` không đổi và dùng chung cho chart/summary.

Summary gồm schemaVersion, policyVersion, project, metricKey/displayName, window, grain, scope (`project`/`source`/null), source, sourceChoices, issueCount, peak, lowest, largestChange, valid/expectedPeriodCount, limitations. Status ready/no_data/insufficient_data/unavailable khác loading/error client. Peak/lowest có value/unit/period/tieCount; change có from/to, signed absolute, relativePercent/relativeReason, direction, eligiblePairCount/tieCount. Không expose workbook/cell/raw text hoặc tạo analysis/import run mới.

Source không thuộc danh sách hợp lệ → 422; không tự đổi source âm thầm. Query không cung cấp source → mặc định đã duyệt. Root mới có tổng numeric được ưu tiên; preference child cũ khi không còn được hỗ trợ sẽ cần khôi phục nguồn mặc định.

`load_current_snapshot` đọc committed version, entities và observations trong một SQLite read transaction. Source cache chỉ ghi snapshot nếu version thực đọc khớp cache key; bounded retry tối đa 3 nếu thay đổi giữa lấy version và đọc snapshot, rồi 503 có thể thử lại. Workspace cache được rekey theo version snapshot thực dùng; key còn chứa source query và toàn bộ policy JSON. Import sau khi snapshot đã đọc có thể khiến response cũ nhưng vẫn đúng identity, không phải latest-at-response guarantee. Không historical revision query.

## 4. Giao diện và vòng đời

- Thay bốn metadata KPI ở cả Tổng quan và Thống kê; giữ biểu đồ, import/Comparison/AI ngoài phạm vi.
- Bỏ heading “Tổng quan trong khoảng đã chọn” và khối thời gian/nguồn mở sẵn phía trên thẻ theo feedback. Giữ bốn thẻ; tên nguồn, phạm vi, khoảng và cách tính nằm trong **Cách đọc các chỉ số**, mặc định đóng. Thẻ đếm ghi **Toàn dự án** riêng.
- Trong mục thu gọn, nguồn được ghi **Nguồn tổng hợp cấp dự án** hoặc **Nguồn theo dõi riêng, không phải tổng toàn dự án**; select chỉ có khi nhiều lựa chọn. ANVF/VSO chọn độc lập với node chart. Nguồn nhớ theo project, dùng chung hai tab trong sessionStorage, không lưu tệp hoặc credential. Đổi nguồn giữ mục mở và focus select.
- Loading/error không hiện số cũ như số của phạm vi mới. API cũ thiếu summary → dấu — và lý do, không đổi nhãn project.records/entities thành số nghiệp vụ.
- Refresh giữ filter/source và fetch lại. Import committed cập nhật cùng workspace, không reload document. Request superseded không ghi đè; dùng AbortController/current request guard hiện có.
- Stored source không hợp lệ có nút **Khôi phục nguồn mặc định**, không reset chart filters. Nội dung “Cách đọc các chỉ số” dùng details/summary native, truy cập được bằng bàn phím.
- 1440/1366: bốn cột; 1200: hai cột; 390: một cột, không crop/tràn ngang. Không thêm modal, chart nhỏ hay tính số ở frontend.

### Thống kê

- Dùng đúng danh sách kỳ và `period_start/period_end` từ `_statistics_period_window` dùng cho chart: ngày/tuần/tháng/quý, số kỳ/gần nhất/toàn bộ/khoảng riêng, có hoặc không kỳ chưa đầy đủ. Không lấy khoảng Tổng quan ở sidebar thay cho khoảng Thống kê.
- `sum` và `both`: thẻ dùng `prepare_period_statistics(...).period_sum`, nhãn **Tổng trong kỳ**. Với `both`, mục thu gọn ghi rõ biểu đồ có hai cách tính nhưng ba thẻ dùng tổng; không nhập hai chuỗi thành một số.
- `average`: dùng `average_per_day` của cùng hàm, đơn vị nguồn/ngày và nhãn **Trung bình mỗi ngày**. Không chia lại cho ngày lịch; giữ quy tắc eligible days/source marker/coverage kế thừa hiện có. Không thay công thức Thống kê.
- Count chỉ nhận observation thuộc các kỳ đang hiển thị, kể cả khi có khoảng trống giữa các kỳ. Cực trị/chênh lệch chỉ nhận giá trị calculation đang chọn. Không nối hai kỳ không liền lịch hoặc dùng kỳ boundary chưa đầy đủ để tính thay đổi.
- `statisticsSummary` bổ sung `calculation` (`sum`/`average_per_day`) và `requestedMode`. Không có kỳ phù hợp: `window=null`, count/extrema/change `no_data`, số hiển thị — có giải thích; không mượn số Tổng quan.
- Context key frontend phân biệt tab; Thống kê gồm chart entity/scope (vì có thể ảnh hưởng danh sách kỳ), grain/cách tính/khoảng/kỳ/incomplete/source. Request guard/cache/version dùng lại cơ chế hiện có.

## 5. Acceptance theo lát dọc

| Lát | Điều kiện | Bằng chứng tự động |
|---|---|---|
| 1 — đếm + contract | Distinct ownership, zero/missing/default zero/quality, source isolation, API cũ trung thực | `test_overview_summary.py` count/source cases; Playwright count/old API |
| 2 — cực trị | Parity SUM, daily raw, missing/single/constant/tie/partial, đổi nguồn giữ count/chart | Backend extrema/period cases; Playwright extrema/source/chart identity |
| 3 — thay đổi | Abs ranking, adjacent calendar, missing gap, clipped boundary, zero baseline, unchanged | Backend change/long range cases; Playwright signed delta/baseline cases |
| 4 — freshness/finish | Atomic version, cache rekey, import/refresh/late response/project/error, responsive | `test_overview_summary_api.py`; Playwright summary/freshness/import/contrast suites |

Chi tiết thực chạy nằm trong evidence, không coi bảng này là tuyên bố mọi trường hợp tương lai đã được kiểm thử. Quý và AVG/ngày chỉ tái sử dụng ở Thống kê, không bổ sung cho Tổng quan. Aggregate lineage/contributor drilldown, historical snapshot và công thức lũy kế mới không thuộc tính năng này.
