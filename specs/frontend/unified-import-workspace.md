# Nhập Excel hợp nhất — đặc tả đã triển khai

- Ngày soạn: 05/10/2026.
- Trạng thái: **As-built — đã triển khai phạm vi hợp nhất cơ bản**. Kết quả kiểm chứng và giới hạn nằm trong [báo cáo nghiệm thu](../quality/unified-import-workspace-evidence.md).
- Chế độ trải nghiệm: **Operate**, ưu tiên hoàn thành thao tác nhập dữ liệu.
- Đã xác nhận: mở tab phải ưu tiên nhập dữ liệu mới; lịch sử chỉ là lựa chọn phụ.
- Đã duyệt triển khai: giữ tên tab **Nhập Excel**, tích hợp lịch sử tối giản ngay trong lần hợp nhất; tìm kiếm/lọc nâng cao chưa triển khai.
- Phạm vi tài liệu: kiến trúc trải nghiệm, điều phối trạng thái và tiêu chí nghiệm thu của bản cơ bản. Không thay hợp đồng API hoặc công thức nghiệp vụ.

## 1. Khuyến nghị phạm vi

**Tích hợp sẵn lịch sử ở mức tối giản, không xây thêm một hệ thống quản lý lịch sử trong lần này.**

Lịch sử là một phần của vòng kiểm chứng nhập dữ liệu: xác nhận lần vừa nhập, nhận biết tệp trùng và kiểm tra khi phản hồi ghi dữ liệu bị mất. Vì vậy không nên trì hoãn việc tích hợp lịch sử sang một đợt khác. Nhưng ưu tiên nhập tệp không đòi hỏi tìm kiếm toàn bộ lịch sử, lọc theo dự án, phân trang máy chủ hoặc phục hồi dữ liệu từ một lần nhập cũ.

| Tích hợp trong bản đầu | Để sau, chưa chốt phạm vi |
|---|---|
| Một tab Nhập Excel duy nhất | Tìm kiếm/lọc phía máy chủ trên toàn bộ lịch sử |
| Chọn tệp, xem trước, kiểm tra, xác nhận | Phân trang ngoài 100 lần nhập gần nhất |
| Kết quả nhập ngay trên cùng màn hình | Lọc lịch sử theo dự án và khoảng ngày |
| Lịch sử thu gọn, mở theo yêu cầu | Báo cáo riêng về mọi dòng thay đổi của một lần nhập |
| Làm mới lịch sử, mở chi tiết cơ bản từ dữ liệu đã trả | Tải lại tệp nguồn hoặc báo cáo kiểm tra lịch sử chưa được API hỗ trợ |
| Giữ đường kiểm tra khi không rõ kết quả ghi | Phục hồi, áp lại tệp cũ hoặc hoàn tác trên giao diện |

Tìm tên tệp/lọc trạng thái trong **100 lần gần nhất đã tải** có thể là một bổ sung nhỏ về sau, không cần mở rộng API. Nếu bổ sung, phải ghi rõ giới hạn; không gọi đó là tìm kiếm toàn bộ lịch sử.

## 2. Baseline trước hợp nhất đã đối chiếu từ source

Bảng dưới mô tả baseline trước thay đổi, không phải trạng thái điều hướng đã triển khai. Bản mới thực hiện các hệ quả thiết kế ở cột cuối.

