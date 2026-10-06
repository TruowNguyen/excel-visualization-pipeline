# AI Insight context — kiểm thử và đánh giá 04/10/2026

## Kết luận

Các luồng riêng từng vấn đề, Thống kê và selected/all con trực tiếp đã hoạt động. Dữ liệu canonical, phạm vi và nguồn tổng hợp trong các ca kiểm tra khớp. **Chưa nghiệm thu chất lượng diễn giải production tổng quát**: nhiều đoạn đúng vẫn bị validator loại, một số câu được chấp nhận còn dài/lặp hoặc diễn giải thời điểm chưa rõ; composer liên vấn đề chưa tạo một câu chuyện tổng hợp sâu bằng LLM.

[As-built](../10-context-insight-as-built.md), [raw response và kết quả hiển thị của lượt cuối](2026-10-04-context-insight-live.json), [manifest offline](2026-10-04-context-insight-offline.json).

## Runtime và tính mới của lượt kiểm thử

- Baseline đã push: `8201e9474275b60bc8bbd17fffa97971c6b51cde`, freeze trước đó `daa3974`/tag v15. Implementation hiện tại là thay đổi local, chưa commit/push trong yêu cầu này.
- Prompt `context-insight-v1.md`; semantic-grounding-v7. Provider cấu hình `ag/gemini-3.7-flash-low`, model trả về `gemini-3.7-flash-tiered`, qua 9Router hiện có. Không thay provider/model, không lưu secrets.
- Lượt cuối gọi endpoint ứng dụng qua TestClient với adapter thật, sau sửa production cuối về scope của chuỗi liên tiếp và prompt. Không replay/mock response, không dùng bằng chứng ngày 02/10 thay lượt mới.
- 14 request đại diện trên cả sáu dự án; **13 request thực sự gọi provider**. Ca quý của VW Vũ Yên chỉ có một kỳ hợp lệ, nên đúng hành vi là không gọi LLM/không tạo trend. Đây không phải bằng chứng live narrative nhiều quý; hồi quy nhiều quý/đổi năm là synthetic.
- SHA256 context.py: `007D6EE520CBF93D3CC9BEF320A838E01E51F6499A9E71289DFDD7DEDF166167`; semantic.py: `F8D228CA762DACBEBA72E03ED290AE8A5C495E1239CD61C564A5F1E59F6F2EB5`; context prompt: `71E3E1F4FF8622D81E84679919E7F345268A56D8962A04B123AB41CBB7841607`.

## Kiểm thử xác định

| Kiểm tra | Kết quả và phạm vi |
|---|---|
| Python toàn suite sau sửa semantic cuối | 333 passed; 19 cảnh báo deprecation FastAPI/Python 3.14 |
| Playwright toàn suite | 69 passed; sau hai sửa UI/fixture theo reviewer chạy lại 5 context tests, đều đạt |
| Frontend build | Đạt; còn cảnh báo kích thước bundle Plotly hiện có |
| git diff --check | Đạt; thông báo LF/CRLF không phải lỗi whitespace |
| Dữ liệu committed | 600 request offline; sáu dự án, 36 entity, process exit 0, mọi HTTP 200/namespace/membership/chart comparison đạt |
| UI review | Reviewer độc lập yêu cầu sửa receipt mock không khớp và ghi rõ provider omissions; verdict ship sau khi chấm cả hai fixes resolved |

Offline phủ overview ngày/tuần/tháng cho mọi entity; Thống kê ngày/tuần/tháng/quý × sum/average/both cho mọi entity; selected/all ở mỗi parent có con; recent/custom và includeIncomplete bật/tắt ở node đại diện từng dự án. Không tuyên bố đã phủ toàn Cartesian product mọi selector/range/flag ở mọi entity. Node không có dữ liệu riêng vẫn được test và ghi exclusion, không được tự rollup.

Ma trận chạy trên adapter canonical ổn định trong lúc tiếp tục sửa semantic/prompt. Offline không gọi/kiểm tra prose của provider, nên `provider_unavailable/offline_evaluation` là trạng thái dự kiến, không phải lỗi live. Full console output từng ca không được giữ; manifest đủ để chạy lại và process exit thành công được ghi. Script đã thêm lấy mẫu aggregate provenance sau khi ma trận bắt đầu; phần lấy mẫu này được chứng minh riêng bằng lượt live cuối.

