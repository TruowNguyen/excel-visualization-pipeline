# Bằng chứng nghiệm thu Nhập Excel hợp nhất

- Ngày: 05/10/2026.
- Phạm vi: hợp nhất Nhập Excel và Lịch sử nhập; nhập mới ưu tiên, lịch sử phụ. Không API/schema/migration mới, không replay, không tìm kiếm/phân trang nâng cao.
- Đặc tả: [Nhập Excel hợp nhất](../frontend/unified-import-workspace.md).
- Giao diện/ảnh dùng dữ liệu mô phỏng từ Playwright, **không chứng minh đã nhập workbook thật vào database vận hành**. Backend regression dùng SQLite/fixture của test.

## 1. Kết quả chạy thực tế

| Lệnh | Kết quả |
|---|---|
| `cd frontend; npm run build` | Thành công: TypeScript + Vite. Cảnh báo bundle Plotly lớn hơn 500 kB, không phải lỗi build. |
| `python -m pytest tests/test_api.py tests/test_storage.py -o addopts='' -q` | **15 passed**, 19 cảnh báo deprecation của FastAPI/Python, 43,86 giây. |
| `cd frontend; npm test` | **107 passed, 2 failed**, 109 ca, 6,1 phút. 18 ca mới của tab nhập đều đạt; hai lỗi thuộc Comparison/Audit round trip và numeric-filter debounce. Không công bố toàn dự án xanh. |
| `cd frontend; npm test -- e2e/contextual-comparison.spec.ts e2e/workspace-performance.spec.ts --grep 'Audit round trip\|rapid numeric'` | **2 passed**, 15,7 giây khi chạy lại riêng, không sửa hai test/source Comparison hoặc debounce. Kết quả cho thấy không tái hiện lỗi trong lần này, chưa chứng minh không còn flakiness. |
| `cd frontend; npm test -- e2e/unified-import-workspace.spec.ts e2e/workspace-freshness.spec.ts e2e/contrast.spec.ts` sau sửa focus | **24 passed**, 36,1 giây (18 ca nhập + 3 freshness + 3 contrast). Sau đó bổ sung ca parity của nút mở đối chiếu; kết quả cuối ghi ở mục 5. |
| Cùng lệnh trên, lần cuối sau ca parity và sửa fixture version đúng kiểu string | **25 passed**, 36,3 giây (19 ca nhập + 3 freshness + 3 contrast); ảnh 12 trạng thái/viewport được chụp lại ở lần này. |
| `impeccable.cmd detect --json frontend/src/main.ts frontend/src/style.css frontend/src/import-history.ts` | Một advisory `overused-font` cho Inter có sẵn. Giữ kiểu chữ incumbent, không thay nhận diện toàn dashboard; không có finding khác. |

Không suy diễn từ lần chạy lại rằng lần chạy toàn bộ không có lỗi. Rà soát độc lập và xác nhận cuối được ghi ở mục 5.

## 2. Mapping parity và kiểm thử

Test mới: [unified-import-workspace.spec.ts](../../frontend/e2e/unified-import-workspace.spec.ts), 19 ca (15 ca hành vi + 4 kích thước màn hình); ca parity của nút mở đối chiếu được thêm sau lần chạy toàn bộ 109 ca.

