# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Người dùng chính là nhân sự CX nội bộ. Họ làm việc với các báo cáo Excel bán cấu trúc và cần chuyển dữ liệu này thành một không gian phân tích có thể kiểm tra chất lượng, truy vết và so sánh mà không phải xử lý thủ công từng bảng tính.

## Product Purpose

Excel Visualization Pipeline chuyển workbook `.xlsx` bán cấu trúc thành dữ liệu chuẩn hóa có lịch sử và dashboard tương tác. MVP giúp người dùng nội bộ:

- kiểm tra dữ liệu trước khi đưa vào kho lưu trữ;
- theo dõi KPI theo project, entity và thời gian;
- thống kê và so sánh các entity có cùng đơn vị;
- truy vết một giá trị đã chuẩn hóa về sheet, ô và giá trị nguồn;
- xem lại lịch sử các lần import.

Thành công của MVP là người dùng có thể đi trọn luồng Excel → validation → import → phân tích → audit trên một hệ thống nội bộ, với kết quả ổn định và không làm mất ngữ nghĩa dữ liệu nguồn.

## Positioning

Sản phẩm kết hợp trực quan hóa với khả năng truy vết dữ liệu nguồn ở cấp ô và lịch sử revision. Dashboard không chỉ hiển thị KPI: mỗi observation còn giữ raw value, display value, chart value, metadata parser và nguồn workbook để người dùng kiểm tra cách dữ liệu được hình thành.

## Operating Context

- Nguồn hiện tại là workbook `.xlsx` bán cấu trúc, có phân cấp Project → Entity theo hàng và Date → Metric theo cột.
- Người dùng preview và kiểm tra quality gate trước khi xác nhận import.
- Dữ liệu nghiệp vụ, current state và lịch sử import được lưu trong SQLite local; bộ lọc giao diện chỉ được giữ trong `sessionStorage` của tab trình duyệt.
- Giao diện chính là TypeScript/Vite sử dụng FastAPI làm backend; Streamlit được giữ làm giao diện legacy để đối chiếu trong giai đoạn chuyển tiếp.
- MVP được chạy và trình diễn trong môi trường nội bộ tin cậy, chưa được thiết kế để public trực tiếp lên Internet.

## Capabilities and Constraints

Phạm vi MVP đã xác nhận:

- parse workbook `.xlsx` không có password và không evaluate công thức Excel;
- dựng cây entity, kế thừa/override unit và chuẩn hóa metric theo cấu hình;
- phân biệt số 0, ô trống/NBSP, source marker, text và phần trăm;
- validation với error quality gate và warning có thể truy vết;
- import idempotent theo artifact/config/contract, hỗ trợ `full_snapshot` và `incremental`;
- lưu current state, append-only revision history, source artifact và import audit trong SQLite;
- dashboard có Tổng quan, Thống kê, So sánh, Audit dữ liệu, Import Excel và Lịch sử import;
- export normalized CSV.

Giới hạn hiện tại:

- chưa có authentication, authorization hoặc phân quyền theo project;
- SQLite phù hợp local/single-writer, chưa dành cho nhiều tiến trình import đồng thời hoặc database trên network share;
- chưa có lịch đồng bộ tự động, Docker hoặc CI;
- parser cần thêm rule khi workbook xuất hiện layout hoặc hierarchy mới;
- file upload phải được chọn lại sau khi reload do giới hạn bảo mật của trình duyệt.

Định hướng mở rộng, không thuộc phạm vi MVP hiện tại: đồng bộ dữ liệu hằng ngày từ nguồn như OneDrive, tài khoản người dùng, phân quyền truy cập và kiến trúc production phù hợp cho nhiều người dùng.

## Brand Commitments

- Tên sản phẩm hiện dùng trong giao diện là **Automated CX Report**; tên kỹ thuật của repository là **Excel Visualization Pipeline**.
- Ngôn ngữ sản phẩm hiện tại là tiếng Việt, có thể giữ thuật ngữ kỹ thuật quen thuộc như Project, Entity, Metric, Audit và Import khi chúng làm rõ mô hình dữ liệu.
- Nội dung giao diện phải thể hiện đúng trạng thái nội bộ/MVP, không đưa ra tuyên bố về bảo mật, quy mô production hoặc khả năng triển khai chưa được chứng minh.

## Evidence on Hand

- Workbook mẫu: `D:\task\test data for CX report dashboard.xlsx`.
- UI template tham chiếu đã được người dùng cung cấp: `D:\task\CX_Platform_export (1).html`.
- Baseline hiện ghi nhận 6 project, 36 entity, 4.182 record chuẩn hóa và 2.343 record có thể vẽ từ ngày 01/08/2026.
- Repository có automated tests, smoke tests, tài liệu đặc tả hệ thống và tài liệu thiết kế SQLite.
- Chưa có testimonial, case study, benchmark production, cam kết SLA hoặc bằng chứng triển khai Internet; các nội dung này không được tự tạo trong công việc thiết kế sau này.

## Product Principles

1. **Truy vết trước khi trang trí:** mọi số liệu quan trọng phải có thể đối chiếu về nguồn và lịch sử hình thành.
2. **Không tự thay đổi ngữ nghĩa nguồn:** bảo toàn zero, blank, marker, text, phần trăm và không tự tính lại KPI nguồn ngoài các rule đã khai báo.
3. **Preview trước, commit sau:** thay đổi dữ liệu phải qua validation và xác nhận rõ ràng trước khi ghi vào database.
4. **Phân tích theo cấu trúc nghiệp vụ:** project, entity hierarchy, unit và thời gian là các trục điều hướng cốt lõi.
5. **MVP trung thực với giới hạn vận hành:** ưu tiên demo nội bộ ổn định; các năng lực production chỉ được giới thiệu sau khi thực sự được triển khai.
