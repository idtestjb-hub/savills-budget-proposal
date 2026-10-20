# Trang nhập liệu + nút "Tạo ngân sách"

Một trang web, hai luồng:
- **Lập ngân sách dự án mới:** điền thông tin dự án, bấm **Tạo ngân sách**, công cụ tự động chạy pipeline (`run.py`)
  và cho tải 3 file kết quả (bản giao khách, bản phân tích nội bộ, lịch trực). Một lượt mất khoảng 45–80 giây
  (trong đó 15–40 giây là bước run log mở Excel; máy không có Excel thì bước này bỏ qua và lượt chạy vẫn xong).
- **Review ngân sách dự án đang vận hành:** tải lên file ngân sách đã duyệt năm ngoái (.xlsx form Savills), điền
  Tỉnh / thành phố và vài dữ kiện file không có, bấm **Tạo ngân sách năm mới**: công cụ chạy `review.py` (RUNNING.md
  mục 2d) và cho xem duyệt vs công cụ từng dòng. Khoảng 60–90 giây; **cần Excel** (sheet Review); máy không có Excel
  thì lượt dừng sau pipeline và trang nói rõ.
- **Lịch sử dự án:** mọi lượt trong thư mục runs, với **Clone** (điền sẵn form từ lượt cũ) và **Gen budget for new
  year** (bản giao của lượt cũ làm ngân sách năm ngoái).

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

## Bốn tab và trang kết quả

- **Nhập liệu:** nhóm nút chọn chế độ *Lập ngân sách dự án mới* / *Review ngân sách dự án đang vận hành*, form của chế
  độ đang chọn, và nút chính (vàng Savills, chữ đen, viền navy; hover đảo navy/vàng; disabled xám): *Tạo ngân sách*
  hoặc *Tạo ngân sách năm mới*.
