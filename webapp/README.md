# Trang nhập liệu + nút "Tạo ngân sách"

Một trang web: điền thông tin dự án, bấm **Tạo ngân sách**, công cụ tự động chạy pipeline (`run.py`) và cho
tải 3 file kết quả (bản giao khách, bản phân tích nội bộ, lịch trực). Một lượt mất khoảng 45–80 giây
(trong đó 15–40 giây là bước run log mở Excel; máy không có Excel thì bước này bỏ qua và lượt chạy vẫn xong).

## Chạy

Từ `Budget_Agent/source_code/` (cài gói một lần: `pip install -r webapp/requirements.txt`; trên máy cá nhân
pip vào system site-packages bị từ chối quyền thì thêm `--user`):

```bash
python -m webapp
```

Rồi mở <http://127.0.0.1:8090/budget/> (chạy thử trên máy cá nhân: đặt `BUDGET_WEB_AUTH=off` trước, xem mục SSO). Biến môi trường, đều có mặc định:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `BUDGET_WEB_HOST` | `127.0.0.1` | Chỉ bind host này |
| `BUDGET_WEB_PORT` | `8090` | Cổng |
| `BUDGET_WEB_PREFIX` | `/budget` | Tiền tố mọi link và fetch trên trang. Reverse proxy chuyển `/budget/*` về app và bỏ tiền tố; app đăng ký route ở cả gốc (`/`) lẫn tiền tố nên mở trực tiếp không qua proxy cũng chạy. `GET /` trả 200 cho heartbeat |
| `BUDGET_WEB_RUNS` | `..\reports\web_runs` | Thư mục ghi các lượt chạy (bên trong bản đóng băng khi chạy trên Hub) |

Log ra stdout/stderr (uvicorn access log + một dòng `budget-web:` khi bắt đầu và kết thúc mỗi lượt, khi đăng nhập
thành công hoặc bị từ chối).

## Ba tab và trang kết quả

- **Nhập liệu:** form và nút Tạo ngân sách (vàng Savills, chữ đen, viền navy; hover đảo navy/vàng; disabled xám).
- **Hướng dẫn** (tab cuối)**:** các bước dùng và ý nghĩa từng trường (rút từ RUNNING.md và docs/17).
- **Kết quả** (tab thứ hai, mở tự động khi lượt chạy xong, dựng từ `summary` trong JSON của `api/runs/<id>`, `webapp/results.py`):
  - thu, chi, thặng dư/thâm hụt năm đầu của quỹ vận hành (không phải lợi nhuận Savills): từ bản ghi run_log của lượt chạy (pipeline đo bằng Excel trên
    '1. Summary'); máy không có Excel thì run_log ghi `excel_unavailable` và trang nói chưa đo được, không đoán;
  - mức dịch vụ vệ sinh và bảo vệ: sheet 'Service Levels' của bản phân tích (mức, chỉ số, percentile so với dự án
    tham chiếu);
  - so sánh với dự án tham chiếu: sheet 'Comparison' của bản phân tích, có tên hai dự án tham chiếu (mọi vai trò);
  - nút tải file. Nguồn số ghi dưới mỗi bảng. Viewer thấy đủ phần tóm tắt, chỉ bị ẩn hai file nội bộ.
  Test: `tests/test_webapp_results.py`.

## Vai trò viewer (tiêu đề `X-Hub-Role` do reverse proxy gắn)

Reverse proxy xoá mọi tiêu đề `X-Hub-Role` trình duyệt tự gửi, rồi gắn `X-Hub-Role: viewer` cho tài khoản chỉ được
xem. Với tiêu đề đó (không phân biệt hoa thường) lượt chạy chỉ trả và cho tải **bản giao khách**: hai file nội bộ
(bản phân tích, lịch trực) bị ẩn khỏi `outputs`, bị bỏ khỏi log hiển thị, và `files/<tên>` trả 403 dù đoán đúng
tên. Vắng tiêu đề hoặc giá trị khác: đủ 3 file. Thư mục chạy vẫn luôn có đủ 3 file. Hàm: `role_of`,
`visible_outputs`, `may_download`, `visible_log` trong `server.py`; test `tests/test_webapp_roles.py`.

## Đăng nhập SSO (Microsoft Entra ID)

Mặc định (`BUDGET_WEB_AUTH=sso`) trang đòi đăng nhập bằng tài khoản Microsoft của Savills và chỉ cho những email
trong danh sách vào; thiếu cấu hình thì server **không khởi động** và in tên biến còn thiếu. Trên máy cá nhân chạy
thử không cần đăng nhập: `BUDGET_WEB_AUTH=off`.