| Bằng chứng | Hành vi hiện tại | Hệ quả thiết kế |
|---|---|---|
| `frontend/src/main.ts`: khai báo tab, `renderImport`, `renderHistory` | Hai tab độc lập, dùng các biến nhập và lịch sử riêng | Hợp nhất nơi hiển thị, không gộp hai trạng thái mạng làm một |
| `previewFile`, `commitFile` | Xem trước và ghi là hai POST riêng; ghi gửi lại tệp cùng `expected_hash` | Giữ nguyên bước kiểm tra và xác nhận, không tự ghi khi chọn tệp |
| `importOutcomeCard`, `view-revision`, `check-import-history` | Kết quả/nhánh lỗi dẫn sang tab history | Chuyển thành mở vùng lịch sử ngay tại chỗ, giữ ngữ cảnh nhập |
| `commitFile` | Lưu kết quả rồi gọi bootstrap và tải lại lịch sử | Hiển thị kết quả ghi trước; xử lý lỗi tải lại độc lập |
| `app/api.py`: `imports`, `load_import_history` | GET trả tối đa 100 attempt của `SOURCE_KEY`, thứ tự attempt mới nhất trước | Lịch sử của nguồn dữ liệu, không phải chỉ của dự án đang xem |
| `v_import_history` trong `storage/migrations/003_views.sql` | Có trạng thái, tên tệp, thời điểm, hash, lỗi, run/duplicate ID và các bộ đếm | Chi tiết cơ bản có thể mở từ chính dữ liệu danh sách |
| API preview | Tổng lỗi/cảnh báo đầy đủ, tối đa 100 chi tiết; chưa tính tác động ghi chính xác | Không đưa số thêm/cập nhật dự đoán vào xem trước |
| API commit và `IMP-*` | Nhiều lỗi được từ chối trước khi tạo attempt; full snapshot mặc định không xóa dữ liệu vắng mặt | Không hứa mọi lỗi đều xuất hiện trong lịch sử; không mô tả bản chụp như thay thế/xóa toàn bộ |
| CSS nhập hiện tại | Hai vùng chọn tệp và xem trước, có bố cục một cột trên màn hình hẹp | Kế thừa phong cách hiện có, không đổi hệ thống thiết kế toàn dashboard |

Tham chiếu chuẩn: [quy trình nhập](../core/import-process.md), [API](../api/api-contract.md), [hành vi dashboard](dashboard-behavior.md). Quy tắc nghiệp vụ trong các tài liệu này không bị thay thế bởi bản hợp nhất.

## 3. Kiến trúc trải nghiệm

Người dùng CX đến đây để đưa báo cáo mới vào hệ thống. Thành công là biết rõ tệp nào đã kiểm tra, dữ liệu thuộc dự án nào, có được phép ghi hay không và kết quả thực tế sau xác nhận.

Một tab chính, không tạo hai tab con “Nhập” và “Lịch sử”. Luồng chính giữ ở phần trên; lịch sử là một vùng mở/thu gọn bên dưới. Không dùng modal hoặc drawer mới cho tác vụ nhập và chi tiết lịch sử cơ bản.

### Phân cấp và hành động

1. Tiêu đề **Nhập Excel**. Mô tả: “Kiểm tra tệp trước khi ghi vào kho dữ liệu.” Liên kết phụ **Xem lịch sử nhập** luôn dễ tìm.
2. Khu làm việc: chọn tệp/cách nhập và kết quả kiểm tra. Chỉ hành động phù hợp với bước hiện tại là nút chính.
3. Khi có kết quả ghi: biên nhận nằm phía trên khu làm việc; không tự chuyển sang dashboard hoặc lịch sử.
4. Vùng **Lịch sử nhập gần đây** mặc định thu gọn; có chú thích phạm vi và thời điểm tải gần nhất khi đã tải.

Giữ tên **Nhập Excel** để thể hiện đúng mục đích và định dạng hiện hỗ trợ. “Quản lý dữ liệu” quá rộng so với phạm vi bản đầu. Tên mới khác chỉ áp dụng sau khi người dùng xác nhận.

### Wireframe — trạng thái sẵn sàng nhập

```text
Nhập Excel                                      Xem lịch sử nhập
Kiểm tra tệp trước khi ghi vào kho dữ liệu.

┌ Chọn tệp và cách nhập ────┐  ┌ Kết quả kiểm tra ─────────────────┐
│ Chọn tệp Excel            │  │ Chọn tệp rồi xem trước để kiểm tra│
│ .xlsx · tối đa 50 MB      │  │ dự án, khoảng ngày và chất lượng.│
│ Tên tệp, dung lượng      │  │                                  │
│ Cách nhập                │  │ Chưa có dữ liệu nào được ghi.    │
│ Giải thích ngắn          │  │                                  │
│ [Xem trước và kiểm tra]  │  │                                  │
└──────────────────────────┘  └──────────────────────────────────┘

▸ Lịch sử nhập gần đây                              [Xem lịch sử]
  Tối đa 100 lần nhập gần nhất của nguồn dữ liệu.
```

