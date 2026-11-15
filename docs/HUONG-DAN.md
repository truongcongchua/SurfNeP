# Hướng dẫn chạy NetJudge

NetJudge là web luyện lập trình mạng IT4062 (Chương 1–3) có chấm bài tự động. Tài liệu này gồm: cài đặt lần đầu,
dùng hằng ngày, cho người thứ hai vào, thêm bài, sửa giao diện, và xử lý lỗi thường gặp.

## 1. Cần có

| Thứ | Ghi chú |
|---|---|
| Windows 11 + **Docker Desktop** | Dùng để chạy bài nộp trong môi trường cô lập. Cần bật WSL2 (Docker Desktop tự hướng dẫn) |
| **Node.js 24** | Kiểm tra: `node --version` (cần ≥ 24 vì dùng `node:sqlite` có sẵn) |
| **Python 3** | Kiểm tra: `python --version` |
| Internet (lần đầu) | Tải image Ubuntu và gói npm. Editor Monaco cũng tải từ CDN mỗi lần mở trang bài |

## 2. Cài đặt lần đầu (làm một lần)

Mở **PowerShell** tại thư mục dự án:

```powershell
cd c:\SurfNeP\netjudge

# 1) Tạo 2 tài khoản (đổi tên và mật khẩu, mật khẩu từ 6 ký tự)
cd web
node scripts/seed.mjs ban:matkhau_cua_ban nguoikia:matkhau_cua_nguoikia
cd ..

# 2) Chạy
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Không cần tự gõ `npm install`: thư viện của dự án (Next.js, React…) nằm trong `web\node_modules`, và `start.ps1` tự tải nếu
thư mục này chưa có (ví dụ khi chép dự án sang máy khác). Node.js cài sẵn trên máy chỉ là chương trình chạy, không chứa các thư viện này.

**Dùng cmd thay cho PowerShell:** các lệnh trên chạy được y nguyên, chỉ cần bỏ các dòng chú thích bắt đầu bằng `#`, và dùng
`cd /d c:\SurfNeP\netjudge` nếu đang ở ổ đĩa khác. Mật khẩu có ký tự `& | ^ %` phải đặt trong ngoặc kép. Ngoài ra có thể chạy
thẳng `start.bat` (gõ `start`, hoặc bấm đúp trong Explorer) thay cho lệnh `powershell -ExecutionPolicy Bypass ...`.

`start.ps1` tự làm các việc sau, bạn không phải gõ riêng:
1. bật Docker Desktop nếu chưa chạy (đợi tối đa ~3 phút);
2. dựng image chấm bài `netjudge-runner:1` nếu chưa có (lần đầu mất vài phút);
3. `npm install` và `next build` nếu chưa có;
4. chạy web ở **http://localhost:3000**. Nhấn `Ctrl+C` để dừng.

> Lần đầu chạy, Windows Firewall có thể hỏi về Node.js: chọn **Private networks** để người thứ hai vào được (mục 4).

> **Xoá tài khoản thử:** trong DB đang có tài khoản `thu` (mật khẩu `thu12345`) dùng để kiểm thử. Để loại bỏ, xoá file
> `data\netjudge.db` **trước khi** chạy bước `seed.mjs` (file sẽ được tạo lại, mất lịch sử nộp thử, không ảnh hưởng gì khác).

## 3. Dùng hằng ngày

1. Chạy `powershell -ExecutionPolicy Bypass -File .\start.ps1` (giữ cửa sổ này mở).
2. Mở http://localhost:3000 và đăng nhập.
3. Vào **Study Plan → Giữa kỳ IT4062 → Bắt đầu**. Trang sẽ tính số bài mỗi ngày đến ngày thi 15/12.
4. Bấm một bài, đọc đề ở khung trái (có mục "Kiến thức nền" trỏ về lecture notes), viết code ở khung phải, bấm **Nộp bài**.
   Kéo các thanh chia giữa các khung để đổi kích thước (trang tự nhớ lại).
   Nút **Chạy thử** (cạnh Nộp bài) chỉ biên dịch và chạy test mẫu, trả kết quả nhanh và **không** tính là một lần nộp.
   Bài không có test mẫu thì chạy thử test đầu tiên. Sau khi sửa `judge/runner/`, nhớ `python judge/judge.py build`.
5. Kết quả hiện ở khung **Kết quả** dưới editor sau khoảng 5–30 giây, kèm từng test. Mở tab **Lịch sử nộp** ở khung trái
   và bấm "Xem" để nạp lại code cũ.
