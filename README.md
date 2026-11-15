# netjudge — Online judge cho IT4062 (Thực hành Lập trình mạng)

Bộ chấm tự động kiểu LeetCode/HUSTack cho bài **server/client socket bằng C**.
Bài nộp được biên dịch và chạy trong container Docker cô lập (Ubuntu 22.04, không có mạng ngoài,
giới hạn tiến trình/bộ nhớ). Kịch bản Python đóng vai client để chấm server.

## Dùng ngay (cần Docker Desktop đang chạy)

```bash
python judge/judge.py build                                   # 1 lần
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
| NL | Server không listen trên cổng được giao |
| BLOCKED | Một client làm treo client khác (server chưa phục vụ đồng thời) |
| LIMIT | Sai giới hạn N client |
| CV | Dùng sai kỹ thuật đề yêu cầu (ví dụ đề bắt `select()` mà dùng `pthread`) |

## Kiểu bài (`type` trong meta.yaml)

| type | Chấm thế nào |
|---|---|
| `server` | Chạy bài nộp với `args` (`{port}` được thay), kịch bản Python đóng vai client. `protocol: udp` cho server UDP |
| `client` | Kịch bản dựng server giả (`ctx.mock_server()`), chạy bài nộp bằng `ctx.run_client(...)` và cấp stdin |
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
  tests/test_*.py # kịch bản chấm (type: server) hoặc tests/*.in + *.out (type: stdio)
  files/          # tệp được chép vào thư mục chạy (ví dụ accounts.txt)
```

Viết test bằng `judge/runner/njlib.py`: `ctx.connect()`, `send_line`, `send_slowly`,
`expect_line`, `expect_silence`, `expect_closed`, `with ctx.verdict(BLOCKED): ...`,
decorator `@args("{port}", "3")`, `@expects_exit`, `@sample`.

**Quy tắc:** mỗi bài mới phải có `solution.c` và ít nhất một `wrong/*.c`, và `selftest` phải xanh.

## Web (thư mục `web/`)

Next.js + SQLite (`node:sqlite` có sẵn trong Node 24, dữ liệu ở `data/netjudge.db`). Bài và plan đọc thẳng từ
`problems/` và `plans/`, nên thêm bài chỉ cần thêm thư mục rồi tải lại trang.

```powershell
.\start.ps1                                              # bật Docker, build nếu cần, chạy http://localhost:3000
cd web; node scripts/seed.mjs ten1:matkhau1 ten2:matkhau2   # tạo / đổi mật khẩu 2 tài khoản (mật khẩu ≥ 6 ký tự)
```

**Cho người thứ hai truy cập:** cài [Tailscale](https://tailscale.com/download) trên cả hai máy, đăng nhập cùng một
tài khoản, rồi mở `http://<tên-máy-hoặc-IP-tailscale>:3000`. Không cần mở cổng ra Internet. Máy chạy server phải bật.

Mỗi người tối đa 2 bài đang chờ chấm; hàng đợi chấm tuần tự để kết quả ổn định.