### Wireframe — xem trước đạt kiểm tra

```text
Chọn tệp / cách nhập       Kết quả kiểm tra: Đạt · chưa ghi dữ liệu
                          Dự án đích · tệp · khoảng ngày
                          Số điểm dữ liệu · ngày · lỗi · cảnh báo
                          Danh sách kiểm tra / xem thêm / tải kết quả
                          Thông tin phiên bản và cách nhập
                          Xác nhận bổ sung nếu là bản chụp đầy đủ
                          [Xác nhận nhập dữ liệu ...]

▸ Lịch sử nhập gần đây
```

Chi tiết hash và giải thích kỹ thuật có thể thu gọn. Không để chúng đẩy danh tính tệp, lỗi chặn hoặc hành động xác nhận ra khỏi luồng đọc. Xác nhận nằm sau nội dung kiểm tra, không dùng footer cố định có thể che nội dung.

### Wireframe — sau khi nhập

```text
Đã nhập tệp Excel                  Đã ghi dữ liệu vào kho nội bộ
Tệp · dự án · khoảng ngày
Thêm mới / cập nhật / giữ nguyên ... theo kết quả máy chủ
Biểu đồ: đã cập nhật | đang tải lại | chưa tải lại được
Lịch sử: đã cập nhật | đang tải lại | chưa tải lại được
[Xem biểu đồ]  Xem lần nhập này  Xem kết quả kiểm tra

Khu nhập tệp                          [Nhập tệp khác]

▸ Lịch sử nhập gần đây
```

Trong bước này, “Nhập tệp khác” là hành động phụ. Chỉ khi bấm mới bắt đầu phiên nhập mới; mở lịch sử không xóa biên nhận hoặc báo cáo kiểm tra vừa nhận.

## 4. Lịch sử phụ trợ

- Khi mở tab bình thường: lịch sử đóng, không chiếm cột phải và không tự chuyển focus.
- “Xem lịch sử nhập”: mở vùng lịch sử, tải nếu chưa có dữ liệu; đưa focus về tiêu đề vùng đó. Không thay tab, không reset tệp/preview.
- Hiển thị bảng gọn gồm thời điểm bắt đầu, tệp, kết quả, cách nhập, tóm tắt thay đổi và nút **Chi tiết**. Dùng thời điểm bắt đầu đúng với `started_at`, không gọi đó là thời điểm ghi.
- Chi tiết mở ngay dưới dòng được chọn: các trường thật đã trả, thời điểm kết thúc/ghi nếu có, các bộ đếm, hash và thông báo lỗi an toàn. Không hiển thị số thiếu như `0`.
- `duplicate`: ghi “Tệp đã được nhập trước đó”; không biến attempt trùng thành một lần ghi mới. Run được tham chiếu chỉ hiển thị khi có dữ liệu xác định.
- Chi tiết cơ bản không gọi endpoint provenance theo một `run_id` số. Endpoint theo project cần public `importRef` và project hợp lệ; danh sách hiện chưa cung cấp ánh xạ này. Không tự tạo hoặc suy đoán public ref.
- Tải lại chỉ làm mới vùng lịch sử. Trong khi tải lại, giữ danh sách trước đó với trạng thái “Đang cập nhật”; lỗi không xóa danh sách thành công gần nhất.
- “Xem lần nhập này” sau ghi: mở lịch sử, lấy dữ liệu mới, tìm bằng `attempt_id`, làm nổi bật dòng và đưa focus vào dòng đó. Không dựa vào tên tệp.
- Nếu attempt không còn trong 100 dòng hoặc chưa thấy: giữ biên nhận, báo chưa tìm thấy trong danh sách đã tải, cho làm mới. Không kết luận “chưa nhập”.
- Thu gọn lịch sử không xóa dữ liệu đã tải hoặc phiên nhập. Mỗi lần vào tab từ điều hướng chính ưu tiên vùng nhập; đường gọi “kiểm tra lịch sử” là ngoại lệ mở lịch sử có chủ đích.