| Biến | Ý nghĩa |
|---|---|
| `BUDGET_WEB_TENANT_ID` | Tenant của Savills (`savills.com.vn` hoặc GUID) |
| `BUDGET_WEB_CLIENT_ID` | Application (client) ID của app registration |
| `BUDGET_WEB_CLIENT_SECRET` | Client secret của app registration; chỉ đặt trong biến môi trường, không ghi vào file |
| `BUDGET_WEB_PUBLIC_URL` | Địa chỉ người dùng mở, kể cả tiền tố, ví dụ `https://host:8443/budget`. Entra chỉ nhận redirect URI **https** (trừ localhost), nên trang qua proxy phải chạy https |
| `BUDGET_WEB_ALLOWED_USERS` | Email được phép, cách nhau bằng `,` hoặc `;`, không phân biệt hoa thường. Trống = không ai vào được |
| `BUDGET_WEB_SESSION_SECRET` | Khoá ký cookie phiên (8 giờ). Trống = sinh ngẫu nhiên mỗi lần khởi động, mọi người đăng nhập lại |

App registration (một lần, người quản trị Entra của Savills làm): Entra admin center → App registrations → New:
tên "PM - Budget Agent web", Supported account types: *Accounts in this organizational directory only*, Platform
**Web**, Redirect URI `<BUDGET_WEB_PUBLIC_URL>/auth/callback`; Certificates & secrets → New client secret; API
permissions giữ `User.Read` (delegated, người dùng tự chấp thuận lần đầu). Lấy Tenant ID, Client ID, secret đặt vào
biến môi trường của task chạy server.

Luồng: `GET /` chưa đăng nhập trả 200 trang đăng nhập (heartbeat vẫn đo được), API trả 401; `/auth/login` chuyển
sang Microsoft (authorization code + PKCE, thư viện MSAL); `/auth/callback` nhận id_token, đối chiếu
`preferred_username` / `email` với danh sách; `/auth/logout` xoá phiên và đăng xuất Microsoft.

## Cách hoạt động

| File | Việc |
|---|---|
| `__main__.py` | `python -m webapp`: đọc biến môi trường, kiểm tra cấu hình SSO, chạy uvicorn |
| `auth.py` | SSO Entra ID: danh sách email được phép, khởi tạo và hoàn tất auth code flow (MSAL), đăng xuất |
| `static/login.html` | Trang đăng nhập (cùng token màu), hiện lý do khi bị từ chối |
| `server.py` | FastAPI: trang, `api/defaults` (giá trị mặc định đọc từ mẫu), `api/runs` (tạo lượt), `api/runs/<id>` (trạng thái + log), `api/runs/<id>/files/<tên>` (tải file). Một lượt tại một thời điểm; bấm khi đang chạy trả 409 "đang chạy" |
| `fill_input.py` | Đọc mặc định và ghi giá trị form vào bản sao của `..\reports\Project_Budget_Input.xlsx`, **theo nhãn** cột A (`input_labels.SheetLabels`), không theo ô. Nhãn mẫu chưa có (`Budget Start Month`, `District`, `City / Province`) được thêm dưới dòng cuối |
| `run_budget.py` | Tiến trình con (`sys.executable`, cwd = `source_code`) chạy `run.main()` với mọi đường dẫn vào/ra đổi hướng về thư mục của lượt chạy bằng `verification/isolation.redirected_paths` (cơ chế sẵn có của verify.py). Không sửa `run.py` |
| `static/index.html` | Trang một màn, tiếng Việt, Arial, palette Savills (token CSS mục 8.4 của brand guide), không logo. `__PREFIX__` được server thay bằng tiền tố |

Mỗi lượt tạo một thư mục `<runs>\<yyyymmdd-hhmmss>_<tên dự án>\` chứa file nhập liệu đã điền, 3 file kết quả,
`run.log` và `run_log\` (bản ghi của pipeline). File mẫu `..\reports\Project_Budget_Input.xlsx` chỉ được đọc;
`..\reports\*.xlsx` và `..\sample_output\` không bị ghi đè.

## Trường trên trang

Quy mô (tên, quận/huyện, tỉnh/thành, diện tích đất, cây xanh, sân đường, số tầng, số tháp); bãi xe (ô tô, xe máy);
tiện ích (hồ bơi, diện tích, thể tích hồ, số cổng); tháng bắt đầu ngân sách (MM/YYYY) và tháng lập lịch trực mẫu;
cơ cấu sản phẩm 9 dòng GFA / NFA / số căn. Các trường khác của mẫu (chế độ dự án đang vận hành, phí Savills, nhóm
khách hàng nước, ESI2, dự phòng...) giữ nguyên giá trị trong file mẫu.

## Chưa làm

- Chưa có hàng đợi: một lượt tại một thời điểm.
- Các trường của chế độ dự án đang vận hành / dự án đã quản lý chưa có trên trang.