Regression mới: legacy endpoint compatibility; node identity; chọn rỗng/ID sai/duplicate/direct-child; parity bốn group × ba calculations; nguồn đúng calculation; dữ liệu đổi version; wrong number bị loại; history/year-crossing; no correlation/rollup; không nối qua missing; budget/feature gate; endpoint proxy qua nhịp đảo chiều; chuỗi tăng/giảm liên tiếp không chứa plateau; dated local stage không thừa hưởng extrema đồng mức ngoài giai đoạn. E2E kiểm tra mở riêng không đổi filter, search không bỏ selection, source navigation, quý/average/all không lấy sidebar window, stale và response đến muộn.

## Lượt API thật cuối

| Ca | Phạm vi | Validation | Thời gian request |
|---|---|---|---|
| 1 | VSO nhóm chất lượng, ngày, một node/ba KPI | accepted | 8.141 s |
| 2 | VSO Camera, toàn lịch sử ngày, một vấn đề | partial | 7.909 s |
| 3 | VSO hai vấn đề được chọn, ngày | accepted | 7.245 s |
| 4 | VSO tất cả chín vấn đề, ngày | partial | 15.131 s |
| 5 | SmartParking node, tuần, tổng và trung bình | partial | 6.618 s |
| 6 | V-Pet tất cả con, tuần, trung bình/ngày | partial | 7.013 s |
| 7 | ANVF Đăng ký bus, mười kỳ ngày gần nhất, tổng | partial | 4.846 s |
| 8 | VOL vấn đề riêng, tháng, tổng | accepted | 3.764 s |
| 9 | VW Vũ Yên tất cả con, quý, cả hai cách tính | not_run/insufficient_data | 1.104 s; không gọi provider |
| 10 | SmartParking tất cả con, tuần đầy đủ, trung bình | partial | 8.955 s |
| 11 | VSO hai con được chọn, ngày/custom, trung bình | accepted | 5.712 s |
| 12 | VSO node, hai tháng, ba KPI | partial | 5.408 s |
| 13 | VSO node, tuần toàn lịch sử, ba KPI | partial | 7.551 s |
| 14 | V-Pet tất cả con, tháng, tổng và trung bình | partial | 6.029 s |

Kết quả: 13 ready (4 accepted, 9 partial), một insufficient_data. Trong 13 response có 69 claim, 55 claim được giữ và 14 claim bị loại; đoạn còn lại dùng Engine. Không có provider timeout trong mẫu cuối. Request có gọi provider: min 3.764 s, median 7.013 s, max 15.131 s. Đây là số đo mẫu hiện tại, không phải SLA hoặc production pass rate. Adapter hiện chưa expose token usage trong evidence này.

Đối chiếu **313 điểm chuỗi** với canonical adapters không có mismatch; **94 lần lấy mẫu aggregate provenance** ở đầu/cuối mỗi metric/calculation không có sai entity/rule/value. Các refs lấy mẫu có thể lặp, không phải 94 nguồn khác nhau. Thống kê so float đúng bằng chart, không epsilon. Overview dùng serialization tám chữ số thập phân vốn có của Engine; không tuyên bố rate float trước serialization hoàn toàn đồng nhất. Tất cả membership được phân tích hoặc ghi exclusion; không có duplicate factId.

Đây không phải audit độc lập mọi ô Excel/contributor: expected values tái sử dụng canonical code đang phục vụ chart, provenance lấy mẫu theo captured refs. JSON compact giữ raw response, toàn bộ series của issue, report hiển thị, receipt/import/checksum và validation; bỏ bundles facts/evidence trùng lặp và danh sách relationshipDetails đầy đủ. Có thể tái tạo bằng manifest/endpoint.

## Đọc và đánh giá output, không chỉ đếm accepted

