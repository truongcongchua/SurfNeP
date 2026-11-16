# SurfNeP — Online judge cho IT4062 (Thực hành Lập trình mạng)

Bộ chấm tự động kiểu LeetCode/HUSTack cho bài **server/client socket bằng C**.
Bài nộp được biên dịch và chạy trong container Docker cô lập (Ubuntu 22.04, không có mạng ngoài,
giới hạn tiến trình/bộ nhớ). Kịch bản Python đóng vai client để chấm server.

## Dùng ngay (cần Docker Desktop đang chạy)

```bash
python judge/judge.py ensure                                  # dựng image nếu thiếu/cũ (tag theo mã băm judge/runner)
python judge/judge.py run problems/chat-select bai_cua_toi.c  # chấm
python judge/judge.py selftest                                # kiểm tra bộ test
```

## Verdict

| Mã | Ý nghĩa |
|---|---|
| AC | Đúng tất cả test |
| WA | Sai giao thức / sai kết quả |
| CE | Lỗi biên dịch |
| RE | Server crash (SIGSEGV…) hoặc thoát giữa chừng |
| TLE | Quá thời gian |
| OLE | In quá nhiều output (một tệp vượt 16 MB) |
| NL | Server không listen trên cổng được giao |
| BLOCKED | Một client làm treo client khác (server chưa phục vụ đồng thời) |
| LIMIT | Sai giới hạn N client |
| CV | Dùng sai kỹ thuật đề yêu cầu (ví dụ đề bắt `select()` mà dùng `pthread`) |

## Kiểu bài (`type` trong meta.yaml)

| type | Chấm thế nào |
|---|---|
| `server` | Chạy bài nộp với `args` (`{port}` được thay), kịch bản Python đóng vai client. `protocol: udp` cho server UDP |
| `client` | Kịch bản dựng server giả (`ctx.mock_server()` cho TCP, `ctx.mock_udp_server()` cho UDP với `protocol: udp`), chạy bài nộp bằng `ctx.run_client(...)`, cấp stdin và kiểm tra stdout kịp thời bằng `cli.expect_stdout(...)` |
| `stdio` | `tests/*.in` → so với `tests/*.out` (sinh `.out` bằng `judge.py genout`) |
| `function` | Như stdio, nhưng biên dịch kèm `tests/harness.c`; bài nộp chỉ viết hàm, không viết `main` |

Tuỳ chọn khác: `constraints.require_any` / `constraints.forbid` (kiểm tra symbol trong binary),
`hide_details: true` (đề thi: chỉ test `@sample` hiện chi tiết), `hosts.txt` (tên miền giả cho bài DNS),
`files/` (chép vào thư mục chạy của mỗi test).

## Cấu trúc một bài

```
problems/<id>/
  meta.yaml       # title, difficulty, chapter, topics, prerequisites, ref, type, args, constraints
  statement.md    # đề bài
  starter.c       # code khung
  solution.c      # lời giải mẫu — selftest yêu cầu AC
  wrong/*.c       # lời giải sai có chủ đích — selftest yêu cầu KHÔNG AC
  mutants.yaml    # bản sai sinh tự động từ solution.c (thay chuỗi) — selftest yêu cầu KHÔNG AC
  tests/test_*.py # kịch bản chấm (type: server/client) hoặc tests/*.in + *.out (type: stdio)
  tests/gen.py    # (stdio) sinh tests/g_*.in + oracle Python đối chiếu với solution.c
  files/          # tệp được chép vào thư mục chạy (ví dụ accounts.txt)
```

Viết test bằng `judge/runner/njlib.py`: `ctx.connect()`, `send_line`, `send_slowly`, `send_chunks`, `reset()` (RST),
`shutdown_write()`, `expect_line`, `expect_silence`, `expect_closed`, `ctx.rng` (ngẫu nhiên có seed), `ctx.zombies()`,
`with ctx.verdict(BLOCKED): ...`, decorator `@sample`, `@group("edge")`, `@cases(...)`, `@timeout(15)`,
`@args("{port}", "3")`, `@expects_exit`. Bộ test dùng chung: `judge/runner/suites.py`, `suite_telnet.py`, `suite_chat.py`.
Bài nộp chạy với giới hạn 256 file descriptor, 128 tiến trình, 512 MB.

**Quy tắc:** thiết kế test theo [docs/TEST-DESIGN.md](docs/TEST-DESIGN.md); mỗi bài mới phải có `solution.c`, ít nhất
một `wrong/*.c` và `mutants.yaml`, và `selftest` phải xanh (không bản sai nào sống sót).

