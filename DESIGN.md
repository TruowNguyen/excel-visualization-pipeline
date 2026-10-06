---
name: "Automated CX Report"
description: "Không gian phân tích CX: nghiệp vụ trung tính, dễ đọc và chính xác."
colors:
  canvas: "#f7f8fb"
  surface: "#ffffff"
  surface-subtle: "#f8f9fc"
  analysis-heading-bg: "#faf9ff"
  analysis-border: "#dcd8ec"
  surface-disabled: "#eef0f4"
  text-primary: "#233044"
  text-body: "#465366"
  text-secondary: "#526176"
  text-tertiary: "#5f6e81"
  navy: "#101827"
  navy-raised: "#1c283b"
  purple: "#6253b5"
  purple-tint: "#f0eef8"
  purple-hover: "#50429b"
  border: "#dde2e8"
  border-strong: "#d7dce5"
  muted: "#58677b"
  report-heading: "#233044"
  report-body: "#38465a"
  report-muted: "#526176"
  focus: "#6253b5"
  ghost-text: "#3c4a5f"
  ghost-border: "#dfe4ec"
  ghost-hover: "#f6f7fb"
  validation-success-bg: "#eef8f4"
  validation-success-text: "#17694f"
  validation-warning-bg: "#fff4dc"
  validation-warning-text: "#83570c"
  validation-error-bg: "#fff0f0"
  validation-error-text: "#9b3030"
typography:
  headline:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "clamp(22px, 2vw, 26px)"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-.3px"
  title:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  report:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  report-title:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
  report-summary-legacy:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.75
  label:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  action:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  action-text:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.5
  metric:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "32px"
    fontWeight: 700
    lineHeight: 1.3
  metric-label:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  metadata:
    fontFamily: '"Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  chart:
    fontFamily: "Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "12px"
  chart-legend:
    fontFamily: "Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "11px"
rounded:
  badge: "5px"
  compact: "7px"
  control: "8px"
  notice: "9px"
  table: "10px"
  receipt: "11px"
  surface: "12px"
  dialog: "14px"
spacing:
  xs: "6px"
  sm: "8px"
  compact: "12px"
  card-gap: "14px"
  md: "16px"
  panel-gap: "18px"
  lg: "20px"
  panel-inset: "20px"
  report-section: "20px"
components:
  button-primary:
    backgroundColor: "{colors.purple}"
    textColor: "{colors.surface}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "8px 13px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.purple-hover}"
  button-ghost:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ghost-text}"
    typography: "{typography.action}"
    rounded: "{rounded.control}"
    padding: "8px 13px"
    height: "40px"
  button-ghost-hover:
    backgroundColor: "{colors.ghost-hover}"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.purple}"
    typography: "{typography.action-text}"
    padding: "6px 0"
    height: "36px"
  button-disabled:
    backgroundColor: "{colors.surface-disabled}"
    textColor: "{colors.text-secondary}"
  input-sidebar:
    backgroundColor: "{colors.navy-raised}"
    textColor: "#f4f6fa"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 10px"
    height: "40px"
  select-analysis:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.report-heading}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "42px"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "#2f3a4b"
    typography: "{typography.metadata}"
    rounded: "{rounded.notice}"
    padding: "0 12px"
    height: "42px"
  navigation-tab:
    backgroundColor: "transparent"
    textColor: "#5b687a"
    typography: "{typography.label}"
    padding: "10px 16px"
    height: "44px"
  navigation-tab-selected:
    backgroundColor: "{colors.purple-tint}"
    textColor: "{colors.purple}"
    typography: "{typography.action}"
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.surface}"
    padding: "16px 18px"
  chart-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
  analysis-heading:
    backgroundColor: "{colors.analysis-heading-bg}"
    textColor: "{colors.report-heading}"
    typography: "{typography.title}"
    padding: "16px 20px"
  validation-badge:
    backgroundColor: "{colors.validation-success-bg}"
    textColor: "{colors.validation-success-text}"
    rounded: "{rounded.badge}"
    padding: "4px 7px"
  validation-badge-warning:
    backgroundColor: "{colors.validation-warning-bg}"
    textColor: "{colors.validation-warning-text}"
  validation-badge-error:
    backgroundColor: "{colors.validation-error-bg}"
    textColor: "{colors.validation-error-text}"
  method-disclosure:
    textColor: "{colors.text-secondary}"
    typography: "{typography.metadata}"