## 5. Phạm vi bộ lọc

Nhập workbook là thao tác trên nguồn dữ liệu, không tự động giới hạn bởi dự án, vấn đề hoặc ngày của dashboard. Dự án đích và khoảng ngày phải lấy từ preview; một tệp có thể chứa nhiều dự án.

Bộ lọc phân tích đang chọn được giữ cho lúc quay lại biểu đồ. Vùng lịch sử ghi rõ “Lịch sử của nguồn dữ liệu, không lọc theo dự án đang xem”. Không thêm bộ chọn dự án giả nếu API chưa lọc theo dự án.

Trong tab nhập, bộ lọc phân tích nên được trình bày là ngữ cảnh quay lại, không khiến người dùng hiểu rằng nó quyết định dữ liệu sẽ ghi. Việc đổi toàn bộ sidebar không nằm trong lần hợp nhất này.

## 6. Điều phối trạng thái và dữ liệu

Không dùng một biến “loading” cho toàn tab. Các miền trạng thái đã tách:

| Miền | Dữ liệu cần giữ | Trạng thái |
|---|---|---|
| Phiên nhập | File trong bộ nhớ, mode, preview, hash, xác nhận, mã phiên | chưa chọn / đã chọn / đang kiểm tra / đạt / không đạt / đang ghi / đã xác định kết quả / chưa rõ kết quả |
| Biên nhận | `ImportOutcome`, danh tính tệp/preview đã chụp, mode đã gửi | đã ghi / tệp trùng / kết quả khác được máy chủ trả |
| Tải lại phân tích | Phiên dữ liệu, trạng thái bootstrap/workspace | chưa yêu cầu / đang tải / thành công / lỗi |
| Lịch sử | items, thời điểm tải, dòng đang xem, token yêu cầu | chưa tải / đang tải / có dữ liệu / rỗng / lỗi; mở hoặc đóng độc lập |
| Báo cáo kiểm tra | Báo cáo gắn với phiên nhập/biên nhận | thu gọn / mở rộng, không dùng chung cờ với chi tiết lịch sử |

Tên trạng thái trên đây mô tả hành vi, không phải enum API mới. Source dùng `importPhase`, `importUncertain`, `importSession`, `importRefresh`, `historyRequest`, `historyOpen` và `showCommittedValidation` độc lập.

| Sự kiện | Đầu vào | Đầu ra / chuyển tiếp |
|---|---|---|
| Vào tab | tab đã lưu hoặc nhấn điều hướng | Khu nhập là điểm bắt đầu; lịch sử mặc định đóng |
| Chọn/đổi tệp | File .xlsx | Tạo mã phiên mới; bỏ preview/xác nhận của tệp cũ; không ghi |
| Bấm xem trước | File của phiên đang hoạt động | POST preview; vô hiệu hóa đổi tệp/mode trong thao tác |
| Preview trả về | manifest, valid, issues, tổng lỗi/cảnh báo | Áp dụng nếu mã phiên/yêu cầu vẫn khớp; focus kết quả kiểm tra |
| Đổi mode sau preview | incremental/full_snapshot | Giữ preview vì API preview chỉ nhận file; reset xác nhận bản chụp; cập nhật giải thích và nút ghi |
| Xác nhận ghi | File, mode, expected_hash, xác nhận bổ sung nếu cần | Một POST ghi; chặn nhấn đôi và đổi tệp/mode |
| Máy chủ trả committed | outcome + danh tính phiên đã chụp | Lưu/hiển thị biên nhận ngay; đánh dấu AI cũ cần cập nhật; tải lại bootstrap/workspace và lịch sử |
| Máy chủ trả duplicate | outcome + duplicate_of_run_id | Biên nhận trung tính; tải lại lịch sử; không giả tạo dataVersion mới hoặc phân tích AI mới |
| Ghi bị từ chối xác định | lỗi hash/validation hoặc kết quả từ chối rõ ràng | Giải thích đúng nhánh; lỗi hash yêu cầu kiểm tra lại; không coi là lỗi tải lại dashboard |
| Mất kết nối khi gửi ghi | yêu cầu đã gửi, chưa có outcome xác định | Trạng thái chưa rõ kết quả; không tự gửi lại; bật hành động kiểm tra lịch sử |
| Mở/đóng lịch sử | ý định của người dùng | Chỉ đổi vùng phụ; giữ File, mode, preview và biên nhận |
| Chọn chi tiết dòng | attempt_id trong danh sách | Chi tiết của đúng dòng, không thay preview của tệp đang nhập |
| Nhập tệp khác | ý định chủ động | Phiên nhập mới; kết quả cũ vẫn tra được trong lịch sử, báo cáo chỉ giữ theo khả năng hiện có |
| Rời tab rồi quay lại | phiên hiện tại trong cùng document | Giữ File/preview khi chưa ghi; không tự POST; khu nhập vẫn ưu tiên |
| Reload toàn trang | bộ lọc/UI state được lưu | Phải chọn lại tệp; không phục hồi File hoặc tự ghi từ sessionStorage |

