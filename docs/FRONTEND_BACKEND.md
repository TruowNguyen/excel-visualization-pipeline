# Tách frontend/backend cho CX Analytics Workspace

## Mục tiêu và nguồn template

`D:\task\CX_Platform_export (1).html` là bản export tĩnh của một giao diện Next.js, không chứa đầy đủ source/asset để dùng như ứng dụng gốc. UI mới tái tạo ngôn ngữ thiết kế: sidebar tối, topbar sáng, KPI cards và khu vực workspace theo tab. Không nhúng bundle Next.js export hoặc phụ thuộc trực tiếp vào website nguồn.

## Ranh giới trách nhiệm

```text
frontend/src (TypeScript, Vite, Plotly.js)
  ├─ sidebar: Project, thời gian, Hierarchy Navigator, phạm vi
  ├─ workspace: Tổng quan, Thống kê, So sánh, Audit, Import, Lịch sử
  └─ sessionStorage: chỉ bộ lọc của tab hiện tại
                     ↓ HTTP /api
app/api.py (FastAPI)
  ├─ kiểm tra tham số, phân trang audit, preview/import Excel
  ├─ đọc SQLite current/history views
  └─ gọi các hàm biểu đồ Plotly Python đã có
                     ↓
src/excel_visualization_pipeline
  ├─ parser/validation/pipeline
  ├─ storage/repository/importer
  └─ visualization/charts
```

Không chạy parser khi người dùng đổi filter hoặc reload. `POST /api/imports/preview` parse/validate nhưng không ghi SQLite. `POST /api/imports` nhận lại file, kiểm tra `expected_hash`, quality gate rồi mới commit. UI không gửi dữ liệu nguồn qua query string.

## API v1

| Endpoint | Vai trò |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/bootstrap` | Project, KPI và biên ngày |
| `GET /api/projects/{project}/entities` | Hierarchy cho sidebar |
| `GET /api/projects/{project}/workspace` | Biểu đồ, thống kê, so sánh, audit có phân trang |
| `GET /api/projects/{project}/export.csv` | Tải normalized CSV của project |
| `GET /api/imports` | 100 import attempts gần nhất |
| `POST /api/imports/preview` | Preview + quality gate workbook |
| `POST /api/imports` | Xác nhận import với hash preview |

`workspace` nhận `mode=recent|week|month|custom`, `count`, `start`, `end`, `entity`, `scope=node|children`, các tham số thống kê/so sánh và `audit_offset/audit_limit`. Trả JSON gồm `window`, biểu đồ Plotly, kỳ thống kê, ứng viên so sánh và trang audit. Frontend chỉ render, không tự tính nghiệp vụ SUM/AVG/tỷ lệ.

## Chạy và build

1. Cài Python dependencies: `python -m pip install -r requirements.txt`.
2. Cài TypeScript dependencies: `cd frontend; npm ci`.
3. Dev: chạy `python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload`; terminal khác chạy `cd frontend; npm run dev`.
4. Production-like local: `cd frontend; npm run build`; sau đó chạy Uvicorn. FastAPI phục vụ `frontend/dist` tại `/` nếu tồn tại.
5. Kiểm thử: `python -m pytest`; `cd frontend; npm run build`.

`EVP_DATABASE` và `EVP_SOURCE_KEY` có thể đổi nguồn SQLite/API. Frontend không truy cập SQLite trực tiếp.

## Trạng thái và giới hạn

- Streamlit trong `app/dashboard.py` được giữ nguyên để đối chiếu; không phải backend của UI mới.
- Bộ lọc được giữ trong `sessionStorage` của cùng tab; mở tab mới là trạng thái mới. Lịch sử nghiệp vụ nằm ở SQLite.
- Upload file phải chọn lại sau reload; vì lý do bảo mật trình duyệt không thể tự khôi phục `File` object.
- API hiện chưa xác thực người dùng và chưa phân quyền theo project. Mặc định chỉ bind localhost; không expose Internet/LAN trước khi bổ sung auth và HTTPS.
- SQLite vẫn là single-writer. Nếu triển khai nhiều ingestion jobs/users, cần cơ chế serialize import hoặc chuyển PostgreSQL.
- Toàn bộ logic chart giữ ở Python để tránh sai khác nghiệp vụ giữa Streamlit và TypeScript. Khi cần tải lớn hơn, có thể tách endpoint theo từng tab và cache read model.