---

# Design System: Automated CX Report

## Overview

**Creative North Star: "Không gian phân tích CX"**

Giao diện nghiệp vụ trung tính, dễ đọc và chính xác. Nền trắng/xám làm chỗ cho số liệu và nguồn kiểm chứng; sidebar navy giữ trục điều hướng quen thuộc. Tím nhận diện dẫn thao tác, focus và lựa chọn. Chữ phân tích dùng màu trung tính để người đọc theo nội dung và dữ liệu.

Hệ thống giữ sự cô đọng và phân nhóm của giao diện cũ: khung làm việc trắng có viền mảnh, tab đang chọn có nền nhạt, tiêu đề AI và phần tổng hợp có sắc độ riêng. Mỗi biểu đồ có container riêng; không bọc thêm thẻ cho từng đoạn báo cáo. Nhập Excel không dùng khung ngoài vì form/xem trước đã phân nhóm. Nút, trường nhập và thẻ giữ hình dáng nhẹ, ổn định, phù hợp công việc đọc báo cáo nội bộ bằng tiếng Việt.

**Key Characteristics:**

- Nền trắng/xám, thanh bên navy và tím cho thao tác hoặc lựa chọn.
- Segoe UI/system stack thống nhất giữa giao diện và Plotly.
- Thẻ phẳng; phân nhóm bằng viền, khoảng cách và tiêu đề.
- Văn bản phân tích trung tính, số liệu và nguồn dễ kiểm tra.

Hồ sơ as-built ngày 05/10/2026 dựa trên `frontend/src/style.css`, `ui-icons.ts`, `chart.ts`, các renderer liên quan trong `main.ts` và `overview-summary.ts`; định hướng đã duyệt nằm ở đầu `.impeccable/surfaces/frontend-src-main-ts.md`. Bản cập nhật này hợp nhất hướng lấy lại phân nhóm cũ, giữ font/thẻ nổi bật và các sửa lỗi đọc AI/đóng popup. Đây là hệ thống frontend TypeScript/Vite; không mô tả giao diện Streamlit legacy. Bằng chứng hiện tại nằm trong `specs/quality/compact-ui-restoration-evidence.md`; review trực tiếp không được gọi là review độc lập.

## Colors

Bảng màu có một accent thao tác, nền trung tính lạnh nhẹ và thanh điều hướng navy đậm. Giá trị chính xác nằm trong frontmatter; các tên dưới đây diễn tả vai trò sử dụng.

### Primary

- **Tím thao tác** (`purple`, `purple-hover`, `focus`): nút chính, hành động bằng chữ, focus và tab đã chọn. Tím nhạt (`purple-tint`) hỗ trợ trạng thái lựa chọn.

### Neutral

- **Nền xám làm việc** (`canvas`): nền toàn workspace.
- **Trắng nội dung** (`surface`): thẻ số liệu, biểu đồ, vùng phân tích và form nhập.
- **Nền phân tích nhạt** (`analysis-heading-bg`, `analysis-border`): tiêu đề AI, phần tổng hợp dẫn đầu và divider; chữ báo cáo vẫn trung tính.
- **Xám phụ** (`surface-subtle`, `surface-disabled`): bảng header, thông tin phụ và nút bị vô hiệu hóa.
- **Navy điều hướng** (`navy`, `navy-raised`): sidebar và các trường nhập nằm trong sidebar.
- **Chữ nghiệp vụ** (`text-primary`, `text-body`, `text-secondary`, `text-tertiary`, `muted`): từ tiêu đề/số liệu đến nội dung và metadata.
- **Chữ báo cáo** (`report-heading`, `report-body`, `report-muted`): tiêu đề, diễn giải và nguồn trong phần phân tích. Một số giá trị trùng role giao diện nhưng tên riêng giữ đúng ánh xạ custom property hiện có.
- **Viền và nút phụ** (`border`, `border-strong`, `ghost-border`, `ghost-text`, `ghost-hover`): phân chia bề mặt và thao tác phụ.

### Semantic states

Xanh xác nhận, vàng cảnh báo và đỏ lỗi của validation badge mang trạng thái cùng nhãn chữ. Các callout nhập/phân tích có biến thể nền/viền hiện có; không biến màu tăng/giảm số liệu thành đánh giá tốt/xấu.