Trong lúc ghi, chuyển sang màn hình phân tích trong cùng ứng dụng không được hủy thao tác hoặc tạo POST lần nữa. Khi quay lại, hiển thị tiến trình/kết quả của cùng phiên. Nếu rời document hoặc reload, cảnh báo thích hợp khi có thể; không hứa chắc có thể ngăn đóng trang.

### Quy tắc tải lại sau ghi

1. Thành công ghi và thành công tải lại là hai sự kiện khác nhau. Kết quả committed đã xác định không được biến thành “Nhập thất bại” vì GET lịch sử/workspace lỗi.
2. Không đợi lịch sử tải xong mới hiện biên nhận. Hai tác vụ tải lại có thể xử lý độc lập, ví dụ thu kết quả theo từng nhánh; không dùng một catch chung để xóa trạng thái ghi thành công.
3. History GET phải có token/yêu cầu mới nhất. Phản hồi GET bắt đầu trước khi commit không được ghi đè danh sách được làm mới sau commit.
4. Giữ cơ chế chống phản hồi cũ của workspace và public `dataVersion` hiện có. Không viết lại cache hoặc logic tính metric.
5. Chỉ ghi “Biểu đồ đã cập nhật” khi workspace của bộ lọc hợp lệ đã tải thành công với phiên dữ liệu phù hợp. Nếu chưa có phạm vi biểu đồ hợp lệ, nói đúng giới hạn, không báo thành công chung chung.
6. Làm mới sau ghi không tự chạy lại AI. Giữ quy tắc đánh dấu kết quả AI cũ theo phiên dữ liệu đã có.
7. Vùng nhập và history không phụ thuộc vào việc có project/workspace phân tích. Kho dữ liệu rỗng vẫn nhập được tệp đầu tiên; lỗi bootstrap/workspace không được thay toàn tab bằng màn hình lỗi nếu các endpoint nhập vẫn có thể sử dụng. Trạng thái kết nối của từng thao tác phải được hiển thị đúng, không khẳng định có thể nhập khi POST đang lỗi.

### Trường hợp chưa rõ kết quả

“Kiểm tra lịch sử” mở vùng phụ và fetch lại. `expected_hash`, tên tệp, mode và khoảng thời điểm chỉ giúp nhận diện ứng viên; không chứng minh một attempt thuộc chính request bị mất phản hồi. Nếu không có `attempt_id` xác định, không tự đánh dấu đã ghi hoặc chưa ghi từ một dòng cùng tên/hash.

Chưa có endpoint tra kết quả theo request ID; đây là giới hạn của bản đầu. Không tự retry POST, không tự cho phép ghi lại từ nhánh chưa rõ kết quả chỉ vì chưa thấy trong 100 dòng. Mọi bổ sung giúp tự giải quyết nhánh này phải có contract idempotency/reconciliation riêng.

## 7. Tái sử dụng và giới hạn hợp đồng

