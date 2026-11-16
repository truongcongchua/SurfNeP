import os
import re
import struct
import time

from njlib import Fail, WA, cases, group, sample, timeout

LINE_RE = re.compile(r"^127\.0\.0\.1 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (.*)$")


def record(mssv, name, y, m, d, gpa100):
    nb = name.encode()
    return struct.pack(">IB", mssv, len(nb)) + nb + struct.pack(">HBBH", y, m, d, gpa100)


def log_tail(ctx):
    """Các dòng log (bỏ phần IP + thời gian, đã kiểm tra định dạng)."""
    path = os.path.join(ctx.workdir, "sv_log.txt")
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8", errors="replace").read().splitlines():
        m = LINE_RE.match(line)
        if not m:
            raise Fail(WA, f"dòng log sai định dạng: {line!r}")
        out.append(m.group(1))
    return out


def expect_log(ctx, want, timeout=1.5):
    deadline = time.monotonic() + timeout
    got = []
    while time.monotonic() < deadline:
        got = log_tail(ctx)
        if got == want:
            return
        time.sleep(0.05)
    raise Fail(WA, f"log (bỏ IP và thời gian) là {got}, mong đợi {want}")


A = (20201234, "Nguyễn Văn A", 2002, 4, 10, 399)
B = (20205678, "Tran Van B", 2002, 8, 18, 350)


@sample
def test_one_record(ctx):
    """Một bản ghi hợp lệ"""
    c = ctx.connect()
    c.send(record(*A))
    c.expect_line("OK")
    expect_log(ctx, ["20201234 Nguyễn Văn A 2002-04-10 3.99"])


@sample
def test_two_records_coalesced(ctx):
    """Hai bản ghi dính trong một lần gửi"""
    c = ctx.connect()
    c.send(record(*A) + record(*B))
    c.expect_line("OK")
    c.expect_line("OK")
    expect_log(ctx, ["20201234 Nguyễn Văn A 2002-04-10 3.99", "20205678 Tran Van B 2002-08-18 3.50"])


@group("stream")
def test_byte_by_byte(ctx):
    """Bản ghi đến từng byte"""
    c = ctx.connect()
    c.send_slowly(record(*B), chunk=1, delay=0.01)
    c.expect_line("OK")
    expect_log(ctx, ["20205678 Tran Van B 2002-08-18 3.50"])


@group("edge")
def test_gpa_format(ctx):
    """Định dạng điểm: 4.00, 0.05, 0.00; mssv lớn"""
    c = ctx.connect()
    for r in [(4294967295, "Max", 1999, 12, 31, 400), (1, "Le Thi C", 2003, 1, 1, 5),
              (7, "Zero", 2000, 2, 29, 0)]:
        c.send(record(*r))
        c.expect_line("OK")
    expect_log(ctx, ["4294967295 Max 1999-12-31 4.00", "1 Le Thi C 2003-01-01 0.05",
                     "7 Zero 2000-02-29 0.00"])


@group("edge")
def test_long_name(ctx):
    """Tên dài 100 byte"""
    c = ctx.connect()
    name = "N" * 100
    c.send(record(42, name, 2001, 6, 15, 321))
    c.expect_line("OK")
    expect_log(ctx, [f"42 {name} 2001-06-15 3.21"])


@group("basic")
def test_invalid_closes(ctx):
    """Bản ghi sai (gpa 401, tháng 13, tên rỗng) thì ERROR và đóng; client sau vẫn được phục vụ"""
    # name_len = 0: chỉ gửi 5 byte đầu (server dừng đọc ngay ở đây, không để dư byte chưa đọc)
    bads = [record(1, "X", 2000, 1, 1, 401), record(1, "X", 2000, 13, 1, 100), struct.pack(">IB", 1, 0)]
    for bad in bads:
        c = ctx.connect()
        c.send(record(*A))
        c.expect_line("OK")
        c.send(bad)
        c.expect_line("ERROR")
        c.expect_closed()
    d = ctx.connect()
    d.send(record(*B))
    d.expect_line("OK")
    expect_log(ctx, ["20201234 Nguyễn Văn A 2002-04-10 3.99"] * 3 + ["20205678 Tran Van B 2002-08-18 3.50"])


@group("basic")
def test_stdout_too(ctx):
    """Dòng log cũng được in ra màn hình"""
    c = ctx.connect()
    c.send(record(*B))
    c.expect_line("OK")
    time.sleep(0.2)
    out = ctx.server_stdout()
    if "20205678 Tran Van B 2002-08-18 3.50" not in out:
        raise Fail(WA, f"không thấy dòng log trên stdout (nhớ fflush(stdout)); stdout: {out[-300:]!r}")


# ======================= phần mở rộng (thiết kế lại) =======================

def fmt(r):
    mssv, name, y, m, d, g = r
    return f"{mssv} {name} {y:04d}-{m:02d}-{d:02d} {g // 100}.{g % 100:02d}"


def random_record(rng):
    name = "".join(rng.choice("abcdefghij XYZ") for _ in range(rng.randint(1, 30))).strip() or "X"
    return (rng.randrange(1 << 32), name, rng.randint(1990, 2010), rng.randint(1, 12), rng.randint(1, 31),
            rng.randint(0, 400))