**The Action Accent Rule.** Dùng tím để nhận diện thao tác, focus và lựa chọn; phần diễn giải báo cáo dùng các role chữ trung tính.

## Typography

Một stack Segoe UI/system dùng cho giao diện và Plotly, không cần font tải ngoài. Code hiện có dùng Cascadia Mono/Consolas; đây là ngoại lệ cho mã và tham chiếu kỹ thuật, không phải một font đọc báo cáo thứ hai. Không có display font trang trí hoặc tỷ lệ phóng cỡ chữ thống nhất; các vai trò là những cỡ quan sát được trong source.

- **Headline**: tiêu đề trang co giãn theo viewport, weight 700.
- **Title**: tiêu đề khu vực và phần phân tích, weight 600.
- **Body / Label**: chữ điều khiển/tab nghỉ dùng weight 400; nhãn thẻ nghiệp vụ, nút và tab đã chọn dùng 600.
- **Report / Report title**: diễn giải theo ngữ cảnh và tiêu đề đoạn; prose dùng toàn chiều rộng vùng báo cáo theo yêu cầu người dùng, xuống dòng dài và khoảng cách đoạn (12px). Các phase/takeaway dùng cùng cỡ và nhịp đọc.
- **Metric**: số chính trong bốn thẻ, chữ số tabular; đơn vị và khoảng/kỳ ở cỡ phụ bên cạnh hoặc phía dưới.
- **Metadata / Chart**: thông tin phụ, trục biểu đồ và legend theo vai trò frontmatter. Một số metadata legacy trong bảng/import/footer vẫn (10–11px); không có cam kết rằng mọi chữ trong sản phẩm đều đạt tối thiểu 12px.

Đoạn tổng hợp legacy cho một node vẫn toàn chiều rộng ở desktop, theo role `report-summary-legacy`; trên màn hình hẹp (760px trở xuống) source dùng (15px). Không áp giới hạn chiều cao hoặc dấu ba chấm để làm gọn nội dung AI.

**The Reading Measure Rule.** Diễn giải dùng hết vùng báo cáo, xuống dòng tự nhiên và không cắt nội dung; bảng nguồn cuộn trong vùng riêng. Dòng desktop dài hơn là đánh đổi đã chọn, không phải quy tắc 75ch mặc định.

## Layout

Desktop dùng sidebar (264px), hoặc rail thu gọn (60px), và phần chính `minmax(0, 1fr)`. Topbar cao (60px); workspace padding ngang `clamp(20px, 2.4vw, 38px)`, không có max-width trang. Drawer nguồn docked chiếm cột (400–440px); ở màn hình desktop hẹp từ (761px) đến (1180px), drawer chuyển thành lớp cố định bên phải và biểu đồ child xếp một cột.

Nhịp bố cục dùng các khoảng đã trích ở frontmatter, với inset phân tích (20px), gap thẻ nghiệp vụ (14px), gap biểu đồ (18px) và khoảng giữa phần báo cáo (20px). Khung làm việc có viền và padding (20px), giảm (16px) trên màn hình hẹp; tab Nhập Excel bỏ khung/padding ngoài. Bốn thẻ Tổng quan/Thống kê có label, số, phạm vi/cách tính và kỳ; thông tin nguồn/chọn nguồn nằm trong `Cách đọc các chỉ số` đóng mặc định. Không thêm lại khối nguồn mở sẵn phía trên thẻ.

Các thẻ nghiệp vụ xếp bốn cột trên desktop, hai cột ở (1200px) trở xuống và một cột ở (640px) trở xuống. Container query theo workspace ở (760px)/(540px) tiếp tục thu gọn thẻ, điều khiển và vùng nhập khi mở bảng nguồn. Biểu đồ child dùng hai cột khi container rộng ít nhất (940px). Khung root cao (433px) để chứa Plotly (420px) và padding dọc (13px); khung child cao (393px) để chứa Plotly (380px) cùng padding. Mobile giữ chiều cao này, padding ngang của plot về 0 ở (480px); không thu khung thấp hơn nội dung Plotly.

