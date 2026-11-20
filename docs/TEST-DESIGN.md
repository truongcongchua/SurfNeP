# Thiết kế test case kiểu LeetCode cho bài lập trình mạng

Tài liệu này là **chuẩn bắt buộc** khi viết/sửa test của một bài trong `problems/`. Mục tiêu: một lời giải
"gần đúng" (chạy được ví dụ nhưng sai ở biên, ở luồng TCP, ở đồng thời…) **không bao giờ AC**.

## 1. LeetCode làm gì, và ta mượn gì

| LeetCode | Áp dụng ở đây |
|---|---|
| Vài ví dụ công khai, hàng chục–hàng trăm test ẩn | 1–3 test `@sample`, còn lại ẩn; mỗi bài server/client **≥ 20 test**, bài stdio **≥ 30 test** |
| Mục **Constraints** ghi rõ biên (`1 ≤ n ≤ 10^5`…) và test bám sát biên | Đề có mục **Ràng buộc**; mỗi con số trong đó có ít nhất một test ở đúng biên (và ngay ngoài biên nếu đề định nghĩa hành vi) |
| Test sinh ngẫu nhiên + so với lời giải chuẩn | `ctx.rng` (seed cố định theo tên test) + **mô hình Python** trong test → so sánh vi sai hàng trăm thao tác |
| Test lớn để bắt thuật toán chậm (TLE) | Nhóm `stress`: MB dữ liệu, hàng nghìn lệnh, hàng chục client cùng lúc |
| Test đối kháng (anti-hash, worst case) | Nhóm `robust`: cắt vụn từng byte, dính lệnh, RST giữa chừng, client không đọc, dòng siêu dài, rò rỉ fd/zombie |
| Thêm test từ bài nộp sai mà lọt AC | **Mutation testing**: `mutants.yaml` sinh bản sai từ `solution.c`; selftest đòi mọi mutant phải trượt và in **ma trận bắt lỗi** |
| "Testcase x / y passed" + hiện input của test sai đầu tiên | Runner trả `passed/total`, thông báo của test sai đầu tiên (đề thi `hide_details` thì ẩn) |

## 2. Các nhóm test (`@group`)

Mỗi test thuộc đúng một nhóm (runner trả về trường `group`):

| Nhóm | Kiểm tra gì | Ví dụ cho bài TCP dòng lệnh |
|---|---|---|
| `sample` | Đúng ví dụ trong đề | `SET a 1` → `OK` |
| `basic` | Mỗi lệnh / mỗi nhánh của đặc tả ít nhất một lần | từng lệnh, từng mã lỗi |
| `edge` | Biên của **Ràng buộc**: rỗng, 1 phần tử, tối đa, ngay trên tối đa, N=1, N=max | key 64 ký tự, 1000 key, `N=50`, dòng rỗng |
| `stream` | TCP là **luồng byte**: một `send` ≠ một `recv` | cắt vụn ngẫu nhiên, gửi từng byte, nhiều lệnh dính nhau, `\r\n`, dòng cuối không có `\n` |
| `robust` | Server sống sót trước client xấu | đóng đột ngột (RST), `shutdown(SHUT_WR)`, rác nhị phân, dòng dài hơn bộ đệm, client không đọc |
| `concurrency` | Đồng thời / giới hạn N | client im lặng không chặn client khác, N+1 bị từ chối, chỗ được giải phóng, xen kẽ ngẫu nhiên |
| `stress` | Khối lượng / hiệu năng / rò rỉ tài nguyên | 1 MB echo, 2000 lệnh ngẫu nhiên so với mô hình, 300 lượt kết nối-ngắt (rò rỉ fd), 60 client fork (zombie) |
| `regression` | Test sinh ra để giết một mutant/bản sai cụ thể | — |

## 3. Danh sách "nguy hiểm" cho bài mạng (dùng như checklist)

**Luồng TCP**
- Tách một thông điệp thành mảnh ngẫu nhiên 1–7 byte (`send_chunks`) — bắt lỗi "một recv = một lệnh".
- Dồn 50+ lệnh trong **một** `send` — bắt lỗi chỉ xử lý lệnh đầu của bộ đệm.
- Ranh giới bộ đệm: thông điệp vắt qua byte thứ 1023/1024/4095/4096 (`buffer_boundary_sizes()`).
- `\r\n`, dòng rỗng, nhiều dấu cách, tab, dòng cuối không có `\n` rồi đóng.
- Dữ liệu chứa `0x00` — bắt `strlen`/`%s`.