| Phần yêu cầu | Ca kiểm thử đã chạy | Bằng chứng |
|---|---|---|
| Nhập ưu tiên, history đóng/lazy-load; không tab history riêng | `import first: history never resets…` | Chưa mở history không GET; form DOM/File, preview và snapshot confirmation còn nguyên sau mở/chi tiết/đóng. |
| Session history cũ có đích mới; vào tab import bình thường ưu tiên nhập | `legacy history session maps…` | Migration sang import, history mở có chủ đích; reentry từ nav collapse. |
| Nhập không phụ thuộc kho có dữ liệu hoặc workspace khỏe | 2 ca `can preview without an analytical workspace…` | Empty bootstrap và lỗi bootstrap vẫn preview/enable confirmation. |
| History lỗi/loading/rỗng không xóa phiên nhập hoặc list tốt gần nhất | `history refresh failure…`; `unknown POST outcome…` | Giữ list, File/commit gate/focus; empty list không tự mở khóa khi POST chưa rõ. |
| Null khác zero, nguồn không thực thi HTML | `history detail distinguishes…` | Null thành `—`, 0 thành `0`, script/img source chỉ là text. |
| Chống history response cũ | `late old history response…` | GET cũ 350ms trả sau GET mới 15ms không đè list mới. |
| Một POST đúng file/hash/mode; kết quả ghi độc lập hai GET | `single POST and receipt survive both refresh failures…` | Nhấn đôi một POST; workspace/history lỗi vẫn giữ committed; retry chỉ GET; focus đúng attempt; báo cáo và nhập tệp khác hoạt động. |
| Tệp trùng không run/version mới; focus đúng attempt trùng | `duplicate highlights…` | Không workspace fetch mới; `attempt_id=3` được highlight. |
| Nút đối chiếu từ biên nhận thực sự lấy workspace hiện hành, quay lại giữ committed | `receipt opens current audit data…` | Bổ sung sau bộ đầy đủ: yêu cầu `view=audit`, bảng có dữ liệu nguồn; không khôi phục tab audit chính hoặc thêm POST. |
| Không báo biểu đồ cập nhật khi version chưa đổi | `unchanged workspace version…` | Giữ committed, hiện trạng thái tải lại chưa xác nhận thay vì thành công giả. |
| Mất phản hồi ghi không auto retry hoặc đối soát theo tên/hash | `unknown POST outcome stays locked…` | File/commit bị khóa, mở history, chỉ một POST dù GET rỗng. |
| Hash guard yêu cầu kiểm tra lại, không ghi lại tự động | `409 invalidates preview…` | Bỏ preview; thử lại chỉ POST preview, không thêm POST commit. |
| Invalid quality gate và issue bị cắt | `invalid preview cannot write…` | Invalid chặn commit; 100/110 issues ghi rõ chỉ phần đã trả. |
| Rời tab/quay lại và reload | `navigation during commit…` | Một POST khi điều hướng lúc ghi; File giữ trong document; reload không tự phục hồi File/commit. |
| Responsive + chi tiết inline | 4 ca `responsive idle, preview and inline history…` | 1440×900,1366×768,1200×650,390×844; không overflow ngang document; commit thấy được khi cuộn tự nhiên. |

Các ca [workspace-freshness.spec.ts](../../frontend/e2e/workspace-freshness.spec.ts) cũng đạt trong bộ đầy đủ: nhập committed cập nhật không reload; Refresh cùng filter fetch lại; workspace request cũ không đè mới. Test full snapshot/truy vết nhập cũ vẫn được giữ. Không thay semantics SUM/AVG, dataVersion, parser hoặc storage.

## 3. Bằng chứng hình ảnh

Ảnh toàn trang từ fixture, 3 trạng thái ở mỗi viewport. Chiều cao ảnh có thể lớn hơn viewport do cuộn trang tự nhiên; không phải crop nút. Baseline trước hợp nhất: [nhập](../../.impeccable/review/import-baseline.png), [history riêng](../../.impeccable/review/import-history-baseline.png).

| Viewport | Chưa chọn tệp | Xem trước đạt | Kết quả + history/chi tiết tại chỗ |
|---|---|---|---|
| 1440×900 | [Ảnh](../../.impeccable/review/unified-import-idle-1440.png) | [Ảnh](../../.impeccable/review/unified-import-preview-1440.png) | [Ảnh](../../.impeccable/review/unified-import-result-1440.png) |
| 1366×768 | [Ảnh](../../.impeccable/review/unified-import-idle-1366.png) | [Ảnh](../../.impeccable/review/unified-import-preview-1366.png) | [Ảnh](../../.impeccable/review/unified-import-result-1366.png) |
| 1200×650 | [Ảnh](../../.impeccable/review/unified-import-idle-1200.png) | [Ảnh](../../.impeccable/review/unified-import-preview-1200.png) | [Ảnh](../../.impeccable/review/unified-import-result-1200.png) |
| 390×844 | [Ảnh](../../.impeccable/review/unified-import-idle-390.png) | [Ảnh](../../.impeccable/review/unified-import-preview-390.png) | [Ảnh](../../.impeccable/review/unified-import-result-390.png) |