Nhập Excel dùng hai cột chọn tệp/xem trước và chuyển một cột ở breakpoint scoped (980px). Ở (760px) trở xuống, shell thành luồng dọc, sidebar theo cơ chế mở/thu gọn hiện có, workspace padding ngang (14px), vùng phân tích inset (18px), action hàng đầu wrap và nhiều nút phụ có chiều cao tối thiểu (44px). Tabbar cuộn ngang khi cần; bảng giữ cuộn cục bộ.

Popup so sánh giữ footer ngoài vùng cuộn và nguồn docked trên desktop. Width `min(1340px, calc(100vw - 48px))`, height `min(820px, calc(100dvh - 32px))`. Từ (980px) trở xuống, popup cách mép (8px), selector nằm trên chart, chart tối thiểu (320px) và cuộn trong vùng làm việc; nguồn mở trong vùng này, không che header/footer. Nguồn mở từ dashboard trên điện thoại dùng lớp cố định toàn màn hình, khác nguồn trong popup. Breakpoint chiều cao (700px) rút gọn khoảng cách popup. Bằng chứng Chrome/fixture không thay thế kiểm chứng mọi trình duyệt hoặc thiết bị thật.

## Elevation & Depth

Thẻ và khung nội dung phẳng tại trạng thái nghỉ: custom property `--shadow` là `none`. Độ sâu chủ yếu đến từ nền navy so với nền trắng/xám, đường viền và khoảng cách. Shadow còn dùng cho modal so sánh và drawer overlay desktop hẹp; focus ring là dấu tương tác, không phải elevation của thẻ.

Sidecar ghi chính xác vocabulary: modal `0 28px 80px rgb(16 24 39 / 22%)`, drawer overlay `-12px 0 28px rgb(30 41 59 / 10%)` và focus sidebar `0 0 0 3px #7366ed22`. Backdrop modal dùng `rgb(16 24 39 / 52%)`.

Chuyển động hiện có ngắn và có mục đích: shell chuyển cột (.2s ease), layout popup (.16s ease), modal vào (.16s ease-out), chevron lịch sử (150ms ease-out); skeleton nguồn pulse (1.35s ease-in-out). Các quy tắc `prefers-reduced-motion` tắt những transition/animation này.

**The Flat Surface Rule.** Phân nhóm nội dung bằng viền, tiêu đề và khoảng cách; shadow chỉ phục vụ lớp nổi đã có.

## Shapes

Góc bo nhẹ, phù hợp mật độ nghiệp vụ: control (8px), badge (5px), nút compact (7px), thông báo (9px), bảng (10px), receipt (11px), thẻ (12px), dialog (14px). Tab chỉ bo hai góc trên (7px); selection được đánh dấu bằng nền nhạt, viền đáy và màu chữ. Đường viền thường (1px); biểu đồ cắt nội dung trong container bo góc, vì vậy chiều cao container phải đủ chứa toàn bộ Plotly và padding.

Icon chrome là inline SVG (16×16px), viewBox 24, stroke (1.7), đầu và góc nét tròn, dùng `currentColor`. Icon trang trí `aria-hidden="true"`, `focusable="false"`; tên truy cập nằm trên control. Không có raster shipping trong thay đổi này. Ảnh dưới `.impeccable/review/compact-ui/` là fixture kiểm thử trong thư mục ignored, không phải asset sản phẩm hoặc bằng chứng dữ liệu production.

## Components

**Nút chính.** Tím thao tác, chữ trắng, bo control, padding/chiều cao theo `button-primary`; hover tím đậm hơn, focus-visible có outline. Disabled dùng nền/chữ trung tính và cursor `not-allowed`. Nút tạo phân tích tăng chiều cao tối thiểu (42px), min-width (200px), padding ngang (20px); ở mobile rộng toàn hàng và tối thiểu (44px).

**Nút phụ và hành động chữ.** Ghost trắng với viền mảnh, hover xám nhẹ; tải CSV dùng biến thể này. Hành động chữ tím có underline với offset (3px), không thêm khung riêng. Nút `Phân tích` và liên kết mở nguồn dùng cấu trúc này. Global focus là outline (2px), offset (3px); các vùng có focus scoped dùng (3px), offset (2–4px) theo source.

**Trường nhập.** Sidebar dùng nền navy-raised và viền sáng hơn sidebar; focus đổi viền và halo. Select trong vùng phân tích dùng nền trắng, border-strong, bo control và chiều cao (42px). Search trong picker có cùng chiều cao, bo notice và placeholder trung tính. Native input/select giữ hành vi trình duyệt.

