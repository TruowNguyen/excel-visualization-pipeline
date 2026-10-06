# Bằng chứng triển khai — bốn thẻ Tổng quan theo nguồn

> Báo cáo mốc triển khai ban đầu. Feedback tiếp theo mở rộng thẻ sang Thống kê và thu gọn khối thông tin phía trên: xem [bằng chứng cập nhật](overview-statistics-summary-evidence.md). Các ảnh cùng tên trong `.impeccable/review/` đã được tạo lại theo giao diện thu gọn, không phải bản lưu bất biến của mốc này.

Ngày: 05/10/2026. Contract: [đặc tả đã cài đặt](../frontend/overview-summary-metrics.md). Người dùng đã duyệt Tổng số ghi nhận + nguồn riêng có nhãn rõ; không còn áp dụng điểm dừng project-only của đề xuất cũ.

## 1. Các phần đã cài đặt

| Yêu cầu | Implementation / bằng chứng |
|---|---|
| Bốn thẻ nghiệp vụ theo khoảng | `overview_summary.py`, `overview-summary.ts`; chỉ thay metadata KPI của Tổng quan |
| Đếm distinct vấn đề toàn dự án | Ownership item/subitem; physical zero, missing/default zero, validation/finite/project/window fixtures |
| Tổng số ghi nhận thay vì lỗi | Metric key `Tổng số`; no error dependency; daily raw và weekly/monthly canonical `total_sum` |
| Nguồn project hoặc nguồn riêng | `config/overview-sources.json`; root priority, explicit named mapping, lựa chọn ANVF/VSO, V-Pet chỉ daily flow |
| Không tạo tổng trùng/lũy kế | Không SUM tree/sheet; cumulative/unknown-unit/cycle/orphan/retired default fail closed |
| Cao nhất/thấp nhất | Same valid set, missing/zero/single/constant/latest tie, period/coverage/unit |
| Thay đổi lớn nhất | Absolute ranking, signed delta/relative %, calendar adjacency, clipped boundaries, zero baseline, unchanged |
| Version/read cache | One SQLite transaction; cache accepts exact snapshot version, retry/rekey fixtures |
| Freshness giao diện | Import same document, Refresh same filters, superseded response, project/range/source change, error/legacy response |
| Responsive và accessibility | 4 viewports, native select/details keyboard, không tràn ngang; giữ chart DOM khi đổi source |

Không gọi LLM, không đổi SUM/AVG/rate/parser, không migration hoặc nhập vào database vận hành. Không thêm lineage/drilldown, historical query, quarter/AVG/ngày cho thẻ hoặc xóa các feature khác.

## 2. Backend regression thực chạy

```text
python -m pytest
391 passed, 19 warnings in 99.32s (0:01:39)
```

Toàn bộ suite backend trong repository tại thời điểm chạy. Warnings là deprecation FastAPI/asyncio hiện có. Test mới của feature: 21 cases tại `tests/test_overview_summary.py` và 3 integration/race cases tại `tests/test_overview_summary_api.py`; fixture Gate 0 cũ vẫn được giữ và chạy trong suite.

Race fixture commit workbook mới sau khi read transaction đã đọc version nhưng trước khi đọc hai views: response vẫn giữ old version + old values; lần đọc tiếp theo có new version + new values. Fixture khác đổi version trước source read và kiểm tra workspace cache chỉ ghi key version thực dùng. Không giả lập historical query.

Lát 1 count/source: 11 backend tests và 2 Playwright cases đạt trước khi thêm extrema. Lát 2 thêm extrema: 16 backend tests và 3 Playwright cases đạt trước khi thêm change. Lát 3: 21 backend tests và 4 Playwright cases đạt; integration/version hoàn thiện ở lát 4.

## 3. Frontend và build

`npm run build`: **đạt**, TypeScript + Vite (3.36s). Còn cảnh báo kích thước chunk Plotly >500KB có từ trước; không giải quyết ngoài phạm vi.

Full Playwright đã chạy sau các sửa fixture:

```text
cd frontend
npx playwright test
124 passed (2.4m)
```

Bao gồm **14 cases Overview summary** và các suite AI, lineage, Comparison, Import, freshness, terminology, contrast, performance hiện có. Không chỉ chạy VSO hoặc chạy lại riêng failed tests để thay full-suite verdict. Giữ Plotly DOM trong performance test: cùng node, 0 render starts khi figure không đổi; figure đổi cập nhật một lần (1 start/1 complete).

Các lỗi test mới phát hiện trong quá trình làm đã được sửa, không che bằng đổi semantics sản phẩm:

- Fixture payload ban đầu đặt nhầm vào trace thay vì workspace; đã sửa scope.
- Refresh assertion cần seed entity rõ ràng để hai query cùng filter, tránh so initial server-default với explicit entity sau load.
- Harness delay trước đây dùng counter mutable sau `await`, có thể gán requestNumber mới cho response cũ. Đã freeze requestNumber tại thời điểm nhận request; stale-response fixture dùng delay đủ để assert pending trước khi đổi mode. Không đổi abort guard ứng dụng để làm test đạt.