**Vòng đời kết nối**
- Client đóng đột ngột bằng RST (`c.reset()`), kể cả khi server đang/sắp `send` → server không được chết vì `SIGPIPE`.
- Client `shutdown(SHUT_WR)` (half-close) rồi vẫn chờ đọc phản hồi.
- Client kết nối rồi đóng ngay không gửi gì; client gửi dở lệnh rồi đóng.
- 300 lượt kết nối-ngắt liên tiếp: bài nộp chạy với **giới hạn 256 file descriptor**, quên `close()` là hết fd → `accept` lỗi.
- Server fork: đếm zombie (`ctx.zombies()`), 60 client liên tiếp với `--pids-limit 128`.

**Đồng thời**
- Client im lặng / gửi dở lệnh / **không đọc phản hồi** (bộ đệm nhận nhỏ) không được làm treo client khác.
- N client cùng lúc, client thứ N+1, giải phóng chỗ khi rời đi bằng QUIT **và** bằng RST, N=1, N=max.
- Xen kẽ ngẫu nhiên lệnh của nhiều client, so với mô hình dùng chung.

**UDP**
- Datagram rỗng (0 byte), datagram 65507 byte (tối đa IPv4), byte `0x00`, nhiều client xen kẽ — trả lời đúng địa chỉ nguồn.
- Không có "kết nối": server không được dừng/chặn vì một client.

**stdio**
- Input rỗng, chỉ có dòng trống, không có `\n` cuối, `\r\n`, khoảng trắng thừa, số âm, số tràn kiểu, chữ lẫn số, giá trị biên (0, max, max+1).
- Test lớn (≥ 10^5 dòng) để bắt thuật toán/IO chậm.

## 4. Cách viết

### Bài server/client (`tests/test_*.py`)

```python
from njlib import sample, group, cases, args, timeout, BLOCKED

@sample
def test_vi_du(ctx): ...

@group("edge")
@cases((1,), (64,), title="Key dài {0} ký tự")      # mỗi bộ tham số là một test riêng
def test_key_len(ctx, n): ...

@group("stress")
@timeout(15)
def test_random_vs_model(ctx):
    rng = ctx.rng                                      # seed cố định theo tên test → tái lập được
    ...
```

Công cụ có sẵn trong `njlib`: `send_chunks`, `send_slowly`, `reset()`, `shutdown_write()`, `expect_lines`,
`ctx.connect(rcvbuf=...)`, `ctx.expect_alive()`, `ctx.zombies()`, `buffer_boundary_sizes()`.

### Bài stdio/function

`tests/gen.py` định nghĩa `generate(rng)` trả danh sách `(tên, input)`. Chạy:

```
python judge/judge.py gentests problems/<id>     # ghi tests/*.in rồi sinh .out từ solution.c
```

Test viết tay (`sample*.in`, test đặc biệt) giữ nguyên; `gentests` chỉ ghi đè các tệp `g_*.in/.out`.

### Mutation testing (`mutants.yaml`)

```yaml
- id: no-sigpipe
  why: Không bỏ qua SIGPIPE → chết khi client RST
  replace:
    - ["signal(SIGPIPE, SIG_IGN);", ""]
```

Mỗi cặp `[cũ, mới]` phải xuất hiện **đúng một lần** trong `solution.c` (nếu không selftest báo lỗi, tránh mutant
vô nghĩa). `python judge/judge.py selftest problems/<id>` chạy `solution.c` (phải AC), `wrong/*.c` và mọi mutant
(phải trượt), rồi in test đầu tiên bắt được từng bản sai. Mutant nào sống sót nghĩa là **thiếu test** — viết thêm
test (nhóm `regression` nếu không thuộc nhóm nào khác) cho tới khi nó chết.

## 5. Tiêu chí xong một bài

1. `selftest` xanh, kể cả `--repeat 3` (không chập chờn).
2. Mỗi nhóm `basic/edge/stream/robust/stress` (và `concurrency` nếu server đồng thời) có ít nhất 2 test.
3. ≥ 4 mutant + bản sai viết tay, tất cả bị giết.
4. Mọi yêu cầu mà test kiểm tra đều được ghi trong đề (mục **Ràng buộc** / **Bộ chấm kiểm tra**) — test
   "nguy hiểm" nhưng không bao giờ **bất ngờ**.
5. Toàn bộ lượt chấm của lời giải mẫu < 60 giây.