Ảnh tại `.impeccable/review/` là artifact kiểm tra local, có thể bị gitignore; không phải asset giao diện hoặc bằng chứng production.

## 4. Thay đổi và giới hạn

- Source: `frontend/src/main.ts`, `style.css`, renderer mới `import-history.ts`. Tests: fixture mở rộng, ca mới và đường mở history trong contrast. Docs: Product, dashboard behavior, quy trình nhập, use cases, acceptance/traceability và đặc tả.
- Parity phát hiện đường `audit-import` chỉ đổi view, chưa fetch workspace Audit khi workspace hiện tại là Overview. Đã bổ sung `loadWorkspace()` đúng hành động này và ca hồi quy riêng; không thay luồng contributor/Comparison hoặc API.
- Không sửa backend/API/database ở lượt hợp nhất này. Worktree có sẵn nhiều thay đổi AI từ công việc trước, không reset hoặc gộp chúng vào tuyên bố phạm vi này.
- Dữ liệu history chỉ tối đa 100 attempt của nguồn, không filter dự án; không thấy một dòng không chứng minh chưa ghi. Không có public importRef trong list, không đoán từ run_id số.
- Báo cáo kiểm tra vừa preview/commit giữ trong memory; không dựng báo cáo attempt cũ từ counters history. API chỉ trả tối đa 100 issue detail, UI/download nói rõ truncation.
- POST không rõ kết quả giữ khóa trong document hiện tại; chưa có reconciliation endpoint/request ID. Phải xác minh thủ công trước khi nhập lại sau reload, không xem reload là bằng chứng thao tác chưa ghi.
- Sidebar/header phân tích có sẵn được giữ; KPI cards chỉ ẩn ở tab nhập. Màn hình nhỏ giữ cách cuộn/global navigation cũ; bảng history cuộn ngang trong vùng riêng.
- Chưa search/filter toàn lịch sử, phân trang, tải lại tệp nguồn, replay/hoàn tác hoặc tự retry ghi.

## 5. Rà soát cuối

- Rà soát Impeccable độc lập đầu tiên: `disposition: fix`, một finding về viền focus đen mặc định bao quanh tiêu đề xem trước. Giữ nguyên phong cách trắng/tím hiện có, bố cục nhập ưu tiên và history phụ trợ.
- Sửa theo finding: focus các đích nhập được scope riêng, viền tím `3px #8173dc`, offset `4px`; vẫn hiển thị focus và giữ luồng di chuyển focus. Không tắt outline.
- Chụp lại đúng 12 ảnh cùng đường dẫn. Reviewer xác nhận ảnh hợp lệ, finding **resolved**, không thấy regression từ sửa này; verdict `disposition: ship` **chỉ bao phủ finding focus đã chấm lại**, không phải đánh giá lại toàn bộ hệ thống.
- Handoff tài liệu đã kiểm tra source thực tế và ghi vào surface brief local `.impeccable/surfaces/frontend-src-main-ts.md`; không tạo DESIGN.md/design.json hoặc sửa drift hệ thống ngoài phạm vi.
- Xác nhận cuối: **25/25 ca giao diện liên quan**, **15/15 backend regression**, build TypeScript/Vite thành công (lần cuối 3,95 giây); `git diff --check` không lỗi whitespace.
- Hai ca toàn dự án lỗi lần đầu đều **đạt khi chạy lại riêng**. Không sửa source/test Comparison hoặc debounce, không khẳng định đã sửa nguyên nhân flakiness hoặc cả bộ 110 ca hiện tại đã chạy xanh cùng một lần. Bản cơ bản hợp nhất đã triển khai/kiểm chứng ở phạm vi trên; độ ổn định toàn bộ hồi quy cần theo dõi riêng.