- **Lịch sử dự án** (tab thứ ba, `api/history`, `webapp/history.py`): bảng mọi lượt trong thư mục runs kể cả lượt của
  phiên server trước (đọc từ đĩa: `web_meta.json` server ghi khi bắt đầu và khi xong; lượt cũ hơn suy từ run_log json
  / review_summary.json và tên thư mục): dự án, năm NS (lượt review: `2026 → 2027`), chế độ Mới / Review, thời điểm,
  người chạy (X-Hub-User hoặc email đăng nhập), trạng thái, link tải file (theo vai trò), và ba nút:
  *Xem* (mở tab Kết quả của lượt đó), *Clone* (`api/runs/<id>/input`: đọc form `Project_Budget_Input.xlsx` của lượt
  theo nhãn, điền vào tab Nhập liệu chế độ dự án mới; lượt review thì đọc form trong `input\`), *Gen budget for new
  year* (chuyển sang chế độ Review, nguồn = bản giao của lượt, các ô dữ kiện điền sẵn từ form của lượt; Tỉnh / thành
  phố trống thì trang bắt điền).
- **Hướng dẫn** (tab cuối)**:** các bước dùng và ý nghĩa từng trường (rút từ RUNNING.md và docs/17).
- **Kết quả** (tab thứ hai, mở tự động khi lượt chạy xong, dựng từ `summary` trong JSON của `api/runs/<id>`, `webapp/results.py`):
  - thu, chi, thặng dư/thâm hụt năm đầu của quỹ vận hành (không phải lợi nhuận Savills): từ bản ghi run_log của lượt chạy (pipeline đo bằng Excel trên
    '1. Summary'); máy không có Excel thì run_log ghi `excel_unavailable` và trang nói chưa đo được, không đoán;
  - mức dịch vụ vệ sinh và bảo vệ: sheet 'Service Levels' của bản phân tích (mức, chỉ số, percentile so với dự án
    tham chiếu);
  - so sánh với dự án tham chiếu: sheet 'Comparison' của bản phân tích, có tên hai dự án tham chiếu (mọi vai trò);
  - nút tải file. Nguồn số ghi dưới mỗi bảng. Viewer thấy đủ phần tóm tắt, chỉ bị ẩn hai file nội bộ.
  Test: `tests/test_webapp_results.py`.
- **Kết quả của lượt review** (`results.review_summary`, từ `review_summary.json` + `review_notes.json` trong thư mục
  lượt): bảng Tổng thu / Tổng chi / Thặng dư cho từng quỹ, "Duyệt NS <năm cũ> (quy đổi)" vs "Công cụ NS <năm mới>",
  chênh và % (triệu VND/năm, cơ sở VAT của bản giao); số dòng so sánh, mã không có trên form 2027, chưa có phương
  pháp; tám phép đối chiếu KHỚP / LỆCH (công cụ = bản giao, duyệt = file nguồn, cho R và E của hai quỹ); 10 dòng lệch
  lớn nhất với "cách công cụ ra số"; ghi chú nhập (để trống PM điền, không có trên form, cần PM xác nhận, từ dữ kiện);
  nút tải file. Phép đối chiếu lệch (review.py trả 1) vẫn là lượt *xong*, trạng thái ghi rõ LỆCH.
  Mọi lượt còn có mục "Điều chỉnh ngân sách trong bản giao" nhắc cách dùng sheet 4. Điều chỉnh (số lượng / đơn giá /
  trượt giá). Test: `tests/test_webapp_review.py`.

## Chế độ Review: cách chạy

`POST api/reviews` (multipart): `prior` = file .xlsx tải lên **hoặc** `source_run` = id lượt cũ; `facts` = JSON các ô
dữ kiện (`city` bắt buộc; `district`, `tower_count`, `floor_count`, `gate_count`, `has_pool`, `pool_volume`,
`car_slots`, `moto_slots`; ô trống không thành dữ kiện, review_import ghi 0 và liệt kê). Server ghi file vào
`<lượt>\prior\`, dữ kiện thành `<lượt>\facts.json` theo nhãn Project Info (`FACT_LABELS` trong `server.py`), rồi
chạy `webapp/review_run.py --prior ... --facts ... --workdir <lượt> [--recalc]` trong tiến trình con. `review.run`
viết form vào `input\`, ba file kết quả vào `run\`, `deliverable_recalc.xlsx`, `review_summary.md/json`;
`review_run.py` ghi thêm `review_notes.json` (ghi chú nhập, những gì đã điền).

`--recalc` (Gen budget for new year): bản giao do openpyxl ghi không có giá trị cache nên review_import đọc thẳng
bị dừng "no month columns"; Excel tính lại một bản sao (`prior_recalc.xlsx`) trước, rồi đọc bản đó. Kiểm tra
20/10/2026 trên bản giao của một lượt mẫu: đọc đủ hai sheet quỹ, R/E khớp dòng tổng, tên dự án, năm, sheet
0. Info (ba sản phẩm kèm đơn giá); 8/8 phép đối chiếu khớp.

Cùng một hàng đợi với lượt thường: đang có lượt chạy (bất kể loại) thì `api/reviews` và `api/runs` trả 409, vì hai
pipeline dùng chung file tạm của lịch trực.

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
| `server.py` | FastAPI: trang, `api/defaults` (giá trị mặc định đọc từ mẫu), `api/runs` (tạo lượt dự án mới), `api/reviews` (tạo lượt review), `api/runs/<id>` (trạng thái + log + tóm tắt; lượt của phiên server trước được dựng lại từ thư mục), `api/runs/<id>/input` (giá trị form của lượt, cho Clone và Gen), `api/runs/<id>/files/<tên>` (tải file), `api/history` (danh sách lượt). Một lượt tại một thời điểm; bấm khi đang chạy trả 409 |
| `history.py` | Đọc thư mục runs cho tab Lịch sử: `outputs_of` (3 file kết quả ở thư mục lượt hoặc `run\`), `describe` / `scan` (loại, dự án, năm, trạng thái từ `web_meta.json` hoặc suy từ file), `write_meta`, `read_log` |
| `review_run.py` | Tiến trình con của lượt review: Excel tính lại bản giao lượt cũ khi `--recalc`, gọi `review.run`, ghi `review_notes.json` |
| `fill_input.py` | Đọc mặc định và ghi giá trị form vào bản sao của `..\reports\Project_Budget_Input.xlsx`, **theo nhãn** cột A (`input_labels.SheetLabels`), không theo ô. Nhãn mẫu chưa có (`Budget Start Month`, `District`, `City / Province`) được thêm dưới dòng cuối |
| `run_budget.py` | Tiến trình con (`sys.executable`, cwd = `source_code`) chạy `run.main()` với mọi đường dẫn vào/ra đổi hướng về thư mục của lượt chạy bằng `verification/isolation.redirected_paths` (cơ chế sẵn có của verify.py). Không sửa `run.py` |
| `static/index.html` | Trang một màn, tiếng Việt, Arial, palette Savills (token CSS mục 8.4 của brand guide), không logo. `__PREFIX__` được server thay bằng tiền tố |

Mỗi lượt tạo một thư mục `<runs>\<yyyymmdd-hhmmss>_<tên dự án>\` (lượt review: `..._review-<tên file hoặc dự án>`)
chứa `web_meta.json`, `run.log`, và: lượt dự án mới = file nhập liệu đã điền, 3 file kết quả, `run_log\`; lượt review
= `prior\` hoặc `prior_recalc.xlsx`, `facts.json`, `input\`, `run\` (3 file), `deliverable_recalc.xlsx`,
`review_summary.md/json`, `review_notes.json`. File mẫu `..\reports\Project_Budget_Input.xlsx` chỉ được đọc;
`..\reports\*.xlsx` và `..\sample_output\` không bị ghi đè.

## Trường trên trang

Quy mô (tên, quận/huyện, tỉnh/thành, diện tích đất, cây xanh, sân đường, số tầng, số tháp); bãi xe (ô tô, xe máy);
tiện ích (hồ bơi, diện tích, thể tích hồ, số cổng); tháng bắt đầu ngân sách (MM/YYYY) và tháng lập lịch trực mẫu;
cơ cấu sản phẩm 9 dòng GFA / NFA / số căn. Các trường khác của mẫu (chế độ dự án đang vận hành, phí Savills, nhóm
khách hàng nước, ESI2, dự phòng...) giữ nguyên giá trị trong file mẫu.

## Chưa làm

- Chưa có hàng đợi: một lượt tại một thời điểm (cả hai loại).
- Các trường khác của chế độ dự án đang vận hành (lịch trực năm cũ từng vị trí, 12 tháng hoá đơn) chưa có trên trang;
  chế độ Review lấy lương và điện nước đã duyệt theo dòng tổng năm.
- Clone một lượt review tạo form dự án mới từ quy mô của lượt đó (không mang theo phần dự án đang vận hành).
- Lịch sử chưa có lọc, tìm kiếm hay xoá lượt.