| Thành phần hiện có | Cách dùng trong bản đầu |
|---|---|
| POST `/api/imports/preview` | Giữ file multipart và response hiện tại |
| POST `/api/imports` | Giữ file, mode, expected_hash; không thêm replay/source_key/scopes |
| GET `/api/imports` | Tải khi mở lịch sử hoặc sau ghi; tối đa 100 attempt của nguồn |
| `validationIssues`, báo cáo tải xuống | Tái sử dụng nội dung/giới hạn 100 issue; thông báo phần bị cắt |
| `importOutcomeCard` | Tái sử dụng số liệu thực tế; tách thông báo tải lại và đổi hành động lịch sử thành tại chỗ |
| `historyCell`, nhãn trạng thái | Tái sử dụng quy tắc null/zero, thời gian và nhãn tiếng Việt |
| bootstrap/workspace, AI invalidation | Tái sử dụng và kiểm thử lại, không đổi aggregation/dataVersion |
| Provenance theo importRef | Giữ luồng hiện có từ truy vết; không suy đoán ref để mở từ bảng history |

Bản đầu không yêu cầu API hoặc migration SQLite mới. Chi tiết dòng chỉ dùng trường có thật, không dựng báo cáo kiểm tra đầy đủ, số liệu dự đoán hoặc danh sách các revision của run từ dữ liệu không được cung cấp.

## 8. Responsive và khả năng truy cập

- Kế thừa nền, kiểu chữ, form, nút và trạng thái hiện có. Không đổi nhận diện hoặc thiết kế lại dashboard.
- 1440×900 và 1366×768: hai vùng nhập/xem trước khi đủ bề ngang thực tế sau sidebar. Không lấy độ rộng viewport làm bằng chứng rằng nội dung còn đủ chỗ.
- 1200×650 và màn hình hẹp: chuyển sang một cột nếu cần; thứ tự chọn tệp → kiểm tra → xác nhận → lịch sử.
- 390×844: danh tính tệp wrap; lịch sử dạng danh sách gọn hoặc bảng cuộn ngang trong vùng riêng. Không làm toàn trang tràn ngang; không bỏ trường, chúng vẫn có trong Chi tiết.
- Một vùng cuộn trang tự nhiên. Không đặt chiều cao cố định cho preview/bảng khiến nút xác nhận bị crop. Lịch sử không chen giữa kết quả kiểm tra và nút xác nhận.
- Nút mở lịch sử có `aria-expanded`/`aria-controls`; trạng thái, lỗi và dòng vừa nhập có ngôn ngữ rõ ràng, không chỉ dựa màu.
- Mở lịch sử bằng hành động chủ động mới di chuyển focus; fetch nền không cướp focus. Khi thu gọn trong lúc focus nằm bên trong, trả focus về nút mở.
- File input vẫn dùng cơ chế chuẩn của trình duyệt. Tái dựng DOM không được làm mất File đang giữ trong bộ nhớ.

## 9. Module đã thay đổi trong bản hợp nhất

- `frontend/src/main.ts`: hợp nhất điều hướng, renderer nhập/lịch sử, handler xem kết quả, session restoration, điều phối request/focus. Có thể tách renderer phụ theo quy ước dự án nếu cần; không refactor cả dashboard.
- `frontend/src/style.css`: vùng lịch sử thu gọn, chi tiết dòng và bố cục phù hợp màn hình hẹp.
- `frontend/src/import-history.ts`: renderer thuần cho vùng lịch sử/chi tiết, escape dữ liệu nguồn và giữ null/zero. Không sửa nhãn ba metric trong lượt hợp nhất này.
- `frontend/e2e/fixtures.ts`: fixture lịch sử, response chậm/lỗi, outcome committed/duplicate/chưa rõ.
- Test mới `frontend/e2e/unified-import-workspace.spec.ts`; test contrast chuyển sang mở lịch sử tại chỗ. Test nhập/truy vết/freshness cũ được giữ để kiểm chứng parity.
- `PRODUCT.md`, dashboard behavior, quy trình nhập, use cases, acceptance/traceability và báo cáo nghiệm thu: đồng bộ điều hướng và trạng thái đã triển khai.
- `app/api.py`, storage schema: **không nằm trong bản hợp nhất cơ bản**. Backend tests hiện có là cổng hồi quy cho contract tái sử dụng.

