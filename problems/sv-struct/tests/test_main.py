import os
import re
import struct
import time

from njlib import Fail, WA, sample

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


def test_byte_by_byte(ctx):
    """Bản ghi đến từng byte"""
    c = ctx.connect()
    c.send_slowly(record(*B), chunk=1, delay=0.01)
    c.expect_line("OK")
    expect_log(ctx, ["20205678 Tran Van B 2002-08-18 3.50"])


def test_gpa_format(ctx):
    """Định dạng điểm: 4.00, 0.05, 0.00; mssv lớn"""
    c = ctx.connect()
    for r in [(4294967295, "Max", 1999, 12, 31, 400), (1, "Le Thi C", 2003, 1, 1, 5),
              (7, "Zero", 2000, 2, 29, 0)]:
        c.send(record(*r))
        c.expect_line("OK")
    expect_log(ctx, ["4294967295 Max 1999-12-31 4.00", "1 Le Thi C 2003-01-01 0.05",
                     "7 Zero 2000-02-29 0.00"])


def test_long_name(ctx):
    """Tên dài 100 byte"""
    c = ctx.connect()
    name = "N" * 100
    c.send(record(42, name, 2001, 6, 15, 321))
    c.expect_line("OK")
    expect_log(ctx, [f"42 {name} 2001-06-15 3.21"])


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


def test_stdout_too(ctx):
    """Dòng log cũng được in ra màn hình"""
    c = ctx.connect()
    c.send(record(*B))
    c.expect_line("OK")
    time.sleep(0.2)
    out = ctx.server_stdout()
    if "20205678 Tran Van B 2002-08-18 3.50" not in out:
        raise Fail(WA, f"không thấy dòng log trên stdout (nhớ fflush(stdout)); stdout: {out[-300:]!r}")