1. **VSO ba KPI theo ngày — đúng diễn biến nhưng còn nhiều số.** Lượt cuối giữ đủ nhịp Tổng số tăng rồi giảm ở đầu, giảm nhẹ 214→209 rồi tăng lên 657; lỗi 43→32→22 giảm liên tiếp, cuối giữ 22 trong khi tỷ lệ tăng 3.35%→5.24%. Không dùng 16→22 thay toàn bộ câu chuyện. Đỉnh/đáy trong các đoạn giai đoạn, không heading riêng. Tuy nhiên model vẫn đọc nhiều giá trị; chưa đạt mức tổng hợp ngắn và insight liên hệ sâu mà người dùng mong muốn.
2. **Selected/all — phạm vi đúng, chiều khác nhau được giải thích; insight nhóm còn cơ bản.** Hai vấn đề được chọn giữ riêng nhịp giảm/giữ/tăng/giảm; tất cả chín vấn đề đều có Engine detail dù chỉ một phần được LLM diễn giải. Liên hệ cấp nhóm dựa trên kỳ chung và nói rõ không được kết luận cả nhóm cùng tăng/giảm. Đây là deterministic synthesis, chưa phải LLM phân tích sâu toàn nhóm. Overview cấp tập vẫn hơi chung và relationships còn gần thống kê kỳ.
3. **Thống kê sum/average — số và basis đúng, salvage còn bảo thủ.** SmartParking tổng đạt 54,563 ở tuần 35, lỗi đạt 476 ở tuần 34. Average giữ đúng 8,634, 6,554, 68 và 31; nhiều đoạn average đúng số bị loại vì role/scope/subject parser, Engine giữ dữ liệu. Không diễn giải khác biệt sum với average là KPI tăng/giảm giữa hai cách tính.
4. **Plateau — cải thiện có chứng cứ.** Lượt thăm dò từng viết V-Pet “tăng liên tục” qua đoạn 15→15. Đã thêm hồi quy/grounding strict continuity, đồng thời sửa scope để không loại nhầm run ngắn vì trough đồng mức ở ngoài giai đoạn. Lượt cuối V-Pet viết tăng lên 15, giữ nguyên tuần 37 rồi lên 16.67; cách mô tả này khớp chuỗi.
5. **Hai kỳ — không trend/extrema thừa, vẫn có lặp.** VOL chỉ so sánh 94,815→111,056 và lỗi giữ 0. Overview/phase còn lặp cùng ý. Không gọi là xu hướng dài hạn. Hai tháng VSO có câu kỳ 09 chưa đủ ngày, tổng thấp chưa đủ kết luận hoạt động giảm. Một số đoạn sum khác chưa nhắc ngay độ dài kỳ; quality limitation đang giữ ở issue nhưng chưa đảm bảo mọi đoạn tự đứng độc lập đều đủ ngữ cảnh.
6. **Ngôn ngữ — chưa đồng đều.** Phần lớn chủ ngữ rõ, không “toàn khoảng”. Một số câu vẫn dài, dùng “đáy/đỉnh”, “tăng vọt”, liệt kê nhiều giá trị hoặc vị trí “hai ngày đầu” không rõ ràng. Validator số/ngày có giới hạn không đủ chứng minh mọi paraphrase thời gian đúng. Không đưa ra điểm CX cao chỉ vì accepted.
7. **Unit/coverage — không tự suy ra sự kiện mới.** V-Pet có đơn vị lũy kế/ngày khác nhau và một nội dung thiếu unit. Không cộng/xếp hạng độ lớn; average nói đúng mức canonical core, không được tự diễn giải thành số đăng ký mới mỗi ngày hoặc cơ chế tác động. Missing của lỗi không thành 0 ngoài rule core; các node thiếu kỳ vẫn hiện giới hạn.

Kết luận đọc thủ công: đủ dùng để kiểm tra các luồng mở rộng và đối chiếu số liệu; **chưa coi mọi exit gate chất lượng ở kế hoạch 09 đã đạt**. Ưu tiên tiếp theo là composer cấp tập/giai đoạn có ý nghĩa, giảm lặp hai kỳ và false rejection dựa trên typed scope/metric/calculation, cùng benchmark ngữ nghĩa vị trí thời gian. Không tiếp tục nới số/ngày/entity/calculation gates để tăng tỷ lệ accepted.

## Lỗi tìm được và đã sửa trong lượt này

- JSON bị bọc Markdown fence: strip fence trước strict parser, không nới schema.
- Generic trend làm tròn average float trước trả về: giữ lại prepared chart float đúng bằng nguồn.
- Fact IDs relation bị trùng giữa issue/calculation: namespace dependencies và snapshot.
- Nhãn tuần/quý được parse như kỳ, không tháng/ngày tùy tiện.
- Liên tục qua plateau và closure của extrema ngoài local run: hồi quy riêng, không fix cứng entity/ngày/dataset.
- Search label bị CSS flex ghi đè hidden; selector E2E sai drawer/control; receipt mock sai window; UI chưa nói provider-budget omissions: đã sửa, review độc lập chấm hai UI fixes resolved.

Không có cache mới/background job/lazy LLM detail; không mobile redesign. Root DESIGN.md/design.json thiếu là drift có sẵn, không sửa ngoài yêu cầu. Impeccable detector chạy một lần, một warning Inter kế thừa; documenter đã ghi extension mà không đổi visual identity. Các screenshots là mock, không bằng chứng live-provider accuracy hoặc Statistics visual review.

Phương pháp giữ automated checks và đọc output thực tế riêng phù hợp với [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices). Không lấy một bộ test nhỏ làm chứng nhận production tổng quát.