6. Nút mặt trời/mặt trăng ở góc phải header để chuyển **Sáng / Tối / Theo hệ thống**.

### Ý nghĩa kết quả

| Mã | Nghĩa | Thường do |
|---|---|---|
| AC | Đúng hết | |
| WA | Sai giao thức hoặc sai kết quả | Xem thông báo của test bị sai |
| CE | Lỗi biên dịch | Đọc log hiện bên dưới |
| RE | Chương trình bị crash | `SIGSEGV`, hoặc server tự thoát giữa chừng |
| TLE | Quá thời gian | Vòng lặp vô hạn, hoặc treo ở `recv` |
| NL | Server không mở cổng | Quên `listen`, hoặc cổng lấy từ `argv[1]` sai |
| BLOCKED | Một client làm treo client khác | Server chưa phục vụ đồng thời (server lặp, `recv` chặn) |
| LIMIT | Sai giới hạn N client | Kiểm tra `>=` và `>`, hoặc chưa giải phóng chỗ khi client rời |
| CV | Dùng sai kỹ thuật đề yêu cầu | Đề bắt `select()` mà bạn dùng `pthread`, hoặc ngược lại |

Quy ước chung: chương trình nhận **cổng từ `argv[1]`** (bộ chấm tự chọn cổng), không cố định `8080`. Chạy trong container
không có Internet, chỉ có `127.0.0.1`.

### Đề thi thử

Hai bài "Thi thử" có đồng hồ 90 phút (bấm **Bắt đầu tính giờ**; đồng hồ chỉ để nhắc, không chặn nộp). Chỉ các test mẫu hiện chi tiết,
các test còn lại chỉ báo đúng/sai, giống đề thi thật. Nên làm sau khi xong khoảng 70% plan.

## 4. Cho người thứ hai vào (qua Tailscale)

Hai máy ở mạng khác nhau nên dùng Tailscale (miễn phí, không mở cổng ra Internet):

1. Cả hai cài https://tailscale.com/download và **đăng nhập cùng một tài khoản** (hoặc chia sẻ máy qua *Share*).
2. Trên máy chạy server, xem tên máy trong ứng dụng Tailscale (ví dụ `desktop-abc`) hoặc chạy `tailscale ip -4`.
3. Người kia mở `http://desktop-abc:3000` (hoặc `http://<IP tailscale>:3000`) và đăng nhập bằng tài khoản của mình.

Máy chạy server phải **bật và đang chạy `start.ps1`** thì người kia mới dùng được.
Nếu hai người ở cùng một mạng Wi-Fi, dùng thẳng `http://<IP LAN của máy>:3000` cũng được.

## 5. Chấm bằng dòng lệnh (không cần web)

Hữu ích khi muốn thử nhanh một file `.c` bất kỳ:

```powershell
python judge/judge.py run problems/chat-select C:\duong\dan\bai.c   # chấm một bài nộp
python judge/judge.py selftest                                      # kiểm tra toàn bộ ngân hàng bài
python judge/judge.py build                                         # dựng lại image sau khi sửa judge/runner/
```

## 6. Thêm hoặc sửa bài

Mỗi bài là một thư mục trong `problems/<id>/` (xem [README.md](../README.md) để biết cấu trúc). Web đọc thẳng từ thư mục này,
**chỉ cần tải lại trang**, không cần build lại. Để bài xuất hiện trong plan, thêm một dòng vào `plans/giua-ky.yaml`.

Quy tắc: mỗi bài mới phải có `solution.c` và ít nhất một `wrong/*.c`, rồi chạy
`python judge/judge.py selftest problems/<id>`. Lời giải mẫu phải AC và mọi lời giải sai phải trượt.

Khi sửa file trong `judge/runner/` (thư viện test hoặc runner), nhớ chạy `python judge/judge.py build` rồi mới chấm lại.

## 7. Sửa giao diện web

`start.ps1` chạy web ở **chế độ production** (`next start`): nó dùng bản đã build sẵn trong `web\.next`. Vì vậy sửa code
trong `web\` (giao diện, trang, component) **không tự hiện ra**. Có hai cách làm việc:

### Cách A: chế độ dev (khi đang sửa giao diện liên tục)

```powershell
# Dừng start.ps1 trước (Ctrl+C), rồi:
cd c:\SurfNeP\netjudge\web
npm run dev
```

Mở http://localhost:3000. Mỗi lần lưu file, trang tự cập nhật, không cần build. Chế độ dev chậm hơn một chút ở lần mở
đầu mỗi trang, và **không** tự bật Docker: nếu muốn nộp bài, mở Docker Desktop trước.

### Cách B: build lại rồi chạy production (khi sửa xong, dùng hằng ngày)

```powershell
# 1) Dừng server đang chạy: Ctrl+C trong cửa sổ start.ps1
# 2) Build lại
cd c:\SurfNeP\netjudge\web
npx next build
# 3) Chạy lại
cd ..
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