Hướng dẫn chạy đầy đủ: [docs/HUONG-DAN.md](docs/HUONG-DAN.md).

## Web (thư mục `web/`)

Next.js + SQLite (`node:sqlite` có sẵn trong Node 24, dữ liệu ở `data/netjudge.db`). Bài và plan đọc thẳng từ
`problems/` và `plans/`, nên thêm bài chỉ cần thêm thư mục rồi tải lại trang.

```powershell
.\start.ps1                                              # bật Docker, build nếu cần, chạy http://localhost:3000
cd web; node scripts/seed.mjs ten1:matkhau1 ten2:matkhau2   # tạo / đổi mật khẩu 2 tài khoản (mật khẩu ≥ 6 ký tự)
cd web; npm run dev                                          # khi sửa giao diện: tự cập nhật, không cần build
```

`start.ps1` chạy bản production đã build sẵn: sau khi sửa code trong `web/`, **dừng server rồi mới** `npx next build`
(xem mục "Sửa giao diện web" trong [docs/HUONG-DAN.md](docs/HUONG-DAN.md)).

**Cho người thứ hai truy cập:** cài [Tailscale](https://tailscale.com/download) trên cả hai máy, đăng nhập cùng một
tài khoản, rồi mở `http://<tên-máy-hoặc-IP-tailscale>:3000`. Không cần mở cổng ra Internet. Máy chạy server phải bật.

Mỗi người tối đa 2 bài đang chờ chấm. Hàng đợi chạy song song (số lượt tính theo CPU/RAM của Docker, tối đa 6) (chỉnh bằng biến `NJ_WORKERS`; đặt `NJ_WORKERS=1` nếu muốn chấm tuần tự).

Bài nộp chạy bằng user `sandbox` riêng; đề, test và đáp án nằm trong `/judge` (chỉ root của runner đọc được).

## Mở cho nhiều người dùng (web)

Web cho phép **đăng ký mở** tại `/register` (tên `a-z0-9_` 3–20 ký tự, mật khẩu ≥ 8), như LeetCode.

| Biến môi trường | Tác dụng |
|---|---|
| `NJ_SIGNUP=0` | Tắt hẳn đăng ký |
| `NJ_INVITE_CODE=<mã>` | Đăng ký phải nhập mã mời (đóng cửa tạm thời) |
| `NJ_HTTPS=1` | Cookie phiên có cờ `secure` — bật khi chạy sau HTTPS |
| `NJ_TRUST_PROXY=1` | Lấy IP thật từ `X-Forwarded-For` — chỉ bật khi đứng sau reverse proxy (Caddy/Nginx) |

Giới hạn tự động: đăng nhập sai 5 lần/15 phút/tên (20 lần/IP) thì khoá tạm; 5 lượt đăng ký/giờ/IP;
nộp bài 1 lượt/10 giây và 60 lượt/giờ/người, tối đa 2 bài chờ chấm; chạy thử 1 lượt/3 giây; mã nguồn ≤ 100 KB.

Quản trị: `node scripts/seed.mjs --admin ten:matkhau` tạo/đổi mật khẩu và cấp quyền admin; admin vào `/admin`
(menu avatar → Quản trị) để xem người dùng, khoá/mở khoá, xoá. Sau khi cập nhật code cần `npx next build` lại
trước khi chạy `start.ps1` (script chỉ build khi chưa có `.next`).

**Hàng đợi chấm song song:** web chấm đồng thời tối đa `NJ_WORKERS` bài (mặc định = min(6, số CPU của Docker − 1, 75% RAM của Docker / 512 MB), đọc từ `docker info` lúc khởi động; mỗi bài một
container 1 CPU / 512 MB). "Chạy thử" được ưu tiên hơn bài nộp khi có chỗ trống; trang bài hiện "vị trí trong hàng đợi".

**Chạy ổn định trên một máy Windows:** `start.ps1` dùng bản build (tự build lại khi mã nguồn mới hơn) và tự chạy lại server nếu sập.
Sao lưu: tác vụ Task Scheduler `NetJudge-Backup` chạy `web/scripts/backup.mjs` lúc 3:00 sáng mỗi ngày (chạy bù nếu máy tắt lúc đó),
lưu ở `backups/`, giữ 14 bản. Khôi phục: dừng server rồi chép một bản `backups/netjudge-*.db` đè lên `data/netjudge.db`
(xoá `netjudge.db-wal` và `netjudge.db-shm` kèm theo).
Mở ra internet miễn phí: `tailscale funnel 3000`, đặt `NJ_HTTPS=1` và `NJ_TRUST_PROXY=1` trước khi chạy `start.ps1`.