**Navigation.** Tabbar ngang có icon và nhãn; tab nghỉ nhẹ, hover và tab đã chọn có nền tím nhạt/chữ tím weight 600, tab đã chọn có viền đáy (2px). Sidebar giữ bộ lọc và grouping hiện có; không chuyển vị trí filter trong công việc đổi style.

**Thẻ nghiệp vụ và biểu đồ.** Thẻ nghiệp vụ có padding (16px 18px), viền trên navy (2px) khi sẵn có và không shadow; số hợp lệ kể cả 0 dùng navy, dữ liệu chưa có dùng chữ dịu và dấu gạch. Chart header có tiêu đề/metadata và action theo ngữ cảnh; thân chứa một Plotly. Khung làm việc bao nhóm chart/AI theo hướng cũ đã duyệt, không bọc thêm lớp quanh một chart. Plotly dùng cùng font, nền trắng, legend ngang, hover nền navy; graph selection vẫn có nét tím. Sidecar chỉ minh họa container chart, không giả lập dữ liệu hoặc runtime Plotly.

**Phần phân tích AI.** Tiêu đề và tổng hợp dẫn đầu có nền nhạt/divider; nội dung còn lại trắng, đoạn diễn giải dùng chữ trung tính. Điều khiển và nội dung cùng inset; chi tiết/nguồn dùng disclosure sẵn có, không tạo card riêng cho mỗi đoạn hoặc ẩn bớt văn bản để giảm chiều cao.

**Validation badge.** Hình bo badge, padding (4px 7px), nhãn (12px/600); xanh, vàng hoặc đỏ theo trạng thái cùng chữ. Đây là dấu trạng thái, không phải chip thao tác.

**Disclosure và phần đọc.** `Cách đọc các chỉ số`, nguồn, chi tiết và lịch sử dùng disclosure/native controls hiện có. Nội dung đọc ưu tiên tiêu đề, đoạn văn và divider. Sidecar giữ một mẫu disclosure native, không thêm JavaScript. Mẫu badge và card tĩnh không gán hover hoặc click giả.

`.impeccable/design.json` cung cấp mười snippet HTML/CSS độc lập: ba biến thể nút, search, navigation, thẻ nghiệp vụ, container biểu đồ, validation badge, disclosure và tiêu đề AI. CSS dùng custom properties thực tế với fallback để render độc lập; mọi class có tiền tố `ds-`, SVG inline và không phụ thuộc framework/runtime. Tonal ramps trong sidecar là swatch minh họa dẫn xuất, không phải token hay palette triển khai mới.

## Do's and Don'ts

### Do:

- Do giữ nền trắng/xám, sidebar navy và tím cho thao tác, focus hoặc lựa chọn.
- Do dùng Segoe UI/system stack nhất quán giữa control, báo cáo và Plotly.
- Do dùng chữ trung tính cho diễn giải, sử dụng hết vùng báo cáo và giữ bảng nguồn cuộn cục bộ.
- Do phân nhóm bằng viền, khoảng cách và tiêu đề; giữ một container cho mỗi biểu đồ.
- Do giữ nhãn chữ bên cạnh trạng thái màu và tên truy cập trên control có icon.
- Do chứa đủ chiều cao Plotly cùng padding khi đặt kích thước khung biểu đồ.

### Don't:

- Don't đổi chữ báo cáo sang tím hoặc thêm shadow cho thẻ thường; nền nhạt chỉ phân nhóm tiêu đề/tổng hợp.
- Don't bọc card cho từng đoạn diễn giải hoặc thêm nhiều lớp quanh cùng một biểu đồ.
- Don't cắt nội dung AI hoặc để bảng nguồn che header/footer của popup.
- Don't dùng font trang trí hoặc icon Unicode thay cho bộ SVG chrome hiện có.
- Don't thêm lại khối nguồn mở sẵn phía trên bốn thẻ nghiệp vụ.
- Don't coi thay đổi màu hoặc cỡ chữ là quyền đổi số liệu, công thức, API, database hay vị trí bộ lọc.
- Don't gọi fixture screenshot, tonal ramp minh họa hoặc detector rỗng là bằng chứng production hay phê duyệt toàn hệ thống.