> **Luôn dừng server trước khi build.** Build trong lúc server đang chạy sẽ ghi đè `web\.next` dưới chân server cũ, làm
> trang báo *"Application error: a server-side exception"*, và có thể làm build lỗi *"database is locked"*.

Ghi chú về giao diện:
- Dùng **Tailwind CSS v4 + shadcn/ui** (component trong `web\components\ui\`), icon **lucide-react**, chế độ sáng/tối bằng
  **next-themes**. Màu sắc định nghĩa một chỗ ở đầu `web\app\globals.css` (khối `:root` và `:root[data-theme="dark"]`).
- Thêm component shadcn mới: `cd web; npx shadcn@latest add <tên>` (ví dụ `tabs`, `table`, `tooltip`).
- Dữ liệu đọc từ SQLite là object đặc biệt; trước khi truyền cho Client Component (file có `"use client"`), chép thành
  object thường: `rows.map((r) => ({ ...r }))`.

## 8. Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `start.ps1` báo "running scripts is disabled" | Chạy bằng `powershell -ExecutionPolicy Bypass -File .\start.ps1` |
| `The argument '.\start.ps1' ... does not exist` | Đang đứng sai thư mục (thường là `web\`). `start.ps1` nằm ở `c:\SurfNeP\netjudge`: chạy `cd c:\SurfNeP\netjudge` trước |
| Trang báo *"Application error: a server-side exception"* | Thường do đã build lại trong lúc server đang chạy: dừng server (`Ctrl+C`), `cd web; npx next build`, rồi chạy lại `start.ps1` (mục 7). Nếu vẫn lỗi, đọc dòng `Error:` trong cửa sổ server |
| Sửa code giao diện mà trang không đổi | `start.ps1` chạy bản đã build: build lại (mục 7, cách B) hoặc dùng `npm run dev` (cách A) |
| `next build` báo "database is locked" | Server đang chạy giữ file `data\netjudge.db`. Dừng server rồi build lại |
| Nộp bài mãi ở "Chờ chấm" hoặc ra **IE** | Docker chưa chạy: mở Docker Desktop, đợi biểu tượng xanh rồi nộp lại. Xem log ở cửa sổ `start.ps1` |
| `failed to connect to the docker API` | Docker Desktop chưa khởi động xong. Đợi 1–2 phút hoặc mở lại Docker Desktop |
| "Bạn còn bài đang chờ chấm" | Mỗi người tối đa 2 bài đang chờ. Đợi kết quả rồi nộp tiếp |
| Cổng 3000 đang bị chiếm | Dừng chương trình đang dùng cổng 3000, hoặc đổi số cổng trong `start.ps1` và `web/package.json` |
| Người kia không vào được | Kiểm tra: server đang chạy; cả hai Tailscale đều "Connected"; Firewall cho Node.js trên Private network |
| Quên mật khẩu | `cd web; node scripts/seed.mjs ten:matkhau_moi` (ghi đè mật khẩu của tên đó) |
| Trang bài không hiện editor | Cần Internet để tải Monaco; kiểm tra mạng rồi tải lại trang |
| Test chập chờn lúc đúng lúc sai | Máy đang quá tải (ví dụ đang build): đóng bớt ứng dụng nặng rồi nộp lại, và báo tôi nếu vẫn lặp lại |
| Muốn dừng hẳn | `Ctrl+C` trong cửa sổ `start.ps1`; Docker Desktop có thể để chạy hoặc thoát tuỳ bạn |

## 9. Dữ liệu nằm ở đâu

| Thứ | Vị trí |
|---|---|
| Tài khoản, bài đã nộp, tiến độ | `data\netjudge.db` (SQLite). **Sao chép file này để sao lưu** |
| Đề bài, test, lời giải mẫu | `problems\` (đã nằm trong Git) |
| Study plan | `plans\giua-ky.yaml` |
| Bộ chấm | `judge\` |
| Giao diện web | `web\` |