## 10. Thứ tự phụ thuộc đã thực hiện

### Gate 0 — khóa thiết kế và fixture, trước implementation

- Duyệt tên tab, phạm vi lịch sử tối giản và cách mở tại chỗ.
- Chụp baseline của hai tab; lập checklist parity cho mọi đường nhập, báo cáo kiểm tra, lịch sử và điều hướng từ biên nhận/lỗi.
- Xác minh fixture chứa đầy đủ/null/missing các trường history, duplicate không có run mới, preview không tạo attempt, và lỗi trước tạo attempt.
- Khóa tiêu chí nghiệm thu dưới đây. Không thêm endpoint trong gate này.

### Lát 1 — tab hợp nhất và lịch sử phụ trợ

- Một tab Nhập Excel; giữ khóa nội bộ `import` để giảm thay đổi.
- Khóa `history` cũ trong sessionStorage chuyển thành `import`, mở vùng lịch sử và bảo toàn đường quay lại; không để màn hình trắng hoặc reset về Tổng quan.
- Renderer vùng phụ không thay nội dung form. Mở/thu gọn/tải lại/chi tiết cơ bản của tối đa 100 dòng.
- Đổi “Xem lịch sử nhập”, “Kiểm tra lịch sử nhập” thành hành động tại chỗ.
- Chỉ bỏ mục tab history khỏi điều hướng sau khi checklist parity của lát này đạt.

### Lát 2 — kết quả nhập và freshness xuyên suốt

- Dùng lại backend commit; chặn nhấn đôi, giữ danh tính File/hash/mode đúng phiên.
- Hiện biên nhận ngay; xử lý tải lại biểu đồ và history độc lập, kể cả lỗi một nhánh.
- Mở/focus đúng attempt từ biên nhận; committed/duplicate và chưa rõ kết quả có hành động riêng.
- Chống stale response cho history và giữ bảo vệ workspace/AI hiện có.
- Mỗi đường phải đi trọn frontend → API hiện có → kết quả/validation → frontend → test trước khi chuyển lát tiếp theo.

### Lát 3 — hardening và phát hành

- Kiểm thử responsive, focus, reload, đổi/rời tab, tệp đổi, lỗi hash, lỗi kiểm tra và kết quả bị cắt.
- Chạy toàn bộ frontend regression và backend contract/storage regression liên quan.
- Ghi bằng chứng gồm log lệnh, số test, ảnh các kích thước mục tiêu và checklist parity; cập nhật tài liệu As-built.

### Lát tùy chọn — tiện ích lịch sử, chỉ sau khi xác nhận nhu cầu

- Bước nhỏ: tìm tên tệp/lọc trạng thái trong danh sách đã tải; nhãn giới hạn 100 dòng, không API mới.
- Bước lớn: truy vấn toàn bộ theo tên/ngày/dự án, phân trang, public ref và tra kết quả request. Cần design/API contract riêng, regression backward compatibility và xem xét khả năng truy vấn/storage.
- Không biến tiện ích này thành điều kiện để hoàn thành việc gộp hai tab.

## 11. Tiêu chí nghiệm thu

Tên ca ở cột cuối là khóa mô tả từ bản kế hoạch, không phải tên test literal. Các test đã viết nằm tại `frontend/e2e/unified-import-workspace.spec.ts`; mapping và kết quả chạy thật nằm trong [báo cáo nghiệm thu](../quality/unified-import-workspace-evidence.md). Freshness workspace còn dùng `workspace-freshness.spec.ts`; không dùng một ca mocked để chứng minh toàn bộ backend/import thật.