## 4. Kiểm chứng dữ liệu thực — cả sáu dự án

SQLite cấu hình thực tế `data/local/analytics.sqlite3`, source `cx_report_master`; đọc bằng `mode=ro`, một transaction cho hierarchy/observations. Gọi pure summary với cùng `_window` backend, không gọi route aggregate lineage có khả năng ghi metadata và không import dữ liệu để dựng ảnh.

Khoảng recent **07–16/09/2026**; số đã kiểm chứng:

| Dự án | Nguồn dùng | Phạm vi ba thẻ | Số vấn đề | Cao nhất | Thấp nhất | Delta lớn nhất |
|---|---|---|---:|---:|---:|---:|
| ANVF | Đăng ký bus | Nguồn riêng | 3 | 18.900 | 18.250 | −550 |
| SmartParking | SmartParking | Project | 5 | 9.437 | 6.586 | −1.727 |
| V-Pet | Cảnh báo vi phạm | Nguồn riêng | 3 | 148 | 51 | −64 |
| VOL | VOL | Project | 2 | 26.027 | 3.921 | −18.216 |
| VSO | Chất lượng cảnh báo – ghi nhận trên hệ thống | Nguồn riêng | 7 | 657 | 71 | +448 |
| VW Vũ Yên | VW Vũ Yên | Project | 4 | 251 | 151 | −97 |

Đơn vị tương ứng: ANVF/SmartParking/VOL = Lượt; V-Pet = Lượt (ngày); VSO/VW = Cảnh báo. Mỗi nguồn có 9/10 ngày numeric trong recent, giữ ngày thiếu thay vì 0. Số trên không so sánh chéo các nguồn/đơn vị.

Đã chạy thêm week và month cho mỗi dự án (**18 tổ hợp project/mode** tổng cộng). Weekly extrema/change có kết quả và coverage warnings. Monthly window 01/08–16/09/2026 có tháng 08 đủ, tháng 09 chưa đủ; tất cả monthly changes trả `insufficient_data`, extrema vẫn có số kèm partial warning. Đây là kết quả đúng chính sách loại boundary chưa đầy đủ, không phải lỗi tải.

## 5. Bằng chứng giao diện và finish

Ảnh **dữ liệu mô phỏng Playwright**, không phải screenshot production:

- `.impeccable/review/overview-summary-desktop.png`: 1440×900.
- `.impeccable/review/overview-summary-user-1366.png`: 1366×768.
- `.impeccable/review/overview-summary-user-1200.png`: 1200×650.
- `.impeccable/review/overview-summary-mobile.png`: 390×844.

Đã mở và kiểm tra cả bốn file, document top/fullpage, chart đã load; source note và bốn thẻ không crop/tràn ngang. Main-thread inspection giới hạn hai vòng. Detector chạy **một lần** trên changed UI targets: chỉ advisory Inter hiện có; giữ incumbent identity. Không tạo raster shipping assets.

Fresh finish reviewer đã mở cả bốn captures và đối chiếu source/contract, trả **disposition: ship** cho vùng tổng quan mới, không có material fixes. Bố cục 4/4/2/1 cột ở bốn viewport đúng contract. Review không bao gồm các vùng AI/sidebar không liên quan và screenshots không chứng minh dữ liệu production. Full Playwright 124 pass đã đóng phần runtime vốn còn pending khi reviewer kiểm tra.

Fresh documenter đã hoàn tất phần bằng chứng trong `.impeccable/surfaces/frontend-src-main-ts.md`: đối chiếu source và cả bốn ảnh, ghi lại phạm vi nguồn, bố cục responsive, control/focus và trạng thái thiếu/tải/lỗi. Giữ nguyên các contract và bằng chứng AI/import trước đó; không sửa DESIGN.md/design.json thiếu từ trước.

## 6. Giới hạn và vận hành

- Source mapping là explicit ID, không heuristic. Workbook mới đổi cấu trúc/ID cần rà lại mapping; không tự fallback sang node lớn nhất. Preference cũ sai có hành động khôi phục nguồn mặc định.
- Cumulative nguồn không có aggregation mới; V-Pet không gộp lũy kế với daily alerts.
- Coverage thiếu không được tuyên bố đủ; grouped SUM vẫn theo calculation hiện có. Không đánh giá tăng/giảm là tốt/xấu, không gọi largest movement là xu hướng.
- Public dataVersion là current read snapshot, không bảo đảm response luôn là commit mới nhất ngay tại thời điểm gửi và không hỗ trợ historical recalculation.
- Chưa commit/push/deploy; tất cả sửa trong workspace. Những thay đổi AI/import có từ trước được giữ nguyên.