@group("edge")
@cases((1, 1), (12, 31), (2, 29), (6, 30), title="Ngày hợp lệ ở biên: tháng {0}, ngày {1}")
def test_valid_date_edges(ctx, m, d):
    c = ctx.connect()
    r = (5, "Bien", 2004, m, d, 200)
    c.send(record(*r))
    c.expect_line("OK")
    expect_log(ctx, [fmt(r)])


@group("edge")
@cases(("tháng 0", (1, "X", 2000, 0, 1, 100)), ("tháng 13", (1, "X", 2000, 13, 1, 100)),
       ("ngày 0", (1, "X", 2000, 5, 0, 100)), ("ngày 32", (1, "X", 2000, 5, 32, 100)),
       ("gpa 401", (1, "X", 2000, 5, 5, 401)), ("gpa 65535", (1, "X", 2000, 5, 5, 65535)),
       ("tháng 255", (1, "X", 2000, 255, 5, 100)),
       title="Bản ghi sai ({0}): ERROR rồi đóng, không ghi log")
def test_invalid_field(ctx, label, r):
    c = ctx.connect()
    c.send(record(*r))
    c.expect_line("ERROR")
    c.expect_closed()
    expect_log(ctx, [], timeout=0.3)


@group("edge")
@cases(101, 200, 255, title="name_len = {0} (> 100): ERROR rồi đóng")
def test_name_len_too_big(ctx, n):
    c = ctx.connect()
    c.send(struct.pack(">IB", 9, n))
    c.expect_line("ERROR")
    c.expect_closed()


@group("edge")
def test_extreme_values(ctx):
    """mssv 0, tên 1 byte, năm 0 / 999 / 65535, gpa 0 và 400"""
    c = ctx.connect()
    rs = [(0, "a", 0, 1, 1, 0), (1, "b", 999, 1, 1, 400), (2, "c", 65535, 12, 31, 1), (3, "d", 2024, 7, 7, 10)]
    for r in rs:
        c.send(record(*r))
        c.expect_line("OK")
    expect_log(ctx, [fmt(r) for r in rs])


@group("basic")
def test_utf8_and_spaces_in_name(ctx):
    """Tên UTF-8 nhiều byte, có dấu cách (100 byte UTF-8)"""
    c = ctx.connect()
    name = ("Đặng Thị Hiền " * 10).encode()[:100].decode(errors="ignore")
    r = (77, name, 2003, 3, 3, 333)
    c.send(record(*r))
    c.expect_line("OK")
    expect_log(ctx, [fmt(r)])


@group("basic")
def test_log_is_appended(ctx):
    """Tệp log đã có sẵn nội dung: phải ghi NỐI TIẾP, không ghi đè"""
    path = os.path.join(ctx.workdir, "sv_log.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("127.0.0.1 2020-01-01 00:00:00 1 Cu 2000-01-01 1.00\n")
    os.chmod(path, 0o666)
    c = ctx.connect()
    c.send(record(*B))
    c.expect_line("OK")
    expect_log(ctx, ["1 Cu 2000-01-01 1.00", "20205678 Tran Van B 2002-08-18 3.50"])


@group("stream")
def test_random_fragments(ctx):
    """60 bản ghi ngẫu nhiên cắt thành mảnh 1–9 byte"""
    rng = ctx.rng
    rs = [random_record(rng) for _ in range(60)]
    c = ctx.connect()
    c.send_chunks(b"".join(record(*r) for r in rs), rng, 1, 9, delay=0)
    for _ in rs:
        c.expect_line("OK", timeout=2)
    expect_log(ctx, [fmt(r) for r in rs], timeout=2)


@group("robust")
def test_close_mid_record(ctx):
    """Client đóng giữa bản ghi (sau mssv / giữa tên / thiếu 1 byte cuối): không ghi log, client sau vẫn được phục vụ"""
    full = record(*A)
    for cut in (3, 7, len(full) - 1):
        c = ctx.connect()
        c.send(full[:cut])
        c.close()
        time.sleep(0.05)
    d = ctx.connect()
    d.send(record(*B))
    d.expect_line("OK")
    expect_log(ctx, ["20205678 Tran Van B 2002-08-18 3.50"])


@group("robust")
def test_reset_after_records(ctx):
    """Client dồn 100 bản ghi rồi RST: server không chết, vẫn phục vụ client sau"""
    c = ctx.connect()
    c.send(record(*A) * 100)
    c.reset()
    time.sleep(0.3)
    ctx.expect_alive("sau khi client đóng đột ngột")
    d = ctx.connect()
    d.send(record(*B))
    d.expect_line("OK")


@group("stress")
@timeout(15)
def test_300_records_fd_leak(ctx):
    """300 bản ghi trên một kết nối (mở log mà quên fclose là hết 256 fd)"""
    rng = ctx.rng
    rs = [random_record(rng) for _ in range(300)]
    c = ctx.connect()
    c.send(b"".join(record(*r) for r in rs))
    for _ in rs:
        c.expect_line("OK", timeout=2)
    expect_log(ctx, [fmt(r) for r in rs], timeout=2)


@group("stress")
@timeout(20)
def test_300_clients(ctx):
    """300 client lần lượt, mỗi client một bản ghi"""
    for i in range(300):
        c = ctx.connect(name=f"C{i}")
        c.send(record(i, "N", 2000, 1, 1, 100))
        c.expect_line("OK", timeout=2)
        c.close()
        ctx.close_quietly(c)
    expect_log(ctx, [f"{i} N 2000-01-01 1.00" for i in range(300)], timeout=2)