| Lát | Điều kiện đạt | Ca kiểm thử dự kiến |
|---|---|---|
| 1 | Mở tab ưu tiên nhập, lịch sử đóng; không còn hai tab chính | `opens-import-first-with-history-collapsed` |
| 1 | Mở/thu gọn/chi tiết history không mất File, mode, preview hoặc xác nhận | `history-does-not-reset-import-session` |
| 1 | Session tab history cũ có đích mới hợp lệ | `restores-legacy-history-tab-to-unified-history` |
| 1 | History rỗng/lỗi/loading chỉ ảnh hưởng vùng phụ | `history-failure-does-not-block-import` |
| 1 | Kho rỗng hoặc workspace phân tích lỗi vẫn có vùng nhập; phản hồi POST quyết định khả năng nhập thực tế | `import-is-independent-of-analytical-workspace` |
| 1 | Chi tiết dùng đúng attempt; null hiển thị —, zero thật hiển thị 0 | `attempt-details-preserve-null-and-zero` |
| 1 | Nhãn phạm vi là nguồn, không giả lọc theo dự án | `history-scope-is-not-dashboard-project-filter` |
| 2 | Chọn/preview không POST ghi, invalid không cho commit; bản chụp cần xác nhận | `retains-preview-and-snapshot-quality-gates` |
| 2 | Nhấn đôi chỉ tạo một POST, gửi đúng file/mode/expected_hash | `commit-is-single-flight-and-bound-to-preview` |
| 2 | Ghi thành công cập nhật workspace mà không reload document | `commit-refreshes-current-dashboard-data` |
| 2 | GET lịch sử/workspace lỗi không đổi committed thành failed hoặc kích hoạt POST lại | `refresh-failure-preserves-confirmed-commit` |
| 2 | Duplicate không có run/version mới, history highlight đúng attempt trùng | `duplicate-is-not-presented-as-new-data` |
| 2 | History cũ trả sau refresh mới không ghi đè; workspace giữ bảo vệ tương tự | `late-history-response-cannot-overwrite-newer-results` |
| 2 | Timeout ghi đưa sang kiểm tra, không tự retry hoặc suy đoán theo tên/hash | `unknown-commit-outcome-requires-verification` |
| 2 | Lỗi 409 yêu cầu kiểm tra lại; dữ liệu preview/report không lẫn phiên | `changed-file-requires-new-preview` |
| 3 | Rời/quay lại tab không gửi ghi thêm; reload phải chọn lại File | `navigation-and-reload-preserve-safe-import-lifecycle` |
| 3 | Tệp dài/nhiều issue không crop nút, không tràn ngang toàn trang | `responsive-import-and-history-at-target-viewports` |
| 3 | Mở/đóng history focus đúng; refresh nền không cướp focus | `history-focus-and-live-status-are-accessible` |
| 3 | Báo cáo >100 issue nói rõ giới hạn, không gọi phần đã trả là toàn bộ | `validation-report-discloses-truncation` |

Đối chiếu backend regression qua `tests/test_api.py`, `tests/test_storage.py` và các test importer liên quan: preview không ghi, hash guard, validation gate, duplicate/replay protection, transaction và history. Chạy đúng tập test tồn tại và báo kết quả thực tế; không đổi semantics để test hợp giao diện.

## 12. Quyết định và điểm còn mở

Đã chốt và triển khai: nhập mới là tác vụ chính; history phụ; giữ tên Nhập Excel, lịch sử tối giản cùng tab, không API/migration mới, không modal nhập, không tự ghi hoặc tự phục hồi. KPI phân tích được ẩn riêng trên tab nhập, không đổi Tổng quan/Thống kê.

Giới hạn đã xác minh: GET lịch sử chỉ có 100 attempt; null counters không được đổi thành 0; lỗi trước khi tạo attempt có thể không xuất hiện trong history; không có public importRef trong list; không có endpoint tra request mất phản hồi. Nhánh chưa rõ kết quả giữ khóa trong document hiện tại; reload không phải bằng chứng chưa ghi và phải đối soát thủ công trước khi nhập lại.

Điểm mở ngoài phạm vi: tìm kiếm/lọc lịch sử, phân trang, tải báo cáo kiểm tra của attempt cũ và đối soát request/idempotency cần yêu cầu và contract riêng. Không sửa source backend/storage có sẵn từ công việc AI trước đó; các thay đổi đó không thuộc bằng chứng bản hợp nhất này.
